#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${PROJECT_ROOT}/models"

mkdir -p "${MODELS_DIR}"

echo "======================================================"
echo "    📦 Realtime Voice Translate - Model Downloader   "
echo "======================================================"

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

# 1. Download Silero VAD ONNX model — pinned version (keep in sync with ai/src/rvt_ai/engines/vad_silero.py)
SILERO_VAD_VERSION="v6.2.1"
SILERO_VAD_SHA256="1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
SILERO_VAD_URL="https://raw.githubusercontent.com/snakers4/silero-vad/${SILERO_VAD_VERSION}/src/silero_vad/data/silero_vad.onnx"
VAD_MODEL="${MODELS_DIR}/silero_vad.onnx"
if [[ ! -f "${VAD_MODEL}" ]]; then
    echo "Downloading Silero VAD ${SILERO_VAD_VERSION} ONNX model (~2.3 MB)..."
    if curl -fsSL "${SILERO_VAD_URL}" -o "${VAD_MODEL}"; then
        if [[ "$(sha256_of "${VAD_MODEL}")" != "${SILERO_VAD_SHA256}" ]]; then
            rm -f "${VAD_MODEL}"
            echo "✗ Silero VAD checksum mismatch for ${SILERO_VAD_URL}" >&2
            exit 1
        fi
        echo "✓ Silero VAD ${SILERO_VAD_VERSION} downloaded and verified: ${VAD_MODEL}"
    else
        echo "⚠ GitHub download failed, falling back to the unverified HuggingFace copy" >&2
        curl -fsSL "https://huggingface.co/onnx-community/silero-vad/resolve/main/onnx/model.onnx" -o "${VAD_MODEL}"
        echo "✓ Silero VAD downloaded (unverified): ${VAD_MODEL}"
    fi
elif [[ "$(sha256_of "${VAD_MODEL}")" != "${SILERO_VAD_SHA256}" ]]; then
    echo "⚠ ${VAD_MODEL} is not the pinned Silero VAD ${SILERO_VAD_VERSION}; delete it and re-run this script to update"
else
    echo "✓ Silero VAD ${SILERO_VAD_VERSION} already exists: ${VAD_MODEL}"
fi

# 2. Check or download MT GGUF model (Qwen2.5-3B-Instruct Q4_K_M)
MT_MODEL="${MODELS_DIR}/mt-model.gguf"
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

if [[ ! -f "${MT_MODEL}" ]]; then
    echo ""
    echo "Notice: Machine Translation GGUF model not found at ${MT_MODEL}"
    echo "Recommended model: Qwen2.5-3B-Instruct Q4_K_M (~2.16 GB) from HuggingFace:"
    echo ""
    echo "  curl -L -o models/mt-model.gguf \\"
    echo "    ${QWEN_URL}"
    echo ""
    read -p "Do you want to download Qwen2.5-3B-Instruct GGUF now? (y/N): " -n 1 -r || true
    echo ""
    if [[ ${REPLY:-n} =~ ^[Yy]$ ]]; then
        echo "Downloading Qwen2.5-3B-Instruct GGUF model (~2.16 GB)..."
        curl -L --fail --progress-bar -o "${MT_MODEL}" "${QWEN_URL}" || {
            echo "Failed to download from HuggingFace. You can manually copy any GGUF model to models/mt-model.gguf"
        }
    else
        echo "Skipping GGUF download. Note: To run GPU stack with llama.cpp, place your GGUF model at models/mt-model.gguf"
        echo "Or run in dev/CPU mode with: ./start.sh --cpu"
    fi
else
    echo "✓ MT GGUF model already exists: ${MT_MODEL}"
fi

echo "======================================================"
echo "✓ Model check complete."
