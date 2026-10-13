# 09 · Nghe và dịch đã chính xác hơn chưa, làm gì để chính xác hơn nữa — Realtime Voice Translate

**Ngày:** 2026-10-13. **Đối chiếu với:** nhánh `main` tại `092c437`, sau 5 bước của
[08 · Rà soát bản cài đặt theo 07](08-ra-soat-ban-cai-dat-07.md). **Phạm vi:**

- đo lại độ chính xác phần nghe trên golden_1, chạy cả phiên;
- xem lại những gì được đưa đi dịch;
- tìm các lỗi còn lại, thử ba cách tăng độ chính xác;
- đề xuất bước tiếp theo;
- đối chiếu các kỹ thuật được gợi ý từ bên ngoài, và tìm vì sao Nhật → Việt kém hơn Anh, Việt (mục 8, 9).

**Tài liệu phân tích và đề xuất.** Code làm theo mục 6 nằm ở các commit sau `092c437`. Mỗi bước có một ghi chú
"Cập nhật" ngay dưới đây.

**Cập nhật 2026-10-13: đã làm bước 0 (sửa Nhật → Việt)**, có test
([`test_mt_ja_vi.py`](../ai/tests/unit/test_mt_ja_vi.py)):

- Trước khi kiểm, bản dịch được làm sạch chữ Nhật còn sót
  ([`fix_leftovers`](../ai/src/rvt_ai/packs/glossary.py)). Tên, thuật ngữ có trong glossary được thay bằng bản dịch cố
  định ("火影" → "Hokage"). Katakana còn lại được đổi sang romaji ("カカシ" → "Kakashi"). Kanji không có trong glossary
  vẫn bị loại.
- Lượt dịch lại giữ nguyên ngữ cảnh và glossary, chỉ thêm một dòng nhắc "viết hết bằng tiếng Việt". Trước đây, dòng
  nhắc này thay chỗ của ngữ cảnh.
- "Sensei" đứng sau dấu câu không còn làm bản dịch bị cắt. Chỉ cắt khi theo sau là câu giải thích, ví dụ "Sensei
  means…" (`EXPLANATION_AFTER_SENTENCE` trong [`mt_llama.py`](../ai/src/rvt_ai/engines/mt_llama.py)).

**Cập nhật 2026-10-13: đã làm bước 2 (dò VAD)**, có test ([`test_vad_probe.py`](../ai/tests/unit/test_vad_probe.py)):

- [`vad_probe.py`](../ai/src/rvt_ai/pipeline/vad_probe.py) làm đúng §4.1. Khung to hơn −30 dBFS, VAD dưới 0,25, lúc
  segmenter không ở trong câu nào, được gom thành vùng: hở tối đa 480 ms, vùng 2–6 s. Vùng được gửi đi nhận dạng như một
  đoạn chốt không prompt, với `vad_mean = 0` để bộ lọc câu bịa luôn áp.
  - Chỉ giữ chữ có `avg_logprob` ≥ −0,5 (tham số mới `min_avg_logprob` của engine), có ít nhất 4 ký tự, có chữ Nhật khi
    nửa đó khoá tiếng Nhật, và không phải tiếng hét.
  - Khi VAD bắt đầu bắt, vùng kết thúc. 400 ms cuối của vùng được bỏ, vì segmenter đã lấy làm preroll.
- **Chỉ chạy khi thu âm tab.** `turn.start` có thêm trường `source` (`"mic"` hoặc `"tab"`), web gửi kèm cả khi kết nối
  lại. Tắt hẳn bằng `RVT_VAD_PROBE=false`.
- Phát lại golden_1 bằng `golden_session.py --capture tab` (Whisper giả lập như ở đầu tài liệu). Con số khớp ước lượng ở
  §4.1:

| golden_1 | `--capture mic` (không dò) | `--capture tab` |
|---|---|---|
| CER | 0,134 | **0,114** |
| Ký tự lời thoại bắt được | 93,6% | 95,7% |
| Câu thoại bắt được | 139/141 | **141/141** |
| Câu bịa trên màn hình | 2 | 2 |
| Lượt nhận dạng | 794 | 820 |

- 2 thẻ mới là hai câu đang bị mất: "引っかかった!引っかかったよ!すみません先生!…" ở giây 46 và "危ない!逃げて!やられちゃうよ!" ở
  giây 546.
- **Chưa kiểm trên video khác.** Đây là điều kiện cuối của bước 2 trong mục 6, cần golden mới (bước 5). Nếu thấy câu rác
  trong đoạn nhạc, tắt bằng `RVT_VAD_PROBE=false`.

**Cập nhật 2026-10-13: đã làm bước 3 (prompt dịch)**, có test:

- **Glossary (§5.2).** [`packs/glossary/naruto.yaml`](../packs/glossary/naruto.yaml) có tên nhân vật, thuật ngữ và quy
  ước xưng hô tiếng Việt theo cặp nhân vật: Naruto ↔ Sakura xưng "tớ/cậu", học trò với Kakashi xưng "em/thầy",
  Kakashi với học trò xưng "thầy/các em", người lớn với Hokage xưng "tôi/ngài".
  - Chọn glossary bằng biến `RVT_GLOSSARIES`, ví dụ `RVT_GLOSSARIES=default,naruto`. Mặc định chỉ có `default`.
  - Prompt chỉ có những mục xuất hiện trong câu. Mục dài được khớp trước: "カカシ先生" → "thầy Kakashi" rồi mới tới
    "カカシ".
