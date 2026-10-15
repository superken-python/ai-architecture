#!/usr/bin/env bash
# Xoá model trong models/ mà chế độ chỉ nghe không dùng (docs 10 §10): model dịch Qwen (.gguf), model Whisper cũ, ...
# Mặc định chỉ liệt kê. Thêm --yes để xoá thật.
#
# Giữ lại:
#   silero_vad.onnx                                   VAD
#   phowhisper-large-ct2/                             tiếng Việt
#   whisper/models--Systran--faster-whisper-large-v3-turbo/   tiếng Anh (cache của faster-whisper)
# Giữ thêm bằng biến RVT_KEEP_MODELS, ví dụ RVT_KEEP_MODELS="whisper/models--Systran--faster-whisper-large-v3".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${RVT_MODELS_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)/models}"
APPLY=0
[[ "${1:-}" == "--yes" ]] && APPLY=1

KEEP=(
    "silero_vad.onnx"
    "phowhisper-large-ct2"
    "whisper/models--Systran--faster-whisper-large-v3-turbo"
    "whisper/.locks"
)
# shellcheck disable=SC2206
KEEP+=(${RVT_KEEP_MODELS:-})

is_kept() {
    local rel="$1" k
    for k in "${KEEP[@]}"; do
        [[ "${rel}" == "${k}" ]] && return 0
    done
    return 1
}

if [[ ! -d "${MODELS_DIR}" ]]; then
    echo "Không có thư mục ${MODELS_DIR}"
    exit 0
fi

CANDIDATES=()
shopt -s nullglob dotglob
for entry in "${MODELS_DIR}"/*; do
    rel="${entry#"${MODELS_DIR}"/}"
    if [[ "${rel}" == "whisper" && -d "${entry}" && ! -L "${entry}" ]]; then
        # Trong cache faster-whisper chỉ giữ model đang dùng
        for sub in "${entry}"/*; do
            subrel="whisper/${sub#"${entry}"/}"
            is_kept "${subrel}" || CANDIDATES+=("${subrel}")
        done
        continue
    fi
    is_kept "${rel}" || CANDIDATES+=("${rel}")
done

if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
    echo "✓ Không có model nào thừa trong ${MODELS_DIR}"
    exit 0
fi

echo "Model không dùng trong ${MODELS_DIR}:"
for rel in "${CANDIDATES[@]}"; do
    path="${MODELS_DIR}/${rel}"
    if [[ -L "${path}" ]]; then
        size="symlink"
    else
        size="$(du -sh "${path}" 2>/dev/null | cut -f1)"
    fi
    printf "  %-8s %s\n" "${size}" "${rel}"
done

if [[ ${APPLY} -eq 0 ]]; then
    echo ""
    echo "Chưa xoá gì. Chạy lại với --yes để xoá các mục trên."
    exit 0
fi

for rel in "${CANDIDATES[@]}"; do
    rm -rf -- "${MODELS_DIR:?}/${rel}"
    echo "✗ đã xoá ${rel}"
done
echo "✓ Xong."
