# API chấm điểm churn (A7 · OPS-01). Image chỉ chứa code + thư viện lõi; model và danh sách gọi gắn vào lúc chạy
# (docker-compose.yml), nên đổi model không phải build lại image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# libgomp1: LightGBM cần OpenMP. uv cài bằng pip để không phụ thuộc registry nào khác ngoài PyPI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.32

WORKDIR /app

# 1) Thư viện trước, đúng phiên bản trong uv.lock, chỉ nhóm lõi (không shap/mlflow/pytest).
#    Lớp này được cache: sửa code rồi build lại không phải cài lại thư viện.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-default-groups --no-install-project

# 2) Rồi mới tới code.
COPY src ./src
RUN uv sync --locked --no-default-groups

# Không chạy bằng root: lỡ có lỗ hổng thì kẻ tấn công cũng không có quyền root trong container.
RUN useradd --create-home --uid 10001 app
USER app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "churn_telco.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
