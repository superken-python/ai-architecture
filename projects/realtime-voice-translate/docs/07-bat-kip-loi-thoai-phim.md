# 07 · Bắt đúng lời thoại phim, dịch đủ câu, và vì sao Safari có lúc không ra chữ — Realtime Voice Translate

**Ngày:** 2026-10-11. **Đối chiếu với:** code nhánh `main` tại `d079cb3` (đã có phần làm theo
[06 · Dịch kịp lời nói nhanh](06-dich-kip-loi-noi-nhanh.md) và bộ dịch Qwen2.5-7B). **Phạm vi:**

1. Chạy bộ golden [`eval/golden_1`](../eval/golden_1/url.txt): tập 2 phim fan làm bằng AI "NARUTO – The Survival Test",
   dài 14 phút 20 giây, thoại tiếng Nhật, có bài hát mở đầu và kết thúc, nhạc nền, tiếng hét. Tìm vì sao app không bắt
   đúng và kịp lời thoại rồi dịch, lỗi nằm ở đâu.
2. Vì sao bật mic trên Safari rồi có lúc app không hiện chữ dù video vẫn nói.

**Tài liệu phân tích và đề xuất. Code thêm vào chỉ có script đo [`eval/golden_eval.py`](../eval/golden_eval.py).**

**Cách đo** (chi tiết ở mục 2): chạy đúng VAD, segmenter, logic chốt sớm và bộ làm sạch bản dịch của `main` trên audio
golden_1. Nhận dạng bằng Whisper large-v3-turbo — cùng trọng số model app dùng — bản ONNX int8 của sherpa-onnx, giải mã
như faster-whisper với đúng tham số và bộ lọc của app. Đáp án là phụ đề tiếng Nhật tự động của YouTube nằm trong
golden_1; phụ đề này cũng có lỗi, nên CER tuyệt đối bị đội lên và chỉ dùng để so các phương án với nhau. Không chạy được
model dịch (Qwen2.5-7B) và Safari trong sandbox: phần dịch được kiểm bằng chính code `mt_validator`, phần Safari dựa trên
code và hành vi đã được ghi nhận của WebKit.

## 1. Kết luận

1. **Lỗi chính ở server: điểm "cắt ở chỗ lặng nhất" (06 §5.1) bị lệch.**
   - Code tính vị trí cắt với giả định đầu buffer luôn có đủ 400 ms preroll. Thực tế preroll dài 0–400 ms, và sau mỗi lần
     cắt phần còn lại không có preroll. Vì vậy điểm cắt thật trễ hơn khung lặng đã chọn, lần cắt nối tiếp sau lại trễ
     thêm 400 ms.
   - Trên golden_1: 71/231 đoạn kết thúc bằng kiểu cắt này. Điểm cắt trễ trung vị 200 ms, p90 600 ms, tối đa 1,16 s.
     Xác suất VAD tại điểm cắt thật trung bình 0,45 (đang có tiếng nói), trong khi khung định cắt chỉ 0,10.
   - Hậu quả trên Whisper thật: mất cụm từ ("でも一番好きなのは" thành "でも一番"), sai chữ ("合格" thành "予約"), và có lúc
     bịa câu. App bắt được 90,8% ký tự lời thoại; sửa 3 dòng code thì lên 93,2%.
2. **Câu bịa "ご視聴ありがとうございました" xuất hiện 21 lần, trong khi phụ đề thật không có lần nào**, rồi được đem đi
   dịch. Whisper rất tự tin với câu này (`no_speech_prob` 0,00, logprob trung bình −0,32), nên không lọc được bằng ngưỡng
   tin cậy. Nhưng các đoạn đó ngắn (trung vị 1 s) và có xác suất VAD trung bình thấp (0,18 so với 0,59 ở đoạn thường).
   Bộ lọc câu bịa tiếng Nhật đã bị gỡ ở `a82c9fc` để giữ câu kết thật của video. Lọc có điều kiện theo VAD bỏ được 18/21
   câu này (và cả 3 câu bịa "おわり") mà không xoá câu thoại nào có trong phụ đề.
3. **Đoạn 4/6 s làm Whisper thiếu ngữ cảnh.** CER so với phụ đề tăng từ 0,33 (đoạn tối đa 7/10 s trước 06) lên 0,42
   (hiện tại); sau khi sửa lỗi 1 còn 0,38. Đưa chữ của 1–2 đoạn trước làm `initial_prompt` (faster-whisper có sẵn,
   app chưa dùng) hạ CER xuống 0,19 và giảm câu bịa từ 17 xuống 12. Cần lọc câu bịa trước khi đưa chữ vào prompt, vì
   Whisper có lúc chép lại prompt.
4. **Dịch theo mảnh câu, và bộ làm sạch bản dịch cắt mất câu.** 83–85% đoạn không kết thúc bằng dấu câu (Whisper turbo
   hay bỏ dấu 。), mỗi đoạn được dịch riêng. `mt_validator` ở bản mới nhất vẫn:
   - giữ tối đa 2 câu khi câu nguồn có không quá 1 dấu kết câu, nên mất câu cuối của bản dịch;
   - xoá mọi thứ sau dấu "—";
   - làm rỗng bản dịch có "**".
5. **Chốt sớm từng câu (06 §5.2).** Với đoạn 4/6 s, chốt sớm gần như không có tác dụng. Trong 5 phút đầu
   có 82 đoạn chốt nhưng chỉ 7 câu được chốt sớm, và chỉ sớm hơn chữ chốt 0,2–1,6 s, vì chữ tạm của Whisper ít khi có dấu
   。！？. Khi có chốt sớm, chữ đã chốt được bỏ khỏi chữ chốt bằng phép so khớp chính xác. Chỉ cần lệch một dấu "。" là
   câu đó hiện lại hai lần: 1/7 lần trên golden_1.
