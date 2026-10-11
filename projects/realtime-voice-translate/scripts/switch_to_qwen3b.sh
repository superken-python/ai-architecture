#!/usr/bin/env bash
# ==============================================================================
# Script: switch_to_qwen3b.sh
# Purpose: Xóa các model dịch cũ (Hy-MT, TranslateGemma, mt-model cũ) để giải phóng
#          dung lượng ổ đĩa, sau đó tải model mới Qwen 2.5 - 3B Instruct GGUF.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${PROJECT_ROOT}/models"

QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
TARGET_FILE="${MODELS_DIR}/mt-model.gguf"
SYMLINK_FILE="${MODELS_DIR}/qwen2.5-3b-instruct-q4_k_m.gguf"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}   🚀 NÂNG CẤP MODEL DỊCH SANG QWEN 2.5 - 3B INSTRUCT (GGUF)     ${NC}"
echo -e "${CYAN}==================================================================${NC}"

mkdir -p "${MODELS_DIR}"

echo -e "\n${YELLOW}📊 Dung lượng ổ đĩa hiện tại:${NC}"
FORCE=0
CLEAN_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --force|-f)
            FORCE=1
            ;;
        --clean-only)
            CLEAN_ONLY=1
            ;;
    esac
done

df -h "${PROJECT_ROOT}"

# 1. Tìm các file model cũ cần xoá
OLD_FILES=()
while IFS= read -r -d '' f; do
    OLD_FILES+=("$f")
done < <(find "${MODELS_DIR}" -maxdepth 1 -type f \( -iname "*hy-mt*" -o -iname "*translategemma*" -o -name "mt-model.gguf" \) -print0)

if [[ ${#OLD_FILES[@]} -gt 0 ]]; then
    echo -e "\n${YELLOW}🔍 Phát hiện các file model cũ cần dọn dẹp:${NC}"
    for f in "${OLD_FILES[@]}"; do
        SIZE=$(du -h "$f" | cut -f1)
        echo -e "   - $(basename "$f") (${SIZE})"
    done

    CLEAN_CONFIRM="y"
    if [ -t 0 ] && [[ ${FORCE} -eq 0 ]]; then
        echo -e "\n${CYAN}Bạn có muốn xoá các file model cũ trên để giải phóng ổ cứng không? [Y/n]${NC}"
        read -r -p "Xác nhận (mặc định Y): " USER_INPUT || USER_INPUT="y"
        CLEAN_CONFIRM="${USER_INPUT:-y}"
    fi

    if [[ "${CLEAN_CONFIRM}" =~ ^[Yy]$ ]]; then
        echo -e "\n${GREEN}🗑️  Đang dọn dẹp các model cũ...${NC}"
        for f in "${OLD_FILES[@]}"; do
            rm -f "$f"
            echo -e "   ✓ Đã xoá: $(basename "$f")"
        done
        echo -e "${GREEN}✓ Đã dọn dẹp thành công!${NC}"
        echo -e "${YELLOW}📊 Dung lượng ổ đĩa sau khi xoá:${NC}"
        df -h "${PROJECT_ROOT}"
    else
        echo -e "${YELLOW}Bỏ qua bước xoá model cũ.${NC}"
    fi
else
    echo -e "\n${GREEN}✓ Không phát hiện file model cũ nào trong ${MODELS_DIR}.${NC}"
fi

# Nếu chạy với flag --clean-only thì dừng ở đây
if [[ ${CLEAN_ONLY} -eq 1 ]]; then
    echo -e "\n${GREEN}✓ Đã hoàn tất chế độ dọn dẹp (--clean-only).${NC}"
    exit 0
fi

# 2. Tải model mới Qwen 2.5 - 3B Instruct
echo -e "\n${CYAN}==================================================================${NC}"
echo -e "${CYAN}📥 TẢI MODEL MỚI: Qwen2.5-3B-Instruct Q4_K_M (~2.16 GB)${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo -e "Source: ${QWEN_URL}"
echo -e "Target: ${TARGET_FILE}"

DO_DOWNLOAD="y"
if [ -t 0 ] && [[ ${FORCE} -eq 0 ]]; then
    echo -e "\n${CYAN}Bắt đầu tải model Qwen 2.5 - 3B ngay bây giờ? [Y/n]${NC}"
    read -r -p "Xác nhận (mặc định Y): " USER_DL || USER_DL="y"
    DO_DOWNLOAD="${USER_DL:-y}"
fi

if [[ "${DO_DOWNLOAD}" =~ ^[Yy]$ ]]; then
    echo -e "\n${CYAN}⏳ Đang tải file... (Vui lòng đợi vài phút tuỳ thuộc tốc độ mạng)${NC}"
    if curl -L --fail --progress-bar -o "${TARGET_FILE}" "${QWEN_URL}"; then
        # Tạo symlink mang tên model gốc để dễ tra cứu
        ln -sf "mt-model.gguf" "${SYMLINK_FILE}" || true
        FILE_SIZE=$(du -h "${TARGET_FILE}" | cut -f1)
        echo -e "\n${GREEN}🎉 TẢI THÀNH CÔNG MODEL QWEN 2.5 - 3B! (${FILE_SIZE})${NC}"
        echo -e "   File chính: ${TARGET_FILE}"
        echo -e "   Symlink:    ${SYMLINK_FILE}"
    else
        echo -e "\n${RED}❌ Tải thất bại. Vui lòng kiểm tra lại kết nối mạng hoặc tải thủ công vào ${TARGET_FILE}.${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}Bỏ qua bước tải model. Bạn có thể tải sau bằng lệnh:${NC}"
    echo -e "  curl -L -o models/mt-model.gguf ${QWEN_URL}"
fi

echo -e "\n${CYAN}==================================================================${NC}"
echo -e "${GREEN}✓ Hoàn tất! Để khởi động stack với Qwen 2.5 - 3B:${NC}"
echo -e "  ${YELLOW}./start.sh --gpu${NC} hoặc ${YELLOW}docker compose -f compose.ai.yaml up -d${NC}"
echo -e "${CYAN}==================================================================${NC}"
