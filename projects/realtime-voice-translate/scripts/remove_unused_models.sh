#!/usr/bin/env bash
# Xoá model trong models/ mà chế độ chỉ nghe không dùng (docs 10 §10): model dịch Qwen (.gguf), model Whisper cũ, ...
# Mặc định chỉ liệt kê. Thêm --yes để xoá thật. Không chạy lúc container đang tải model.
#
# Giữ lại:
#   silero_vad.onnx                                   VAD
#   phowhisper-large-ct2/                             tiếng Việt
#   whisper/models--*--faster-whisper-large-v3-turbo/   large-v3-turbo (cache của faster-whisper, repo mobiuslabsgmbh)
# Giữ thêm bằng biến RVT_KEEP_MODELS (mẫu kiểu shell, cách nhau bởi dấu cách), ví dụ khi đã chọn model tiếng Nhật khác:
#   RVT_KEEP_MODELS="whisper/models--Systran--faster-whisper-large-v3 whisper/models--kotoba-tech--*"
#
# whisper/ là cache Hugging Face: mỗi model là một thư mục models--<org>--<tên>. huggingface_hub bản mới để dữ liệu thật
# trong kho dùng chung whisper/blobs/<2 ký tự>/<mã băm>, thư mục models--* chỉ chứa liên kết tới đó (docs 10 §13.7).
# Nên trong whisper/ chỉ xoá thư mục models--*, không đụng blobs/, .locks/, CACHEDIR.TAG. Xoá model xong mới xoá các
# file trong kho không còn liên kết nào trỏ tới.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${RVT_MODELS_DIR:-${PROJECT_ROOT}/models}"
CACHE_DIR="${MODELS_DIR}/whisper"
STORE_DIR="${CACHE_DIR}/blobs"
APPLY=0
[[ "${1:-}" == "--yes" ]] && APPLY=1

KEEP=(
    "silero_vad.onnx"
    "phowhisper-large-ct2"
    "whisper/models--*--faster-whisper-large-v3-turbo"
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

# Dung lượng thật: model trong whisper/ đi theo liên kết vào kho whisper/blobs/
size_of() {
    local path="$1"
    if [[ -L "${path}" ]]; then
        echo "symlink"
    elif [[ "${path}" == "${CACHE_DIR}"/* ]]; then
        du -shL -- "${path}" 2>/dev/null | cut -f1 || true
    else
        du -sh -- "${path}" 2>/dev/null | cut -f1 || true
    fi
}

# In các file trong kho dùng chung whisper/blobs/ mà không liên kết nào trong cache trỏ tới, mỗi dòng một file.
# Không chắc thì không in gì: kho không có dấu của huggingface_hub, máy thiếu readlink -f (macOS cũ), có thư mục hay
# liên kết không đọc được (bỏ sót một liên kết là xoá nhầm dữ liệu của model còn dùng).
orphan_blobs() {
    [[ -f "${STORE_DIR}/.huggingface-shared-blobs" ]] || return 0
    local links used=$'\n' link target blob name prefix
    if ! readlink -f / >/dev/null 2>&1 || ! links="$(find "${CACHE_DIR}" -path "${STORE_DIR}" -prune -o -type l -print)"
    then
        echo "⚠ Không đọc hết được ${CACHE_DIR}: bỏ qua bước dọn whisper/blobs/" >&2
        return 0
    fi
    while IFS= read -r link; do
        [[ -n "${link}" && -e "${link}" ]] || continue  # liên kết hỏng không giữ file nào
        if ! target="$(readlink -f -- "${link}")"; then
            echo "⚠ Không đọc được ${link}: bỏ qua bước dọn whisper/blobs/" >&2
            return 0
        fi
        used+="${target}"$'\n'
    done <<< "${links}"
    for blob in "${STORE_DIR}"/??/*; do
        name="${blob##*/}"
        prefix="${blob%/*}"
        prefix="${prefix##*/}"
        [[ "${name}" =~ ^[0-9a-f]{64}$ && "${name:0:2}" == "${prefix}" && -f "${blob}" && ! -L "${blob}" ]] || continue
        target="$(readlink -f -- "${blob}")" || continue
        [[ "${used}" == *$'\n'"${target}"$'\n'* ]] || printf '%s\n' "${blob}"
    done
}

total_size() {
    du -ch -- "$@" 2>/dev/null | tail -1 | cut -f1 || true
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
        # Cache Hugging Face: chỉ thư mục models--* là model. blobs/ chứa dữ liệu của mọi model, kể cả model đang dùng
        for sub in "${entry}"/models--*; do
            subrel="whisper/${sub#"${entry}"/}"
            is_kept "${subrel}" || CANDIDATES+=("${subrel}")
        done
        continue
    fi
    is_kept "${rel}" || CANDIDATES+=("${rel}")
done

ORPHANS=()
while IFS= read -r blob; do ORPHANS+=("${blob}"); done < <(orphan_blobs)

if [[ ${#CANDIDATES[@]} -eq 0 && ${#ORPHANS[@]} -eq 0 ]]; then
    echo "✓ Không có model nào thừa trong ${MODELS_DIR}"
    exit 0
fi

echo "Model không dùng trong ${MODELS_DIR}:"
for rel in ${CANDIDATES[@]+"${CANDIDATES[@]}"}; do
    printf "  %-8s %s\n" "$(size_of "${MODELS_DIR}/${rel}")" "${rel}"
done
if [[ ${#ORPHANS[@]} -gt 0 ]]; then
    printf "  %-8s %s\n" "$(total_size "${ORPHANS[@]}")" "whisper/blobs/: ${#ORPHANS[@]} file không model nào dùng"
fi

if [[ ${APPLY} -eq 0 ]]; then
    echo ""
    echo "Chưa xoá gì. Chạy lại với --yes để xoá các mục trên."
    exit 0
fi

for rel in ${CANDIDATES[@]+"${CANDIDATES[@]}"}; do
    rm -rf -- "${MODELS_DIR:?}/${rel}"
    echo "✗ đã xoá ${rel}"
done

# Dữ liệu của model vừa xoá còn nằm trong kho dùng chung: xoá các file không còn liên kết nào trỏ tới
ORPHANS=()
while IFS= read -r blob; do ORPHANS+=("${blob}"); done < <(orphan_blobs)
if [[ ${#ORPHANS[@]} -gt 0 ]]; then
    freed="$(total_size "${ORPHANS[@]}")"
    for blob in "${ORPHANS[@]}"; do
        rm -f -- "${blob}" "${blob}.refs"
    done
    echo "✗ đã xoá ${#ORPHANS[@]} file trong whisper/blobs/ không còn model nào dùng (${freed})"
fi
echo "✓ Xong."
