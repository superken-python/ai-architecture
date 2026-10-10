#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${PROJECT_ROOT}/models"

mkdir -p "${MODELS_DIR}"

echo "======================================================"
echo "    📦 Realtime Voice Translate - Model Downloader   "
echo "======================================================"

# 1. Download Silero VAD ONNX model
VAD_MODEL="${MODELS_DIR}/silero_vad.onnx"
if [[ ! -f "${VAD_MODEL}" ]]; then
    echo "Downloading Silero VAD ONNX model (~1.8 MB)..."
    curl -fsSL "https://raw.githubusercontent.com/snakers4/silero-vad/master/files/silero_vad.onnx" -o "${VAD_MODEL}"
    echo "✓ Silero VAD downloaded: ${VAD_MODEL}"
else
    echo "✓ Silero VAD already exists: ${VAD_MODEL}"
fi

# 2. Check or download MT GGUF model
MT_MODEL="${MODELS_DIR}/mt-model.gguf"
if [[ ! -f "${MT_MODEL}" ]]; then
    echo ""
    echo "Notice: Machine Translation GGUF model not found at ${MT_MODEL}"
    echo "You can download Hy-MT2-1.8B Q4_K_M (~1.1 GB) from HuggingFace:"
    echo ""
    echo "  curl -L -o models/mt-model.gguf \\"
    echo "    https://huggingface.co/mradermacher/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B.Q4_K_M.gguf"
    echo ""
    read -p "Do you want to download Hy-MT2-1.8B GGUF now? (y/N): " -n 1 -r || true
    echo ""
    if [[ ${REPLY:-n} =~ ^[Yy]$ ]]; then
        echo "Downloading Hy-MT2-1.8B GGUF model (~1.13 GB)..."
        curl -L --fail --progress-bar -o "${MT_MODEL}" "https://huggingface.co/mradermacher/Hy-MT2-1.8B-GGUF/resolve/main/Hy-MT2-1.8B.Q4_K_M.gguf" || {
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