6. **Safari: app không nhận ra khi WebKit ngừng đưa âm thanh, nên vẫn báo "đang nghe".** Các đường chính dẫn tới không
   ra chữ:
   - màn hình tự khoá, chuyển app hay tab: AudioContext chuyển sang "interrupted", mic dừng;
   - trang hoặc app khác lấy mic: track bị "muted", app vẫn gửi khung toàn số 0;
   - máy ngủ hoặc đổi mạng: WebSocket "nửa mở", client không kiểm tra pong;
   - kết nối lại liên tục: phiên cũ chưa bị dọn, server đủ 4 phiên và từ chối kết nối mới ít nhất 20–40 s.
   Chi tiết và cách sửa ở mục 9.
7. **Đường thu âm trên web** chỉ lấy kênh trái và hạ 48 → 16 kHz không lọc chống aliasing (04 §3.5 đã nêu, chưa làm).
   Trên golden_1 ảnh hưởng nhỏ: thoại nằm giữa hai kênh, nhiễu aliasing thấp hơn lời 26 dB, và chỉ 8/60 đoạn đổi vài
   chữ. Đây không phải nguyên nhân chính, nhưng phim có nhạc và tiếng động lớn hơn sẽ bị ảnh hưởng nhiều hơn.

### Thử ngay hôm nay (không cần sửa code)

1. **iPhone/iPad (Safari):**
   - đặt Tự động khoá (Auto-Lock) là Không bao giờ trong lúc dùng, tắt Chế độ nguồn điện thấp;
   - giữ Safari ở màn hình chính, không chuyển app, và phát video trên thiết bị khác (TV, laptop);
   - chỉ mở app ở một tab;
   - nếu chữ ngừng hiện: tắt rồi bật lại mic. Lần chạm đó cho phép iOS chạy lại âm thanh.
2. **Video trên cùng máy tính:** dùng Chrome hoặc Edge với chế độ 💻 Thu âm Tab. Safari không thu được âm thanh tab.
3. **Kiểm tra server có từ chối phiên không:** `docker logs rvt_ai 2>&1 | grep "max sessions reached"`.
4. **Đo bộ golden trên server** bằng `eval/golden_eval.py` (mục 11), trước và sau mỗi lần sửa.

## 2. Cách đo

- **Audio:** `eval/golden_1/audio/videoplayback.mp4` (AAC 44,1 kHz stereo, 860 s, −20,2 LUFS), chuyển thành 16 kHz mono.
- **Đáp án:** file phụ đề trong `eval/golden_1/subtitle`, 193 dòng. Dòng 12–25 và từ dòng 180 trở đi là lời bài hát; phần
  còn lại là lời thoại (2 313 ký tự sau khi bỏ dấu câu, khoảng trắng và nhãn như `[音楽]`). Chỉ số chính là **tỉ lệ ký tự
  lời thoại bắt được**: phần đáp án khớp với chữ nhận được khi căn hai chuỗi.
- **Code được chạy:** `SileroVadEngine` và `Segmenter` với profile `balanced` (ngưỡng 0,4/0,25, đoạn tối đa 4/6 s), mỗi
  lần một khung 40 ms như web app gửi; `find_stable_prefix` và đoạn dọn chữ đã chốt của `RVTSession`; `mt_validator`.
  Bản sao có ghi vết của segmenter được kiểm là cho kết quả giống hệt code thật ở từng khung.
- **Nhận dạng:** Whisper large-v3-turbo, bản ONNX int8 của [sherpa-onnx][sherpa-models], giải mã lại như faster-whisper
  1.2.1 với tham số app dùng:
  - đặc trưng mel của faster-whisper, đệm thành 30 s;
  - prompt `<|startoftranscript|><|ja|><|transcribe|><|notimestamps|>`, giải mã tham lam;
  - chặn token ký hiệu giống hệt Whisper (82 token);
  - tính `no_speech_prob` và logprob trung bình, rồi áp đúng các bộ lọc trong `asr_whisper.py`.
  Khác biệt còn lại so với server: int8 ONNX thay vì CTranslate2 `int8_float16`, nên số có thể lệch nhẹ.
- **Các cách cắt đoạn được so:**
  - `main`: code hiện tại;
  - `sửa`: chỉ sửa cách tính vị trí cắt (mục 3.4);
  - `7/10 s`: segmenter trước 06 (đoạn tối đa 7/10 s, cắt tại chỗ).
- **Không đo được:** model dịch Qwen2.5-7B (không tải được trong sandbox), Safari/WebKit, và GPU của server.

## 3. Lỗi 1 — cắt "ở chỗ lặng nhất" bị lệch khỏi chỗ lặng

### 3.1 Cơ chế

