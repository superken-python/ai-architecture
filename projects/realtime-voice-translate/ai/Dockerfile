FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Install basic tools and uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install Python 3.12 via uv and dependencies
COPY pyproject.toml ./
RUN uv python install 3.12
RUN uv sync --no-install-workspace

# Copy source
COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV RVT_USE_FAKE=0

CMD ["uv", "run", "uvicorn", "rvt_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
