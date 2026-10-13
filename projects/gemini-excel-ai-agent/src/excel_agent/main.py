from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from excel_agent.api.v1.router import api_v1_router
from excel_agent.core.config import settings
from excel_agent.core.logging import app_logger
from excel_agent.schemas.common import HealthCheckResponse, ResponseEnvelope


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("=" * 60)
    app_logger.info("Khởi động Excel Enterprise AI Agent (Agno AgentOS SDK)")
    app_logger.info(f"Mô hình Azure OpenAI: {settings.AZURE_DEPLOYMENT_NAME} ({settings.AZURE_OPENAI_MODEL})")
    app_logger.info(f"Endpoint API: http://{settings.HOST}:{settings.PORT}")
    app_logger.info(f"Taskpane Add-in UI: http://{settings.HOST}:{settings.PORT}/taskpane/index.html")
    app_logger.info("=" * 60)
    yield
    app_logger.info("Dừng dịch vụ Excel Enterprise AI Agent.")


app = FastAPI(
    title="Excel Enterprise AI Agent (Agno AgentOS)",
    description="Backend AI Agent điều phối tương tác Microsoft Excel nhúng hai chiều và tra cứu Mock Database",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn v1 API Router
app.include_router(api_v1_router, prefix="/api")

# Gắn thư mục tĩnh phục vụ Office Add-in Taskpane UI
addin_dir = Path(__file__).resolve().parent.parent.parent / "addin"
if addin_dir.exists():
    app.mount("/taskpane", StaticFiles(directory=str(addin_dir), html=True), name="taskpane")
    app_logger.info(f"Đã mount thư mục Office Add-in tại /taskpane từ: {addin_dir}")


@app.get("/health", response_model=ResponseEnvelope[HealthCheckResponse])
def health_check() -> ResponseEnvelope[HealthCheckResponse]:
    """Kiểm tra tình trạng hoạt động của hệ thống."""
    data = HealthCheckResponse(
        status="healthy",
        agent_id=settings.AGENT_ID,
        azure_model=settings.AZURE_DEPLOYMENT_NAME,
        agno_sdk_version="agno-agentos-v3",
        environment=settings.ENVIRONMENT,
    )
    return ResponseEnvelope[HealthCheckResponse](
        success=True,
        message="Hệ thống hoạt động bình thường",
        data=data,
    )


@app.get("/", response_model=ResponseEnvelope[dict])
def root() -> ResponseEnvelope[dict]:
    """Thông tin tổng quan dịch vụ."""
    return ResponseEnvelope[dict](
        success=True,
        message="Excel Enterprise AI Agent Service (Agno AgentOS) đang hoạt động",
        data={
            "app_name": settings.AGENT_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "taskpane_ui": "/taskpane/index.html",
            "azure_model": settings.AZURE_DEPLOYMENT_NAME,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("excel_agent.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
