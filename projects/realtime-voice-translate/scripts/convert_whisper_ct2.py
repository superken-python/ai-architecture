"""Chuyển một model Whisper dạng Hugging Face (ví dụ vinai/PhoWhisper-large) sang CTranslate2 cho faster-whisper.

Chạy qua scripts/prepare_listen_models.sh, cần ctranslate2, transformers, torch (CPU là đủ):

    uv run --no-project --with "ctranslate2==4.8.4" --with "transformers[torch]==5.21.0" --with huggingface_hub \\
        python scripts/convert_whisper_ct2.py vinai/PhoWhisper-large models/phowhisper-large-ct2

- Mặc định lưu trọng số ở float16, độ chính xác gốc của model (docs 10 §13.1).
- Ghi kèm tokenizer.json và preprocessor_config.json mà faster-whisper cần (docs 10 §10.3).
- Model gốc chỉ tải những file cần (cấu hình, tokenizer, một loại trọng số) vào <output_dir>.download. Chuyển xong thì
  xoá; lỗi giữa chừng thì giữ, để lần chạy lại không phải tải lại.
"""

import argparse
import fnmatch
import os
import shutil
import sys

# Trọng số PyTorch, ưu tiên safetensors. Trọng số TensorFlow, Flax, ONNX (nếu repo có kèm) không tải.
WEIGHT_PATTERNS = ("*.safetensors", "*.bin")


def allow_patterns(repo_files: list[str]) -> list[str]:
    """Mẫu file cần tải: cấu hình và tokenizer (.json, .txt), cộng một loại trọng số có trong repo."""
    for pattern in WEIGHT_PATTERNS:
        if any(fnmatch.fnmatch(f, pattern) for f in repo_files):
            return ["*.json", "*.txt", pattern]
    sys.exit("✗ Repo không có trọng số PyTorch (.safetensors hoặc .bin)")


def download(repo: str, dest: str) -> str:
    from huggingface_hub import list_repo_files, snapshot_download

    return snapshot_download(repo, local_dir=dest, allow_patterns=allow_patterns(list_repo_files(repo)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", help="repo Hugging Face hoặc thư mục model Whisper dạng transformers")
    parser.add_argument("output_dir")
    parser.add_argument("--quantization", default="float16", help="kiểu lưu trọng số; khi chạy vẫn chọn compute_type")
    parser.add_argument("--force", action="store_true", help="ghi đè thư mục đã có")
    args = parser.parse_args()

    from ctranslate2.converters import TransformersConverter
    from transformers import WhisperFeatureExtractor, WhisperTokenizerFast

    if os.path.exists(os.path.join(args.output_dir, "model.bin")) and not args.force:
        print(f"✓ {args.output_dir} đã có, bỏ qua (thêm --force để chuyển lại)")
        return

    download_dir = None
    if os.path.isdir(args.model):
        source = args.model
    else:
        download_dir = args.output_dir + ".download"
        source = download(args.model, download_dir)
    tmp_dir = args.output_dir + ".tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    # Lưu float16 thì đọc trọng số thẳng ở float16: kết quả như nhau, RAM lúc chuyển còn khoảng một nửa
    converter = TransformersConverter(source, load_as_float16=args.quantization == "float16")
    converter.convert(tmp_dir, quantization=args.quantization, force=True)
    # Tokenizer nhanh (tokenizer.json) và cấu hình đặc trưng âm thanh (số kênh mel) cho faster-whisper
    WhisperTokenizerFast.from_pretrained(source).save_pretrained(tmp_dir)
    WhisperFeatureExtractor.from_pretrained(source).save_pretrained(tmp_dir)
    for required in ("model.bin", "tokenizer.json", "preprocessor_config.json"):
        if not os.path.exists(os.path.join(tmp_dir, required)):
            sys.exit(f"✗ Thiếu {required} sau khi chuyển; giữ lại {tmp_dir} để kiểm tra")
    shutil.rmtree(args.output_dir, ignore_errors=True)
    os.replace(tmp_dir, args.output_dir)
    if download_dir:
        shutil.rmtree(download_dir, ignore_errors=True)
    print(f"✓ Đã chuyển {args.model} → {args.output_dir} ({args.quantization})")


if __name__ == "__main__":
    main()
