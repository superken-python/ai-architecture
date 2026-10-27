#!/usr/bin/env bash
# Chuẩn bị model cho chế độ chỉ nghe trên GPU 8 GB (docs 10 §10.3, §11.1):
#   - Silero VAD (models/silero_vad.onnx)
#   - PhoWhisper-large cho tiếng Việt, chuyển sang CTranslate2, lưu float16 (models/phowhisper-large-ct2)
#   - faster-whisper large-v3-turbo cho tiếng Anh, tải trước vào models/whisper (container cũng tự tải nếu thiếu)
# Không tải model dịch Qwen. Cần uv trên máy (https://docs.astral.sh/uv/) và mạng tới Hugging Face.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${PROJECT_ROOT}/models"
PHOWHISPER_REPO="${RVT_PHOWHISPER_REPO:-vinai/PhoWhisper-large}"
PHOWHISPER_DIR="${MODELS_DIR}/phowhisper-large-ct2"
# Repo mà faster-whisper dùng cho tên "large-v3-turbo" (faster_whisper.utils._MODELS)
EN_REPO="${RVT_EN_ASR_REPO:-mobiuslabsgmbh/faster-whisper-large-v3-turbo}"
mkdir -p "${MODELS_DIR}"

echo "== 1/3 Silero VAD"
RVT_SKIP_MT=1 "${SCRIPT_DIR}/download_models.sh"

if ! command -v uv >/dev/null 2>&1; then
    echo "✗ Cần uv để chuyển model: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

echo "== 2/3 ${PHOWHISPER_REPO} → ${PHOWHISPER_DIR}"
echo "   (lần đầu tải torch, transformers vào bộ đệm của uv và model gốc 6,2 GB; lúc chuyển cần khoảng 10 GB trống)"
# Ghim bản để lần chuyển nào cũng như nhau; bản mới hơn của transformers có thể đổi API (docs 10 §13.7)
uv run --no-project --python 3.12 \
    --with "ctranslate2==4.8.4" --with "transformers[torch]==5.21.0" --with huggingface_hub \
    python "${SCRIPT_DIR}/convert_whisper_ct2.py" "${PHOWHISPER_REPO}" "${PHOWHISPER_DIR}" "$@"

echo "== 3/3 ${EN_REPO} → ${MODELS_DIR}/whisper"
# Đã có (container tự tải) thì bỏ qua, để huggingface_hub trên máy, có thể khác bản trong container, không ghi vào
# cache container đang dùng. Liên kết hỏng (docs 10 §13.7) thì -e sai, nên vẫn tải lại.
EN_MODEL_BIN=("${MODELS_DIR}/whisper/models--${EN_REPO//\//--}"/snapshots/*/model.bin)
if [[ -e "${EN_MODEL_BIN[0]}" ]]; then
    echo "✓ ${EN_REPO} đã có"
else
    uv run --no-project --python 3.12 --with huggingface_hub python - "${EN_REPO}" "${MODELS_DIR}/whisper" <<'PY'
import sys
from huggingface_hub import snapshot_download

path = snapshot_download(sys.argv[1], cache_dir=sys.argv[2])
print(f"✓ {sys.argv[1]}: {path}")
PY
fi

echo "✓ Xong. Stack đang chạy thì nạp model mới: docker restart rvt_ai. Chưa chạy: ./start.sh --api-mt hoặc --listen"
echo "  Bộ đệm của uv (torch, transformers) không còn cần cho app: uv cache clean"
echo "  Xoá model không còn dùng (Qwen, model Whisper cũ): ./scripts/remove_unused_models.sh"
