import json
import os
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.core.security import verify_session_token
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import ClientEvent, ErrorEvent, Pong, ServerEvent

router = APIRouter()

active_sessions: dict[str, RVTSession] = {}


async def handle_websocket_connection(websocket: WebSocket):
    # 1. Subprotocol extraction & authentication
    requested_protocols = websocket.scope.get("subprotocols", [])
    token = None
    for proto in requested_protocols:
        if proto.startswith("rvt.token."):
            token = proto[len("rvt.token.") :]

    if settings.ACCESS_CODE and (not token or not verify_session_token(token)):
        logger.warning("Rejecting WebSocket connection: invalid or missing session token")
        await websocket.close(code=4401, reason="Unauthorized: invalid or missing session token")
        return

    # Check session limit
    if len(active_sessions) >= settings.MAX_SESSIONS:
        logger.warning(f"Rejecting WebSocket connection: max sessions reached ({settings.MAX_SESSIONS})")
        await websocket.close(code=4429, reason="Too many active sessions")
        return

    await websocket.accept(subprotocol="rvt.v1")
    session_id = f"sess-{os.urandom(4).hex()}"

    async def send_event(event: ServerEvent):
        try:
            await websocket.send_json(event.model_dump())
        except Exception as e:
            logger.debug(f"Failed to send event to {session_id}: {e}")

    app_state = websocket.app.state
    if not hasattr(app_state, "vad_engine"):
        from rvt_ai.engines.registry import build_engines_from_profile
        from rvt_ai.packs.loader import get_pack_registry

        pack_reg = get_pack_registry()
        profile = pack_reg.get_profile(settings.PROFILE)
        app_state.pack_reg = pack_reg
        app_state.profile = profile
        vad, asr, mt = build_engines_from_profile(profile)
        app_state.vad_engine = vad
        app_state.asr_engine = asr
        app_state.mt_engine = mt

    vad_engine = app_state.vad_engine
    asr_engine = app_state.asr_engine
    mt_engine = app_state.mt_engine
    pack_reg = app_state.pack_reg

    session = RVTSession(session_id=session_id, vad=vad_engine, asr=asr_engine, mt=mt_engine, send_event_cb=send_event)
    active_sessions[session_id] = session
    logger.info(f"WebSocket session connected: {session_id} (total: {len(active_sessions)})")

    # Send initial session.ready event
    profile = pack_reg.get_profile(settings.PROFILE)
    await websocket.send_json(
        {
            "type": "session.ready",
            "session_id": session_id,
            "profile": profile.name,
            "pack_revision": pack_reg.revision,
            "models": {"vad": profile.vad.engine, "asr": profile.asr.engine, "mt": profile.mt.engine},
        }
    )

    client_event_adapter = TypeAdapter(ClientEvent)

    try:
        while True:
            # Idle timeout check
            if time.time() - session.last_activity_time > settings.SESSION_IDLE_TIMEOUT_SEC:
                logger.info(f"Session {session_id} idle timeout ({settings.SESSION_IDLE_TIMEOUT_SEC}s). Closing.")
                await websocket.close(code=1000, reason="Idle timeout")
                break

            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                logger.info(f"WebSocket client disconnected: {session_id}")
                break

            if data.get("bytes"):
                await session.handle_audio_chunk(data["bytes"])
            elif data.get("text"):
                try:
                    payload = json.loads(data["text"])
                    event = client_event_adapter.validate_python(payload)

                    if event.type == "session.start":
                        await session.handle_session_start(event)
                    elif event.type == "turn.start":
                        await session.handle_turn_start(event.side)
                    elif event.type == "turn.stop":
                        await session.handle_turn_stop()
                    elif event.type == "sides.update":
                        await session.handle_sides_update(event)
                    elif event.type == "utterance.override_lang":
                        await session.handle_override_lang(event.utterance_id, event.lang)
                    elif event.type == "ping":
                        server_t = int(time.time() * 1000)
                        await send_event(Pong(t=event.t, server_t=server_t))

                except ValidationError as ve:
                    logger.warning(f"ClientEvent validation error from {session_id}: {ve}")
                    await send_event(
                        ErrorEvent(
                            code="invalid_message",
                            message=f"Message validation error: {ve.errors()[0]['msg']}",
                            retryable=False,
                        )
                    )
                except json.JSONDecodeError as je:
                    logger.warning(f"Invalid JSON received from {session_id}: {je}")
                    await send_event(
                        ErrorEvent(code="malformed_json", message="Received malformed JSON string", retryable=False)
                    )
                except Exception as ex:
                    logger.error(f"Error handling text event: {ex}")
                    await send_event(
                        ErrorEvent(
                            code="server_error", message=f"Internal error processing event: {ex!s}", retryable=False
                        )
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {session_id}")
    except Exception as e:
        logger.warning(f"WebSocket exception for {session_id}: {e}")
    finally:
        await session.close()
        active_sessions.pop(session_id, None)
        logger.info(f"Session {session_id} cleaned up (remaining: {len(active_sessions)})")


@router.websocket("/ws")
async def websocket_ws(websocket: WebSocket):
    await handle_websocket_connection(websocket)


@router.websocket("/v1/stream")
async def websocket_v1_stream(websocket: WebSocket):
    await handle_websocket_connection(websocket)
