import os

from fastapi import APIRouter, HTTPException, status

from rvt_ai.core.config import settings
from rvt_ai.core.security import create_session_token, verify_access_code
from rvt_contracts.messages import SessionTokenRequest, SessionTokenResponse

router = APIRouter(prefix="/v1", tags=["session"])


@router.post("/session", response_model=SessionTokenResponse)
async def create_session(req: SessionTokenRequest) -> SessionTokenResponse:
    if not verify_access_code(req.access_code or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access code")
    session_id = f"sess-{os.urandom(4).hex()}"
    token = create_session_token(session_id)
    return SessionTokenResponse(token=token, expires_in=settings.TOKEN_TTL_MINUTES * 60)
