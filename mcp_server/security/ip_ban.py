"""IP Auto-Ban: 50 429s in 5 min -> 1 hour ban."""

import logging
import time
import threading

logger = logging.getLogger(__name__)

BAN_THRESHOLD = 50
BAN_WINDOW = 300  # 5 minutes
BAN_DURATION = 3600  # 1 hour

_lock = threading.RLock()
_bans: dict = {}  # ip -> expiry timestamp
_strikes: dict = {}  # ip -> [timestamps]


def is_banned(ip: str) -> bool:
    with _lock:
        expiry = _bans.get(ip, 0)
        if time.time() < expiry:
            return True
        if expiry:
            del _bans[ip]
        return False


def record_429(ip: str) -> bool:
    with _lock:
        now = time.time()
        strikes = _strikes.setdefault(ip, [])
        strikes.append(now)
        strikes[:] = [t for t in strikes if t > now - BAN_WINDOW]
        if len(strikes) >= BAN_THRESHOLD:
            _bans[ip] = now + BAN_DURATION
            _strikes.pop(ip, None)
            logger.warning(
                "IP_BANNED ip=%s strikes=%d duration=%ds",
                ip,
                len(strikes),
                BAN_DURATION,
            )
            try:
                from audit import audit_log

                audit_log(
                    "ip_banned", ip=ip, strikes=len(strikes), ban_duration=BAN_DURATION
                )
            except Exception:
                pass
            return True
        return False


def get_stats() -> dict:
    with _lock:
        now = time.time()
        return {
            "active_bans": sum(1 for exp in _bans.values() if now < exp),
            "tracked_ips": len(_strikes),
        }
