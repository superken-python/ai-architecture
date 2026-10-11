from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rvt_ai.api import api_router
from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.registry import build_engines_from_profile
from rvt_ai.packs.loader import get_pack_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Realtime Voice Translate service...")

    # 1. Load packs and profiles
    pack_reg = get_pack_registry()
    profile = pack_reg.get_profile(settings.PROFILE)
    app.state.pack_reg = pack_reg
    app.state.profile = profile

    # 2. Build engines with resilient fallback
    try:
        vad_engine, asr_engine, mt_engine = build_engines_from_profile(profile)
    except Exception as e:
        logger.error(
            f"Error initializing engines for profile '{profile.name}': {e}. Falling back to resilient fake engines."
        )
        from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine

        vad_engine = FakeVadEngine()
        asr_engine = FakeAsrEngine()
        mt_engine = FakeMtEngine()

    app.state.vad_engine = vad_engine
    app.state.asr_engine = asr_engine
    app.state.mt_engine = mt_engine

    logger.info(f"Service initialized successfully with profile '{profile.name}'.")
    yield
    logger.info("Shutting down Realtime Voice Translate service...")


app = FastAPI(
    title="Realtime Voice Translate API",
    description="Low-latency Japanese ⇄ English ⇄ Vietnamese speech translation",
    version="0.2.0",
    lifespan=lifespan,
)

# Restrict CORS to same origin / localhost in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("rvt_ai.main:app", host=settings.HOST, port=settings.PORT, reload=False)
