"""
Execution Market SDK for Python

Simple client for AI agents to create and manage human tasks.
Supports ERC-8128 wallet signing (API key auth is disabled).
"""

import asyncio
import base64
import hashlib
import httpx
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# SDK Data Classes (used by other scripts — DO NOT REMOVE)
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    """Task status values."""
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    """Task categories."""
    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


class EvidenceType(str, Enum):
    """Evidence types."""
    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    SIGNATURE = "signature"
    TEXT_RESPONSE = "text_response"


@dataclass
class Task:
    """Execution Market task."""
    id: str
    title: str
    instructions: str
    category: TaskCategory
    bounty_usd: float
    status: TaskStatus
    deadline: datetime
    evidence_required: List[str]
    location_hint: Optional[str] = None
    executor_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Submission:
    """Task submission."""
    id: str
    task_id: str
    executor_id: str
    evidence: Dict[str, Any]
    status: str
    pre_check_score: float
    submitted_at: datetime
    notes: Optional[str] = None


@dataclass
class TaskResult:
    """Completed task result."""
    task_id: str
    status: TaskStatus
    evidence: Dict[str, Any]
    answer: Optional[str] = None
    completed_at: Optional[datetime] = None
    payment_tx: Optional[str] = None


class ExecutionMarketClient:
    """
    Execution Market API client for AI agents (API key auth — DEPRECATED).

    API key auth is disabled on the server. Use EM8128Client instead.
    Kept for backward compatibility with scripts that import this class.

    Example:
        >>> client = ExecutionMarketClient(api_key="your_key")
        >>> task = client.create_task(...)
    """

    DEFAULT_BASE_URL = "https://api.execution.market"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.api_key = api_key or os.getenv("EXECUTION_MARKET_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set EXECUTION_MARKET_API_KEY or pass api_key.")

        self.base_url = base_url or os.getenv("EXECUTION_MARKET_API_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout
        )

    def create_task(
        self,
        title: str,
        instructions: str,
        category: str,
        bounty_usd: float,
        deadline_hours: int,
        evidence_required: List[str],
        evidence_optional: Optional[List[str]] = None,
        location_hint: Optional[str] = None,
        min_reputation: int = 0,
        payment_token: str = "USDC",
        **kwargs
    ) -> Task:
        response = self._client.post("/tasks", json={
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": evidence_required,
            "evidence_optional": evidence_optional,
            "location_hint": location_hint,
            "min_reputation": min_reputation,
            "payment_token": payment_token,
            **kwargs
        })
        response.raise_for_status()
        data = response.json()
        return Task(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=TaskCategory(data["category"]),
            bounty_usd=data["bounty_usd"],
            status=TaskStatus(data["status"]),
            deadline=datetime.fromisoformat(data["deadline"]),
            evidence_required=data["evidence_required"],
            location_hint=data.get("location_hint")
        )

    def get_task(self, task_id: str) -> Task:
        response = self._client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        data = response.json()
        return Task(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=TaskCategory(data["category"]),
            bounty_usd=data["bounty_usd"],
            status=TaskStatus(data["status"]),
            deadline=datetime.fromisoformat(data["deadline"]),
            evidence_required=data["evidence_required"],
            location_hint=data.get("location_hint"),
            executor_id=data.get("executor_id")
        )

    def get_submissions(self, task_id: str) -> List[Submission]:
        response = self._client.get(f"/tasks/{task_id}/submissions")
        response.raise_for_status()
        return [
            Submission(
                id=s["id"],
                task_id=s["task_id"],
                executor_id=s["executor_id"],
                evidence=s["evidence"],
                status=s["status"],
                pre_check_score=s.get("pre_check_score", 0.5),
                submitted_at=datetime.fromisoformat(s["submitted_at"]),
                notes=s.get("notes")
            )
            for s in response.json()
        ]

    def approve_submission(self, submission_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        response = self._client.post(f"/submissions/{submission_id}/approve", json={"notes": notes})
        response.raise_for_status()
        return response.json()

    def reject_submission(self, submission_id: str, notes: str) -> Dict[str, Any]:
        response = self._client.post(f"/submissions/{submission_id}/reject", json={"notes": notes})
        response.raise_for_status()
        return response.json()

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        response = self._client.post(f"/tasks/{task_id}/cancel", json={"reason": reason})
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        task_id: str,
        timeout_hours: float = 24,
        poll_interval: float = 30
    ) -> TaskResult:
        deadline = time.time() + (timeout_hours * 3600)
        while time.time() < deadline:
            task = self.get_task(task_id)
            if task.status == TaskStatus.COMPLETED:
                submissions = self.get_submissions(task_id)
                approved = [s for s in submissions if s.status == "approved"]
                evidence = approved[0].evidence if approved else {}
                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence=evidence,
                    answer=evidence.get("text_response"),
                    completed_at=datetime.now(timezone.utc)
                )
            if task.status in [TaskStatus.EXPIRED, TaskStatus.CANCELLED, TaskStatus.DISPUTED]:
                return TaskResult(task_id=task_id, status=task.status, evidence={})
            time.sleep(poll_interval)
        raise TimeoutError(f"Task {task_id} did not complete within {timeout_hours} hours")

    def batch_create(self, tasks: List[Dict[str, Any]]) -> List[Task]:
        response = self._client.post("/tasks/batch", json={"tasks": tasks})
        response.raise_for_status()
        return [
            Task(
                id=t["id"],
                title=t["title"],
                instructions=t["instructions"],
                category=TaskCategory(t["category"]),
                bounty_usd=t["bounty_usd"],
                status=TaskStatus(t["status"]),
                deadline=datetime.fromisoformat(t["deadline"]),
                evidence_required=t["evidence_required"],
                location_hint=t.get("location_hint")
            )
            for t in response.json()["tasks"]
        ]

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        response = self._client.get("/analytics", params={"days": days})
        response.raise_for_status()
        return response.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Convenience function
