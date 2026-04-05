"""IP Auto-Ban with progressive escalation.

Hardened 2026-04-04 after Tor exit node flood (20.5% of traffic was 4xx junk).
Changes from original:
  - Threshold lowered: 50 -> 10 strikes
  - Duration increased: 1h -> 2h base, progressive (2h -> 24h -> 7d)
  - 401 Unauthorized now counts as strikes (record_unauthorized)
  - Ban history tracked for progressive escalation
"""

import logging
import time
import threading

logger = logging.getLogger(__name__)

# Rate-limit violation (429) thresholds
BAN_THRESHOLD = 10
BAN_WINDOW = 300  # 5 minutes

# Progressive ban durations (seconds)
BAN_DURATION_FIRST = 7200      # 2 hours (first offense)
BAN_DURATION_SECOND = 86400    # 24 hours (second offense)
BAN_DURATION_REPEAT = 604800   # 7 days (third+ offense)

# Unauthorized (401) thresholds — separate from 429
UNAUTH_THRESHOLD = 20          # 20 consecutive 401s
UNAUTH_WINDOW = 300            # in 5 minutes
UNAUTH_BAN_DURATION = 3600     # 1 hour ban

_lock = threading.RLock()
_bans: dict = {}          # ip -> expiry timestamp
_strikes: dict = {}       # ip -> [timestamps] (429 strikes)
_unauth: dict = {}        # ip -> [timestamps] (401 strikes)
_ban_history: dict = {}   # ip -> count of times banned (for progressive)


def _get_ban_duration(ip: str) -> int:
    """Get ban duration based on how many times this IP has been banned."""
    count = _ban_history.get(ip, 0)
    if count == 0:
        return BAN_DURATION_FIRST
    elif count == 1:
        return BAN_DURATION_SECOND
    else:
        return BAN_DURATION_REPEAT


def is_banned(ip: str) -> bool:
    with _lock:
        expiry = _bans.get(ip, 0)
        if time.time() < expiry:
            return True
        if expiry:
            del _bans[ip]
        return False


def _apply_ban(ip: str, reason: str, strike_count: int) -> None:
    """Apply ban with progressive duration. Must be called under _lock."""
    duration = _get_ban_duration(ip)
    _bans[ip] = time.time() + duration
    _ban_history[ip] = _ban_history.get(ip, 0) + 1
    _strikes.pop(ip, None)
    _unauth.pop(ip, None)
    logger.warning(
        "IP_BANNED ip=%s reason=%s strikes=%d duration=%ds offense=#%d",
        ip,
        reason,
        strike_count,
        duration,
        _ban_history[ip],
    )
    try:
        from audit import audit_log

        audit_log(
            "ip_banned",
            ip=ip,
            reason=reason,
            strikes=strike_count,
            ban_duration=duration,
            offense_number=_ban_history[ip],
        )
    except Exception:
        pass


def record_429(ip: str) -> bool:
    """Record a 429 rate-limit hit. Returns True if IP was banned."""
    with _lock:
        now = time.time()
        strikes = _strikes.setdefault(ip, [])
        strikes.append(now)
        strikes[:] = [t for t in strikes if t > now - BAN_WINDOW]
        if len(strikes) >= BAN_THRESHOLD:
            _apply_ban(ip, "rate_limit_429", len(strikes))
            return True
        return False


def record_unauthorized(ip: str) -> bool:
    """Record a 401 Unauthorized response. Returns True if IP was banned.

    Catches persistent unauthorized access attempts (e.g., bots probing
    /a2a/v1 without credentials). Separate from 429 tracking.
    """
    with _lock:
        now = time.time()
        hits = _unauth.setdefault(ip, [])
        hits.append(now)
        hits[:] = [t for t in hits if t > now - UNAUTH_WINDOW]
        if len(hits) >= UNAUTH_THRESHOLD:
            _bans[ip] = now + UNAUTH_BAN_DURATION
            _ban_history[ip] = _ban_history.get(ip, 0) + 1
            _unauth.pop(ip, None)
            logger.warning(
                "IP_BANNED ip=%s reason=unauthorized_flood strikes=%d duration=%ds",
                ip,
                len(hits),
                UNAUTH_BAN_DURATION,
            )
            return True
        return False


def get_stats() -> dict:
    with _lock:
        now = time.time()
        return {
            "active_bans": sum(1 for exp in _bans.values() if now < exp),
            "tracked_ips": len(_strikes),
            "tracked_unauth_ips": len(_unauth),
            "total_bans_issued": sum(_ban_history.values()),
        }
