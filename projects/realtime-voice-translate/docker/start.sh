#!/usr/bin/env bash
set -euo pipefail

# Determine script and project root directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Default parameters
MODE="auto" # "auto", "gpu", "cpu"
REBUILD=""
ACTION="up"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}======================================================${NC}"
    echo -e "${CYAN}   🎙️  Realtime Voice Translate (RVT) Deployer        ${NC}"
    echo -e "${BLUE}======================================================${NC}"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --gpu          Force GPU mode (requires NVIDIA Docker runtime & CUDA)"
    echo "  --cpu          Force CPU/dev mode (no GPU required, uses fake/CPU engine)"
    echo "  --build        Rebuild Docker images before starting"
    echo "  --down, stop   Stop all running containers"
    echo "  --restart      Restart all containers"
    echo "  --status       Show running container status"
    echo "  --logs         Tail live logs from containers"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh                # Auto-detect hardware & start in background"
    echo "  ./start.sh --cpu          # Start in CPU/fake mode"
    echo "  ./start.sh --build        # Rebuild images & start"
    echo "  ./start.sh --down         # Stop all services"
    exit 0
}

# Parse command line flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu)
            MODE="gpu"
            shift
            ;;
        --cpu)
            MODE="cpu"
            shift
            ;;
        --build)
            REBUILD="--build"
            shift
            ;;
        --down|stop)
            ACTION="down"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --status|ps)
            ACTION="status"
            shift
            ;;
        --logs)
            ACTION="logs"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Action handlers: status, logs, down
if [[ "${ACTION}" == "status" ]]; then
    docker compose -f docker/docker-compose.yml ps 2>/dev/null || docker compose -f docker/docker-compose.cpu.yml ps
    exit 0
fi

if [[ "${ACTION}" == "logs" ]]; then
    docker compose -f docker/docker-compose.yml logs -f 2>/dev/null || docker compose -f docker/docker-compose.cpu.yml logs -f
    exit 0
fi

if [[ "${ACTION}" == "down" ]]; then
    echo -e "${YELLOW}Stopping all RVT services...${NC}"
    docker compose -f docker/docker-compose.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker/docker-compose.cpu.yml down --remove-orphans 2>/dev/null || true
    echo -e "${GREEN}✓ All services stopped.${NC}"
    exit 0
fi

print_banner

# Step 1: Ensure required directories exist
mkdir -p "${PROJECT_ROOT}/models"
mkdir -p "${PROJECT_ROOT}/config/tls"

# Step 2: Ensure TLS certificates exist for Nginx
CERT_FILE="${PROJECT_ROOT}/config/tls/cert.pem"
KEY_FILE="${PROJECT_ROOT}/config/tls/key.pem"

if [[ ! -f "${CERT_FILE}" || ! -f "${KEY_FILE}" ]]; then
    echo -e "${YELLOW}[TLS] Certificate files not found in config/tls. Generating self-signed certificates...${NC}"
    if command -v mkcert &>/dev/null; then
        echo -e "${CYAN}Using mkcert for trusted local certificates...${NC}"
        mkcert -key-file "${KEY_FILE}" -cert-file "${CERT_FILE}" localhost 127.0.0.1 ::1
    elif command -v openssl &>/dev/null; then
        echo -e "${CYAN}Using OpenSSL for self-signed certificates...${NC}"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "${KEY_FILE}" \
            -out "${CERT_FILE}" \
            -subj "/C=VN/ST=HCM/L=HCM/O=RVT/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
    else
        echo -e "${RED}[ERROR] Neither mkcert nor openssl is installed. Cannot generate TLS certificates.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ TLS certificates ready: ${CERT_FILE}${NC}"
else
    echo -e "${GREEN}✓ Existing TLS certificates found in config/tls.${NC}"
fi

# Step 3: Hardware & Mode Detection
if [[ "${MODE}" == "auto" ]]; then
    echo -e "${CYAN}Auto-detecting hardware environment...${NC}"
    HAS_NVIDIA_SMI=0
    HAS_DOCKER_NVIDIA=0

    if command -v nvidia-smi &>/dev/null; then
        HAS_NVIDIA_SMI=1
    fi

    if docker info 2>/dev/null | grep -qi "nvidia"; then
        HAS_DOCKER_NVIDIA=1
    fi

    if [[ ${HAS_NVIDIA_SMI} -eq 1 && ${HAS_DOCKER_NVIDIA} -eq 1 ]]; then
        echo -e "${GREEN}✓ NVIDIA GPU & Docker runtime detected. Using GPU mode.${NC}"
        MODE="gpu"
    else
        echo -e "${YELLOW}! No NVIDIA Docker runtime detected (macOS / CPU host). Falling back to CPU/Dev mode.${NC}"
        MODE="cpu"
    fi
fi

# Step 4: Run Docker Compose
if [[ "${ACTION}" == "restart" ]]; then
    echo -e "${YELLOW}Restarting services...${NC}"
    docker compose -f docker/docker-compose.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker/docker-compose.cpu.yml down --remove-orphans 2>/dev/null || true
fi

if [[ "${MODE}" == "gpu" ]]; then
    COMPOSE_FILE="docker/docker-compose.yml"
    echo -e "${BLUE}Starting GPU stack with ${COMPOSE_FILE}...${NC}"