def create_client(api_key: Optional[str] = None) -> ExecutionMarketClient:
    """Create an Execution Market client."""
    return ExecutionMarketClient(api_key=api_key)


# ---------------------------------------------------------------------------
# ERC-8128 Wallet Signing Client (replaces API key auth)
# ---------------------------------------------------------------------------

class EM8128Client:
    def __init__(self, private_key: str, chain_id: int = 8453,
                 api_url: str = "https://api.execution.market"):
        from eth_account import Account
        self.account = Account.from_key(private_key)
        self.wallet = self.account.address
        self.chain_id = chain_id
        self.api_url = api_url
        self.private_key = private_key

    def _build_sig_params(self, covered, params):
        comp_str = " ".join(f'"{c}"' for c in covered)
        parts = [f"({comp_str})"]
        for key in ["created", "expires", "nonce", "keyid"]:
            if key in params:
                v = params[key]
                parts.append(f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"')
        for key in sorted(params.keys()):
            if key not in ["created", "expires", "nonce", "keyid"]:
                v = params[key]
                parts.append(f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"')
        return ";".join(parts)

    async def _sign_headers(self, method, url, body=None):
        from eth_account import Account
        from eth_account.messages import encode_defunct
        async with httpx.AsyncClient() as c:
            nonce = (await c.get(f"{self.api_url}/api/v1/auth/erc8128/nonce")).json()["nonce"]
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
        params = {"created": created, "expires": created + 300, "nonce": nonce,
                  "keyid": f"erc8128:{self.chain_id}:{self.wallet}", "alg": "eip191"}
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
        signed = Account.sign_message(msg, self.private_key)
        sig_b64 = base64.b64encode(signed.signature).decode()
        headers = {"Signature": f"eth=:{sig_b64}:", "Signature-Input": f"eth={sp}"}
        if content_digest:
            headers["Content-Digest"] = content_digest
        return headers

    async def post(self, path, data=None):
        url = f"{self.api_url}{path}"
        body = json.dumps(data) if data else None
        auth = await self._sign_headers("POST", url, body)
        headers = {"Content-Type": "application/json", **auth}
        async with httpx.AsyncClient(timeout=180) as c:
            return (await c.post(url, content=body, headers=headers)).json()

    async def get(self, path):
        url = f"{self.api_url}{path}"
        auth = await self._sign_headers("GET", url)
        async with httpx.AsyncClient(timeout=30) as c:
            return (await c.get(url, headers=auth)).json()


# ---------------------------------------------------------------------------
# Config & Paths
# ---------------------------------------------------------------------------

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "execution-market"
ACTIVE_TASKS_FILE = SKILL_DIR / "active-tasks.json"
TELEGRAM_CHAT_ID = os.getenv("EM_TELEGRAM_CHAT_ID", "")

TERMINAL_STATUSES = {
    TaskStatus.COMPLETED, TaskStatus.EXPIRED, TaskStatus.CANCELLED
}
ACTIVE_STATUSES = {
    TaskStatus.PUBLISHED, TaskStatus.ACCEPTED,
    TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED, TaskStatus.VERIFYING
}


def _load_creds() -> Dict[str, str]:
    """Load credentials from credentials.json."""
    creds_file = SKILL_DIR / "credentials.json"
    if not creds_file.exists():
        raise FileNotFoundError(f"Credentials not found: {creds_file}")
    return json.loads(creds_file.read_text())


def _load_config() -> Dict[str, Any]:
    """Load config from config.json, with defaults."""
    cfg_file = SKILL_DIR / "config.json"
    defaults = {
        "auto_assign_threshold": 0.8,
        "api_url": "https://api.execution.market",
        "chain_id": 8453,
    }
    if cfg_file.exists():
        cfg = json.loads(cfg_file.read_text())
        defaults.update(cfg)
    return defaults


def _load_telegram_token() -> Optional[str]:
    """Load Telegram bot token from clawdbot config."""
    bot_cfg = Path.home() / ".clawdbot" / "clawdbot.json"
    if not bot_cfg.exists():
        return None
    try:
        data = json.loads(bot_cfg.read_text())
        return data.get("telegram", {}).get("token")
    except (json.JSONDecodeError, KeyError):
        return None


def _load_active_tasks() -> Dict[str, Any]:
    """Load active tasks tracker."""
    if not ACTIVE_TASKS_FILE.exists():
        return {"tasks": [], "completed": []}
    try:
        return json.loads(ACTIVE_TASKS_FILE.read_text())
    except (json.JSONDecodeError, ValueError):
        return {"tasks": [], "completed": []}


def _save_active_tasks(data: Dict[str, Any]):
    """Save active tasks tracker."""
    ACTIVE_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_TASKS_FILE.write_text(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Telegram Notifications
# ---------------------------------------------------------------------------

async def notify_telegram(
    token: str,
    chat_id: str,
    text: str,
    photo_url: Optional[str] = None
):
    """Send a Telegram notification (text or photo with caption)."""
    async with httpx.AsyncClient(timeout=15) as c:
        if photo_url:
            await c.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                json={
                    "chat_id": chat_id,
                    "photo": photo_url,
                    "caption": text[:1024],
                    "parse_mode": "HTML",
                },
            )
        else:
            await c.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )


# ---------------------------------------------------------------------------
# Monitor Command
# ---------------------------------------------------------------------------

def _extract_photo_url(evidence: Any) -> Optional[str]:
    """Extract the first photo URL from submission evidence, if any."""
    if not evidence:
        return None
    items = evidence if isinstance(evidence, list) else [evidence]
    for item in items:
        if isinstance(item, dict):
            url = item.get("url") or item.get("photo_url") or item.get("presigned_url")
            if url:
                return url
            # Nested evidence_items
            for sub in item.get("evidence_items", []):
                url = sub.get("url") or sub.get("photo_url") or sub.get("presigned_url")
                if url:
                    return url
    return None


def _has_gps_evidence(evidence: Any) -> bool:
    """Check if evidence contains GPS/geo data."""
    if not evidence:
        return False
    items = evidence if isinstance(evidence, list) else [evidence]
    for item in items:
        if isinstance(item, dict):
            if item.get("type") in ("photo_geo", "gps", "geolocation"):
                return True
            if item.get("latitude") or item.get("longitude") or item.get("coordinates"):
                return True
            for sub in item.get("evidence_items", []):
                if sub.get("type") in ("photo_geo", "gps", "geolocation"):
                    return True
                if sub.get("latitude") or sub.get("longitude"):
                    return True
    return False


async def cmd_monitor(dry_run: bool = False):
    """
    Check all active tasks. For each task:
    - published: check applications, notify on new ones
    - accepted/in_progress/submitted: check submissions, notify with photo+score
    - completed/expired/cancelled: archive to completed list
    """
    creds = _load_creds()
    cfg = _load_config()
    tg_token = _load_telegram_token()
    tg_chat_id = cfg.get("telegram_chat_id") or TELEGRAM_CHAT_ID
    tracker = _load_active_tasks()

    if not tracker["tasks"]:
        print("No active tasks to monitor.")
        return

    client = EM8128Client(
        private_key=creds["private_key"],
        chain_id=cfg.get("chain_id", 8453),
        api_url=cfg.get("api_url", "https://api.execution.market"),
    )

    now = datetime.now(timezone.utc).isoformat()
    tasks_to_remove = []
    changed = False

    for task_entry in tracker["tasks"]:
        task_id = task_entry["id"]
        title = task_entry.get("title", task_id[:8])

        try:
            task_data = await client.get(f"/api/v1/tasks/{task_id}")
        except Exception as e:
            print(f"[ERROR] Failed to fetch task {task_id}: {e}", file=sys.stderr)
            continue

        if isinstance(task_data, dict) and "detail" in task_data:
            print(f"[WARN] Task {task_id}: {task_data['detail']}", file=sys.stderr)
            continue

        current_status = task_data.get("status", task_entry.get("status"))
        task_entry["status"] = current_status

        # Archive terminal tasks
        if current_status in [s.value for s in TERMINAL_STATUSES]:
            tasks_to_remove.append(task_id)
            tracker.setdefault("completed", []).append({
                "id": task_id,
                "title": title,
                "status": current_status,
                "archived_at": now,
            })
            msg = f"📋 Task terminada: <b>{title}</b>\nStatus: {current_status}"
            print(f"[ARCHIVE] {title} → {current_status}")
            if tg_token and not dry_run:
                try:
                    await notify_telegram(tg_token, tg_chat_id, msg)
                except Exception as e:
                    print(f"[ERROR] Telegram notify failed: {e}", file=sys.stderr)
            changed = True
            continue

        # Ensure tracking fields exist
        task_entry.setdefault("notified_app_ids", [])
        task_entry.setdefault("notified_submission_ids", [])
        task_entry.setdefault("lastCheck", {})

        # --- Check applications (published tasks) ---
        if current_status == TaskStatus.PUBLISHED.value:
            try:
                apps = await client.get(f"/api/v1/tasks/{task_id}/applications")
                if isinstance(apps, list):
                    for app in apps:
                        app_id = app.get("id", "")
                        if app_id in task_entry["notified_app_ids"]:
                            continue

                        worker_name = app.get("executor_name") or app.get("wallet_address", "unknown")[:10]
                        rep_score = app.get("reputation_score", 0)
                        message = app.get("message", "")

                        threshold = cfg.get("auto_assign_threshold", 0.8)
                        if rep_score >= threshold:
                            rec = f"⚡ Rep {rep_score:.1f} >= {threshold} — candidato para auto-assign"
                        else:
                            rec = f"⏳ Rep {rep_score:.1f} — requiere revisión manual"

                        msg = (
                            f"🙋 Nueva aplicación: <b>{title}</b>\n"
                            f"Worker: {worker_name}\n"
                            f"{rec}\n"
                        )
                        if message:
                            msg += f'Mensaje: "{message[:200]}"\n'
                        msg += f"\n🔗 https://execution.market/tasks/{task_id}"

                        print(f"[APP] {title}: {worker_name} (rep={rep_score})")

                        if tg_token and not dry_run:
                            try:
                                await notify_telegram(tg_token, tg_chat_id, msg)
                            except Exception as e:
                                print(f"[ERROR] Telegram: {e}", file=sys.stderr)

                        task_entry["notified_app_ids"].append(app_id)
                        changed = True

                task_entry["lastCheck"]["applications"] = now
            except Exception as e:
                print(f"[ERROR] Applications for {task_id}: {e}", file=sys.stderr)

        # --- Check submissions (accepted/in_progress/submitted/verifying) ---
        if current_status in [
            TaskStatus.ACCEPTED.value, TaskStatus.IN_PROGRESS.value,
            TaskStatus.SUBMITTED.value, TaskStatus.VERIFYING.value,
        ]:
            try:
                subs = await client.get(f"/api/v1/tasks/{task_id}/submissions")
                if isinstance(subs, list):
                    for sub in subs:
                        sub_id = sub.get("id", "")
                        if sub_id in task_entry["notified_submission_ids"]:
                            continue

                        score = sub.get("pre_check_score", 0)
                        evidence = sub.get("evidence", {})
                        photo_url = _extract_photo_url(evidence)
                        has_gps = _has_gps_evidence(evidence)

                        score_display = f"{score:.0%}" if isinstance(score, float) else str(score)
                        gps_line = "\n📍 GPS verificado ✓" if has_gps else ""

                        msg = (
                            f"📸 Nueva submission: <b>{title}</b>\n"
                            f"Score: {score_display}{gps_line}\n"
                            f"Status: {sub.get('status', 'pending')}\n"
                            f"\n🔗 Verificar en: https://execution.market/tasks/{task_id}"
                        )

                        print(f"[SUB] {title}: score={score_display} photo={'yes' if photo_url else 'no'}")

                        if tg_token and not dry_run:
                            try:
                                await notify_telegram(
                                    tg_token, tg_chat_id, msg,
                                    photo_url=photo_url,
                                )
                            except Exception as e:
                                print(f"[ERROR] Telegram: {e}", file=sys.stderr)

                        task_entry["notified_submission_ids"].append(sub_id)
                        changed = True

                task_entry["lastCheck"]["submissions"] = now
            except Exception as e:
                print(f"[ERROR] Submissions for {task_id}: {e}", file=sys.stderr)

    # Remove archived tasks
    if tasks_to_remove:
        tracker["tasks"] = [
            t for t in tracker["tasks"] if t["id"] not in tasks_to_remove
        ]
        changed = True

    if changed:
        _save_active_tasks(tracker)
        print(f"Tracker updated. {len(tracker['tasks'])} active, {len(tracker.get('completed', []))} completed.")
    else:
        print(f"No changes. {len(tracker['tasks'])} active tasks checked.")


# ---------------------------------------------------------------------------
# Status Command
# ---------------------------------------------------------------------------

def cmd_status():
    """Print current active-tasks.json summary."""
    tracker = _load_active_tasks()
    tasks = tracker.get("tasks", [])
    completed = tracker.get("completed", [])

    print(f"Active tasks: {len(tasks)}")
    print(f"Completed/archived: {len(completed)}")
    print()

    if tasks:
        print("--- Active ---")
        for t in tasks:
            status = t.get("status", "?")
            bounty = t.get("bounty_usd", "?")
            network = t.get("network", "?")
            apps = len(t.get("notified_app_ids", []))
            subs = len(t.get("notified_submission_ids", []))
            print(f"  [{status}] {t.get('title', t['id'][:8])} — ${bounty} on {network} (apps:{apps} subs:{subs})")

    if completed:
        print("\n--- Recently Completed ---")
        for t in completed[-5:]:
            print(f"  [{t.get('status', '?')}] {t.get('title', t['id'][:8])} — archived {t.get('archived_at', '?')}")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Execution Market CLI (ERC-8128 auth)",
        prog="em.py",
    )
    subparsers = parser.add_subparsers(dest="command")

    # monitor
    mon_parser = subparsers.add_parser("monitor", help="Check active tasks and notify")
    mon_parser.add_argument("--dry-run", action="store_true", help="Print actions without notifying")
    mon_parser.add_argument("--notify-telegram", action="store_true",
                            help="Send Telegram notifications (default behavior, kept for cron compat)")

    # status
    subparsers.add_parser("status", help="Show active tasks summary")

    args = parser.parse_args()

    if args.command == "monitor":
        try:
            asyncio.run(cmd_monitor(dry_run=args.dry_run))
        except Exception as e:
            print(f"[FATAL] Monitor failed: {e}", file=sys.stderr)
            sys.exit(0)  # Never crash the cron
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()