Khi đoạn dài quá `max_ms`, segmenter chọn khung có xác suất VAD thấp nhất `k` trong 1,5 s gần nhất, rồi cắt buffer ở
cuối khung đó ([segmenter.py#L109-L133][c-mincut]):

```python
preroll_bytes = min(len(self.buffer), (self.config.preroll_ms * self.config.sample_rate * 2) // 1000)
...
cut = preroll_bytes + (k + 1) * chunk_bytes
```

- `frame_probs[0]` là khung tiếng nói đầu tiên. Trong buffer, trước khung đó có P − 1 khung preroll, với P từ 1 tới 10
  tuỳ khoảng lặng trước câu. Vị trí đúng là `(P − 1 + k + 1)` khung, còn code luôn cộng 10 khung, nên lần cắt đầu trễ
  `11 − P` khung, tức 40–400 ms.
- Sau khi cắt, `buffer = buffer[cut:]` không còn preroll, nhưng lần cắt sau code vẫn cộng 400 ms. Mỗi lần cắt nối tiếp,
  độ lệch giữa buffer và `frame_probs` tăng thêm 10 khung. Khi `cut` vượt độ dài buffer, nó bị kẹp lại, và đoạn bị cắt
  ngay tại thời điểm hiện tại.
- Bộ test hiện có không có ca nào cho việc cắt ở `max_ms`, nên lỗi này không bị phát hiện.

### 3.2 Số đo trên golden_1

| | `main` (hiện tại) | `sửa` | `7/10 s` (trước 06) |
|---|---|---|---|
| Số đoạn (chốt vì lặng / cắt khi đang nói) | 231 (160 / 71) | 231 (160 / 71) | 180 |
| Dài trung bình / dài nhất | 2,6 / 6,0 s | 2,6 / 5,9 s | 3,3 / 10,4 s |
| Điểm cắt trễ so với khung định cắt: trung vị / p90 / tối đa | 200 / 600 / 1 160 ms | 0 | — |
| Lần cắt bị kẹp ở cuối buffer | 22 | 0 | — |
| Xác suất VAD trung bình tại điểm cắt thật | 0,45 | 0,10 | — |
| Điểm cắt rơi vào chỗ lặng (thấp hơn mức lời ≥ 10 dB) | 48% | 69% | — |
| **Ký tự lời thoại bắt được** | **90,8%** | **93,2%** | 93,0% |
| Câu thoại bắt được (≥ 60% ký tự) | 135/141 | 138/141 | 138/141 |
| CER so với phụ đề YouTube | 0,42 | 0,38 | 0,33 |
| Đoạn bị bộ lọc của app bỏ (RMS, `no_speech`, ảo giác) | 0 | 0 | 0 |

Không đoạn nào bị bộ lọc bỏ: chữ không mất ở bước lọc mà mất ở chỗ cắt đoạn và do Whisper nghe sai.

### 3.3 Ví dụ (Whisper thật, cùng đoạn audio)

| Vị trí | Code hiện tại (cắt trễ) | Sau khi sửa |
|---|---|---|
| 12,1 s (trễ 440 ms) | 落ち着きなさいよ。私だって知らないわ。少しは… / 我慢しなさい | 落ち着きなさいよ。私だって知らないわ。/ 少しは我慢しなさい |
| 159,2 s (trễ 440 ms) | …ラーメンが大好きだでも一番 / 昔の先生が… — **mất "好きなのは"** | …大好きだ! / でも一番好きなのは昔の先生が… |
| 263,6 s (trễ 560 ms) | 今年の卒業生27人のうち忍者になれる / 残りの18人は… — **mất "のは9人だけ"** | …のうち / 忍者になれるのは9人だけ残りの18人は… |
| 270,3 s (trễ 600 ms) | …超選抜しか / **ご視聴ありがとうございました** (bịa) | …以上の / 超選抜試験だ |
| 282,2 s (trễ 640 ms) | …見習いに**慣れる** / 見込みのある… | …見習いになれる見込みのある… |
| 288,8 s (trễ 760 ms) | **予約**かどうかは明日俺が判断する… | 合格かどうかは明日俺が判断する |

Mỗi lỗi như vậy còn đi tiếp sang bản dịch: câu thiếu ý, sai nghĩa, hoặc một dòng "Cảm ơn các bạn đã xem" giữa phim.

### 3.4 Sửa

Ghi số byte đứng trước khung tiếng nói đầu tiên, và đặt về 0 sau mỗi lần cắt:

```python
# Khi bắt đầu câu (has_speech và chưa is_speaking): khung hiện tại đã nằm cuối ring buffer preroll
self.lead_bytes = len(self.buffer) - len(chunk)

# Khi cắt ở max_ms
cut = self.lead_bytes + (k + 1) * chunk_bytes
final_audio, self.buffer = bytes(self.buffer[:cut]), self.buffer[cut:]
self.lead_bytes = 0  # phần còn lại bắt đầu đúng ở khung k + 1
```

- Đặt lại `_prob_sum`, `_prob_count`, `_prob_max` sau mỗi lần cắt, để thống kê trong log là của riêng từng đoạn.
- Thêm test: một đoạn có khung lặng ở vị trí biết trước, preroll thiếu (câu bắt đầu ngay sau câu trước) và hai lần cắt
  nối tiếp. Đoạn chốt phải kết thúc đúng ở cuối khung lặng.
- Đã thử chọn điểm cắt ở giữa đoạn lặng dài nhất thay vì khung thấp nhất: 65% điểm cắt rơi vào chỗ lặng, so với 69%.
  Không tốt hơn, nên giữ cách chọn hiện tại.

## 4. Lỗi 2 — câu bịa "ご視聴ありがとうございました"

| Cách cắt | Số lần xuất hiện (phụ đề thật: 0) | Đoạn có chữ ngắn dưới 1,2 s |
|---|---|---|
| `main` | 21 | 31 |
| `sửa` | 17 | 28 |
| `7/10 s` | 5 | 15 |

- Câu bịa rơi vào các đoạn ngắn chứa tiếng thở, hét, tiếng động hoặc nhạc. Đoạn càng ngắn và càng nhiều thì càng nhiều
  câu bịa. Cùng loại có "おわり" (3 lần).
- `HALLUCINATIONS` trong [asr_whisper.py#L12-L36][c-halluc] chỉ còn mẫu tiếng Anh và tiếng Việt. Mẫu tiếng Nhật bị gỡ ở
  `a82c9fc`, vì lọc vô điều kiện thì xoá luôn câu kết thật của video.
- Ngưỡng tin cậy không giúp được: các đoạn này có `no_speech_prob` 0,00 và logprob trung bình −0,32. Bỏ đoạn theo
  `no_speech_prob > 0,2` hoặc logprob < −0,5 không bắt được câu nào, mà bỏ nhầm 23 đoạn thật.
- Xác suất VAD trung bình của đoạn thì phân biệt được: trung vị 0,18 ở đoạn bịa, 0,59 ở đoạn thường.
- **Đề xuất:** khôi phục danh sách câu bịa tiếng Nhật, gồm ご視聴ありがとうございました, チャンネル登録, 字幕, おわり.
  Chỉ bỏ câu khớp danh sách khi VAD trung bình của đoạn dưới 0,35. Trên golden_1: bỏ 18/21 câu "ご視聴…" và cả 3 câu
  "おわり", không câu nào trong số đó có trong phụ đề. Câu kết thật do người đọc rõ ràng có VAD cao nên vẫn giữ.
- Không bỏ mọi đoạn có VAD thấp: trong 38 đoạn có VAD trung bình dưới 0,3 có nhiều câu thoại ngắn thật (マジかよ, おはよう,
  嘘, くそ, 油断しただけだ).

## 5. Đoạn ngắn thiếu ngữ cảnh

- Mỗi đoạn được nhận dạng độc lập: `condition_on_previous_text=False`, không có `initial_prompt`
  ([asr_whisper.py#L86-L97][c-asr-args]). Đoạn 2–6 s cho Whisper ít ngữ cảnh hơn đoạn 7–10 s, nên sai nhiều hơn và bịa
  nhiều hơn (bảng 3.2 và mục 4).
- **Thử đưa chữ của 1–2 đoạn trước (tối đa 60 ký tự, bỏ khi cách nhau quá 5 s) làm `initial_prompt`** trên cách cắt
  `sửa`:

| Chỉ số (cách cắt `sửa`) | Không prompt | Có prompt ngữ cảnh |
|---|---|---|
| Ký tự lời thoại bắt được | 93,2% | 94,1% |
| Câu thoại bắt được | 138/141 | 139/141 |
| CER so với phụ đề | 0,38 | 0,19 |
| Tổng số ký tự nhận được (đáp án: 2 491) | 3 084 | 2 652 |
| Câu "ご視聴ありがとうございました" | 17 | 12 |
| Đoạn kết thúc bằng dấu câu | 17% | 11% |

- 77/231 đoạn đổi chữ, không đoạn nào thành rỗng. Chữ thừa giảm mạnh (432 ký tự), nên CER giảm một nửa.
- **Rủi ro thấy được:** ở đoạn không có lời, Whisper có lúc chép lại prompt. Có 12 đoạn có chữ nằm trọn trong prompt, đa
  số hợp lệ (ví dụ "おはよう" được nói hai lần), nhưng có ca chép sai:
  - 482,6 s: đoạn không lời ra "お前ちょっと", chép từ câu trước;
  - câu bịa "ご視聴…" nằm trong prompt thì lan sang đoạn sau (421,8 s và 425,7 s).
  Vì vậy chỉ đưa vào prompt những chữ đã qua bộ lọc câu bịa ở mục 4, và bỏ prompt sau khoảng lặng dài hoặc đoạn nhạc.
- Prompt không có dấu câu làm Whisper ra ít dấu câu hơn (17% → 11%), trong khi chốt sớm và bộ làm sạch bản dịch cần dấu
  câu. Nên nối các câu trong prompt bằng "。".

- faster-whisper có sẵn `initial_prompt` và `hotwords`, không cần đổi model. Cũng có thể đưa vào prompt các tên riêng và
  thuật ngữ của phim (カカシ, 上忍, 手裏剣, 丸太, 体術…). Chính phụ đề YouTube cũng sai các từ này (照理剣, 丸ト, 退術).

## 6. Dịch: mảnh câu và bộ làm sạch cắt mất câu

### 6.1 Mảnh câu

- 83–85% đoạn (`sửa` và `main`) không kết thúc bằng 。！？ — Whisper turbo hay bỏ dấu câu tiếng Nhật, và điểm cắt
  thường nằm giữa câu. Ví dụ: "…私だって知らないわ。少しは" rồi "我慢しなさい".
- Mỗi đoạn được dịch riêng, nên phụ đề thành từng mẩu rời ("Một chút…" rồi "Hãy kiên nhẫn"), có khi sai nghĩa.
- **Đề xuất:** giữ lại phần đuôi sau dấu kết câu cuối cùng. Ghép phần đó vào đầu chữ của đoạn kế tiếp rồi mới dịch. Nếu
  sau 1,5 s chưa có đoạn kế thì dịch luôn.

### 6.2 `mt_validator` cắt mất bản dịch

Chạy `mt_validator.validate` của `d079cb3` với bản dịch mẫu:

| Câu nguồn (chữ Whisper) | Bản dịch mẫu | Kết quả sau khi làm sạch |
|---|---|---|
| 先生どこだよ他のクラスはもう来てるのにうちらだけ | Thầy đâu rồi? Lớp khác đến hết rồi. Chỉ còn mỗi bọn mình. | Thầy đâu rồi? Lớp khác đến hết rồi. — **mất câu 3** |
| 落ち着きなさいよ。私だって知らないわ。少しは | Bình tĩnh đi. Tớ cũng không biết. Kiên nhẫn chút đi. | Bình tĩnh đi. Tớ cũng không biết. — **mất câu 3** |
| 待てよ! | Đợi đã — ê! | Đợi đã — **mất phần sau "—"** |
| 今日の課題は…2つの鈴を奪うことだ | \*\*Nhiệm vụ hôm nay\*\* là cướp hai cái chuông… | rỗng → không hợp lệ → dịch lại hoặc "[Chưa dịch được vi]" |

- **Giới hạn số câu** (bước 12, [mt_validator.py#L271-L287][c-cap]) đếm dấu kết câu của câu nguồn. Câu nguồn không có dấu
  (83–85% đoạn) được tính là 1 câu, nên bản dịch chỉ được giữ 2 câu.
- **Dấu "—" và "\*\*"** nằm trong danh sách xoá "từ đây tới hết" ([mt_validator.py#L123-L124][c-dash]), còn llama.cpp
  dừng sinh khi gặp "\*\*".
- **Đề xuất:**
  - bỏ giới hạn số câu với ja → vi, thay bằng kiểm tra độ dài (ví dụ bản dịch dài quá 4 lần câu nguồn);
  - coi "—" là dấu câu (thay bằng ", " hoặc "…");
  - chỉ xoá ký hiệu "\*\*", giữ phần chữ.

## 7. Chốt sớm từng câu trên Whisper thật

Mô phỏng 5 phút đầu golden_1 với 230 lần nhận dạng tạm thật, đúng thời điểm và độ dài buffer mà segmenter yêu cầu,
dùng đúng `find_stable_prefix` và đoạn dọn chữ đã chốt của `RVTSession`:

| Chỉ số | Kết quả |
|---|---|
| Đoạn chốt | 82 |
| Câu được chốt sớm | 7 (8,5% số đoạn) |
| Chốt sớm hơn chữ chốt của cả đoạn | 0,2–1,6 s, trung vị 0,56 s |
| Câu bị hiện hai lần | 1/7 |

- **Ít câu được chốt sớm.** Chốt sớm cần một câu kết thúc bằng 。！？ xuất hiện giống hệt ở hai lần nhận dạng tạm liên
  tiếp. Whisper turbo ít khi trả dấu câu ở chữ tạm. Đoạn giờ chỉ dài tối đa 4–6 s, nên thường bị cắt trước khi kịp có
  hai lần nhận dạng tạm trùng nhau. Chốt sớm được thiết kế cho đoạn 10 s (06 §5.2); với đoạn ngắn, lợi về độ trễ chỉ
  còn khoảng nửa giây.
- **Câu bị hiện hai lần** ([session.py#L321-L345][c-clean]). Lúc 209,96 s, câu đã chốt là "夢は自分の中に留めておく。".
  Chữ chốt của cả đoạn là "夢は自分の中に留めておく俺にあるのは目的だ一族", thiếu dấu "。". Phép `startswith` không
  khớp, nên phần chữ chốt hiện thêm lại có đúng câu đã hiện.
- **Đề xuất:**
  - so khớp sau khi bỏ dấu câu và khoảng trắng, căn bằng `difflib.SequenceMatcher` thay vì `startswith`;
  - gửi `asr.final` rỗng cho thẻ chữ tạm của phần đuôi khi mọi câu đã được chốt sớm (mục 10);
  - với đoạn tối đa 4/6 s, lợi chỉ khoảng nửa giây: có thể tắt chốt sớm để bớt rủi ro trùng chữ, và bật lại nếu sau này
    tăng độ dài đoạn.

## 8. Đường thu âm trên web: kênh trái và aliasing

- AudioWorklet ([audio-processor.js#L28-L71][c-worklet]) chỉ đọc `input[0][0]`, tức kênh trái khi thu âm tab (stereo).
  Nó hạ 48 → 16 kHz bằng "nội suy tuyến tính" với tỉ lệ đúng 3, nên thực chất là lấy 1/3 số mẫu, không lọc. Mọi âm
  8–24 kHz của nhạc nền, tiếng động, chũm chọe gập vào dải 0–8 kHz của lời nói.
- Mô phỏng đúng thuật toán trên golden_1 (48 kHz stereo như tab Chrome) và so với trộn L+R rồi hạ mẫu có lọc:

| Chỉ số | Trộn L+R, hạ mẫu có lọc | Như AudioWorklet (kênh trái, không lọc) |
|---|---|---|
| Nhiễu aliasing trong các khung có lời, so với mức lời | — | −26 dB |
| Chênh lệch giữa hai kênh (L−R so với L+R) | −12 dB: thoại nằm giữa | — |
| Khung có VAD ≥ 0,4 | 43,0% | 42,6% (2,5% khung đổi trạng thái) |
| 60 đoạn đầu: số đoạn có chữ khác nhau | — | 8/60, khác 27 ký tự |
| 60 đoạn đầu: ký tự lời thoại bắt được\* | 23,1% | 22,7% |

\* Tính trên toàn bộ phụ đề nên tỉ lệ thấp; chỉ dùng để so hai cột.

- **Đề xuất:** trộn các kênh `(L + R) / 2` và chèn bộ lọc FIR thông thấp trước khi hạ mẫu (04 §6.4c).

## 9. Safari: bật mic rồi có lúc không ra chữ

### 9.1 Đường đi của âm thanh trên Safari

Mic → `getUserMedia` (bật khử vọng, lọc ồn, AGC) → `AudioContext` → AudioWorklet (40 ms một khung) → WebSocket → server.
Chỉ cần một mắt xích ngừng là server không còn âm thanh để nhận dạng. App hiện chỉ theo dõi hai thứ:

- trạng thái `AudioContext`: gọi `resume()` khi nó "suspended" hoặc "interrupted";
- thời điểm khung audio cuối cùng được gửi: watchdog mỗi 1,5 s ([ws_client.ts#L152-L170][c-watchdog]).

App không theo dõi track mic có bị "muted" hay "ended" không, mức âm của khung, server có còn trả lời không, hay vì sao
kết nối bị đóng.

### 9.2 Nguyên nhân

| # | Tình huống | WebKit làm gì | Code hiện tại | Kết quả |
|---|---|---|---|---|
| 1 | Màn hình tự khoá, chuyển app (ví dụ mở YouTube trên chính iPhone), chuyển tab, kéo Trung tâm điều khiển | `AudioContext` chuyển sang "interrupted", cần `resume()` khi quay lại ([MDN][mdn-state]); trang chạy nền không được thu mic. Đã có báo lỗi `resume()` không có tác dụng ([WebAudio #2585][wa-2585]) | `onstatechange` và watchdog gọi `resume()` không kèm thao tác của người dùng; nút mic vẫn sáng | không có âm thanh lên server |
| 2 | Tab khác, Siri, cuộc gọi hoặc app ghi âm lấy mic | WebKit chỉ cho một trang giữ mic; track của trang cũ bị "muted" ([WebKit][webkit-rtc], [webrtcHacks][webrtchacks]) | chỉ bắt `onunmute`, không bắt `onmute`; watchdog chỉ đếm khung, không đo mức âm, nên khung toàn số 0 vẫn "khoẻ" | server nhận im lặng số |
| 3 | iPhone ngủ, đổi Wi-Fi/4G rồi quay lại | WebSocket có thể "nửa mở": trình duyệt vẫn báo OPEN nhưng đường truyền đã chết | client gửi ping 3 s nhưng bỏ qua `pong` của server, nên không biết kết nối đã chết ([ws_client.ts#L49-L57][c-ping]) | khung audio bị gửi vào khoảng không |
| 4 | Kết nối lại nhiều lần trong ít phút | Server chỉ dọn phiên cũ khi phát hiện kết nối chết: uvicorn mặc định ping mỗi 20 s và chờ pong 20 s, lâu hơn nếu Safari vẫn trả pong khi trang đã chạy nền | `MAX_SESSIONS = 4` ([config.py#L16][c-max]); phiên thứ 5 bị từ chối trước `accept()` ([stream.py#L33-L36][c-reject]), nên trình duyệt chỉ thấy lỗi bắt tay, không thấy mã 4429; client cứ 2 s thử lại mà không báo lý do | không ra chữ ít nhất 20–40 s |
| 5 | Phát video ngay trên iPhone đang chạy app | trang app bị đẩy xuống nền (dòng 1); nếu dùng hình-trong-hình thì khử vọng xoá luôn tiếng của chính máy (05 §2.2) | Safari không thu được âm thanh tab ([addpipe][gdm-safari]) | không ra chữ |
| 6 | Không giữ được màn hình sáng | Screen Wake Lock chỉ có từ Safari 16.4, và trình duyệt có thể từ chối, ví dụ khi pin yếu ([Chrome Developers][wakelock]); với web app thêm vào màn hình chính, API này từng hỏng tới iOS 18.4 ([progressier][wakelock-pwa]) | xin wake lock lúc tải trang, không kiểm tra kết quả ([App.tsx#L95][c-wakelock]); sau 30 s–5 phút không chạm, màn hình khoá và rơi vào dòng 1 | không ra chữ sau vài phút |

Dòng 1 và 6 khớp với mô tả "có lúc": xem video vài phút không chạm vào iPhone, màn hình tự khoá, hoặc người dùng chuyển
sang app khác rồi quay lại. Dòng 4 dễ xảy ra khi vừa thử trên điện thoại vừa chạy test Playwright, hoặc mở nhiều tab.

### 9.3 Chẩn đoán: ghi lại để biết rơi vào dòng nào

- **Client, mỗi 2 s:**
  - `AudioContext.state`;
  - `track.readyState`, `track.muted`, `track.enabled`;
  - số khung đã gửi và mức âm (RMS dBFS) của 2 s vừa qua;
  - `ws.readyState`, thời gian từ tin nhắn cuối cùng của server;
  - wake lock còn giữ không, `document.visibilityState`.
  Hiện các thông số này trên một dòng trạng thái khi mở `?debug=1`, và gửi lên server event `client.health` mỗi 5 s.
- **Server, mỗi phiên:**
  - số giây audio nhận được trên mỗi giây thực;
  - log khi hai khung cách nhau quá 1 s;
  - log khi nhận khung toàn số 0 liên tục quá 2 s;
  - log `client.health`.
  Khi đó chỉ cần đọc log là biết lỗi ở mic, ở `AudioContext` hay ở mạng.
- **Đóng kết nối:** client đọc `event.code` và `event.reason` trong `onclose`. Server nên `accept()` rồi mới đóng với mã
  4429, để client hiện được lý do "server đầy phiên".

### 9.4 Sửa

1. **Máy trạng thái "đang nghe":** chỉ báo "đang nghe" khi đủ 4 điều kiện: `AudioContext` đang chạy, track còn sống và
   không bị muted, khung tới đều, mức âm không phải im lặng số. Thiếu một điều kiện thì hiện lớp phủ "Chạm để tiếp tục
   nghe":
   - lần chạm gọi `resume()`;
   - nếu track đã "ended" thì xin lại `getUserMedia` trong chính lần chạm đó;
   - iOS cần thao tác người dùng cho cả hai việc này.
   Bắt thêm `track.onmute`, `onended`, `visibilitychange` và `pageshow` để kiểm tra ngay khi trang quay lại.
2. **Chỉ một luồng mic:** không gọi `getUserMedia` lần hai khi đang có luồng, vì WebKit sẽ mute luồng cũ. Dùng lại hoặc
   `clone()` luồng sẵn có.
3. **Kiểm tra kết nối còn sống:** server đã trả `pong` cho mỗi `ping`. Nếu quá 8 s không có tin nhắn nào từ server thì
   đóng và nối lại ngay.
4. **Không để phiên cũ chặn phiên mới:**
   - client tạo `client_id` (lưu trong `localStorage`) và gửi kèm `session.start`; server đóng phiên cũ cùng
     `client_id` khi phiên mới tới;
   - hạ `--ws-ping-interval`/`--ws-ping-timeout` của uvicorn xuống 10 s để dọn phiên chết nhanh hơn;
   - nâng `RVT_MAX_SESSIONS` nếu GPU còn dư.
5. **Wake lock:** xin lại khi bật mic (trong lần chạm), báo trên giao diện nếu không giữ được, và nhắc tắt Tự động khoá.
6. **Hướng dẫn trong app:** trên iPhone/iPad, hiện ghi chú "Giữ Safari mở và màn hình sáng; phát video trên thiết bị
   khác".

Phác thảo cho các điểm 1 và 3 trong `ws_client.ts`:

```ts
// Track mic: WebKit mute khi trang/app khác lấy mic, ended khi mất hẳn (cần một lần chạm để xin lại)
const track = this.mediaStream.getAudioTracks()[0];
track.onmute = () => this.setCapture("muted");
track.onunmute = () => this.setCapture("ok");
track.onended = () => this.setCapture("ended");

// Trong audioProcessor.port.onmessage: đo mức âm trước khi gửi, để phát hiện khung toàn số 0
const pcm = new Int16Array(event.data);
let energy = 0;
for (let i = 0; i < pcm.length; i++) energy += pcm[i] * pcm[i];
if (energy > 0) this.lastNonZeroAt = Date.now();

// Kiểm tra kết nối: server trả pong cho mỗi ping 3 s, nên 8 s không có tin nhắn nào là kết nối đã chết
this.ws.onmessage = (e) => { this.lastServerMessageAt = Date.now(); /* ... */ };
setInterval(() => {
  if (this.ws?.readyState === WebSocket.OPEN && Date.now() - this.lastServerMessageAt > 8000) {
    this.ws.close(); // onclose sẽ nối lại và gửi lại turn.start
  }
}, 2000);
```

## 10. Các lỗi nhỏ khác

- **`targets` cũ không được xoá.** Client chỉ gửi `targets` ở chế độ 📺 Video & Họp. Server chỉ ghi đè khi trường này có
  mặt ([session.py#L128-L137][c-targets]). Ví dụ: dùng Video & Họp với "Dịch sang: vi", rồi quay về chế độ hội thoại
  ja ↔ vi. Server vẫn giữ `targets = ["vi"]`, nên lời tiếng Việt của nửa B không được dịch sang đâu cả. Sửa: client
  luôn gửi danh sách đích đầy đủ.
- **Thẻ "đang xử lý" bị treo.** Khi mọi câu của đoạn đã được chốt sớm mà chữ chốt còn lại rỗng, server `return` luôn
  ([session.py#L361-L364][c-allcommitted]) mà không gửi `asr.final` rỗng. Thẻ chữ tạm của phần đuôi vì thế treo mãi.
- **Câu chốt sớm gửi `audio_ms=0` và `lang_probs={}`** ([session.py#L262][c-audioms]). Mọi thứ dựa vào độ dài audio
  (thống kê, `replay_ws.py`) bị sai với các câu này.
- **`speech_pad_ms`** có trong cấu hình nhưng không được dùng ở đâu.
- **Bộ lập lịch chưa ưu tiên bản dịch hơn nhận dạng tạm** (06 §5.3). Với model dịch 7B, việc này càng quan trọng hơn.
- **Lượt dịch lại khi không hợp lệ** truyền `context="Strictly translate completely into vi"`: mã ngôn ngữ thay vì tên,
  và câu lệnh nằm trong ô ngữ cảnh.

## 11. Bộ đo golden: `eval/golden_eval.py`

Script chạy đúng `SileroVadEngine` + `Segmenter` (theo profile) + `FasterWhisperEngine` của app trên toàn bộ audio, mỗi
lần một khung 40 ms, rồi so chữ nhận được với phụ đề tham chiếu. Script không chạy nhận dạng tạm, chốt sớm hay dịch;
`replay_ws.py` (06 §6) đo các phần đó.

```bash
docker cp eval rvt_ai:/app/eval
docker exec -it rvt_ai uv run python eval/golden_eval.py --golden eval/golden_1 --skip-lines 12-25,180- \
    --out /tmp/golden_1.json
```

- `--skip-lines 12-25,180-` loại lời bài hát khỏi phần chấm.
- `--max-seconds 120` để đo nhanh 2 phút đầu.
- Script in số đoạn, số lần cắt khi đang nói và bao nhiêu lần rơi vào khung còn tiếng nói, tỉ lệ ký tự lời thoại bắt được
  và các câu thoại bị bỏ sót. File JSON ghi từng đoạn: vị trí, có bị cắt giữa chừng không, chữ nhận được.
- Script giải mã mp4 bằng PyAV. `faster_whisper.decode_audio` của bản 1.2.1 không chạy được với PyAV 19, vì nó truyền
  tham số `metadata_errors` mà PyAV 19 đã bỏ.
- Đã chạy thử 60 s đầu trong sandbox, với engine Whisper thay bằng bản mô phỏng ở mục 2: 12 đoạn, 4 lần cắt khi đang
  nói, 3 lần trong số đó rơi vào khung còn tiếng nói — đúng lỗi ở mục 3.

**Mức đạt đề xuất trên golden_1:**

| Chỉ số | Hiện tại (sandbox) | Đạt khi |
|---|---|---|
| Ký tự lời thoại bắt được | 90,8% | ≥ 93% |
| Điểm cắt rơi vào khung còn tiếng nói | 3/4 (60 s đầu) | ≤ 10% số lần cắt |
| Câu "ご視聴ありがとうございました" | 21 | ≤ 1 (sau khi sửa cắt đoạn và lọc theo VAD: 1) |
| Bản dịch mất câu do làm sạch | có (mục 6.2) | không còn |
| CER so với phụ đề YouTube | 0,42 | ≤ 0,25 (sau bước 2 ở mục 12; thử nghiệm: 0,19) |

## 12. Lộ trình đề xuất

| Bước | Nội dung | Tầng | Công | Xong khi |
|---|---|---|---|---|
| 0 · Đo | `golden_eval.py` trên server; log Safari ở mục 9.3 | eval + web | 0,5–1 ngày | có số thật trước khi sửa |
| 1 · Sửa lỗi | 3.4 vị trí cắt (kèm test); 4 lọc câu bịa theo VAD; 6.2 bộ làm sạch bản dịch; so khớp chữ đã chốt (7); `targets`; thẻ treo | server + web | 1–2 ngày | golden_1 đạt các dòng 1–4 của bảng mục 11 |
| 2 · Ngữ cảnh | 5: prompt ngữ cảnh (đã lọc câu bịa, nối bằng "。") và thuật ngữ; 6.1 ghép mảnh câu trước khi dịch | server | 1–2 ngày | CER golden_1 ≤ 0,25; câu bịa không tăng |
| 3 · Safari | 9.4: trạng thái "đang nghe", "Chạm để tiếp tục", kiểm tra kết nối, `client_id`, wake lock | web + server | 2–3 ngày | khoá màn hình, đổi app, gọi Siri thì app báo đúng và nghe lại sau một lần chạm; không còn bị từ chối vì đủ phiên |
| 4 · Thu âm | 8: trộn kênh và lọc chống aliasing trong AudioWorklet | web | 1 ngày | nhiễu aliasing thấp hơn lời ≥ 40 dB; chữ golden_1 không xấu hơn hạ mẫu chuẩn |

## 13. Rủi ro và đánh đổi

- **Lọc câu bịa theo VAD** có thể bỏ câu kết thật nếu người đọc nói nhỏ giữa nhạc lớn. Chỉ áp cho danh sách câu kết, và
  ghi log mỗi lần bỏ.
- **Prompt ngữ cảnh:** Whisper có thể chép lại chữ trong prompt khi đoạn sau là nhạc. Giữ prompt ngắn, bỏ prompt sau khoảng
  lặng dài, và theo dõi số câu bịa bằng golden.
- **Ghép mảnh câu trước khi dịch** làm phụ đề của mảnh đó trễ thêm tối đa 1,5 s.
- **"Chạm để tiếp tục"** cần người dùng thao tác. Trên iOS, không có cách nào để trang web tiếp tục thu mic khi chạy nền.
- **Số liệu golden** dùng Whisper chạy bằng ONNX và phụ đề tự động làm đáp án. Phải đo lại trên server bằng
  `golden_eval.py`.

## Phụ lục — nguồn tham khảo

- MDN, `BaseAudioContext.state` — trạng thái "interrupted" trên iOS Safari: [MDN][mdn-state]. WebAudio issue #2585 —
  AudioContext kẹt ở "interrupted" trên Safari: [GitHub][wa-2585].
- WebKit, *A Closer Look Into WebRTC* — mỗi lúc chỉ một tab được thu, tab cũ bị mute: [webkit.org][webkit-rtc].
  *Guide to WebRTC with Safari in the Wild* — gọi `getUserMedia` lần hai thì luồng cũ bị mute: [webrtcHacks][webrtchacks].
- Screen Wake Lock API — hỗ trợ từ Safari 16.4: [Chrome Developers][wakelock]; tình trạng trên web app cài vào màn hình
  chính iOS: [progressier][wakelock-pwa].
- `getDisplayMedia` — thu âm thanh tab chỉ có trên trình duyệt Chromium: [addpipe][gdm-safari].
- Model Whisper ONNX dùng để đo: [sherpa-onnx asr-models][sherpa-models]; tham số `initial_prompt`, `hotwords` của
  faster-whisper: [transcribe.py][fw].

[c-mincut]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L109-L133
[c-halluc]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L12-L36
[c-asr-args]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L86-L97
[c-cap]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/mt_validator.py#L271-L287
[c-dash]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/mt_validator.py#L123-L124
[c-worklet]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/web/public/audio-processor.js#L28-L71
[c-watchdog]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/web/src/net/ws_client.ts#L152-L170
[c-ping]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/web/src/net/ws_client.ts#L49-L57
[c-max]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/core/config.py#L16
[c-reject]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/api/stream.py#L33-L36
[c-wakelock]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/web/src/App.tsx#L95
[c-targets]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L128-L137
[c-allcommitted]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L361-L364
[c-clean]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L321-L345
[c-audioms]: https://github.com/superken-python/ai-architecture/blob/d079cb30b815c295047b17b409bd771fd8b03805/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L262
[mdn-state]: https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/state
[wa-2585]: https://github.com/WebAudio/web-audio-api/issues/2585
[webkit-rtc]: https://webkit.org/blog/7763/a-closer-look-into-webrtc/
[webrtchacks]: https://webrtchacks.com/guide-to-safari-webrtc/
[wakelock]: https://developer.chrome.com/docs/capabilities/web-apis/wake-lock
[wakelock-pwa]: https://progressier.com/pwa-capabilities/screen-wake-lock
[gdm-safari]: https://addpipe.com/getdisplaymedia-demo/
[sherpa-models]: https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models
[fw]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py
