# OPS-05 · Trung cấp · Lượng tử model Whisper: kích thước, tốc độ, độ chính xác

**Kỹ năng:** [OPS-05 Tối ưu suy luận và serving model](../../docs/02-skill-map/generated/mang/ops.md#ops-05) · **Mức:** Trung cấp
(kèm [STAT-02](../../docs/02-skill-map/generated/mang/stat.md#stat-02) Cơ bản)
**Thời lượng:** ~2 giờ · **Môi trường:** `uv`, mạng tới Hugging Face; CPU là đủ, có GPU NVIDIA thì đo thêm float16 ·
**Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn làm được bốn việc:

- chuyển một model Whisper dạng PyTorch sang CTranslate2 ở float32, float16, int8;
- đo kích thước, thời gian nạp, tốc độ và WER trên cùng một bộ đo;
- chọn kiểu chạy giữ chất lượng trong biên sai số (khoảng tin cậy của chênh WER), mà nhỏ hơn hoặc nhanh hơn đo được;
- giải thích vì sao kiểu lưu và kiểu chạy là hai lựa chọn khác nhau.

## Dữ liệu

- **Model:** [`vinai/PhoWhisper-tiny`](https://huggingface.co/vinai/PhoWhisper-tiny), khoảng 150 MB, giấy phép
  BSD-3-Clause. Cùng họ với PhoWhisper-large mà app dịch giọng nói dùng cho tiếng Việt. Lab tự tải một lần vào `work/`.
- **Bộ đo:** 31 câu tiếng Việt của [video chữ cái](../../projects/g9-video-chu-cai/README.md) (dự án g9), cắt theo
  `media/phu-de.vtt`. File phụ đề cho mốc thời gian và chữ đúng của từng câu.
  - Giọng đọc Piper vi_VN, dữ liệu VAIS-1000, giấy phép CC BY 4.0.
  - Có nhạc nền, giống điều kiện dịch video.
  - Đã có trong repo, không phải tải.
- **Bộ đo khác:** `--audio <file audio hoặc video> --vtt <phụ đề có đáp án>`.

## Đọc trước

- [Hướng dẫn chuyển model PyTorch sang CTranslate2](../../projects/realtime-voice-translate/docs/11-huong-dan-chuyen-model-pytorch-sang-ctranslate2.md),
  mục 1 và 4: kích thước = số tham số × số byte; kiểu lưu khác kiểu chạy; từng bước chuyển.
- [Lab A3 · bootstrap](../stat-02-co-ban-bootstrap/README.md): vì sao lấy mẫu lại theo câu, và vì sao chỉ kết luận khi
  khoảng tin cậy của chênh lệch không chứa 0.

## Các bước

1. **Chạy lab** ở thư mục gốc repo. Lần đầu tải torch và transformers vào bộ đệm của uv; trên Linux, gói torch kèm
   thư viện CUDA nặng vài GB.

   ```bash
   uv run --no-project --python 3.12 --with "ctranslate2==4.8.4" --with "transformers[torch]==5.21.0" \
       --with huggingface_hub --with "faster-whisper==1.2.1" --with psutil \
       python labs/ops-05-trung-cap-luong-tu-whisper/lab.py
   ```

   Lab in năm mục, ghi `work/ket-qua.md` (bảng) và `work/ket-qua.json` (chữ từng câu của mỗi cách chạy).
   Chạy lại thì dùng lại model đã tải và đã chuyển.

2. **Mục 1–2: kích thước.** Lab tải model gốc một lần, rồi chuyển ra ba bản `ct2-float32`, `ct2-float16`,
   `ct2-int8_float16` bằng chính script của app ([`convert_whisper_ct2.py`](../../projects/realtime-voice-translate/scripts/convert_whisper_ct2.py)).
   So `model.bin` với công thức số tham số × số byte.

3. **Mục 3: bộ đo.** Giải mã audio của video, cắt 31 câu theo mốc trong phụ đề, nới 0,1 giây mỗi đầu.

4. **Mục 4: chạy từng cách.** Mỗi dòng là một cặp (kiểu lưu, kiểu chạy):

   | Máy | Các cặp đo | Muốn thấy gì |
   |---|---|---|
   | CPU | float32/float32 (bản gốc), float16/float32, float32/int8, int8_float16/float32 | int8 có nhanh hơn không; lưu float16 có mất gì không |
   | GPU | float32/float32 (bản gốc), float16/float16, float16/int8_float16, int8_float16/float16 | float16 so với int8_float16 |

   - Cột "Thời gian / thời lượng audio" (RTF): dưới 1 là nhận dạng nhanh hơn thời gian nói.
   - Cột "RAM thêm" chỉ là gần đúng, vì lần chạy sau dùng lại bộ nhớ lần trước đã cấp. Trên GPU, xem VRAM bằng
     `nvidia-smi`.

5. **Mục 5: so với bản gốc.** Với mỗi cách chạy, lab tính:
   - chênh WER so với float32 trên cùng 31 câu;
   - khoảng tin cậy 95% của chênh đó, bằng bootstrap lấy mẫu lại theo câu;
   - số câu ra chữ khác bản gốc.

   **Quy tắc chọn:** cách nào có cận trên của khoảng tin cậy không quá `--margin` (mặc định +0,02, tức 2 điểm WER)
   là "giữ chất lượng". Trong các cách đó, chọn file nhỏ nhất, rồi đến cách chạy nhanh nhất.

6. **Nối với app.** Kiểu chạy chọn được tương ứng với `compute_type` trong profile của app dịch giọng nói
   (`packs/profiles/api-mt.yaml`). Ví dụ app chạy PhoWhisper-large ở float16 trên GPU 8 GB (docs 10 §13.1).

Test phần tính toán (đọc phụ đề, bootstrap, quy tắc chọn), không cần torch:

```bash
uv run --no-project --python 3.12 --with pytest --with numpy python -m pytest labs/ops-05-trung-cap-luong-tu-whisper
```

## Kiểm tra kết quả

- [ ] Bảng mục 2: `model.bin` của float16 khoảng 50% float32, của int8_float16 khoảng 25–30%. Giải thích được bằng số
      byte mỗi tham số.
- [ ] "Lưu float16, chạy float32": chênh WER có khoảng tin cậy chứa 0. Nếu không, mở `ket-qua.json` xem những câu
      khác bản gốc.
- [ ] "Lưu int8_float16, chạy float32": trả lời được chạy kiểu cao hơn có lấy lại chữ của bản gốc không, và vì sao.
- [ ] Chọn được một cách chạy, nói được nó giữ chất lượng thế nào (khoảng tin cậy) và lợi gì (nhỏ hơn hay nhanh hơn
      bao nhiêu).
- [ ] `work/ket-qua.md` ghi đủ bảng, loại máy và phiên bản thư viện.

## Câu hỏi mở rộng

- Đổi sang `--model vinai/PhoWhisper-base` hoặc `vinai/PhoWhisper-small`. Model lớn hơn bị ảnh hưởng bởi lượng tử nhiều
  hơn hay ít hơn?
- Với 31 câu, khoảng tin cậy rộng bao nhiêu? Cần khoảng bao nhiêu câu để phân biệt được chênh 1 điểm WER?
- Trên GPU: float16 so với int8_float16 khác nhau bao nhiêu VRAM và tốc độ? Vì sao app chọn float16 cho
  PhoWhisper-large?
- Mức trung cấp của OPS-05 còn có ONNX Runtime. Dự án g9 nghe lại lời đọc bằng sherpa-onnx (zipformer int8). Trên
  cùng bộ đo, cách nào nhanh hơn, cách nào chính xác hơn?

## Đã thử

- **Đã chạy trọn lab trong sandbox (2026-10-30), trên CPU.** Sandbox không tải được Hugging Face, nên lab chạy với một
  model Whisper tí hon, trọng số ngẫu nhiên, cùng bố cục với PhoWhisper (`--model <thư mục>`).
  - Kích thước `model.bin`: 14,5 MB (float32) → 7,3 MB (float16, 50%) → 4,0 MB (int8_float16, 27%).
  - Đủ bốn cách chạy trên CPU, ghi được báo cáo. WER của model ngẫu nhiên không có nghĩa.
- **Chưa chạy** với `vinai/PhoWhisper-tiny` thật, và chưa chạy trên GPU.