- **Ngữ cảnh có bản dịch trước (§5.3).** 2 câu ngay trước được đưa vào dạng "câu nguồn → bản dịch đã hiện". Câu chưa
  dịch xong thì chỉ có câu nguồn.
- **Few-shot trung tính (§5.4).** Ví dụ mới gồm một câu xin lỗi, một câu gọi tên, một câu về lịch, một câu bị cắt giữa
  chừng. Không còn ví dụ "trái Kiki".
- **Câu cảm thán, câu bị cắt (§5.5).** [`packs/phrasebook/ja.yaml`](../packs/phrasebook/ja.yaml) dịch khoảng 25 câu
  ngắn bằng bảng tra, không gọi model: "うん" → "Ừ.", "え?" → "Hả?", "くそっ" → "Chết tiệt!". Prompt có thêm luật:
  câu có thể bị cắt giữa chừng, chỉ dịch phần đang có.
- Chưa có số chrF trước/sau (cần server, xem bước 1). Điều kiện "chrF không giảm" của bước 3 phải kiểm khi chạy bộ đo
  trên server.

**Cập nhật 2026-10-13: đã làm bước 1 (bộ đo dịch), chưa có số.**

- [`eval/golden_1/translation/ja-vi.jsonl`](../eval/golden_1/translation/ja-vi.jsonl) có 168 câu: câu tiếng Nhật đã sửa
  lỗi nghe của phụ đề tự động ("里の長", "手裏剣", "上忍"), người nói và bản dịch tiếng Việt tham chiếu.
  - Bản dịch do model viết nháp, rồi được soát theo ngữ cảnh, glossary và quy ước xưng hô. Chưa có người bản ngữ duyệt
    ([README](../eval/golden_1/translation/README.md)).
  - 168 mục, nhiều hơn 141 câu thoại, vì mỗi mục là một câu nói trọn ý. Có dòng phụ đề chứa hai câu của hai người.
- (a) **Bộ dịch:** [`eval/mt_eval.py`](../eval/mt_eval.py) dịch các câu đúng y như app: bảng tra, glossary, 2 câu trước
  kèm bản dịch, làm sạch, dịch lại một lần. Sau đó chấm chrF (n ≤ 6, β = 2, cùng công thức với `sacrebleu`). Các tuỳ
  chọn `--no-context`, `--glossary ""`, `--pivot-en` để so từng phần.
- (b) **Cả chuỗi:** `golden_session.py --mt-url http://mt:8080/v1` dịch các câu mà phiên phát lại đã đưa đi dịch, rồi
  chấm chrF cả bài.
- Sandbox không chạy được model dịch, nên **chưa có số chrF nào**. Lệnh chạy trên server:

  ```bash
  docker exec -it rvt_ai uv run python eval/mt_eval.py --golden eval/golden_1 --api-url http://mt:8080/v1 \
      --out /tmp/mt_golden_1.json
  docker exec -it rvt_ai uv run python eval/golden_session.py --golden eval/golden_1 --skip-lines 12-25,180- \
      --mt-url http://mt:8080/v1
  ```

**Cập nhật 2026-10-13: đổi model dịch sang Qwen2.5-7B-Instruct Q5_K_M** (một phần của bước 4, §5.6):

- Mọi file compose, script tải model, `start.sh`, `config/models.yaml` và profile `balanced`, `quality` đều trỏ tới
  `qwen2.5-7b-instruct-q5_k_m.gguf`.
- Muốn quay lại bản cũ, đặt `RVT_MT_MODEL_FILE=qwen2.5-7b-instruct-q4_k_m.gguf`, không cần sửa file.
- **VRAM.** File Q5_K_M nặng 5,44 GB, Q4_K_M nặng 4,68 GB, tức thêm khoảng 0,76 GB. Để bù, context của llama.cpp giảm
  từ 16 384 xuống 8 192 token (4 slot, mỗi slot 2 048 token), bớt khoảng 0,47 GB KV cache. Tổng cộng vẫn thêm khoảng
  0,3 GB VRAM.
  - Prompt dài nhất hiện có (glossary, xưng hô, 2 câu trước kèm bản dịch, few-shot) khoảng 2 300 ký tự, cỡ 700–900
    token. Vẫn vừa một slot.
- Chưa so được với Q4_K_M bằng chrF và độ trễ. Đây là việc của bước 4 trên GPU thật.

**Cách đo:**

- [`eval/golden_session.py`](../eval/golden_session.py) chạy `RVTSession` thật theo đồng hồ ảo, rồi dựng lại màn hình
  như web.
- Whisper large-v3-turbo được giả lập bằng bản ONNX int8 (sherpa-onnx) trên CPU, giải mã tham lam như app
  (`beam_size=1`). Độ trễ GPU giả định: 0,15 s + 0,04 s cho mỗi giây audio.
- Đáp án là phụ đề tự động của YouTube: 141 câu thoại, 2 313 ký tự, không tính hai bài hát. Chính đáp án cũng sai nhiều
  tên riêng ("里の蝶", "照理剣", "丸ト").
