# 11 · Hướng dẫn: tải model PyTorch về và chuyển sang CTranslate2 float16

**Ví dụ: PhoWhisper-large, 6,2 GB → 3,1 GB.** Cập nhật 2026-10-28.

Bài này đi lại đúng các bước đã làm để có `models/phowhisper-large-ct2`. Đây là model nghe tiếng Việt mà app nạp ở
`float16` khi nửa nói khoá "Tiếng Việt" (docs 10 §13.7, bước 8). Cách làm dùng được cho mọi model Whisper lưu dạng
transformers (PyTorch).

| | |
|---|---|
| Model gốc | [`vinai/PhoWhisper-large`](https://huggingface.co/vinai/PhoWhisper-large): Whisper large-v2 fine-tune cho tiếng Việt, 1,55 tỉ tham số, giấy phép BSD-3-Clause |
| Đầu vào | `pytorch_model.bin` 6,2 GB (float32, định dạng PyTorch), cộng cấu hình và tokenizer |
| Đầu ra | `models/phowhisper-large-ct2/`, khoảng 3,1 GB (float16, định dạng CTranslate2), chạy bằng faster-whisper |
| Lệnh | `./scripts/prepare_listen_models.sh`, hoặc gọi thẳng [`scripts/convert_whisper_ct2.py`](../scripts/convert_whisper_ct2.py) |
| Máy | Linux có `uv`, mạng tới Hugging Face, khoảng 10 GB trống trong `models/` lúc chuyển. CPU là đủ, không cần GPU |

## 1. "Nén" ở đây là gì

- **Không phải nén kiểu zip.** Kích thước model = số tham số × số byte mỗi tham số.
  - File gốc lưu mỗi tham số bằng float32 (4 byte): 1,55 tỉ × 4 ≈ 6,2 GB.
  - Đổi sang float16 (2 byte): 1,55 tỉ × 2 ≈ 3,1 GB.
- **float16 không làm mất độ chính xác đáng kể khi suy luận.** Whisper gốc của OpenAI cũng chạy float16 trên GPU. Đổi
  tiếp xuống int8 (1 byte) thì nhỏ hơn nữa, nhưng có sai số nhỏ, phải đo lại.
- **Đồng thời đổi định dạng:** từ PyTorch (cho thư viện transformers) sang CTranslate2 (cho faster-whisper).
  CTranslate2 là thư viện suy luận viết bằng C++, nhanh hơn và tốn ít VRAM hơn chạy thẳng bằng PyTorch. App vẫn dùng nó
  cho large-v3-turbo.

| Kiểu lưu | Byte mỗi tham số | PhoWhisper-large | Model tí hon đã thử (đo thật) | Dùng khi |
|---|---|---|---|---|
| float32 | 4 | 6,2 GB (file gốc) | 14,55 MB | Huấn luyện; file gốc trên Hugging Face |
| **float16** | 2 | **~3,1 GB** | **7,28 MB** | **Đang dùng:** chạy trên GPU, giữ độ chính xác |
| int8_float16 | ~1 | ~1,6 GB (ước tính) | 3,99 MB | Thiếu VRAM; phải đo lại độ chính xác |

Model tí hon là model thử ở mục 6: 3,65 triệu tham số, cùng bố cục với PhoWhisper-large. Bản `int8` đo được 4,24 MB,
lớn hơn `int8_float16` vì các tham số không bị lượng tử được lưu float32 thay vì float16.

**Kiểu lưu khác kiểu chạy.** Kiểu lưu đặt bằng `--quantization` lúc chuyển. Kiểu chạy đặt bằng `compute_type` lúc nạp
(trong profile của app).

- Model lưu float16 chạy được `float16`, hoặc `int8_float16` (CTranslate2 tự lượng tử lúc nạp). large-v3-turbo trước
  đây là như vậy: file float16, chạy `int8_float16`, VRAM đo được 1,1 GB.
- Model lưu int8 thì chạy `float16` cũng không lấy lại phần độ chính xác đã mất. Vì vậy lưu float16 là lựa chọn an
  toàn: sau này chạy kiểu nào cũng được.
- CPU không có kiểu float16. Trên CPU, app tự lùi về `int8`.

## 2. Công cụ

| Công cụ | Vai trò | Bản đã thử |
|---|---|---|
| `uv` | Chạy Python và thư viện trong môi trường tạm, không cài vào máy | — |
| `huggingface_hub` | Liệt kê file trong repo, tải file | 2.3.0 |
| `transformers` + `torch` | Đọc model PyTorch (chạy CPU là đủ) | 5.21.0 + 2.14.1 |
| `ctranslate2` | Bộ chuyển `TransformersConverter`, và runtime trong app | 4.8.4 khi chuyển, 4.8.2 khi nạp |
| `faster-whisper` | Chạy model CTranslate2 trong app | 1.2.1 |

Script ghim `ctranslate2==4.8.4` và `transformers==5.21.0`. transformers 5.x đổi API so với 4.x (mục 5), nên ghim bản
đã thử để lần chuyển nào cũng giống nhau.

## 3. Chạy

Cách nhanh, trên máy GPU, trong thư mục dự án:

```bash
./scripts/prepare_listen_models.sh   # Silero VAD (nếu thiếu), PhoWhisper-large → CTranslate2 float16, turbo (nếu thiếu)
docker restart rvt_ai                # nạp model mới
uv cache clean                       # torch, transformers chỉ cần lúc chuyển
```

Chỉ chuyển một model:

```bash
uv run --no-project --python 3.12 \
    --with "ctranslate2==4.8.4" --with "transformers[torch]==5.21.0" --with huggingface_hub \
    python scripts/convert_whisper_ct2.py vinai/PhoWhisper-large models/phowhisper-large-ct2
```

Thêm `--quantization int8_float16` để lưu nhỏ hơn, `--force` để chuyển lại khi thư mục đích đã có.

## 4. Từng bước script làm

### Bước 1 · Xem repo có file gì, chỉ tải file cần

```python
files = list_repo_files("vinai/PhoWhisper-large")
weights = "*.safetensors" if any(f.endswith(".safetensors") for f in files) else "*.bin"
snapshot_download("vinai/PhoWhisper-large", local_dir="models/phowhisper-large-ct2.download",
                  allow_patterns=["*.json", "*.txt", weights])
```

| File | Để làm gì |
|---|---|
| `config.json` | Kiến trúc: số lớp, kích thước, 80 kênh mel |
| `generation_config.json` | Token đặc biệt, mã các ngôn ngữ, các token bị chặn khi sinh chữ |
| `pytorch_model.bin` | Trọng số, float32, 6,2 GB |
| `vocab.json`, `merges.txt`, `tokenizer_config.json`, `added_tokens.json`, `special_tokens_map.json` | Tokenizer: cách cắt chữ thành token và các token đặc biệt |
| `preprocessor_config.json` | Cách biến âm thanh thành phổ mel |
| `normalizer.json` | Chuẩn hoá chữ tiếng Anh khi chấm điểm; app không dùng |

- **Không tải** trọng số dành cho TensorFlow, Flax, ONNX (`tf_model.h5`, `flax_model.msgpack`, `*.onnx`) nếu repo có
  kèm. Mỗi bản thêm vài GB mà không dùng.
- **Repo có cả `.safetensors` lẫn `.bin`** thì chỉ lấy `.safetensors`: đọc nhanh hơn, và không chạy code lúc đọc như
  file pickle `.bin`.
- **Tải vào `<đích>.download`** cạnh thư mục đích, không vào cache chung `~/.cache/huggingface`, để xoá gọn sau khi
  chuyển xong.

### Bước 2 · Đọc trọng số ở float16

```python
converter = TransformersConverter(source, load_as_float16=True)
```

transformers đọc `pytorch_model.bin` và đổi sang float16 ngay lúc nạp (`from_pretrained(..., dtype=torch.float16)`).
Model nằm trong RAM chỉ còn khoảng một nửa so với đọc float32 rồi mới đổi (ước tính, chưa đo trên model thật). Kết
quả như nhau, vì bước 3 cũng làm tròn về float16.

### Bước 3 · Chuyển sang CTranslate2

```python
converter.convert("models/phowhisper-large-ct2.tmp", quantization="float16", force=True)
```

Ra ba file:

- `model.bin`: trọng số, khoảng 3,1 GB.
- `config.json`: mã 99 ngôn ngữ, các token bị chặn, các đầu attention dùng để canh thời gian từng từ.
- `vocabulary.json`: 51 865 token.

### Bước 4 · Ghi `tokenizer.json` và `preprocessor_config.json`

```python
WhisperTokenizerFast.from_pretrained(source).save_pretrained(tmp_dir)
WhisperFeatureExtractor.from_pretrained(source).save_pretrained(tmp_dir)
```

- **`tokenizer.json`:** faster-whisper đọc file này. Thiếu nó, faster-whisper tải tokenizer của `openai/whisper-tiny`
  từ mạng mỗi lần nạp model. Repo chỉ có `vocab.json` + `merges.txt` thì transformers dựng `tokenizer.json` từ hai
  file đó.
- **`preprocessor_config.json`:** ghi số kênh mel, 80 với model gốc large-v2 (như PhoWhisper), 128 với large-v3. Sai
  số kênh thì model không chạy được.

### Bước 5 · Kiểm đủ file, đổi tên, dọn

- **Đủ file:** có đủ `model.bin`, `tokenizer.json`, `preprocessor_config.json` thì đổi tên `.tmp` thành thư mục đích
  trong một lần, nên không bao giờ có thư mục đích dở dang. Sau đó xoá `.download`.
- **Lỗi giữa chừng** (hết RAM, mất mạng): `.download` được giữ lại, chạy lại không phải tải lại.
- **Thư mục đích đã có `model.bin`** thì bỏ qua; thêm `--force` để chuyển lại.

### Bước 6 · Nạp và kiểm

Profile `api-mt` và `listen` có sẵn `vi: "phowhisper-large-ct2"` và `compute_type: "float16"`, nên chỉ cần khởi
động lại container:

```bash
docker restart rvt_ai
docker logs --since 5m rvt_ai 2>&1 | grep -E "Loading|ASR model|Falling back"
nvidia-smi
```

- **Log phải có hai dòng:**
  - `Loading ASR model for 'vi': /models/phowhisper-large-ct2`
  - `Loading faster-whisper model '/models/phowhisper-large-ct2' on cuda (float16)`
- **Log không có** `Falling back` hay `not found`.
- **VRAM** khoảng 5 GB khi có cả turbo và PhoWhisper (ước tính, chưa đo).
- **Trên web:** chọn "Nói: Tiếng Việt" thì dùng PhoWhisper. "Tự động", tiếng Nhật, tiếng Anh vẫn dùng turbo.

Thử riêng bằng Python, không qua app:

```python
from faster_whisper import WhisperModel

model = WhisperModel("models/phowhisper-large-ct2", device="cuda", compute_type="float16")
print(model.model.n_mels)  # 80
segments, _ = model.transcribe("mau-tieng-viet.wav", language="vi")
print(" ".join(s.text for s in segments))
```

## 5. Lỗi đã gặp hoặc dễ gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `No module named 'transformers.models.whisper.convert_openai_to_hf'` | transformers 5.x bỏ các script chuyển đổi khỏi gói | Không cần; script của dự án không dùng |
| Tài liệu cũ dùng `WhisperTokenizerFast`, sợ bản mới không còn | transformers 5.x gộp tokenizer chậm và nhanh thành một lớp | Vẫn import được (là `WhisperTokenizer`); đã thử với 5.21.0, bản ghim |
| `Requested float16 compute type, but the target device or backend do not support efficient float16 computation` | Chạy float16 trên CPU | App tự lùi về CPU int8; trên GPU không gặp |
| Model nạp được nhưng lỗi kích thước hoặc ra chữ rác | `preprocessor_config.json` sai số kênh mel | Ghi lại từ model gốc (bước 4) |
| Nạp model cần mạng, chậm | Thiếu `tokenizer.json` | Bước 4 |
| Hết RAM khi chuyển | Đọc trọng số float32 | `load_as_float16` (bước 2); tắt bớt chương trình khác |
| Hết đĩa | Lúc chuyển cần cả bản tải 6,2 GB lẫn bản ra 3,1 GB | Dọn `models/`, `uv cache clean` |
| Model trong `models/whisper` hỏng sau khi xoá tay | huggingface_hub bản mới để dữ liệu thật trong kho chung `whisper/blobs/` | Dùng `scripts/remove_unused_models.sh`, đừng xoá tay `whisper/blobs` (docs 10 §13.7) |

## 6. Đã kiểm, chưa kiểm

- **Đã kiểm trong sandbox (2026-10-27, 28):** sandbox không ra được Hugging Face, nên thử trên model Whisper tí hon,
  trọng số ngẫu nhiên, cùng bố cục với `vinai/PhoWhisper-large`:
  - bố cục: 80 kênh mel, 99 ngôn ngữ, 51 865 token, `pytorch_model.bin` float32, tokenizer kiểu transformers 4.x, có
    và không có `tokenizer.json`;
  - chuyển bằng đúng hai bản đã ghim: ra đủ file faster-whisper cần; trọng số float16 đúng bằng nửa float32 (bảng mục
    1);
  - chỉ tải cấu hình, tokenizer và `.bin`, bỏ bản TensorFlow, Flax; lỗi giữa chừng thì giữ bản tải, xong thì xoá;
  - app nạp được bằng ctranslate2 4.8.2, cũ hơn bản dùng để chuyển; phiên khoá tiếng Việt chạy qua model này.
- **Chưa kiểm:**
  - chuyển PhoWhisper-large thật;
  - VRAM, độ trễ trên GPU;
  - độ chính xác tiếng Việt so với large-v3-turbo.

## 7. Dùng cho model khác

- **Model Whisper khác dạng transformers** (fine-tune tiếng Việt khác, anime-whisper cho phim hoạt hình,
  kotoba-whisper):
  - chạy cùng lệnh ở mục 3, đổi tên repo và thư mục đích (đuôi `-ct2`);
  - rồi đặt `RVT_ASR_MODELS=ja=<tên>-ct2` trong `.env`, hoặc sửa `models:` trong profile;
  - riêng anime-whisper: tác giả khuyên không đưa prompt vào model. App đang gửi prompt ngữ cảnh mỗi câu chốt, nên phải
    thêm tuỳ chọn tắt prompt trước khi dùng.
- **Model đã có sẵn bản CTranslate2** (large-v3-turbo của mobiuslabsgmbh, `kotoba-tech/kotoba-whisper-v2.0-faster`):
  không cần chuyển, faster-whisper tự tải.
- **LLM (Qwen2.5-7B dịch, stack cũ) đi đường khác:** lượng tử GGUF cho llama.cpp.
  - Dự án tải bản GGUF người khác đã lượng tử sẵn (bartowski), không tự chuyển: Q5_K_M 5,44 GB, Q4_K_M 4,68 GB
    (docs 09, mục "Cập nhật 2026-10-13").
  - Tự chuyển thì dùng `convert_hf_to_gguf.py` rồi `llama-quantize` của llama.cpp. Chưa làm trong dự án.
- **ONNX, TensorRT, AWQ, GPTQ:** chưa làm trong dự án.

## 8. Trong 9 nhóm bài toán đã có hướng dẫn nào chưa

Rà ngày 2026-10-28 các dự án g1–g9, `labs/` và `docs/`:

- **Chưa có bài hướng dẫn từng bước nào** về tải, chuyển định dạng hay lượng tử model. Bài này là bài đầu tiên.
- **Kỹ năng liên quan mới có thẻ trong danh mục, chưa có lab:**
  - [OPS-05 Tối ưu suy luận và serving model](../../../docs/02-skill-map/generated/mang/ops.md#ops-05): mức trung cấp
    là quantization int8, ONNX Runtime/TensorRT. Cốt lõi cho Nhóm 5 Ảnh/tài liệu; cần cho Nhóm 3, 4, 6.
  - LLM-07 Fine-tune, distill và tự host LLM: mức nâng cao có quantization AWQ/GPTQ. Cần cho Nhóm 5, 6.
- **Ghi chú rải rác trong dự án này:**
  - docs 01 §5: chọn model và kiểu số cho GPU 8 GB;
  - docs 09: đổi Qwen sang Q5_K_M;
  - docs 10 §13: float16, PhoWhisper.
- **g9 (video chữ cái)** dùng model nhận dạng int8 dựng sẵn (sherpa-onnx zipformer-vi), không tự chuyển.
- **Nếu muốn thành lab:** tách bài này thành `labs/ops-05-trung-cap-...`. Trên một model nhỏ, đo kích thước, tốc độ và
  CER theo float32, float16, int8.

## Nguồn

- [vinai/PhoWhisper-large](https://huggingface.co/vinai/PhoWhisper-large),
  [VinAIResearch/PhoWhisper](https://github.com/VinAIResearch/PhoWhisper).
- CTranslate2: [Quantization](https://opennmt.net/CTranslate2/quantization.html),
  [Transformers](https://opennmt.net/CTranslate2/guides/transformers.html).
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
