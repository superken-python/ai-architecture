import hashlib
import hmac
import time

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger


def create_session_token(session_id: str, ttl_minutes: int | None = None) -> str:
    ttl = ttl_minutes or settings.TOKEN_TTL_MINUTES
    exp = int(time.time()) + ttl * 60
    msg = f"{session_id}:{exp}"
    signature = hmac.new(settings.TOKEN_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}:{signature}"


def verify_session_token(token: str) -> bool:
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False
        session_id, exp_str, signature = parts
        exp = int(exp_str)
        if time.time() > exp:
            logger.warning(f"Session token expired for session: {session_id}")
            return False
        expected_sig = hmac.new(
            settings.TOKEN_SECRET.encode(), f"{session_id}:{exp}".encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return False


def verify_access_code(code: str) -> bool:
    if not settings.ACCESS_CODE:
        # No access code required
        return True
    return hmac.compare_digest(settings.ACCESS_CODE, code)