- **Không đo được chất lượng bản dịch.** Sandbox không tải được model dịch Qwen2.5-7B (Hugging Face bị chặn), và
  golden_1 chưa có bản dịch tham chiếu. Mục 3 chỉ đo những gì được đưa vào bộ dịch.

## 1. Kết luận

1. **Nghe: chính xác hơn rõ.** Trên golden_1, so với `873d676` (trước 08):
   - CER 0,231 → 0,134, giảm 42%. Nếu bỏ khác biệt kanji/kana ("俺"/"オレ", "随分"/"ずいぶん") thì 0,209 → 0,116;
   - câu thoại bắt được 134 → 139/141; câu bịa trên màn hình 8 → 2;
   - không còn thẻ đã chốt bị xoá (7 → 0) hay câu hiện hai lần do lỗi (4 → 0).
2. **Dịch: đầu vào sạch hơn, hai lỗi phá bản dịch đã sửa. Chất lượng của chính bản dịch chưa đo.**
   - CER của câu đưa đi dịch 0,208 → 0,134; câu bịa bị đem đi dịch 9 → 2; câu lặp bị dịch lại 7 → 2.
   - Bản dịch có ngoặc kép không còn bị thay bằng "[Lỗi dịch vi]" (08 §3.1). Bản dịch không còn bị cắt ở "—", "\*\*"
     (08 §3.5).
3. **Lỗi lớn nhất còn lại của phần nghe: VAD bỏ sót câu hét lẫn nhạc nền.**
   - 2 câu thoại mất trọn, chiếm khoảng 1/5 số ký tự lời thoại sai.
   - Một bước dò những vùng audio to mà VAD không bắt, kèm bộ lọc, lấy lại cả 2 câu mà không thêm câu rác: CER 0,134 →
     0,114, 141/141 câu (ước lượng, §4.1).
4. **Hai cách khác không có lợi rõ trên golden_1:**
   - glossary tên riêng làm hotwords cho Whisper: sửa được 2 chỗ "体術", nhưng thêm 1 câu bịa trong đoạn nhạc, CER 0,138;
   - beam 5 thay cho giải mã tham lam: áp cho mọi đoạn thì CER 0,160, vì ở đoạn ngắn không có lời model ra
     "ありがとうございました。", "またね。". Chỉ áp cho đoạn có lời thì CER 0,134, bằng hiện tại, mà chậm hơn.
5. **Phía dịch còn nhiều chỗ dễ làm:**
   - chưa dùng glossary: gói `packs/glossary` có sẵn nhưng không có code nào đọc;
   - ngữ cảnh chỉ có 2 câu nguồn trước, không có bản dịch trước;
   - 3 ví dụ few-shot lấy từ một phim khác.

   Phải làm bộ đo dịch trước (§5.1) mới biết thay đổi nào có lợi.
6. **Các kỹ thuật được gợi ý từ bên ngoài** (mục 8): gần hết app đã có. Hai gợi ý sẽ làm kém đi: đổi Whisper sang
   bản medium, và bỏ câu dịch đến trễ.
7. **Nhật → Việt kém hơn Anh, Việt** vì khó ở cả phần nghe lẫn phần dịch (mục 9). Có thêm 2 lỗi trong code chỉ ảnh hưởng
   chiều này:
   - bản dịch còn sót một chữ Nhật bị loại rồi dịch lại, mất ngữ cảnh;
   - bản dịch bị cắt ngang khi gặp "Sensei" sau dấu câu.
8. **Thứ tự làm** (mục 6): sửa 2 lỗi Nhật → Việt → bộ đo dịch → bước dò VAD → prompt dịch → so model trên GPU thật →
   thêm golden.

## 2. Phần nghe: đo lại theo từng bước

| golden_1, cả phiên | `873d676` | Sau bước 0–3 (`466ba30`) | Sau bước 4 (`092c437`) |
|---|---|---|---|
| CER so với phụ đề | 0,231 | 0,167 | **0,134** |
| CER theo cách đọc (đổi hết sang kana) | 0,209 | 0,146 | 0,116 |
| Câu thoại bắt được | 134/141 | 138/141 | 139/141 |
| Ký tự lời thoại bắt được | 90,7% | 93,4% | 93,6% |
| Câu bịa trên màn hình | 8 | 2 | 2 |
| Thẻ đã chốt bị xoá | 7 | 0 | 0 |
| Câu hiện hai lần do lỗi của phiên (chữ tạm đến muộn, thẻ trùng) | 4 | 0 | 0 |

- CER theo cách đọc dùng `pykakasi` đổi cả đáp án lẫn chữ nhận được sang kana. Khoảng 0,018 của CER hiện tại chỉ là khác
  cách viết, nghĩa không đổi.
- Bước 2 (Safari) và bước 3 (lọc FIR) không hiện trong bảng. Mô phỏng dùng audio 16 kHz đã hạ mẫu chuẩn, không qua mic
  hay tab.
  - Bước 3 giảm aliasing khi thu âm tab từ −33 dB xuống −58 dB so với lời.
  - Trên 60 đoạn đầu, chữ nhận dạng không kém đi (08, ghi chú bước 3).

## 3. Phần dịch: những gì được đưa đi dịch

