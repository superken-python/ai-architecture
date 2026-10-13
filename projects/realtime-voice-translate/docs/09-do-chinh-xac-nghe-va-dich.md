# 09 · Nghe và dịch đã chính xác hơn chưa, làm gì để chính xác hơn nữa — Realtime Voice Translate

**Ngày:** 2026-10-13. **Đối chiếu với:** nhánh `main` tại `092c437`, sau 5 bước của
[08 · Rà soát bản cài đặt theo 07](08-ra-soat-ban-cai-dat-07.md). **Phạm vi:**

- đo lại độ chính xác phần nghe trên golden_1, chạy cả phiên;
- xem lại những gì được đưa đi dịch;
- tìm các lỗi còn lại, thử ba cách tăng độ chính xác;
- đề xuất bước tiếp theo.

**Tài liệu phân tích và đề xuất, không đổi code.**

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
6. **Thứ tự làm** (mục 6): bộ đo dịch → bước dò VAD → prompt dịch → so model trên GPU thật → thêm golden.

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
| 1 · Đo dịch | §5.1: bản dịch tham chiếu cho golden_1, script chấm chrF cho bộ dịch và cả chuỗi | eval + server | 1–2 ngày | có chrF của bản hiện tại, chạy lại được bằng một lệnh |
| 2 · Dò VAD | §4.1: dò vùng audio to mà VAD bỏ sót, chỉ khi thu âm tab; engine trả thêm `avg_logprob` | server | 1 ngày | golden_1: 141/141 câu, CER ≤ 0,12, câu bịa trên màn hình không tăng; kiểm trên ít nhất một video khác |
| 3 · Prompt dịch | §5.2–5.5: glossary, ngữ cảnh có bản dịch trước, few-shot trung tính, bảng tra câu cảm thán | server | 1–2 ngày | chrF ở bước 1 không giảm; tên riêng có trong glossary được dịch đúng |
| 4 · So model | §4.4, §5.6: large-v3 (đo lại cả beam), các model dịch, đo trên GPU thật | server | 1–2 ngày | chọn theo CER, chrF và độ trễ p95 |
| 5 · Thêm golden | 2–3 video khác loại (phim người đóng, vlog, hai người nói qua mic); sửa tên riêng sai trong đáp án golden_1 | eval | 1–2 ngày | các số ở bước 2–4 được đo trên ít nhất 2 golden |

## 7. Rủi ro

- **Mô phỏng:** số liệu phần nghe đo bằng Whisper ONNX trên CPU với độ trễ GPU giả định. Thứ tự sự kiện giống chạy thật,
  nhưng số tuyệt đối phải đo lại trên server bằng `golden_session.py`.
- **Chỉ có một golden:** một tập anime có nhạc nền và tiếng hét. Ngưỡng ở §4.1 và kết luận ở §4.2–4.3 có thể không đúng
  với loại video khác.
- **Đáp án sai tên riêng:** đáp án là phụ đề tự động của YouTube, nên CER ở các câu có tên riêng không phản ánh đúng.
- **Bước dò VAD** gửi cả đoạn nhạc đi nhận dạng. Nếu bộ lọc để lọt, màn hình sẽ hiện lời bài hát hoặc chữ rác.

[c-mt-prompt]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L98-L175
[c-mt-context]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L579-L583
[c-asr-args]: https://github.com/superken-python/ai-architecture/blob/092c43722d885818c651d0aec90424d2f3094934/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L103-L115
