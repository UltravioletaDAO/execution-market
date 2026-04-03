#!/usr/bin/env python3
"""
em_monitor.py — Standalone Execution Market task monitor.

Checks active tasks for new applications, submissions, expirations,
and approaching deadlines. Notifies via Telegram. No LLM inference.

Usage:
    python3 scripts/em_monitor.py              # Check once, exit
    python3 scripts/em_monitor.py --dry-run    # Print what would notify
    python3 scripts/em_monitor.py --loop 180   # Check every 180 seconds

Environment:
    TELEGRAM_BOT_TOKEN   (required for notifications)
    EM_PRIVATE_KEY        (fallback if config.json has no private_key)
    EM_API_URL            (default: https://api.execution.market)

Config:
    ~/.openclaw/skills/execution-market/config.json
    ~/.openclaw/skills/execution-market/active-tasks.json
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Third-party imports (pip install eth-account httpx)
# ---------------------------------------------------------------------------
try:
    import httpx
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    print(
        "ERROR: Missing dependencies. Install with:\n"
        "  pip install eth-account httpx",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging — minimal for cron friendliness
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [em-monitor] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("em-monitor")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "execution-market"
CONFIG_PATH = SKILL_DIR / "config.json"
TRACKER_PATH = SKILL_DIR / "active-tasks.json"
CREDENTIALS_PATH = SKILL_DIR / "credentials.json"

DEFAULT_API_URL = "https://api.execution.market"
DEFAULT_CHAIN_ID = 8453  # Base

# Deadline warning threshold in seconds (1 hour)
DEADLINE_WARNING_SECONDS = 3600

# Max retries per HTTP request
MAX_RETRIES = 1


# ===================================================================
# ERC-8128 Signer (matches EM8128Client from skill.md exactly)
# ===================================================================
class EM8128Signer:
    """Signs HTTP requests with ERC-8128 wallet authentication."""

    def __init__(self, private_key: str, chain_id: int = DEFAULT_CHAIN_ID,
                 api_url: str = DEFAULT_API_URL):
        self.account = Account.from_key(private_key)
        self.wallet = self.account.address
        self.chain_id = chain_id
        self.api_url = api_url
        # Store key reference only — never log or print
        self._key = private_key

    def _build_sig_params(self, covered: list[str], params: dict) -> str:
        comp_str = " ".join(f'"{c}"' for c in covered)
        parts = [f"({comp_str})"]
        for key in ["created", "expires", "nonce", "keyid"]:
            if key in params:
                v = params[key]
                parts.append(
                    f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"'
                )
        for key in sorted(params.keys()):
            if key not in ["created", "expires", "nonce", "keyid"]:
                v = params[key]
                parts.append(
                    f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"'
                )
        return ";".join(parts)

    async def _fetch_nonce(self, client: httpx.AsyncClient) -> str:
        resp = await client.get(
            f"{self.api_url}/api/v1/auth/erc8128/nonce", timeout=10
        )
        resp.raise_for_status()
        return resp.json()["nonce"]

    async def sign_headers(
        self, method: str, url: str, body: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, str]:
        """Build ERC-8128 Signature + Signature-Input headers."""
        if client:
            nonce = await self._fetch_nonce(client)
        else:
            async with httpx.AsyncClient() as c:
                nonce = await self._fetch_nonce(c)

        parsed = urlparse(url)
        created = int(time.time())
        covered = ["@method", "@authority", "@path"]
        content_digest = None

        if parsed.query:
            covered.append("@query")
        if body:
            b = body.encode() if isinstance(body, str) else body
            b64 = base64.b64encode(hashlib.sha256(b).digest()).decode()
            content_digest = f"sha-256=:{b64}:"
            covered.append("content-digest")

        params = {
            "created": created,
            "expires": created + 300,
            "nonce": nonce,
            "keyid": f"erc8128:{self.chain_id}:{self.wallet}",
            "alg": "eip191",
        }

        lines = []
        for comp in covered:
            if comp == "@method":
                lines.append(f'"@method": {method.upper()}')
            elif comp == "@authority":
                lines.append(f'"@authority": {parsed.netloc}')
            elif comp == "@path":
                lines.append(f'"@path": {parsed.path}')
            elif comp == "@query":
                lines.append(f'"@query": ?{parsed.query}')
            elif comp == "content-digest":
                lines.append(f'"content-digest": {content_digest}')

        sp = self._build_sig_params(covered, params)
        lines.append(f'"@signature-params": {sp}')
        sig_base = "\n".join(lines)

        msg = encode_defunct(text=sig_base)
        signed = Account.sign_message(msg, self._key)
        sig_b64 = base64.b64encode(signed.signature).decode()

        headers = {
            "Signature": f"eth=:{sig_b64}:",
            "Signature-Input": f"eth={sp}",
        }
        if content_digest:
            headers["Content-Digest"] = content_digest
        return headers

    async def get(self, path: str, client: httpx.AsyncClient) -> dict:
        """Signed GET request."""
        url = f"{self.api_url}{path}"
        auth = await self.sign_headers("GET", url, client=client)
        resp = await client.get(url, headers=auth, timeout=30)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, data: dict | None,
                   client: httpx.AsyncClient) -> dict:
        """Signed POST request."""
        url = f"{self.api_url}{path}"
        body = json.dumps(data) if data else None
        auth = await self.sign_headers("POST", url, body=body, client=client)
        headers = {"Content-Type": "application/json", **auth}
        resp = await client.post(url, content=body, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ===================================================================
# Telegram Notifier
# ===================================================================
class TelegramNotifier:
    """Send notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str, dry_run: bool = False):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.dry_run = dry_run

    async def send(self, message: str) -> None:
        if self.dry_run:
            log.info("[DRY-RUN] Would notify: %s", message)
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post(url, json=payload)
                if resp.status_code != 200:
                    log.warning(
                        "Telegram API returned %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as e:
            log.warning("Telegram notification failed: %s", e)


class NullNotifier:
    """Fallback when no Telegram config is available."""

    async def send(self, message: str) -> None:
        log.info("[NO-NOTIFIER] %s", message)


# ===================================================================
# Config loader
# ===================================================================
def load_config() -> dict[str, Any]:
    """Load config from config.json with env var fallbacks."""
    cfg: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Failed to read config.json: %s", e)

    # Private key: config.json > credentials.json > env var
    # NEVER log the key value
    if not cfg.get("private_key"):
        if CREDENTIALS_PATH.exists():
            try:
                creds = json.loads(
                    CREDENTIALS_PATH.read_text(encoding="utf-8")
                )
                if creds.get("private_key"):
                    cfg["private_key"] = creds["private_key"]
            except (json.JSONDecodeError, OSError):
                pass
    if not cfg.get("private_key"):
        env_key = os.environ.get("EM_PRIVATE_KEY", "")
        if env_key:
            cfg["private_key"] = env_key

    # API URL from env or default
    cfg.setdefault("api_url", os.environ.get("EM_API_URL", DEFAULT_API_URL))

    # Chain ID
    cfg.setdefault("chain_id", DEFAULT_CHAIN_ID)

    # Notification config
    notification = cfg.get("notification", {})
    if not notification.get("chat_id"):
        notification["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID", "")
    cfg["notification"] = notification

    # Autonomy defaults
    cfg.setdefault("autonomy", "notify")
    cfg.setdefault("auto_approve_threshold", 0.8)

    return cfg


def load_tracker() -> dict[str, Any]:
    """Load active-tasks.json. Returns empty structure if missing."""
    if not TRACKER_PATH.exists():
        return {"tasks": []}
    try:
        data = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
        if not isinstance(data.get("tasks"), list):
            return {"tasks": []}
        return data
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to read active-tasks.json: %s", e)
        return {"tasks": []}


def save_tracker(data: dict[str, Any]) -> None:
    """Persist active-tasks.json."""
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===================================================================
# API helpers with retry
# ===================================================================
async def api_get_safe(signer: EM8128Signer, path: str,
                       client: httpx.AsyncClient) -> dict | None:
    """GET with one retry on failure. Returns None on error."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await signer.get(path, client)
        except Exception as e:
            if attempt < MAX_RETRIES:
                log.debug("Retry %s after error: %s", path, e)
                await asyncio.sleep(1)
            else:
                log.warning("GET %s failed after %d attempts: %s",
                            path, MAX_RETRIES + 1, e)
                return None
    return None


# ===================================================================
# Event detection
# ===================================================================
def parse_deadline(deadline_str: str | None) -> datetime | None:
    """Parse ISO deadline string to timezone-aware datetime."""
    if not deadline_str:
        return None
    try:
        dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


async def check_task(
    task_entry: dict,
    signer: EM8128Signer,
    client: httpx.AsyncClient,
    notifier: TelegramNotifier | NullNotifier,
) -> dict | None:
    """
    Check a single task for events. Returns updated task_entry,
    or None if the task should be removed from the tracker.
    """
    task_id = task_entry.get("id")
    title = task_entry.get("title", "Untitled")
    prev_status = task_entry.get("status", "unknown")
    prev_app_count = task_entry.get("_last_app_count", 0)
    prev_sub_count = task_entry.get("_last_sub_count", 0)

    if not task_id:
        log.warning("Task entry missing 'id', skipping")
        return None

    # 1. Fetch current task status
    task_data = await api_get_safe(signer, f"/api/v1/tasks/{task_id}", client)
    if task_data is None:
        log.warning("Could not fetch task %s, keeping in tracker", task_id)
        return task_entry

    # Handle API error responses
    if task_data.get("error") or task_data.get("detail"):
        error_msg = task_data.get("error") or task_data.get("detail")
        if "not found" in str(error_msg).lower():
            await notifier.send(
                f"<b>Task removed</b>\n"
                f"Task <i>{title}</i> no longer exists on the server.\n"
                f"ID: <code>{task_id}</code>"
            )
            return None
        log.warning("API error for task %s: %s", task_id, error_msg)
        return task_entry

    current_status = task_data.get("status", prev_status)
    bounty = task_data.get("bounty_usd", task_entry.get("bounty_usd", "?"))

    # 2. Status change detection
    if current_status != prev_status:
        if current_status in ("completed", "cancelled", "expired"):
            await notifier.send(
                f"<b>Task {current_status.upper()}</b>\n"
                f"<i>{title}</i> (${bounty})\n"
                f"ID: <code>{task_id}</code>"
            )
            return None  # Remove from tracker
        else:
            await notifier.send(
                f"<b>Status change</b>\n"
                f"<i>{title}</i>: {prev_status} -> {current_status}\n"
                f"ID: <code>{task_id}</code>"
            )

    # 3. Deadline warning (< 1 hour remaining)
    deadline = parse_deadline(
        task_data.get("deadline") or task_entry.get("deadline")
    )
    if deadline:
        now = datetime.now(timezone.utc)
        remaining = (deadline - now).total_seconds()
        if 0 < remaining < DEADLINE_WARNING_SECONDS:
            minutes_left = int(remaining / 60)
            # Only warn once per run — use a flag
            if not task_entry.get("_deadline_warned"):
                await notifier.send(
                    f"<b>Deadline approaching</b>\n"
                    f"<i>{title}</i> has {minutes_left} minutes remaining!\n"
                    f"ID: <code>{task_id}</code>"
                )
                task_entry["_deadline_warned"] = True
        elif remaining <= 0 and current_status in ("published", "accepted"):
            await notifier.send(
                f"<b>Task EXPIRED</b>\n"
                f"<i>{title}</i> deadline has passed.\n"
                f"ID: <code>{task_id}</code>"
            )
            task_entry["status"] = "expired"
            return task_entry

    # 4. Check applications (only for tasks we published)
    apps_data = await api_get_safe(
        signer, f"/api/v1/tasks/{task_id}/applications", client
    )
    if apps_data and not apps_data.get("error") and not apps_data.get("detail"):
        app_count = apps_data.get("count", 0)
        applications = apps_data.get("applications", [])
        if app_count > prev_app_count:
            new_count = app_count - prev_app_count
            # Notify about each new application
            for app in applications[prev_app_count:]:
                executor_id = app.get("executor_id", "unknown")
                message = app.get("message", "")
                wallet = app.get("wallet_address", "")
                wallet_display = (
                    f"{wallet[:6]}...{wallet[-4:]}" if len(wallet) > 10
                    else wallet
                )
                await notifier.send(
                    f"<b>New application</b>\n"
                    f"<i>{title}</i> (${bounty})\n"
                    f"Worker: {executor_id}"
                    + (f" ({wallet_display})" if wallet_display else "")
                    + (f"\nMessage: {message}" if message else "")
                    + f"\nID: <code>{task_id}</code>"
                )
        task_entry["_last_app_count"] = app_count

    # 5. Check submissions (only for tasks we published)
    subs_data = await api_get_safe(
        signer, f"/api/v1/tasks/{task_id}/submissions", client
    )
    if subs_data and not subs_data.get("error") and not subs_data.get("detail"):
        sub_count = subs_data.get("count", 0)
        submissions = subs_data.get("submissions", [])
        if sub_count > prev_sub_count:
            for sub in submissions[prev_sub_count:]:
                sub_id = sub.get("id", "unknown")
                pre_check = sub.get("pre_check_score")
                evidence = sub.get("evidence", {})
                # Extract photo URL from evidence if present
                photo_url = None
                if isinstance(evidence, dict):
                    for key, val in evidence.items():
                        if isinstance(val, str) and (
                            val.startswith("http") and
                            any(ext in val.lower()
                                for ext in [".jpg", ".png", ".jpeg", ".webp"])
                        ):
                            photo_url = val
                            break
                        if isinstance(val, dict) and val.get("url"):
                            photo_url = val["url"]
                            break

                score_text = (
                    f"Score: {pre_check:.2f}" if pre_check is not None
                    else "Score: pending"
                )
                msg = (
                    f"<b>New submission</b>\n"
                    f"<i>{title}</i> (${bounty})\n"
                    f"{score_text}\n"
                    f"Submission: <code>{sub_id}</code>"
                )
                if photo_url:
                    msg += f"\nPhoto: {photo_url}"
                msg += f"\nTask: <code>{task_id}</code>"
                await notifier.send(msg)
        task_entry["_last_sub_count"] = sub_count

    # Update tracked status
    task_entry["status"] = current_status
    return task_entry


# ===================================================================
# Main monitor loop
# ===================================================================
async def run_once(dry_run: bool = False) -> int:
    """Run a single monitoring pass. Returns 0 on success."""
    cfg = load_config()
    tracker = load_tracker()
    tasks = tracker.get("tasks", [])

    if not tasks:
        log.info("No active tasks. Nothing to check.")
        return 0

    # Validate private key is available
    private_key = cfg.get("private_key")
    if not private_key:
        log.error(
            "No private key found. Set EM_PRIVATE_KEY env var or add "
            "private_key to config.json / credentials.json"
        )
        return 1

    api_url = cfg.get("api_url", DEFAULT_API_URL)
    chain_id = cfg.get("chain_id", DEFAULT_CHAIN_ID)

    # Initialize signer
    try:
        signer = EM8128Signer(private_key, chain_id, api_url)
    except Exception as e:
        log.error("Failed to initialize signer: %s", e)
        return 1

    log.info(
        "Checking %d task(s) as wallet %s...%s",
        len(tasks), signer.wallet[:6], signer.wallet[-4:]
    )

    # Initialize notifier
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = cfg.get("notification", {}).get("chat_id", "")
    if bot_token and chat_id:
        notifier = TelegramNotifier(bot_token, chat_id, dry_run=dry_run)
    else:
        if not dry_run:
            log.warning(
                "Telegram not configured (TELEGRAM_BOT_TOKEN env + "
                "notification.chat_id in config.json). Using log output."
            )
        notifier = NullNotifier()

    # Check each task
    updated_tasks = []
    async with httpx.AsyncClient() as client:
        for task_entry in tasks:
            result = await check_task(task_entry, signer, client, notifier)
            if result is not None:
                updated_tasks.append(result)
            else:
                task_id = task_entry.get("id", "?")
                log.info("Removed task %s from tracker", task_id)

    # Persist updated tracker
    tracker["tasks"] = updated_tasks
    tracker["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_tracker(tracker)

    removed = len(tasks) - len(updated_tasks)
    log.info(
        "Done. %d task(s) checked, %d removed, %d remaining.",
        len(tasks), removed, len(updated_tasks),
    )
    return 0


async def run_loop(interval: int, dry_run: bool = False) -> None:
    """Run monitoring in a loop with the given interval in seconds."""
    stop = asyncio.Event()

    def _signal_handler(*_: Any) -> None:
        log.info("Received stop signal, shutting down...")
        stop.set()

    # Handle graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)
    except (NotImplementedError, OSError):
        # Windows doesn't support add_signal_handler
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    log.info("Starting monitor loop (interval: %ds). Ctrl+C to stop.", interval)
    while not stop.is_set():
        try:
            await run_once(dry_run=dry_run)
        except Exception as e:
            log.error("Monitor pass failed: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            break  # stop was set
        except asyncio.TimeoutError:
            pass  # Interval elapsed, run again


# ===================================================================
# CLI
# ===================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execution Market task monitor — "
                    "checks active tasks and notifies via Telegram.",
        epilog=(
            "Environment variables:\n"
            "  TELEGRAM_BOT_TOKEN   Bot token for notifications\n"
            "  EM_PRIVATE_KEY       Wallet private key (fallback)\n"
            "  EM_API_URL           API base URL (default: %(default)s)\n"
            "  TELEGRAM_CHAT_ID     Chat ID (fallback for config.json)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be notified without sending Telegram messages",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Check once and exit (default behavior)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        metavar="SECONDS",
        default=0,
        help="Run continuously with the given interval in seconds (e.g. --loop 180)",
    )
    args = parser.parse_args()

    if args.loop > 0:
        asyncio.run(run_loop(args.loop, dry_run=args.dry_run))
    else:
        code = asyncio.run(run_once(dry_run=args.dry_run))
        sys.exit(code)


if __name__ == "__main__":
    main()