| golden_1, yêu cầu dịch ja → vi | `873d676` | `466ba30` | `092c437` |
|---|---|---|---|
| Số câu đưa đi dịch | 238 | 227 | 221 |
| CER của câu nguồn | 0,208 | 0,167 | **0,134** |
| Câu nguồn là câu bịa ("ご視聴…", "おわり。") | 9 | 2 | 2 |
| Câu lặp lại một trong 3 câu ngay trước | 7 | 6 | 2 |
| Câu ≤ 6 ký tự | 73 | 70 | 69 |

- Ở `873d676`, CER của câu nguồn (0,208) thấp hơn CER trên màn hình (0,231): 7 thẻ đã được dịch rồi mới bị xoá.
- 40/221 câu không có dấu kết câu. Phần lớn là câu ngắn trọn ý ("マジかよ", "うん", "くそ") hoặc lời bài hát. Câu bị cắt đôi
  thật chỉ khoảng 5 câu, ví dụ "つまり、失格率66%以上の" rồi "超選抜試験だ。" (cách nhau 0,5 s).
- Hai lỗi đã sửa ở bước 0 làm hỏng chính bản dịch, không chỉ đầu vào:
  - bản dịch được model bọc ngoặc kép thành "[Lỗi dịch vi]" (08 §3.1);
  - bản dịch bị cắt ở "—" hoặc "\*\*", ví dụ "Đợi đã — ê!" chỉ còn "Đợi đã" (08 §3.5).

**Prompt dịch hiện tại** ([`mt_llama.py`][c-mt-prompt], [`session.py`][c-mt-context]):

- Qwen2.5-7B-Instruct Q4_K_M qua llama.cpp, temperature 0,1;
- prompt hệ thống có luật đầu ra và 3 ví dụ ja → vi lấy từ một phim khác ("trái Kiki", "vương quốc người khổng lồ");
- ngữ cảnh là 2 câu nguồn trước, không có bản dịch trước của chúng;
- không có glossary. [`packs/glossary/default.yaml`](../packs/glossary/default.yaml) có sẵn (mới có "FastAPI",
  "WebSocket") nhưng không có code nào đọc. Thư mục `prompts/mt/` có mẫu cho `chat-generic` và `hy-mt`, nhưng
  `mt_llama.py` không dùng mẫu nào.

## 4. Phần nghe: các lỗi còn lại và ba thử nghiệm

**Lỗi còn lại** (golden_1, `092c437`, CER lời thoại khoảng 0,10):

| Loại | Ví dụ | Ước lượng |
|---|---|---|
| Câu thoại mất trọn vì VAD không bắt | "引っかかった。…無理でした。" (41 s), "危ない。逃げて。やられちゃうよ。" (543 s) | 50 ký tự, khoảng 1/5 số ký tự sai |
| Câu bịa còn trên màn hình | "ご視聴ありがとうございました", "おわり。" | 17 ký tự |
| Khác cách viết, nghĩa không đổi | "俺"/"オレ", "随分"/"ずいぶん", "1人"/"一人" | khoảng 0,018 CER |
| Tên riêng, thuật ngữ của phim | 体術 → 大術, 正気 → ジョンキ, 手裏剣 → 照り剣, 上忍 → 昇給/昇級 | vài chục ký tự; đáp án cũng sai |
| Còn lại: nghe sai, thiếu vài chữ | "これが俺の技だ" → "いやいやいや" | phần còn lại |

### 4.1 Dò những vùng audio to mà VAD bỏ sót

- Từ 31 s đến 45 s, audio to (−12 đến −35 dBFS) nhưng Silero VAD cho xác suất gần 0 suốt 15 s, nên không có đoạn nào
  được gửi đi nhận dạng. Trong khoảng này có câu "引っかかった!引っかかったよ!…", Whisper nghe ra rõ (`avg_logprob` −0,25).
- Trên cả golden_1 có 19 vùng như vậy dài ít nhất 2 s, tổng 108 s: audio to hơn −30 dBFS, VAD dưới 0,25, không nằm trong
  đoạn nào. Whisper (không prompt) nghe ra:
  - đúng 2 câu thoại đang bị mất (41 s và 543 s);
  - 13 lần "ご視聴ありがとうございました" trong đoạn nhạc;
  - tiếng hét ("あーーー"), lời bài hát, "me", "ん".
- **Đề xuất:** khi đang thu âm tab, vùng audio to mà VAD không bắt, dài 2–6 s, được gửi đi nhận dạng như một đoạn chốt
  không prompt. Chỉ giữ kết quả khi:
  - không khớp mẫu câu bịa (`JA_HALLUCINATIONS`, luôn áp vì VAD của vùng này gần 0);
  - có ít nhất 4 ký tự sau khi bỏ dấu câu, và có chữ Nhật khi nửa đó khoá tiếng Nhật;
  - `avg_logprob` ≥ −0,5 (`FasterWhisperEngine` cần trả thêm giá trị này);
  - không phải tiếng hét, tức không chỉ là một chữ kéo dài ("あーーーっ").
- **Kết quả trên golden_1** (ước lượng bằng cách chèn kết quả nhận dạng của các vùng này vào phiên `092c437`): chỉ 2 câu
  thoại thật qua được bộ lọc.

| golden_1 | `092c437` | + bước dò |
|---|---|---|
| CER | 0,134 | **0,114** |
| Ký tự lời thoại bắt được | 93,6% | 95,7% |
| Câu thoại bắt được | 139/141 | 141/141 |
| Câu rác thêm vào | — | 0 |

