#!/usr/bin/env bash
# Chuẩn bị model cho chế độ chỉ nghe trên GPU 8 GB (docs 10 §10.3, §11.1):
#   - Silero VAD (models/silero_vad.onnx)
#   - PhoWhisper-large cho tiếng Việt, chuyển sang CTranslate2 (models/phowhisper-large-ct2)
#   - faster-whisper large-v3-turbo cho tiếng Anh, tải trước vào models/whisper (container cũng tự tải nếu thiếu)
# Không tải model dịch Qwen. Cần uv trên máy (https://docs.astral.sh/uv/) và mạng tới Hugging Face.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${PROJECT_ROOT}/models"
PHOWHISPER_REPO="${RVT_PHOWHISPER_REPO:-vinai/PhoWhisper-large}"
PHOWHISPER_DIR="${MODELS_DIR}/phowhisper-large-ct2"
EN_REPO="${RVT_EN_ASR_REPO:-Systran/faster-whisper-large-v3-turbo}"
mkdir -p "${MODELS_DIR}"

echo "== 1/3 Silero VAD"
RVT_SKIP_MT=1 "${SCRIPT_DIR}/download_models.sh"

if ! command -v uv >/dev/null 2>&1; then
    echo "✗ Cần uv để chuyển model: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

echo "== 2/3 ${PHOWHISPER_REPO} → ${PHOWHISPER_DIR}"
echo "   (lần đầu tải torch CPU và model ~3 GB, mất vài phút)"
uv run --no-project --python 3.12 \
    --with ctranslate2 --with "transformers[torch]" --with huggingface_hub \
    python "${SCRIPT_DIR}/convert_whisper_ct2.py" "${PHOWHISPER_REPO}" "${PHOWHISPER_DIR}" "$@"

echo "== 3/3 ${EN_REPO} → ${MODELS_DIR}/whisper"
uv run --no-project --python 3.12 --with huggingface_hub python - "${EN_REPO}" "${MODELS_DIR}/whisper" <<'PY'
import sys
from huggingface_hub import snapshot_download

path = snapshot_download(sys.argv[1], cache_dir=sys.argv[2])
print(f"✓ {sys.argv[1]}: {path}")
PY

echo "✓ Xong. Khởi động: ./start.sh --listen"
echo "  Xoá model không còn dùng (Qwen, model Whisper cũ): ./scripts/remove_unused_models.sh"
