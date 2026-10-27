#!/usr/bin/env bash
# Xoá model trong models/ mà chế độ chỉ nghe không dùng (docs 10 §10): model dịch Qwen (.gguf), model Whisper cũ, ...
# Mặc định chỉ liệt kê. Thêm --yes để xoá thật.
#
# Giữ lại:
#   silero_vad.onnx                                   VAD
#   phowhisper-large-ct2/                             tiếng Việt
#   whisper/models--*--faster-whisper-large-v3-turbo/   large-v3-turbo (cache của faster-whisper, repo mobiuslabsgmbh)
# Giữ thêm bằng biến RVT_KEEP_MODELS (mẫu kiểu shell, cách nhau bởi dấu cách), ví dụ khi đã chọn model tiếng Nhật khác:
#   RVT_KEEP_MODELS="whisper/models--Systran--faster-whisper-large-v3 whisper/models--kotoba-tech--*"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${RVT_MODELS_DIR:-${PROJECT_ROOT}/models}"
APPLY=0
[[ "${1:-}" == "--yes" ]] && APPLY=1

KEEP=(
    "silero_vad.onnx"
    "phowhisper-large-ct2"
    "whisper/models--*--faster-whisper-large-v3-turbo"
    "whisper/.locks"
)
# Tách theo dấu cách nhưng không bung mẫu "*" thành file trong thư mục hiện tại
set -f
# shellcheck disable=SC2206
KEEP+=(${RVT_KEEP_MODELS:-})
set +f

# Model đang chọn qua RVT_ASR_MODELS (trên shell, .env hoặc docker/.env), ví dụ "ja=large-v3": giữ cache của chúng
ASR_MODELS="${RVT_ASR_MODELS:-}"
if [[ -z "${ASR_MODELS}" ]]; then
    for env_file in "${PROJECT_ROOT}/.env" "${PROJECT_ROOT}/docker/.env"; do
        line="$(grep -s '^RVT_ASR_MODELS=' "${env_file}" | tail -1 || true)"
        if [[ -n "${line}" ]]; then
            ASR_MODELS="${line#RVT_ASR_MODELS=}"
            ASR_MODELS="${ASR_MODELS//\"/}"
            ASR_MODELS="${ASR_MODELS//\'/}"
            break
        fi
    done
fi
IFS=',' read -ra ASR_PAIRS <<< "${ASR_MODELS}"
for pair in ${ASR_PAIRS[@]+"${ASR_PAIRS[@]}"}; do
    model="${pair#*=}"
    model="${model// /}"
    [[ -z "${model}" || "${model}" == "${pair}" ]] && continue
    if [[ "${model}" == */* ]]; then
        KEEP+=("whisper/models--${model//\//--}")  # repo Hugging Face: a/b → models--a--b
    else
        KEEP+=("${model}" "whisper/models--*--faster-whisper-${model}")  # thư mục trong models/ hoặc tên ngắn
    fi
done

is_kept() {
    local rel="$1" k
    for k in "${KEEP[@]}"; do
        # shellcheck disable=SC2053
        [[ "${rel}" == ${k} ]] && return 0  # ${k} không trong ngoặc kép: so như mẫu (có *)
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