- **Giá:** 26 lượt nhận dạng thêm trong 14 phút, so với 794 lượt hiện có (thêm khoảng 3%), chủ yếu trong đoạn nhạc.
- **Rủi ro:** các ngưỡng được chọn khi nhìn chính golden_1, nên phải kiểm trên video khác trước khi bật. Với mic thì
  không bật: tiếng TV, nhạc trong phòng sẽ bị nhận dạng.

### 4.2 Glossary tên riêng làm hotwords cho Whisper

- Thử như tham số `hotwords` của faster-whisper: đặt danh sách
  "ナルト、サスケ、サクラ、カカシ先生、上忍、下忍、火影、忍者、忍術、体術、幻術、手裏剣、木ノ葉" trước prompt ngữ cảnh, chỉ ở đoạn có
  VAD ≥ 0,35.

| golden_1 | `092c437` | + glossary |
|---|---|---|
| CER | 0,134 | 0,138 |
| CER theo cách đọc | 0,116 | 0,115 |
| Câu bịa trên màn hình | 2 | 3 |

- Sửa được: "大術"/"背術" → "体術" (2 chỗ), "サバイバー演習" → "サバイバル演習".
- Không sửa được "上忍" (vẫn "昇級", "小級") và "手裏剣" (vẫn "照理剣").
- Làm hỏng: đoạn nhạc ở 115 s (VAD 0,44) ra "ご視聴ありがとうございました。" thay cho lời bài hát.
- **Kết luận:** không dùng như vậy. Muốn thử tiếp thì chỉ đặt glossary ở đoạn có VAD cao (≥ 0,5), hoặc sửa sau nhận dạng
  theo cách đọc (ví dụ "大術" và "体術" cùng đọc là たいじゅつ). Glossary hợp với phía dịch hơn (§5.2).

### 4.3 Beam search

- App giải mã tham lam (`beam_size=1`, [`asr_whisper.py`][c-asr-args]). Thử beam 5, mặc định của faster-whisper:
  thêm beam search vào bản Whisper giả lập (patience 1, length penalty 1 như CTranslate2), chạy lại cả phiên.

| golden_1 | Tham lam (hiện tại) | Beam 5 mọi đoạn | Beam 5 khi VAD ≥ 0,35 |
|---|---|---|---|
| CER | 0,133 | 0,160 | 0,134 |
| CER theo cách đọc | 0,116 | 0,137 | 0,116 |
| Ký tự lời thoại bắt được | 93,7% | 93,7% | 93,5% |

- Bảng này tính trên chữ chốt của từng đoạn, trước khi bỏ câu chốt sớm, nên lệch khoảng 0,001 so với mục 2. Cột cuối
  ghép kết quả beam của đoạn có VAD ≥ 0,35 với kết quả tham lam của các đoạn còn lại.
- Ở đoạn ngắn không có lời, beam 5 ra những câu chào kết thường gặp trong dữ liệu huấn luyện: "ありがとうございました。"
  (3 lần), "またね。" (3 lần), "それではまた。", "by H.". Bộ lọc câu bịa hiện tại không bắt các câu này.
- Ở đoạn có lời, 17/189 đoạn ra chữ khác, nhưng tính chung không tốt hơn.
- Trên CPU, mỗi đoạn chậm hơn khoảng 3 lần. Trên GPU sẽ ít hơn nhưng vẫn chậm hơn.
- **Kết luận:** giữ `beam_size=1` với turbo. Nếu đổi sang large-v3 (§4.4) thì đo lại cả beam.

### 4.4 Model lớn hơn: chưa thử được

- Cả profile `balanced` lẫn `quality` đều dùng `large-v3-turbo`. Bản turbo chỉ có 4 lớp decoder (large-v3 có 32), nên
  nhanh hơn nhiều, nhưng có thể kém hơn ở một số ngôn ngữ. Chưa đo với tiếng Nhật trên golden_1.
- Sandbox không tải được large-v3. Cần so trên server bằng `golden_session.py` (đổi `model` trong profile), đo cả CER
  lẫn độ trễ mỗi đoạn, vì GPU 8 GB còn phải chạy Qwen2.5-7B.

## 5. Phần dịch: đề xuất

### 5.1 Làm bộ đo dịch trước

- Hiện chưa có con số nào về chất lượng bản dịch. Không có phép đo thì không biết các thay đổi ở §5.2–5.6 làm bản dịch
  tốt lên hay kém đi.
- **Bản dịch tham chiếu:** tiếng Việt cho 141 câu thoại của golden_1, mỗi dòng ứng với một dòng phụ đề, ví dụ
  `eval/golden_1/translation/vi.txt`. Người dịch, hoặc model mạnh dịch rồi người duyệt.
- **Hai phép đo**, chấm bằng chrF (`sacrebleu`):
  - (a) **bộ dịch:** dịch từng dòng phụ đề (chữ Nhật đúng) với đúng prompt và ngữ cảnh như app. Đây là mức trần của bộ
    dịch hiện tại;
  - (b) **cả chuỗi:** `golden_session.py` gọi bộ dịch thật thay vì chỉ ghi lại câu nguồn, nối bản dịch của mọi thẻ rồi
    so với bản tham chiếu nối lại.