else
    COMPOSE_FILE="docker/docker-compose.cpu.yml"
    echo -e "${BLUE}Starting CPU/Dev stack with ${COMPOSE_FILE}...${NC}"
fi

# Check if model exists for GPU mode
if [[ "${MODE}" == "gpu" && ! -f "${PROJECT_ROOT}/models/mt-model.gguf" ]]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW}⚠️  THIẾU MODEL DỊCH: Chưa có file 'models/mt-model.gguf'!${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${CYAN}Container 'mt' (llama.cpp) yêu cầu file model GGUF để khởi động trên GPU.${NC}"
    
    DOWNLOAD_URL="https://huggingface.co/mradermacher/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B.Q4_K_M.gguf"
    DO_DOWNLOAD=0

    if [ -t 0 ]; then
        echo -e "${CYAN}Bạn có muốn tự động tải model Hy-MT2-1.8B GGUF (~1.13 GB) từ HuggingFace ngay bây giờ? [Y/n]${NC}"
        read -r -p "Lựa chọn (mặc định Y): " USER_CHOICE || USER_CHOICE="y"
        if [[ -z "${USER_CHOICE}" || "${USER_CHOICE}" =~ ^[Yy]$ ]]; then
            DO_DOWNLOAD=1
        fi
    fi

    if [[ ${DO_DOWNLOAD} -eq 1 ]]; then
        echo -e "${CYAN}Đang tải model Hy-MT2-1.8B GGUF (~1.13 GB)...${NC}"
        echo -e "URL: ${DOWNLOAD_URL}"
        mkdir -p "${PROJECT_ROOT}/models"
        if curl -L --fail --progress-bar -o "${PROJECT_ROOT}/models/mt-model.gguf" "${DOWNLOAD_URL}"; then
            echo -e "${GREEN}✓ Đã tải thành công model vào models/mt-model.gguf!${NC}"
        else
            echo -e "${RED}❌ Tải thất bại từ HuggingFace.${NC}"
            echo -e "${YELLOW}Tự tải sau bằng lệnh: ${GREEN}make models${NC}"
            echo -e "${YELLOW}Tạm thời chuyển sang chế độ CPU/dev để hệ thống khởi động không bị lỗi crash...${NC}"
            MODE="cpu"
            COMPOSE_FILE="docker/docker-compose.cpu.yml"
        fi
    else
        echo -e "${YELLOW}Chưa có model GGUF. Tự động chuyển sang chế độ CPU/dev mode để hệ thống khởi động mượt mà không crash container mt!${NC}"
        echo -e "${CYAN}(Sau khi tải model bằng 'make models', bạn có thể khởi động lại GPU bằng './start.sh --gpu')${NC}"
        MODE="cpu"
        COMPOSE_FILE="docker/docker-compose.cpu.yml"
    fi
fi

# Ensure Silero VAD exists
if [[ ! -f "${PROJECT_ROOT}/models/silero_vad.onnx" ]]; then
    echo -e "${CYAN}Đang chuẩn bị Silero VAD ONNX (~1.8 MB)...${NC}"
    curl -fsSL -o "${PROJECT_ROOT}/models/silero_vad.onnx" "https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx" 2>/dev/null || \
    curl -fsSL -o "${PROJECT_ROOT}/models/silero_vad.onnx" "https://huggingface.co/onnx-community/silero-vad/resolve/main/onnx/model.onnx" 2>/dev/null || true
fi

# Execute Compose up
echo -e "${CYAN}Deploying containers (mode: ${MODE})...${NC}"
docker compose -f "${COMPOSE_FILE}" up -d ${REBUILD}

# Step 5: Wait for health check & print status
echo -e "${CYAN}Waiting for services to become healthy...${NC}"
ATTEMPTS=0
MAX_ATTEMPTS=20
SUCCESS=0

while [[ ${ATTEMPTS} -lt ${MAX_ATTEMPTS} ]]; do
    if curl -sk https://localhost:8443/api/health/live >/dev/null 2>&1 || curl -s http://localhost:8080 >/dev/null 2>&1; then
        SUCCESS=1
        break
    fi
    sleep 2
    ATTEMPTS=$((ATTEMPTS + 1))
    echo -n "."
done
echo ""

echo -e "\n${BLUE}======================================================${NC}"
if [[ ${SUCCESS} -eq 1 ]]; then
    echo -e "${GREEN}🎉 RVT Stack is RUNNING and ACCESSIBLE!${NC}"
else
    echo -e "${YELLOW}⚠️  Services started. Verification still in progress.${NC}"
fi
echo -e "${BLUE}======================================================${NC}"
echo -e "  🌐 ${CYAN}Web Application (HTTPS):${NC}  https://localhost:8443"
echo -e "  🌐 ${CYAN}Web Application (HTTP):${NC}   http://localhost:8080"
echo -e "  🩺 ${CYAN}AI Health Endpoint:${NC}       https://localhost:8443/api/health/ready"
echo -e "  🔌 ${CYAN}WebSocket Endpoint:${NC}       wss://localhost:8443/ws"
echo -e "${BLUE}------------------------------------------------------${NC}"
echo -e "  📋 Commands:"
echo -e "     - View status:  ${GREEN}./start.sh --status${NC}"
echo -e "     - View logs:    ${GREEN}./start.sh --logs${NC}"
echo -e "     - Stop stack:   ${GREEN}./start.sh --down${NC}"
echo -e "${BLUE}======================================================${NC}\n"
