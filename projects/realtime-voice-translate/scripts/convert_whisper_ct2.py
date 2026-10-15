"""Chuyển một model Whisper dạng Hugging Face (ví dụ vinai/PhoWhisper-large) sang CTranslate2 cho faster-whisper.

Chạy qua scripts/prepare_listen_models.sh, cần ctranslate2, transformers, torch (CPU là đủ):

    uv run --no-project --with ctranslate2 --with "transformers[torch]" --with huggingface_hub \\
        python scripts/convert_whisper_ct2.py vinai/PhoWhisper-large models/phowhisper-large-ct2

Ghi kèm tokenizer.json và preprocessor_config.json mà faster-whisper cần (docs 10 §10.3).
"""

import argparse
import os
import shutil
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", help="repo Hugging Face hoặc thư mục model Whisper dạng transformers")
    parser.add_argument("output_dir")
    parser.add_argument("--quantization", default="float16", help="kiểu lưu trọng số; khi chạy vẫn chọn compute_type")
    parser.add_argument("--force", action="store_true", help="ghi đè thư mục đã có")
    args = parser.parse_args()

    from ctranslate2.converters import TransformersConverter
    from huggingface_hub import snapshot_download
    from transformers import WhisperFeatureExtractor, WhisperTokenizerFast

    if os.path.exists(os.path.join(args.output_dir, "model.bin")) and not args.force:
        print(f"✓ {args.output_dir} đã có, bỏ qua (thêm --force để chuyển lại)")
        return

    source = args.model if os.path.isdir(args.model) else snapshot_download(args.model)
    tmp_dir = args.output_dir + ".tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    TransformersConverter(source).convert(tmp_dir, quantization=args.quantization, force=True)
    # Tokenizer nhanh (tokenizer.json) và cấu hình đặc trưng âm thanh (số kênh mel) cho faster-whisper
    WhisperTokenizerFast.from_pretrained(source).save_pretrained(tmp_dir)
    WhisperFeatureExtractor.from_pretrained(source).save_pretrained(tmp_dir)
    for required in ("model.bin", "tokenizer.json", "preprocessor_config.json"):
        if not os.path.exists(os.path.join(tmp_dir, required)):
            sys.exit(f"✗ Thiếu {required} sau khi chuyển; giữ lại {tmp_dir} để kiểm tra")
    shutil.rmtree(args.output_dir, ignore_errors=True)
    os.replace(tmp_dir, args.output_dir)
    print(f"✓ Đã chuyển {args.model} → {args.output_dir}")


if __name__ == "__main__":
    main()