- (a) − (b) là phần mất do nghe sai và cắt câu. Hai phép đo này chạy trên server, vì cần GPU và model dịch.

### 5.2 Glossary cho bộ dịch

- Không có glossary thì mỗi câu dịch tên riêng và thuật ngữ một kiểu.
- **Đề xuất:**
  - đọc `packs/glossary/*.yaml`, file đã có khung `source`, `target_vi`, `target_en`, `target_ja`;
  - chọn glossary theo pack hoặc theo phiên;
  - chỉ đưa vào prompt những mục có trong câu nguồn, để prompt ngắn: "Glossary: カカシ先生 → thầy Kakashi; 上忍 → Thượng
    nhẫn".
- Ví dụ cho phim Naruto: ナルト → Naruto, サスケ → Sasuke, サクラ → Sakura, カカシ先生 → thầy Kakashi, 上忍 → Thượng nhẫn,
  下忍 → Hạ nhẫn, 火影 → Hokage, 手裏剣 → phi tiêu, 体術 → thể thuật.
- Ở phía dịch không có rủi ro chép prompt như ở Whisper (§4.2). Nhưng glossary không sửa được chữ đã nghe sai: "昇級"
  không thành "上忍".

### 5.3 Ngữ cảnh có cả bản dịch trước

- Hiện tại model chỉ nhận "Previous context: <2 câu nguồn trước>". Nó không thấy mình đã dịch câu trước thế nào, nên
  cách xưng hô ("cậu/tớ", "thầy/em") và cách gọi tên có thể đổi giữa các câu.
- **Đề xuất:** đưa 2 cặp "câu nguồn → bản dịch đã chốt" gần nhất. Prompt dài thêm khoảng 50 token.

### 5.4 Ví dụ few-shot trung tính

- 3 ví dụ ja → vi hiện có là câu của một phim khác ("trái Kiki", "vương quốc người khổng lồ"). Chúng có thể kéo bản dịch
  theo từ và văn phong của phim đó.
- **Đề xuất:** thay bằng ví dụ hội thoại ngắn, gồm một câu cảm thán ("え?" → "Hả?"), một câu bị cắt giữa chừng và một câu
  có tên riêng. Hoặc lấy ví dụ theo pack.

### 5.5 Câu cảm thán ngắn và câu bị cắt đôi

- 69/221 câu đưa đi dịch dài không quá 6 ký tự, phần lớn là "うん", "え?", "くそ", "はぁ". Nên dịch bằng bảng tra: nhanh,
  không gọi model, không bị model thêm chữ. Chỉ gọi model khi câu không có trong bảng.
- Khoảng 5 câu bị cắt đôi thật, ví dụ "つまり、失格率66%以上の" rồi "超選抜試験だ。".
  - Cách rẻ: thêm một luật vào prompt, rằng câu có thể bị cắt giữa chừng và chỉ dịch phần đang có, không tự thêm.
  - Cách tốt hơn là ghép hai nửa rồi dịch lại, nhưng phải đổi cả web. Cách ghép cũ đã bị bỏ vì lỗi (08 §3.4).

### 5.6 So model dịch trên GPU thật

- Các ứng viên phải được đo bằng §5.1 cùng độ trễ, và phải vừa GPU 8 GB cùng Whisper:
  - Qwen2.5-7B-Instruct Q4_K_M (hiện tại) so với bản Q5_K_M hoặc Q6_K của cùng model: lượng tử hoá nhẹ hơn, tốn thêm
    VRAM;
  - một model chuyên dịch như Hunyuan-MT-7B. Repo đã có thư mục prompt `prompts/mt/hy-mt`, có lẽ để dành cho model
    này;
  - một model 7–9B mới hơn, như Qwen3-8B.
- Chỉ đổi khi chrF ở cả (a) lẫn (b) tăng, và độ trễ p95 của bản dịch không tăng đáng kể.

## 6. Lộ trình đề xuất

| Bước | Nội dung | Tầng | Công | Xong khi |
|---|---|---|---|---|
| 0 · Sửa Nhật → Việt | §9: bản dịch có chữ Nhật bị loại và dịch lại không ngữ cảnh; bản dịch bị cắt ở "Sensei" | server | 0,5 ngày | test mới đỏ ở bản cũ, xanh ở bản sửa; bản dịch có tên riêng không bị loại, không bị cắt. **Đã làm** |
| 1 · Đo dịch | §5.1: bản dịch tham chiếu cho golden_1, script chấm chrF cho bộ dịch và cả chuỗi | eval + server | 1–2 ngày | có chrF của bản hiện tại, chạy lại được bằng một lệnh. **Đã có bộ đo và lệnh chạy, chưa có số:** cần chạy trên server |
| 2 · Dò VAD | §4.1: dò vùng audio to mà VAD bỏ sót, chỉ khi thu âm tab; engine trả thêm `avg_logprob` | server | 1 ngày | golden_1: 141/141 câu, CER ≤ 0,12, câu bịa trên màn hình không tăng; kiểm trên ít nhất một video khác. **Đã làm:** 141/141, CER 0,114, câu bịa 2 → 2; còn kiểm trên video khác |
| 3 · Prompt dịch | §5.2–5.5, §9: glossary kèm cách xưng hô, ngữ cảnh có bản dịch trước, few-shot trung tính, bảng tra câu cảm thán | server | 1–2 ngày | chrF ở bước 1 không giảm; tên riêng có trong glossary được dịch đúng. **Đã làm**, còn kiểm chrF trên server |
| 4 · So model | §4.4, §5.6, §9: large-v3 (đo lại cả beam), các model dịch, dịch qua tiếng Anh, đo trên GPU thật | server | 1–2 ngày | chọn theo CER, chrF và độ trễ p95. **Đã đổi sang Qwen Q5_K_M**, chưa so bằng số |
| 5 · Thêm golden | 2–3 video khác loại (phim người đóng, vlog, hai người nói qua mic); sửa tên riêng sai trong đáp án golden_1 | eval | 1–2 ngày | các số ở bước 2–4 được đo trên ít nhất 2 golden |

## 7. Rủi ro

- **Mô phỏng:** số liệu phần nghe đo bằng Whisper ONNX trên CPU với độ trễ GPU giả định. Thứ tự sự kiện giống chạy thật,
  nhưng số tuyệt đối phải đo lại trên server bằng `golden_session.py`.
- **Chỉ có một golden:** một tập anime có nhạc nền và tiếng hét. Ngưỡng ở §4.1 và kết luận ở §4.2–4.3 có thể không đúng
  với loại video khác.
- **Đáp án sai tên riêng:** đáp án là phụ đề tự động của YouTube, nên CER ở các câu có tên riêng không phản ánh đúng.
- **Bước dò VAD** gửi cả đoạn nhạc đi nhận dạng. Nếu bộ lọc để lọt, màn hình sẽ hiện lời bài hát hoặc chữ rác.

## 8. Đối chiếu các kỹ thuật được gợi ý từ bên ngoài

Các gợi ý chung (từ Google AI Mode) cho bài toán nghe dịch Nhật → Việt trên GPU 8 GB, so với app hiện tại:

| Kỹ thuật được gợi ý | App hiện tại | Có giúp Nhật → Việt không |
|---|---|---|
| Lượng tử hoá: Faster-Whisper **medium** INT8, Qwen2.5-7B Q4 | Đã làm, với model tốt hơn: Whisper large-v3-turbo `int8_float16`, Qwen2.5-7B Q4_K_M | Không đổi sang medium: bản medium kém hơn turbo ở tiếng Nhật. Ngược lại, nên thử Qwen Q5_K_M nếu VRAM còn chỗ (§5.6) |
| Streaming qua WebSocket, nghe tới đâu dịch tới đó | Đã có: khung 40 ms qua WebSocket, chữ tạm mỗi 0,8 s, chốt sớm câu đã ổn định | Không nên dịch chữ tạm tiếng Nhật: động từ, phủ định, câu hỏi nằm cuối câu, dịch sớm dễ sai nghĩa |
| Cửa sổ ngữ cảnh trượt 5–10 câu để VRAM không tăng | Mỗi lượt dịch là một yêu cầu riêng, kèm 2 câu nguồn trước. llama.cpp cấp KV cache cố định, nên VRAM không tăng theo thời gian | Không có vấn đề VRAM. Nhưng 2 câu nguồn là ngữ cảnh ít với tiếng Nhật: nên thêm bản dịch trước (§5.3) |
| VAD cắt câu khi ngừng nói quá 0,5 s | Đã có: Silero, `min_silence_ms` 500, cắt ở 4 s, cắt cứng ở 6 s | Đã có. Lỗi lớn của VAD với phim là bỏ sót câu hét lẫn nhạc (§4.1) |
| Mốc thời gian từng từ (`word_timestamps`), bỏ câu dịch quá trễ | Không dùng. Scheduler ưu tiên lượt chốt, gộp và bỏ chữ tạm cũ | Không tăng độ chính xác: `word_timestamps` tốn thêm thời gian nhận dạng, bỏ câu trễ là mất nội dung |
| Chống trùng chữ bằng khoảng cách Levenshtein | Đã có: bỏ câu chốt sớm theo khoảng cách sửa (08 §3.6), bỏ chữ tạm đến muộn (08 §3.7). Các đoạn audio không chồng lên nhau | Đã có |
| Hàng đợi ưu tiên bất đồng bộ | Đã có: `AsrScheduler` cho lượt chốt chạy trước, gộp chữ tạm và bỏ chữ tạm khi hàng chờ dài; mỗi lượt dịch chạy riêng | Đã có. Trên golden_1 trung bình 3,9 s mới có một câu cần dịch, không dồn ứ |
| Gộp 2–3 câu ngắn rồi dịch một lần | Chưa có | Ý đúng ở chỗ câu ngắn tiếng Nhật cần ngữ cảnh. Nhưng gộp làm câu đầu hiện chậm, và một bản dịch phải chia lại cho nhiều thẻ. Đưa bản dịch trước vào ngữ cảnh (§5.3) đạt cùng mục đích mà không đổi giao diện |
| Phụ đề hai trạng thái, chữ mờ và chữ đậm | Đã có dạng cơ bản: thẻ chữ tạm có "● đang xử lý...", bản dịch hiện "… đang dịch" rồi được chốt | Có thể làm chữ tạm mờ hơn cho dễ nhìn. Không ảnh hưởng độ chính xác |

**Kết luận:** gần hết các kỹ thuật này app đã có, có cái ở dạng tốt hơn. Đổi sang Whisper medium và bỏ câu dịch trễ sẽ
làm kém đi. Không gợi ý nào chạm tới các nguyên nhân làm Nhật → Việt kém hơn Anh, Việt (mục 9).

## 9. Vì sao Nhật → Việt kém hơn Anh, Việt

**Phần nghe:**

- Audio phim (nhạc nền, tiếng hét, giọng lồng tiếng) khó hơn lời nói trực tiếp. Nếu tiếng Anh, tiếng Việt được thử bằng
  lời nói rõ (họp, nói vào mic), thì một phần khác biệt là do audio, không phải do ngôn ngữ.
- Tiếng Nhật trên golden_1 còn CER 0,134: 2 câu bị VAD bỏ sót (§4.1), tên riêng và thuật ngữ bị nghe sai (mục 4).

**Phần dịch khó hơn vì bản chất hai ngôn ngữ:**

- Tiếng Nhật hay bỏ chủ ngữ, còn tiếng Việt bắt buộc chọn cách xưng hô (tớ/cậu, thầy/em, tao/mày). Ngữ cảnh chỉ có 2 câu
  nguồn, nên model đoán lại ở mỗi câu và cách xưng hô dễ đổi giữa các câu.
- Động từ, phủ định và câu hỏi nằm ở cuối câu. Câu bị cắt đôi mất đúng phần quyết định nghĩa. Trên golden_1 chỉ khoảng
  5/221 câu bị cắt như vậy, nhưng ở cuộc họp tiếng Nhật, câu dài hơn, sẽ nhiều hơn.
- Qwen2.5-7B mạnh nhất ở tiếng Trung và tiếng Anh. Nhật → Việt là hướng ít dữ liệu hơn, và lượng tử hoá 4 bit thường làm
  những hướng như vậy kém đi nhiều hơn.

**Hai lỗi trong code chỉ ảnh hưởng chiều Nhật → Việt** (kiểm bằng chính code ở `092c437`):

1. **Bản dịch còn sót chữ Nhật bị loại** ([`mt_validator.py`][c-cjk]). Bản dịch tiếng Việt chỉ cần còn một chữ kana hay
   kanji là bị coi là hỏng.
   - Ví dụ "Tớ sẽ trở thành 火影!" và "Thầy カカシ, thầy đến muộn rồi." đều bị loại. Tên nhân vật và thuật ngữ là nguồn
     chính, vì model hay để nguyên "ナルト", "火影".
   - App dịch lại, nhưng lượt dịch lại thay ngữ cảnh 2 câu trước bằng dòng chữ "Strictly translate completely into
     Vietnamese" ([`session.py`][c-retry]).
   - Người xem thấy bản dịch có chữ Nhật hiện dần, rồi bị thay sau một lượt dịch nữa. Nếu lượt sau cũng hỏng thì vẫn
     hiện bản có chữ Nhật, hoặc "[Chưa dịch được vi]".
   - **Sửa:** dặn model viết tên bằng chữ Latin (Naruto, Kakashi) và dùng glossary (§5.2). Nếu vẫn còn katakana thì đổi
     sang romaji thay vì loại cả câu. Giữ ngữ cảnh khi dịch lại.
2. **Bản dịch bị cắt khi gặp "Sensei" sau dấu câu** ([`mt_llama.py`][c-sensei]). Luật chặn lời giải thích kiểu "…
   Sensei means teacher" bắt nhầm cả câu dịch bình thường.
   - "Thầy ơi! Sensei đến muộn quá." chỉ còn "Thầy ơi! Sensei".
   - "Đúng vậy. Sensei nói thế." chỉ còn "Đúng vậy. Sensei".
   - Trên golden_1 có 11/221 câu đưa đi dịch chứa "先生".
   - **Sửa:** chỉ coi là lời giải thích khi sau "sensei" là "means", "is", "refers". `mt_validator` đã có đúng luật này.

Ngoài ra, 3 ví dụ few-shot lạc đề (§5.4) cũng chỉ có ở chiều Nhật → Việt.

**Việc nên làm cho Nhật → Việt, theo thứ tự:**

1. Sửa 2 lỗi trên, kèm test. Việc nhanh, không cần chờ bộ đo.
2. Làm bộ đo dịch Nhật → Việt (§5.1), để mọi bước sau có số.
3. Glossary kèm cách xưng hô cho từng pack, ví dụ "Naruto ↔ Sakura: tớ/cậu; học trò → Kakashi: em/thầy". Đưa bản dịch
   trước vào ngữ cảnh (§5.2, §5.3).
4. Thử dịch qua tiếng Anh (Nhật → Anh → Việt) bằng cùng model, so chrF và độ trễ. Hai hướng Nhật → Anh và Anh → Việt
   thường mạnh hơn Nhật → Việt, nhưng tốn hai lượt dịch.
5. So model dịch: Qwen2.5-7B Q5_K_M, Hunyuan-MT-7B (§5.6).

[c-mt-prompt]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L98-L175
[c-mt-context]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L579-L583
[c-asr-args]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L103-L115
[c-cjk]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/mt_validator.py#L336-L339
[c-retry]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L648-L658
[c-sensei]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L93-L96
