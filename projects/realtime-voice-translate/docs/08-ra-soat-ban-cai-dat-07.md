# 08 · Rà soát bản cài đặt theo 07: lỗi còn lại và việc làm tiếp — Realtime Voice Translate

**Ngày:** 2026-10-12. **Đối chiếu với:** nhánh `main` tại `873d676`, gồm 4 commit làm theo
[07 · Bắt đúng lời thoại phim, dịch đủ câu…](07-bat-kip-loi-thoai-phim.md): `765aec9`, `f877b0f`, `4bb0a28`, `873d676`
(20 file, thêm 835 dòng, bớt 107 dòng). **Phạm vi:** đọc hết thay đổi ở server, web và eval; chạy unit test; đo lại
golden_1 bằng cả phiên dịch thay vì chỉ nhận dạng từng đoạn; chỉ ra lỗi còn lại, cách sửa, cách kiểm.

**Tài liệu phân tích và đề xuất.** Code đi kèm (commit `799502f`):

- script đo [`eval/golden_session.py`](../eval/golden_session.py);
- sửa lỗi lint mà `873d676` để lại trong `eval/golden_eval.py` (dòng quá 120 ký tự, chưa format, biến `re` che tên module
  `re`).

**Cập nhật 2026-10-12: đã làm bước 0 (hotfix) của mục 7** — §3.1, §3.2 kèm §3.7, §3.5, có test. Phát lại golden_1 bằng
`golden_session.py` sau hotfix:

- 0 thẻ đã chốt bị xoá, 0 thẻ chữ tạm treo;
- 138/141 câu thoại; 93,6% ký tự lời thoại (trước hotfix: 134/141 và 90,9%, cùng cách chấm `difflib`).

§3.2 phải đi kèm §3.7. Khi chỉ sửa §3.2, một chữ tạm "đến muộn" ở 850 s ("だけ") không còn bị xoá nhầm nữa, nên treo
trên màn hình tới hết video. Câu bịa trên màn hình tăng từ 8 lên 9, vì lỗi cũ từng xoá nhầm một thẻ câu bịa; phần này
sửa ở bước 1 (§3.3).

## 1. Kết luận

**Chưa ổn để chạy lâu dài.** Phần lớn hạng mục của 07 đã được làm, và phần quan trọng nhất — vị trí cắt đoạn — đúng hoàn
toàn. Nhưng bản cài đặt có một lỗi làm hỏng bản dịch, một lỗi xoá phụ đề đã hiện, và năm tính năng mới chỉ có tác dụng một
phần.

1. **Đã đúng, giữ nguyên:**
   - **Vị trí cắt (07 §3.4).** Segmenter ở `873d676` cắt golden_1 thành 231 đoạn, trùng cả 231 vị trí với bản sửa đã đo ở
     07. Có test cho preroll thiếu và hai lần cắt liên tiếp.
   - **Kết nối:**
     - client đóng rồi nối lại khi 8 s không nhận được tin nào từ server;
     - server `accept()` rồi mới đóng với mã 4429, client hiện được lý do;
     - uvicorn ping 10 s / chờ 10 s (cần build lại image `rvt_ai` mới có hiệu lực);
     - client luôn gửi đủ `targets`.
   - **Chẩn đoán:** thanh trạng thái `?debug=1`; event `client.health` mỗi 5 s; server ghi log khi hai khung audio cách
     nhau quá 1 s và khi nhận 2 s toàn số 0.
   - **Lỗi nhỏ của 07 §10:** câu chốt sớm gửi `audio_ms` và `lang_probs`; lượt dịch lại dùng tên ngôn ngữ thay cho mã.
   - **Web:** AudioWorklet trộn hai kênh (L+R)/2; ghi chú riêng cho iPhone/iPad.
2. **Phải sửa ngay** (mỗi lỗi dưới một giờ):
   - **Bản dịch bắt đầu bằng dấu `"` luôn thành "[Lỗi dịch vi]"** (§3.1). Dòng 41 của `mt_validator.py` gọi
     `endsWith`, tên hàm của JavaScript. Chuỗi Python không có hàm này, nên `validate()` ném `AttributeError`.
   - **Phụ đề đã hiện bị xoá** (§3.2). Khi một đoạn nhận dạng ra rỗng, server gửi `asr.final` rỗng cho
     `last_partial_uid`. Biến này không được đặt lại sau mỗi câu chốt, nên thường trỏ vào thẻ của câu trước, và web xoá
     thẻ đó cùng bản dịch. Trên golden_1: 7 thẻ bị xoá trong 14 phút, 5 thẻ là câu thoại thật.
   - **llama.cpp vẫn dừng sinh ở "—" và "\*\*"** (§3.5). Hai chuỗi này vẫn nằm trong `stop` của `mt_llama.py`, nên phần
     sửa "—" và "\*\*" trong `mt_validator` không bao giờ được dùng: bản dịch vẫn mất phần sau dấu gạch.
3. **Chỉ có tác dụng một phần:**
   - **Lọc câu bịa tiếng Nhật** (§3.3) bắt 10/20 câu trên golden_1, thay vì 18/20 như 07 đã đo. `vad_mean` mà segmenter
     truyền vào chỉ là trung bình của các khung đã được coi là tiếng nói. Ngoài ra mẫu `^…おわり…$` không chấp nhận dấu
     "。" ở cuối. Chữ tạm cũng không qua bộ lọc, nên câu bịa vẫn nháy lên và có lúc quay lại qua nhánh "cứu chữ từ chữ
     tạm".
   - **Ghép phần đuôi câu** (§3.4) chỉ được kích hoạt 3 lần trong 14 phút. Cả 3 phần đuôi đều bị chốt riêng sau 1,5 s,
     không lần nào được ghép, và 1 lần mảnh đuôi chiếm thẻ chữ tạm của câu đang nói. Lợi ích đo được rất nhỏ, nên đề
     xuất tắt hẳn.
   - **"Chạm để tiếp tục nghe"** (§4.1) chỉ cứu được `AudioContext` bị dừng và track đã "ended". Nếu mic bị "muted" hoặc
     chỉ ra toàn số 0 thì lần chạm chỉ xoá dòng cảnh báo, và cảnh báo không hiện lại.
   - **`client_id`** (§4.3) lưu trong `localStorage` — chính 07 §9.4 đề xuất cách này — nên mọi tab dùng chung một mã. Mở
     app ở hai tab là hai kết nối thay nhau đá nhau khoảng 2 s một lần, kể cả khi chỉ một tab bật mic. Ngoài ra, khi thu
     âm tab, bấm "Dừng chia sẻ" không còn tắt thu (§4.2).
   - **AudioWorklet** (§4.4): biquad bậc 2 hạ nhiễu aliasing từ −26 dB xuống −33 dB so với lời, chưa tới mục tiêu
     −40 dB. Bộ lọc FIR 63 tap đạt −58 dB.
4. **Đo lại golden_1 bằng cả phiên dịch** (mục 5, mô phỏng theo đồng hồ ảo):

| Trên màn hình (golden_1, 14 phút, cả phiên) | `873d676` | Sau khi sửa (mục 3) |
|---|---|---|
| Thẻ phụ đề đã chốt bị xoá | 7 (5 câu thoại thật) | 0 |
| Chữ tạm "đến muộn" hiện thành thẻ trùng | 56 lần, mỗi lần trung vị 1,0 s | 0 |
| Câu hiện hai lần (không tính câu lặp thật của video) | 4 | 0 |
| Câu bịa "ご視聴…", "おわり。" còn trên màn hình | 8 | 2 |
| Mảnh đuôi bị chốt riêng thành thẻ mới | 3/3 | 0/4 (4/4 được ghép) |
| Ký tự lời thoại bắt được | 90,7% | 93,4% |
| Câu thoại bắt được | 134/141 | 138/141 |
| CER so với phụ đề YouTube | 0,231 | 0,167 |

5. **Bảng đối chiếu từng đề xuất của 07** ở Phụ lục A.
6. **Thứ tự làm** (mục 7):
   - hotfix ba lỗi ở điểm 2, kèm §3.7 (đã làm);
   - sửa session (§3.3, §3.6) và tắt ghép phần đuôi (§3.4), kèm test ở mục 6;
   - sửa web (§4.1–4.3);
   - lọc FIR trong worklet;
   - đo lại trên server bằng `eval/golden_session.py`.

## 2. Cách kiểm tra

- **Đọc code:** `git diff d7f8fae 873d676`. Server: `session.py`, `segmenter.py`, `asr_whisper.py`, `mt_validator.py`,
  `scheduler.py`, `stream.py`, `messages.py`, `Dockerfile`. Web: `ws_client.ts`, `App.tsx`, `audio-processor.js`,
  `useStore.ts`, `cleanText.ts`. Eval: `golden_eval.py`, `compose.ai.yaml`.
- **Unit test:** `pytest ai/tests/unit` cho 37 passed, 6 skipped (sandbox thiếu file model Silero). Bộ test hiện có
  không bắt được lỗi nào trong tài liệu này:
  - không có ca bản dịch nằm trong dấu ngoặc kép;
  - test xoá thẻ "ma" đặt sẵn `last_partial_uid` bằng đúng uid của đoạn đang xử lý, nên không gặp ca thẻ của câu trước;
  - test ghép phần đuôi gọi hai đoạn liền nhau, không có khoảng thời gian thật giữa hai đoạn, và đang khẳng định kết quả
    sai `"少しは 我慢しなさい"` (thừa dấu cách).
- **Mô phỏng cả phiên theo đồng hồ ảo.** `golden_eval.py` của 07 chỉ đo nhận dạng từng đoạn. Lần này đo đúng thứ người
  xem thấy:
  - chạy `RVTSession` thật của `873d676` (nhận dạng tạm, chốt sớm, prompt ngữ cảnh, lọc câu bịa, ghép phần đuôi, xoá thẻ
    "ma") trên 860 s audio golden_1;
  - mỗi khung 40 ms được đưa vào đúng nhịp như web app gửi lên;
  - vòng lặp asyncio dùng đồng hồ ảo, nên `asyncio.sleep`, bộ hẹn giờ 1,5 s của phần đuôi và `time.time()` của session
    đều chạy theo thời gian audio;
  - VAD là xác suất Silero thật của từng khung; ASR là `FasterWhisperEngine.transcribe` thật với mọi bộ lọc của app,
    chỉ thay `WhisperModel` bằng Whisper large-v3-turbo ONNX int8 như 07 §2;
  - mỗi lần nhận dạng "tốn" 0,15 s + 0,04 s cho mỗi giây audio, chạy tuần tự qua `AsrScheduler` thật;
  - không gọi model dịch: chỉ ghi lại câu nguồn được đưa đi dịch;
  - dựng lại màn hình đúng như `useStore.ts` xử lý `asr.partial` và `asr.final` (final rỗng thì xoá thẻ).
- **Ba bản được so:**
  - `873d676`;
  - `873d676` cộng các sửa đề xuất ở mục 3;
  - như bản thứ hai nhưng tắt ghép phần đuôi.

  Code của từng sửa nằm trong mục 3 và 4.
- **Script cho server:** [`eval/golden_session.py`](../eval/golden_session.py) chạy đúng phép đo trên, nhưng với
  faster-whisper thật trên GPU và thời gian nhận dạng đo thật:

  ```bash
  docker exec -it rvt_ai uv run python eval/golden_session.py --golden eval/golden_1 --skip-lines 12-25,180- \
      --out /tmp/golden_1_session.json
  ```

  Script in ra các số sau, rồi chấm chữ trên màn hình với phụ đề như `golden_eval.py`:
  - số thẻ đã chốt bị xoá, thẻ chữ tạm còn treo, câu hiện hai lần;
  - số lần giữ / ghép / chốt riêng phần đuôi;
  - số câu bịa còn trên màn hình;
  - số lượt dịch câu rất ngắn (≤ 6 ký tự). Số này gồm cả câu ngắn thật như "はい", nên chỉ dùng để so trước và sau khi
    sửa.

  Đã chạy thử script trong sandbox trên toàn bộ golden_1, với `WhisperModel` thay bằng bản giả lập. Kết quả trùng từng
  số với cột `873d676` ở mục 5: 7 thẻ bị xoá ở đúng các thời điểm, 3 phần đuôi chốt riêng, 8 câu bịa, 134/141 câu. Riêng
  ký tự lời thoại bắt được là 90,9% thay vì 90,7%, vì script chấm bằng `difflib` như `golden_eval.py`, còn mục 5 chấm
  bằng căn chỉnh Levenshtein như 07.
- **Kiểm riêng từng chỗ:** `mt_validator.validate` với bản dịch có dấu ngoặc kép; `strip_committed_prefix` với 9 ca;
  thuật toán AudioWorklet mới trên audio 48 kHz stereo của golden_1.
- **Không chạy được trong sandbox:** model dịch, Safari, GPU. Số liệu tuyệt đối cần đo lại trên server.

## 3. Server

### 3.1 Bản dịch có dấu ngoặc kép thành "[Lỗi dịch vi]"

```python
# mt_validator.py:41 (873d676)
if (cleaned.startswith('"') and cleaned.endsWith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
```

- `str` của Python không có `endsWith`. Vế `startswith('"')` sai thì Python không xét vế sau, nên lỗi chỉ nổ khi bản dịch
  bắt đầu bằng `"` — đúng lúc nhánh này cần chạy.
- Kiểm: `mt_validator.validate("こんにちは", "ja", "vi", '"Xin chào"')` →
  `AttributeError: 'str' object has no attribute 'endsWith'`. Bản dịch không có ngoặc kép, hoặc có ngoặc đơn, vẫn qua.
- `_run_mt` bắt mọi exception ở khối ngoài cùng ([session.py#L672-L677][c-mt-except]), gửi `error mt_failed` rồi
  `mt.final "[Lỗi dịch vi]"`. Chữ dịch đang hiện dần trên màn hình bị thay bằng "[Lỗi dịch vi]".
- LLM có lúc bọc bản dịch trong ngoặc kép, nhất là khi câu nguồn có 「」. App có sẵn nhánh bỏ ngoặc kép ở cả server
  lẫn `cleanText.ts` cho trường hợp này.
- Dòng này được chép từ `cleanText.ts`, nơi `endsWith` là đúng.

**Sửa:**

```python
if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
```

- Tách `validate()` ra khỏi khối `try` lớn của `_run_mt`. Nếu bộ làm sạch lỗi thì dùng bản dịch thô đã `strip()`, đừng
  thay bằng "[Lỗi dịch …]": model dịch đã chạy xong, chỉ khâu làm sạch hỏng.
- Thêm test ở mục 6.

### 3.2 Phụ đề đã chốt bị xoá

```python
# session.py:419-435 (873d676) — đoạn vừa nhận dạng ra rỗng
if self.last_partial_uid is not None:
    await self.send_event(AsrFinal(utterance_id=self.last_partial_uid, text="", ...))
    self.last_partial_uid = None
```

- `last_partial_uid` được gán mỗi khi gửi chữ tạm ([session.py#L333-L345][c-partial-uid]) và chỉ được đặt lại ở đoạn code
  trên. Sau một câu chốt có chữ, biến vẫn giữ uid của câu đó.
- Đoạn kế tiếp nhận dạng ra rỗng → server gửi `asr.final` rỗng cho uid của câu trước → `useStore.ts` xoá thẻ đó
  ([useStore.ts#L122-L127][c-store-delete]), mất cả chữ gốc lẫn bản dịch. Đoạn rỗng thường là:
  - đoạn ngắn dưới 0,8 s, chưa có chữ tạm;
  - câu bịa vừa bị lọc (§3.3);
  - tiếng động, tiếng thở.
- **Ca thứ hai:** mọi câu của đoạn đã được chốt sớm. Câu chốt sớm lấy đúng uid của thẻ chữ tạm đang hiện. Nếu sau đó không
  còn chữ tạm mới thì `last_partial_uid` vẫn trỏ vào uid ấy, và `asr.final` rỗng xoá luôn câu vừa chốt sớm.
- Bộ lọc câu bịa mới làm số đoạn rỗng tăng, nên lỗi này gặp nhiều hơn trước.
- **golden_1:** 7 thẻ đã chốt bị xoá trong 860 s, 5 thẻ là câu thoại thật:
  - 4 lần ngay sau một đoạn ngắn 0,7–1,2 s mà bộ lọc câu bịa mới vừa xoá chữ "ご視聴…". Ví dụ: mất
    "嫌いなのは出来上がるまで待つこと。趣味はラーメンの食べ比べ。" ở 167,5 s và "腹が減ってても戦えるさ!" ở 620,8 s;
  - 3 lần là chính câu vừa chốt sớm: "始め!" (421,8 s), "これまで彼が受け持った反応、結果だ。" (453,6 s),
    "ぶっ飛ばしてやる!" (514,0 s).
  - Nếu giữ lại các thẻ này, ký tự lời thoại bắt được tăng từ 90,7% lên 93,6% và CER giảm từ 0,231 xuống 0,208. Riêng
    lỗi này đã chiếm phần lớn chênh lệch giữa hai bản ở mục 5.

**Sửa:** chỉ xoá thẻ chữ tạm của chính đoạn này. Chữ tạm của một đoạn luôn mang uid mà đoạn đó sẽ dùng khi chốt, nên chỉ
cần so với `uid`:

```python
if self.last_partial_uid == uid:  # thay cho: is not None
    await self.send_event(AsrFinal(utterance_id=uid, side=side, text="", ...))
```

Sửa kèm §3.7 để chữ tạm "đến muộn" không mang uid của đoạn sau.

### 3.3 Lọc câu bịa tiếng Nhật chỉ bắt được một nửa

- 07 §4 đề xuất bỏ câu khớp danh sách câu bịa khi **VAD trung bình của đoạn** dưới 0,35. Trung bình ở 07 tính trên mọi khung
  của đoạn audio gửi đi nhận dạng: preroll, lời nói và khoảng lặng cuối.
- Code truyền `stats.prob_mean` của segmenter. Giá trị này chỉ cộng các khung có `has_speech`
  ([segmenter.py#L65-L77][c-probsum], [segmenter.py#L155-L160][c-stats]). Với balanced profile, `neg_threshold` là 0,25,
  nên một đoạn bắt đầu sau khoảng lặng luôn có trung bình ≥ 0,25, và hầu như ≥ 0,35.
- Trên golden_1, chỉ 14/231 đoạn có `prob_mean` < 0,35:
  - 12 đoạn là phần còn lại ngay sau một lần cắt, vì khi cắt thì `_prob_sum` được nạp lại bằng mọi khung còn lại, kể cả
    khung thấp;
  - 1 đoạn bị cắt giữa chừng;
  - 1 đoạn bình thường.

  Trong 160 đoạn bắt đầu sau khoảng lặng, giá trị nhỏ nhất là 0,325 và chỉ 2 đoạn dưới 0,35.

| Cách tính "VAD trung bình" của đoạn | Câu bịa bị lọc (golden_1, không prompt) | Có prompt ngữ cảnh (cách thử ở 07 §5) |
|---|---|---|
| `prob_mean` của segmenter (`873d676`) | 10/20 | 6/13 |
| Mọi khung của đoạn audio (cách đo ở 07 §4) | 18/20 | 11/13 |
| Mọi khung trong `frame_probs`, tức từ lúc bắt đầu nói (đề xuất) | 18/20 | 11/13 |

- **Lỗi thứ hai: mẫu có neo `^…$` không chấp nhận dấu câu ở cuối.** `^[\s・…—\-]*おわり[\s・…—\-]*$` không khớp
  "おわり。", "終わり!" hay "字幕。". Prompt nối bằng "。" (§3.8) làm Whisper thêm "。" thường hơn. Trong mô phỏng phiên,
  "おわり。" ở 15,7 s lọt qua bộ lọc và hiện trên màn hình.
- **Lỗi thứ ba: chữ tạm không qua bộ lọc.** Nhận dạng tạm không truyền `vad_mean`
  ([session.py#L279-L285][c-partial-start]), nên bộ lọc câu bịa không áp cho chữ tạm:
  - câu bịa vẫn nháy lên trên thẻ chữ tạm: 11 lần trên golden_1;
  - câu bịa quay lại màn hình qua nhánh "cứu chữ từ chữ tạm" ([session.py#L405-L417][c-rescue]). Ở 846,8 s, chữ chốt
    "ご視聴ありがとうございました。" bị lọc, rồi chính chữ tạm "ご視聴ありがとうございました" được dùng thay.

**Sửa:**

```python
# segmenter.py — _stats(): trung bình trên mọi khung từ lúc bắt đầu nói (gồm khung thấp giữa câu và khoảng lặng cuối)
probs = self.frame_probs
prob_mean = sum(probs) / len(probs) if probs else 0.0

# asr_whisper.py — cho phép dấu câu quanh câu bịa ngắn
_EDGE = r"[\s・…—\-。、！？!?]*"
JA_HALLUCINATIONS = [
    r"ご視聴(?:ありがとう|いただき)",
    r"チャンネル登録",
    rf"^{_EDGE}字幕{_EDGE}$",
    rf"^{_EDGE}おわり{_EDGE}$",
    rf"^{_EDGE}終わり{_EDGE}$",
]
```

- `prob_mean` cũng được in trong log `vad_mean=` của mỗi câu. Sau khi sửa, số này thấp hơn trước với cùng một đoạn: trung
  vị trên golden_1 giảm từ 0,81 xuống 0,62. Lưu ý khi so log cũ và mới.
- Ở nhánh cắt giữa chừng, code đã dùng trung bình mọi khung (`cut_probs`), nên chỉ cần sửa `_stats()`.
- Nhận dạng tạm cũng mang `vad_mean`, tính trên `frame_probs` tới lúc đó:

  ```python
  # session.py — handle_audio_chunk
  probs = self.segmenter.frame_probs
  vad_mean = sum(probs) / len(probs) if probs else None
  asyncio.create_task(self._process_partial_audio(buffer, side, uid, vad_mean))
  # _process_partial_audio(..., vad_mean) truyền tiếp vad_mean=vad_mean vào execute_transcribe(..., is_final=False)
  ```

- Trên cả phiên (mục 5), ba sửa này đưa số câu bịa còn trên màn hình từ 8 xuống 2, và số lần câu bịa nháy lên ở chữ tạm từ
  11 xuống 4.

### 3.4 Ghép phần đuôi câu

Cách làm hiện tại:

1. Nếu chữ của đoạn có dấu kết câu và phần sau dấu kết câu cuối cùng không quá 30 ký tự, server giữ phần đuôi đó lại và
   chỉ chốt phần trước ([session.py#L482-L501][c-tail-hold]).
2. Đoạn chốt kế tiếp được nối phần đuôi vào đầu ([session.py#L447-L452][c-tail-merge]).
3. Bộ hẹn giờ 1,5 s tính từ lúc chốt ([session.py#L542-L552][c-tail-timer]). Hết giờ mà chưa có đoạn kế tiếp thì phần
   đuôi được chốt thành một thẻ mới.

Mô phỏng phiên trên golden_1:

| Phần đuôi trên golden_1 (860 s) | `873d676` | Sửa như dưới đây |
|---|---|---|
| Số lần giữ phần đuôi | 3 | 4 |
| Được ghép vào câu phát ra ngay sau | 0 | 4 |
| Bị chốt riêng thành thẻ mới sau 1,5 s | 3 | 0 |
| Chiếm thẻ chữ tạm của câu đang nói | 1 | 0 |
| Từ lúc giữ tới lúc phần đuôi hiện trên màn hình | 1,5 s | trung vị 2,4 s, tối đa 3,5 s |

Ví dụ ở 263,8 s:

- `873d676` hiện ba thẻ: "え?", rồi 1,5 s sau "今年の卒業生27人のうち、", rồi "忍者になれるのは9人だけ。". Mảnh ở giữa được dịch
  riêng.
- Bản sửa hiện hai thẻ: "え?" và "今年の卒業生27人のうち、忍者になれるのは9人だけ。", đúng câu của phụ đề.

- **Hẹn giờ 1,5 s tính từ lúc chốt là quá ngắn.** Đoạn kế tiếp chỉ được chốt khi người nói dừng hoặc đoạn chạm 4–6 s,
  nên thường tới sau 2–6 s. Trên golden_1, cả 3 lần giữ đều hết 1,5 s trước khi đoạn kế tiếp được chốt.
- **Mảnh đuôi chiếm thẻ chữ tạm của câu đang nói.** Khi hết giờ, phần đuôi được gán uid = `utterance_id_counter`. Đó
  chính là uid mà chữ tạm của câu đang nói đang dùng. Thẻ chữ tạm vì thế bỗng thành mảnh đuôi đã chốt, còn chữ tạm nhảy
  sang một thẻ mới. Trên golden_1 gặp 1/3 lần. Nếu đoạn đang nói sau đó ra rỗng, §3.2 xoá luôn mảnh đuôi này.
- **Ghép tiếng Nhật có thêm dấu cách:** `self.pending_tail_fragment + " " + text` cho ra "少しは 我慢しなさい". Unit test
  [test_session.py#L237][c-tail-test] đang khẳng định đúng chuỗi có dấu cách này.
- **Hết lượt nói (`turn.stop`) hoặc đổi bên:** phần đuôi được chốt với nhãn ngôn ngữ cố định "vi"
  ([session.py#L263-L271][c-flush-vi]). Với `targets=["vi"]`, câu "tiếng Việt" không được dịch đi đâu; nhãn trên thẻ
  cũng sai. Phần đuôi còn được chốt trước phần audio còn lại trong buffer, trong khi đáng lẽ phải ghép vào đầu phần đó.
- **Mảnh đuôi bị dịch riêng** đúng như 07 §6.1 muốn tránh: "少しは" → "Một chút…".

**Khuyến nghị: tắt hẳn tính năng này**, tức luôn chốt cả đoạn:

- Trên golden_1, tắt hay giữ (đã sửa) cho cùng chữ trên màn hình và cùng điểm chấm: CER 0,167, 138/141 câu. Chỉ khác chỗ
  ngắt thẻ ở 4 nơi trong 14 phút.
- Whisper turbo hiếm khi đặt dấu kết câu giữa đoạn (07 §6.1), nên điều kiện giữ phần đuôi hiếm khi xảy ra.
- Giữ tính năng thì phải sửa mọi chỗ ở dưới, kể cả ghép vào câu chốt sớm. Phần đuôi hiện trễ thêm khoảng 1 s, và web phải
  xoá bản dịch cũ khi thẻ được chốt lại.
- Muốn bản dịch liền mạch qua các đoạn bị cắt thì đã có cách rẻ hơn: `_run_mt` đã gửi 2 câu trước làm ngữ cảnh.

**Nếu vẫn giữ tính năng, sửa như sau** (bản đã chạy trong mô phỏng):

```python
# session.py — khi giữ phần đuôi: nhớ thẻ gốc và ngôn ngữ
self.pending_tail_fragment = tail_part
self.pending_tail_uid = uid  # thẻ của câu vừa chốt
self.pending_tail_head = complete_part
self.pending_tail_lang = final_lang
self._pending_tail_task = asyncio.create_task(self._flush_pending_tail_timer(tail_part, side, final_lang))


async def _flush_pending_tail_timer(self, tail: str, side: Side, lang: Lang) -> None:
    """Giữ phần đuôi chừng nào đoạn kế tiếp còn đang nói; trả về thẻ gốc khi im lặng 1 s hoặc đã giữ 8 s."""
    try:
        waited, quiet = 0.0, 0.0
        while self.pending_tail_fragment == tail and waited < 8.0 and quiet < 1.0:
            await asyncio.sleep(0.2)
            waited += 0.2
            quiet = 0.0 if self.segmenter.is_speaking else quiet + 0.2
        if self.pending_tail_fragment == tail:
            await self._return_tail_to_card(side)
    except asyncio.CancelledError:
        pass


async def _return_tail_to_card(self, side: Side) -> None:
    """Không ghép được thì trả phần đuôi về thẻ gốc (chốt lại cả câu và dịch lại), không tạo thẻ mới."""
    if not self.pending_tail_fragment or self.pending_tail_uid is None:
        self.pending_tail_fragment = ""
        return
    tail, uid, head, lang = (
        self.pending_tail_fragment,
        self.pending_tail_uid,
        self.pending_tail_head,
        self.pending_tail_lang,
    )
    self.pending_tail_fragment, self.pending_tail_uid = "", None
    joiner = "" if lang == "ja" else " "
    await self._emit_final_and_mt(uid, side, head + joiner + tail, lang, {lang: 1.0}, False, 0)


# Khi ghép vào đoạn kế tiếp: không thêm dấu cách với tiếng Nhật
joiner = "" if self.pending_tail_lang == "ja" else " "
text = self.pending_tail_fragment + joiner + text
self.pending_tail_fragment, self.pending_tail_uid = "", None

# _flush_segmenter: xử lý phần audio còn lại TRƯỚC (nó sẽ ghép phần đuôi), rồi mới trả phần đuôi còn sót về thẻ gốc
buf = self.segmenter.force_final()
if buf:
    await self._process_final_audio(buf, self.current_side, self.segmenter.last_stats)
if self._pending_tail_task and not self._pending_tail_task.done():
    self._pending_tail_task.cancel()
await self._return_tail_to_card(self.current_side or "A")
```

- **Web cần sửa kèm.** `asr.final` gửi lại cho một thẻ đã chốt nghĩa là chữ gốc đã đổi. `useStore.ts` phải xoá bản dịch
  cũ của thẻ đó. Nếu không, các `mt.delta` của lần dịch mới bị nối vào sau bản dịch cũ
  ([useStore.ts#L156-L170][c-store-delta]) cho tới khi `mt.final` tới:

  ```ts
  case "asr.final": {
    // ...
    const prev = newUtterances[event.utterance_id];
    const textChanged = prev?.isFinal && prev.originalText !== event.text;
    newUtterances[event.utterance_id] = {
      ...(prev ?? { id: event.utterance_id, side: event.side as Side }),
      translations: textChanged ? {} : prev?.translations ?? {},
      originalText: event.text,
      // ...
    };
  }
  ```

- **Câu chốt sớm cũng phải nhận phần đuôi.** Lần chạy đầu của bản sửa ghép "今年の卒業生27人のうち、" vào sai câu. Câu
  ngay sau nó được chốt sớm, mà đường chốt sớm không biết có phần đuôi đang giữ, nên phần đuôi bị ghép vào câu thứ hai và
  thứ tự trên màn hình bị đảo. Phải thêm vào khối chốt sớm của `_process_partial_audio`:

  ```python
  shown = stable_sentence
  if self.pending_tail_fragment:  # phần đuôi thuộc về câu phát ra ngay sau nó, kể cả câu chốt sớm
      if self._pending_tail_task and not self._pending_tail_task.done():
          self._pending_tail_task.cancel()
      joiner = "" if self.pending_tail_lang == "ja" else " "
      shown = self.pending_tail_fragment + joiner + stable_sentence
      self.pending_tail_fragment, self.pending_tail_uid = "", None
  # committed_sentences vẫn giữ stable_sentence để bỏ khỏi chữ chốt của đoạn; asr.final và bản dịch dùng shown
  ```

### 3.5 llama.cpp vẫn dừng ở "—" và "\*\*"

- 07 §6.2 nêu hai vấn đề cùng lúc: `mt_validator` xoá từ "—" hoặc "\*\*" tới hết câu, **và** llama.cpp dừng sinh khi gặp
  "\*\*".
- `873d676` sửa phần `mt_validator` (thay "—" bằng ", ", bỏ ký hiệu "\*\*"). Nhưng "—" và "\*\*" vẫn nằm trong `stop`
  của request gửi llama.cpp ([mt_llama.py#L195-L200][c-stop]). Model sinh tới "—" là dừng: "Đợi đã — ê!" về tới server
  chỉ còn "Đợi đã".
- `_run_mt` cũng ngừng gửi `mt.delta` khi gặp hai chuỗi này ([session.py#L576-L579][c-cutoff]).
- Unit test của validator vẫn qua, vì nó đưa thẳng cả câu vào `validate()` mà không qua llama.cpp.

**Sửa:** bỏ `"**"` và `"—"` khỏi `stop` trong `mt_llama.py` và khỏi `cutoff_markers` trong `_run_mt`. Phần dọn dẹp đã có
trong `mt_validator`, ở cả server và `cleanText.ts`.

### 3.6 So khớp câu đã chốt sớm

- `strip_committed_prefix` mới ([session.py#L35-L73][c-strip]) có ba bước: khớp nguyên văn, khớp sau khi bỏ dấu câu, và
  `SequenceMatcher`.
- Bước thứ ba có hai lỗi:
  - Nó bỏ đi `match.size` ký tự tính từ đầu chuỗi, bỏ qua `match.b`. Khi chữ chốt có thêm vài ký tự ở đầu (ví dụ "あ、"),
    vị trí cắt bị lệch.
  - Nó đòi `match.a == 0`, nên nếu Whisper làm rơi ký tự đầu của câu đã chốt thì không khớp, và câu hiện hai lần.
- Đề xuất: căn bằng khoảng cách sửa (edit distance) giữa câu đã chốt và từng đoạn đầu có độ dài `n − 3 … n + 3` của chữ
  chốt, sau khi bỏ dấu câu. Chọn đoạn gần nhất, chỉ cắt khi khác không quá 1/4 số ký tự.

| Chữ chốt của cả đoạn (câu đã chốt sớm: "夢は自分の中に留めておく。") | `873d676` | Đề xuất |
|---|---|---|
| 夢は自分の中に留めておく俺にあるのは目的だ一族 | 俺にあるのは目的だ一族 | 俺にあるのは目的だ一族 |
| あ、夢は自分の中に留めておく。俺にあるのは目的だ | **く。**俺にあるのは目的だ | 俺にあるのは目的だ |
| え夢は自分の中に留めておく俺にあるのは目的だ | **く**俺にあるのは目的だ | 俺にあるのは目的だ |
| は自分の中に留めておく。俺にあるのは目的だ (rơi ký tự đầu) | **cả câu, hiện hai lần** | 俺にあるのは目的だ |
| 夢は自分の中に留めて置く。俺にあるのは目的だ (おく → 置く) | **置く。**俺にあるのは目的だ | 俺にあるのは目的だ |
| 全然違う文章がここに来るとどうなる (không liên quan) | giữ nguyên | giữ nguyên |

Ca thật trong mô phỏng phiên (§5), ở 482,7 s: câu chốt sớm "ズレてるのは先生の髪型だろ?" viết bằng katakana, chữ chốt của
cả đoạn "ずれてるのは先生の髪型だろ?" viết bằng hiragana. `873d676` hiện câu này hai lần; cách đề xuất bỏ đúng.

Thêm ba ca trong test: "Xin chào các bạn." / "Xin chào các bạn! Hôm nay trời đẹp." → "Hôm nay trời đẹp."; "そうだ。" /
"そうだそうだ行こう" → "そうだ行こう"; "はい。" / "はい" → "". Cả 9/9 ca đều ra đúng.

```python
def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def strip_committed_prefix(full: str, committed: str) -> str:
    """Bỏ câu đã chốt sớm khỏi đầu chữ chốt của cả đoạn; chịu được lệch dấu câu, thừa/thiếu/sai vài ký tự."""
    full = full.strip()
    norm_c = PUNCT_REGEX.sub("", committed)
    if not norm_c or not full:
        return full
    pos = [i for i, ch in enumerate(full) if not PUNCT_REGEX.match(ch)]  # vị trí các ký tự không phải dấu câu
    norm_full = "".join(full[i] for i in pos)
    n = len(norm_c)
    best = None  # (khoảng cách, |j - n|, j)
    for j in range(max(1, n - 3), min(len(norm_full), n + 3) + 1):
        cand = (_edit_distance(norm_c, norm_full[:j]), abs(j - n), j)
        best = cand if best is None or cand < best else best
    if best is None or best[0] > max(1, n // 4):
        return full  # không giống: giữ nguyên, thà hiện trùng còn hơn mất chữ
    idx = pos[best[2] - 1] + 1
    while idx < len(full) and PUNCT_REGEX.match(full[idx]):
        idx += 1
    return full[idx:].strip()
```

Chuỗi ngắn (dưới 60 ký tự) nên mỗi lần chỉ tốn vài chục micro giây.

### 3.7 Chữ tạm "đến muộn" hiện thành thẻ trùng

- Mỗi lần nhận dạng tạm được tạo với `uid = self.utterance_id_counter`, nhưng `_process_partial_audio` không dùng tham số
  `uid` này ([session.py#L279-L285][c-partial-start]). Khi có kết quả, nó lấy uid **hiện tại**
  ([session.py#L333][c-partial-uid]).
- Nếu đoạn vừa được chốt trong lúc nhận dạng tạm đang chạy, uid hiện tại đã sang đoạn sau. Chữ tạm cũ — chính là chữ của
  câu vừa chốt — hiện thành một thẻ mới bên dưới, cho tới khi chữ tạm của đoạn sau ghi đè lên.
- `cancel_session_partials` chỉ huỷ được lượt đang chờ trong hàng đợi, không huỷ được lượt đang chạy trên GPU.
- Ví dụ ở 12,9 s: thẻ uid 2 hiện "落ち着きなさいよ。私だって知らないわ。少しは我慢しなさい。" — chữ của đoạn uid 1 — trong
  khoảng 1 s, rồi mới thành "少しは我慢しなさい".
- **golden_1:** 56 lần trong 860 s. 51 lần trong số đó là chữ của chính câu vừa chốt, tức người xem thấy cùng một câu hai
  lần. Thẻ trùng nằm trên màn hình trung vị 1,0 s; 10% số lần lâu hơn 3,5 s; lâu nhất 11,8 s, khi câu sau tới muộn.
- Chữ tạm cũ còn ghi đè `last_partial_text`. Hai trong bốn câu hiện hai lần ở mục 5 ("思っていたよりずっとひどい…",
  "お前は本当に") đến từ nhánh "cứu chữ từ chữ tạm" dùng đúng chữ tạm cũ này.

**Sửa:** bỏ kết quả nhận dạng tạm nếu uid đã đổi kể từ lúc gửi đi:

```python
async def _process_partial_audio(self, audio: bytes, side: Side, uid: int) -> None:
    text, lang, _ = await self.scheduler.execute_transcribe(...)
    if uid != self.utterance_id_counter:
        return  # đoạn đã chốt (hoặc vừa chốt sớm) trong lúc chờ: chữ tạm này đã cũ
    if not text or self.current_side != side:
        return
```

### 3.8 Prompt ngữ cảnh: kết quả và chỉnh nhỏ

- Prompt ngữ cảnh làm đúng 07 §5: chỉ dùng chữ đã qua bộ lọc, nối bằng "。", tối đa 60 ký tự. Sau khi sửa các lỗi khác,
  CER của cả phiên là 0,167, thấp nhất từ trước tới giờ trên golden_1. Để so sánh, 07 đo theo từng đoạn: 0,38 khi không
  có prompt, 0,19 với prompt thử nghiệm.
- Ca chép prompt mà 07 §5 đã thấy vẫn còn. Ở 484,1 s, một đoạn không lời ra "お前ちょっと。" (`873d676`) hoặc
  "お前ちょっと待って。" (bản sửa), chép từ câu "お前ちょっとずれてるな" ngay trước. Đây là giá phải trả cho prompt; theo dõi
  bằng `golden_session.py`.

Ba chỗ nên chỉnh, ưu tiên thấp:

- **Prompt được dựng lúc lượt chốt được tạo, chưa phải lúc nó chạy.** Khi GPU bận (dịch cùng GPU, hoặc phải chạy CPU như ca
  OOM trong `873d676`), lượt trước có thể chưa xong nên prompt thiếu câu ngay trước. Nên dựng prompt trong worker của
  `AsrScheduler`, ngay trước khi nhận dạng.
- **Câu chốt sớm không vào lịch sử prompt.** Lịch sử chỉ thêm chữ chốt của cả đoạn, sau khi đã bỏ phần chốt sớm. Nên thêm
  cả câu chốt sớm.
- **Cửa sổ 5 s tính theo giờ hệ thống**, từ lúc câu trước có kết quả. Một đoạn nói liền 5–6 s vì thế không có prompt dù
  không có khoảng lặng nào. Trên golden_1 chỉ gặp 2/176 đoạn nối tiếp (dài 5,6 và 5,9 s), nên chỉ cần sửa khi tiện: tính
  theo thời gian audio, bỏ prompt khi khoảng lặng giữa hai đoạn quá 5 s, như 07 §5 đã đo.

### 3.9 Lỗi nhỏ

- **`AsrScheduler._run_transcribe`** ([scheduler.py#L44-L59][c-typeerror]) gặp `TypeError` thì gọi lại không kèm
  `vad_mean` và `initial_prompt`. Một `TypeError` nổ bên trong faster-whisper sẽ làm câu đó bị nhận dạng hai lần, và lỗi
  bị giấu đi. Nên kiểm chữ ký hàm một lần lúc khởi tạo (`inspect.signature`), không bắt `TypeError` lúc chạy.
- **`client.health`** chỉ được ghi ở mức DEBUG ([stream.py#L170-L175][c-health]), nên log mặc định (INFO) không có gì.
  Nên ghi INFO khi có bất thường:
  - `audio_context_state` khác "running";
  - `track_muted` hoặc `track_ended`;
  - `chunks_sent` không tăng sau 5 s;
  - `rms_dbfs` dưới −80;
  - trang bị ẩn.
- **Giới hạn phiên được kiểm trước khi biết `client_id`** ([stream.py#L37-L43][c-limit]). `client_id` chỉ có trong
  `session.start`, sau `accept()`. Khi bốn chỗ đều bị phiên "chết" chiếm, phiên mới bị đóng 4429 trước khi kịp đá phiên
  cũ cùng `client_id`. Cách sửa ở §4.3.
- **`Dockerfile`:** cờ `--ws-ping-interval 10 --ws-ping-timeout 10` chỉ có hiệu lực sau
  `docker compose build ai`. Mount `./ai/src` không đủ, vì `CMD` nằm trong image.
- **`speech_pad_ms`** vẫn có trong cấu hình nhưng không được dùng (07 §10).
- **`golden_eval.py`:** đã sửa dòng quá dài, format và biến `re` che tên module `re` (commit `799502f`).

## 4. Web

### 4.1 "Chạm để tiếp tục nghe" không cứu được mic bị mute hoặc im lặng số

```ts
// ws_client.ts:366-378 (873d676)
async resumeCapture() {
  useStore.getState().setCaptureWarning(null);
  if (ctx suspended/interrupted) await this.audioContext.resume();
  const track = this.mediaStream?.getAudioTracks()[0];
  if (!track || track.readyState === 'ended') { await this.startAudio(...); }
}
```

- **Mic bị "muted"** (tab hoặc app khác lấy mic, cuộc gọi, Siri — 07 §9.2 dòng 2): track vẫn "live" nên không được xin
  lại. Lần chạm chỉ xoá cảnh báo. `onmute` đã phát một lần rồi, nên cảnh báo chỉ hiện lại khi trang bị ẩn rồi hiện lại,
  trong khi mic vẫn câm.
- **Im lặng số** (2 s toàn số 0): cảnh báo chỉ hiện khi bộ đếm bằng đúng 50 (`silentChunkCount === 50`). Chạm xoá cảnh
  báo; bộ đếm tiếp tục tăng qua 50 nên cảnh báo không bao giờ hiện lại.
- **Quay lại từ nền:** cảnh báo "Trang vừa quay lại…" hiện kể cả khi `resume()` thành công ngay
  ([ws_client.ts#L32-L44][c-foreground]).
- **Thu âm tab:** khi video tạm dừng, luồng âm thanh của tab thường là im lặng số. Cảnh báo "Microphone đang nhận toàn số
  0" vẫn hiện ra dù không có gì hỏng.
- **Khung audio ngừng tới** (watchdog 2 s): chỉ ghi console, không hiện gì cho người dùng.

**Sửa:** thay các cảnh báo một lần bằng một phép kiểm "đang nghe" chạy mỗi giây (07 §9.4 điểm 1):

```ts
private checkListening() {
  if (!useStore.getState().isMicActive) return;
  const track = this.mediaStream?.getAudioTracks()[0];
  const problems: string[] = [];
  if (this.audioContext?.state !== 'running') problems.push('ctx');
  if (!track || track.readyState === 'ended') problems.push('ended');
  else if (track.muted) problems.push('muted');
  if (Date.now() - this.lastChunkTime > 2000) problems.push('stalled');
  if (this.audioSource === 'mic' && this.zeroSince > 0 && Date.now() - this.zeroSince > 2000) problems.push('zeros');
  useStore.getState().setCaptureWarning(problems.length ? messageFor(problems) : null);
}

async resumeCapture() {  // gọi trong lần chạm
  await this.audioContext?.resume().catch(() => {});
  const track = this.mediaStream?.getAudioTracks()[0];
  const zeros = this.zeroSince > 0 && Date.now() - this.zeroSince > 2000;
  const { activeSide, audioSource } = useStore.getState();
  if (activeSide && (!track || track.readyState === 'ended' || track.muted || zeros)) {
    await this.startAudio(activeSide, audioSource);  // dừng luồng cũ rồi getUserMedia lại, ngay trong lần chạm
  }
  setTimeout(() => this.checkListening(), 1500);  // còn lỗi thì cảnh báo hiện lại
}
```

- Trên Safari, gọi lại `getUserMedia` trong một lần chạm là cách để lấy lại mic từ trang hoặc app khác (07 §9.2).
- Không coi im lặng số là lỗi khi thu âm tab.

### 4.2 Thu âm tab: "Dừng chia sẻ" không còn tắt thu

- Với nguồn tab, code gán `audioTracks[0].onended = () => this.stopAudio()` ([ws_client.ts#L271][c-tab-ended]). Ngay
  sau đó vòng `getTracks().forEach` gán lại `track.onended` cho mọi track ([ws_client.ts#L298][c-track-ended]), nên
  handler cũ bị ghi đè.
- Khi bấm "Dừng chia sẻ" của Chrome, app không tắt nữa: nút mic vẫn sáng, kèm cảnh báo "Microphone đã bị đóng".

**Sửa:** chỉ gán `onended` cảnh báo cho nguồn mic. Với nguồn tab, giữ `stopAudio()`.

### 4.3 `client_id` dùng chung giữa các tab: hai tab đá nhau

Đây là hệ quả của đề xuất ở 07 §9.4 điểm 4: lưu `client_id` trong `localStorage` là sai.

- `localStorage` dùng chung cho mọi tab cùng origin, nên mọi tab gửi cùng một `client_id`
  ([ws_client.ts#L3-L14][c-clientid]).
- Mỗi tab mở kết nối ngay khi tải trang, kể cả khi chưa bật mic. Tab sau tới thì server đóng kết nối của tab trước
  (mã 1000).
- Client nối lại sau 2 s với mọi mã đóng ([ws_client.ts#L147][c-reconnect]), và lại đá tab kia. Hai tab thay nhau mất
  kết nối, và mỗi lần nối lại là một phiên mới, mất buffer của câu đang nói.
- **Kiểm trên server thật** (`rvt_ai.main` với engine giả): hai client cùng `client_id`, nối lại sau 2 s như
  `ws_client.ts`. Trong 20 s, mỗi client bị đóng 5 lần với mã 1000 "Replaced by new connection", hai bên xen kẽ cách
  nhau đúng 2 s.

**Sửa:**

- `client_id` theo từng trang: sinh một lần trong bộ nhớ của `RVTClient`, hoặc lưu trong `sessionStorage`. Mục đích chỉ là
  để chính trang đó, khi nối lại, đá được kết nối "chết" của mình.
- Gửi `client_id` trên URL (`/ws?client_id=…`), để server đá phiên cũ **trước** khi kiểm giới hạn phiên (§3.9).
- Server đóng kết nối bị thay bằng mã riêng, ví dụ 4409 "replaced". Client gặp 4409 thì không tự nối lại, mà hiện "App
  đang mở ở tab khác".

### 4.4 AudioWorklet: biquad bậc 2 chưa đủ chặn aliasing

Mô phỏng đúng thuật toán của `audio-processor.js` trên audio 48 kHz stereo của golden_1. Nhiễu aliasing được đo trong các
khung có lời, so với mức lời, theo cách đo của 07 §8:

| Cách hạ 48 → 16 kHz | Nhiễu aliasing so với lời | Suy giảm ở 8 kHz / 12 kHz / 16 kHz |
|---|---|---|
| Cũ: kênh trái, không lọc (`d079cb3`) | −26,1 dB | không lọc |
| Mới: (L+R)/2, biquad 7,5 kHz bậc 2 (`873d676`) | −33,2 dB | −3,7 / −11,2 / −20,5 dB |
| Hai biquad nối tiếp (bậc 4) | −38,8 dB | — |
| FIR 63 tap (cửa sổ Hamming, cắt 7 kHz) | −58,4 dB | −31 / −75 / −72 dB |

- Biquad bậc 2 chỉ giảm 3,7 dB ở 8 kHz (tần số Nyquist mới) và 11 dB ở 12 kHz, nên vẫn còn nhiều âm 8–16 kHz gập vào
  dải lời nói.
- FIR 63 tap tốn khoảng 3 triệu phép nhân-cộng mỗi giây ở 48 kHz, chưa tới 1–2% một nhân CPU trên điện thoại.
- `process()` tạo một `Float32Array` mới mỗi khối 128 mẫu, tức 375 lần mỗi giây trên luồng audio. Bộ thu gom rác có thể
  làm mất khung trên máy yếu. Nên cấp phát một lần trong constructor.

```js
// constructor: FIR thông thấp 63 tap, cửa sổ Hamming, cắt 7 kHz; bộ đệm cấp phát một lần
const taps = 63, fc = 7000 / sampleRate, m = (taps - 1) / 2;
this.h = new Float32Array(taps);
let sum = 0;
for (let i = 0; i < taps; i++) {
  const x = i - m;
  const sinc = x === 0 ? 2 * fc : Math.sin(2 * Math.PI * fc * x) / (Math.PI * x);
  this.h[i] = sinc * (0.54 - 0.46 * Math.cos((2 * Math.PI * i) / (taps - 1)));
  sum += this.h[i];
}
for (let i = 0; i < taps; i++) this.h[i] /= sum;
this.hist = new Float32Array(taps);
this.histPos = 0;
this.mono = new Float32Array(128);

// process(): với mỗi mẫu x đã trộn (L+R)/2
this.hist[this.histPos] = x;
let y = 0;
for (let k = 0, p = this.histPos; k < taps; k++) {
  y += this.h[k] * this.hist[p];
  p = p === 0 ? taps - 1 : p - 1;
}
this.histPos = this.histPos + 1 === taps ? 0 : this.histPos + 1;
mono[i] = y;  // sau đó giữ nguyên bộ nội suy tuyến tính hiện có
```

### 4.5 Lỗi nhỏ

- **Wake lock** (07 §9.4 điểm 5) chưa làm:
  - App vẫn chỉ xin wake lock lúc tải trang và khi trang hiện lại ([App.tsx#L113-L116][c-wakelock]).
  - Nên xin lại ngay trong lần chạm bật mic, và hiện trên giao diện khi không giữ được.
- **Cảnh báo dùng chữ "Microphone"** cả khi đang thu âm tab.

## 5. Đo lại golden_1 bằng cả phiên dịch

Cùng audio, cùng cách mô phỏng ở mục 2. Cột "sửa" gồm mọi sửa ở mục 3, trừ §3.1 và §3.5, vì mô phỏng không chạy model
dịch:

- §3.2: xoá đúng thẻ;
- §3.3: `vad_mean` trên mọi khung, mẫu câu bịa chấp nhận dấu câu, lọc cả chữ tạm;
- §3.4: giữ phần đuôi theo VAD, trả về thẻ gốc, ghép cả vào câu chốt sớm;
- §3.6: so khớp bằng khoảng cách sửa;
- §3.7: bỏ chữ tạm cũ.

| Chỉ số (golden_1, 860 s, cả phiên) | `873d676` | Sửa, giữ ghép phần đuôi | Sửa, tắt ghép phần đuôi |
|---|---|---|---|
| Thẻ đã chốt trên màn hình lúc cuối | 231 | 227 | 227 |
| Thẻ đã chốt bị xoá | 7 | 0 | 0 |
| Chữ tạm "đến muộn" hiện thành thẻ trùng | 56 | 0 | 0 |
| Thẻ liền nhau gần giống nhau\* | 8 | 4 | 4 |
| Câu chốt sớm | 13 | 12 | 12 |
| Câu bịa bị bộ lọc bỏ (chữ chốt và chữ tạm) | 8 | 21 | 21 |
| Câu bịa còn trên màn hình | 8 | 2 | 2 |
| Chữ tạm hiện câu bịa rồi mất | 11 | 4 | 4 |
| Phần đuôi: giữ / ghép / chốt riêng | 3 / 0 / 3 | 4 / 4 / 0 | — |
| Lượt dịch | 238 | 227 | 227 |
| Ký tự lời thoại bắt được | 90,7% | 93,4% | 93,4% |
| Câu thoại bắt được | 134/141 | 138/141 | 138/141 |
| CER so với phụ đề | 0,231 | 0,167 | 0,167 |
| Tổng số ký tự (đáp án: 2 491) | 2 528 | 2 490 | 2 490 |

\* Video có 4 chỗ lặp thật, ví dụ "おはよう" nói hai lần và lời bài hát, nên 4 là mức sàn. Ở `873d676` còn thêm 4 câu
hiện hai lần thật: "ズレてるのは先生の髪型だろ?" (chốt sớm bằng katakana, chữ chốt của cả đoạn bằng hiragana — §3.6),
"お前たちのこと、だんだん気に入ってきた。", và hai câu từ nhánh cứu chữ tạm (§3.7).

- **Chênh lệch điểm** đến từ thẻ bị xoá, câu bịa và câu hiện hai lần. Chỉ cần giữ lại 7 thẻ bị xoá, `873d676` đã lên 93,6%
  và CER 0,208.
- **2 câu bịa còn lại** là "ご視聴ありがとうございました。" ở 356,1 s và "おわり。" ở 616,2 s. Hai đoạn này có VAD trung bình
  0,38–0,39 (nhạc lẫn giọng). Hạ ngưỡng thì bắt được, nhưng dễ bỏ nhầm câu kết thật, nên giữ 0,35.
- **3 câu thoại vẫn sót** là các câu la hét, nói chồng mà 07 đã ghi nhận: "引っかかった。…", "危ない。逃げて…",
  "うわ、命中した…".
- **Tắt hay giữ ghép phần đuôi** cho cùng chữ và cùng điểm; chỉ khác chỗ ngắt thẻ ở 4 nơi (§3.4).

## 6. Test cần thêm

Mỗi lỗi ở mục 3 đều lọt qua bộ test hiện có. Các test dưới đây đỏ ở `873d676` và xanh sau khi sửa.

```python
def test_mt_validator_strips_double_quotes():
    res = mt_validator.validate("こんにちは", "ja", "vi", '"Xin chào"')
    assert res.is_valid and res.cleaned_text == "Xin chào"


@pytest.mark.asyncio
async def test_empty_final_does_not_wipe_previous_card():
    events = []

    async def send(e):
        events.append(e)

    texts = iter(["こんにちは。", ""])  # đoạn 1 có chữ; đoạn 2 ngắn, không có chữ tạm, nhận dạng ra rỗng
    session = RVTSession("t", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), send)
    session.scheduler = AsrScheduler(lambda *a, **k: (next(texts), "ja", {"ja": 1.0}))
    stats = SegmentStats(speech_ms=900, prob_mean=0.6, prob_max=0.9)
    session.last_partial_uid = 0  # đoạn 1 đã hiện chữ tạm với uid 0
    await session._process_final_audio(b"\x01" * 3200, "A", stats)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)
    assert not [e for e in events if isinstance(e, AsrFinal) and e.utterance_id == 0 and e.text == ""]
    await session.close()


def test_segment_vad_mean_counts_quiet_frames():
    seg = Segmenter(SegmenterConfig(threshold=0.4, neg_threshold=0.25, min_silence_ms=200))
    # 40 ms/khung: 1 khung rõ, 6 khung nửa vời (tiếng động, nhạc), rồi lặng
    finals = [seg.add_chunk(b"\x00\x00" * 640, p)[1] for p in [0.9] + [0.3] * 6 + [0.1] * 8]
    assert any(finals) and seg.last_stats.prob_mean < 0.35  # 873d676: 0,386; sau khi sửa: 0,267


@pytest.mark.parametrize("text", ["おわり。", "終わり!", "字幕。"])
def test_ja_hallucination_patterns_allow_trailing_punctuation(text):
    assert any(re.search(p, text) for p in JA_HALLUCINATIONS)
```

Thêm các ca của bảng §3.6 cho `strip_committed_prefix`. Sửa test ghép phần đuôi ([test_session.py#L237][c-tail-test]):
khẳng định "少しは我慢しなさい" (không dấu cách). Thêm một ca đúng thời gian thật: giữ phần đuôi, đặt
`segmenter.is_speaking = True`, chờ 3 s rồi mới đưa đoạn sau vào — phần đuôi phải được ghép vào đoạn sau, không bị chốt
riêng.

**Kiểm cả phiên:** chạy `eval/golden_session.py` trên server sau mỗi đợt sửa. Ngưỡng đạt ở mục 7.

## 7. Lộ trình đề xuất

| Bước | Nội dung | Tầng | Công | Xong khi |
|---|---|---|---|---|
| 0 · Hotfix | §3.1 `endswith`, bộ làm sạch lỗi thì dùng bản dịch thô; §3.2 xoá đúng thẻ, kèm §3.7 bỏ chữ tạm cũ; §3.5 bỏ "—", "\*\*" khỏi `stop` | server | 1 giờ | **Đã làm.** Test mục 6 xanh; `golden_session.py`: 0 thẻ đã chốt bị xoá, 0 thẻ treo |
| 1 · Session | §3.3 `vad_mean`, mẫu câu bịa, lọc cả chữ tạm; §3.4 tắt ghép phần đuôi (hoặc sửa đủ, kèm `useStore`); §3.6 so khớp | server (+ web nếu giữ ghép đuôi) | 1 ngày | `golden_session.py` trên golden_1: 0 thẻ bị xoá, 0 chữ tạm đến muộn, câu bịa trên màn hình ≤ 2, CER ≤ 0,18 (mô phỏng: 0,167) |
| 2 · Safari | §4.1 phép kiểm "đang nghe" + chạm để xin lại mic; §4.2; §4.3 `client_id` theo trang, 4409; wake lock | web + server | 1–2 ngày | Safari: tab khác lấy mic rồi trả, khoá màn hình, gọi Siri — app báo đúng và nghe lại sau một lần chạm; mở hai tab không đá nhau |
| 3 · Thu âm | §4.4 FIR 63 tap, cấp phát một lần | web | 0,5 ngày | aliasing ≤ −40 dB so với lời |
| 4 · Prompt | §3.8 ba chỉnh nhỏ | server | 0,5 ngày | CER golden_1 không tăng, câu bịa không tăng |

## 8. Rủi ro và đánh đổi

- **Số liệu mô phỏng** dùng Whisper ONNX trên CPU, độ trễ GPU giả định, và phụ đề tự động của YouTube làm đáp án. Thứ tự
  sự kiện và các lỗi logic (xoá thẻ, ghép đuôi, chữ tạm cũ) không phụ thuộc nhiều vào điều đó. Số tuyệt đối (CER, số câu
  bịa) thì phải đo lại bằng `golden_session.py` trên server.
- **Nếu vẫn giữ ghép phần đuôi:**
  - giữ lâu hơn (tới khi im lặng 1 s, tối đa 8 s) thì ghép được nhiều hơn, nhưng mảnh đuôi hiện trễ hơn — trên golden_1
    trễ thêm khoảng 1 s;
  - trả phần đuôi về thẻ gốc tốn thêm một lượt dịch cho thẻ đó.
- **Lọc cả chữ tạm** (§3.3) dùng cùng danh sách và cùng ngưỡng với chữ chốt. Các mẫu "おわり", "字幕" chỉ khớp khi cả câu chỉ
  có từ đó, nên câu thoại thật như "おわりだ" không bị bỏ.
- **`vad_mean` mới thấp hơn** với cùng một đoạn: log cũ và mới không so trực tiếp được; ngưỡng 0,35 của bộ lọc câu bịa giữ
  nguyên vì 07 §4 đã đo theo cách tính mới.
- **Xin lại `getUserMedia`** khi mic bị mute sẽ lấy mic khỏi trang hoặc app đang giữ nó, ví dụ một cuộc gọi. Chỉ làm khi
  người dùng chạm.

## Phụ lục A — Đối chiếu từng đề xuất của 07

| 07 | Đề xuất | Trạng thái ở `873d676` | Ghi chú |
|---|---|---|---|
| §3.4 | Sửa vị trí "cắt ở chỗ lặng nhất" | Đạt | 231/231 vị trí đúng; có test |
| §4 | Lọc câu bịa tiếng Nhật khi VAD trung bình < 0,35 | Một phần | §3.3: bắt 10/20; mẫu không chấp nhận "。" |
| §5 | Prompt ngữ cảnh: đã lọc câu bịa, nối bằng "。", ≤ 60 ký tự, bỏ sau 5 s | Đạt | §3.8: ba chỉnh nhỏ |
| §5 | Tên riêng, thuật ngữ của phim trong prompt / `hotwords` | Chưa làm | |
| §6.1 | Ghép mảnh câu trước khi dịch | Có lỗi | §3.4: chỉ kích hoạt 3 lần trong 14 phút; đề xuất tắt |
| §6.2 | Bỏ giới hạn số câu với ja → vi, thay bằng giới hạn độ dài | Đạt | |
| §6.2 | Coi "—" là dấu câu; bỏ ký hiệu "\*\*", giữ chữ | Một phần | §3.5: llama.cpp vẫn dừng ở hai chuỗi này; §3.1: lỗi `endsWith` |
| §7 | So khớp câu đã chốt sau khi bỏ dấu câu, căn bằng `SequenceMatcher` | Một phần | §3.6 |
| §7, §10 | `asr.final` rỗng cho thẻ chữ tạm khi mọi câu đã chốt sớm | Có lỗi | §3.2: xoá nhầm thẻ đã chốt |
| §8 | Trộn (L+R)/2 và lọc FIR trước khi hạ mẫu | Một phần | §4.4: biquad bậc 2, −33 dB |
| §9.3 | Thanh `?debug=1`, `client.health` mỗi 5 s | Đạt | §3.9: server chỉ ghi ở mức DEBUG |
| §9.3 | Server: log khoảng trống > 1 s, log 2 s toàn số 0 | Đạt | Chưa có số giây audio nhận được trên mỗi giây thực |
| §9.3 | `accept()` rồi đóng 4429; client đọc mã đóng | Đạt | |
| §9.4.1 | Trạng thái "đang nghe", "Chạm để tiếp tục" | Một phần | §4.1 |
| §9.4.2 | Chỉ một luồng mic | Đạt | `startAudio` dừng luồng cũ trước khi xin luồng mới |
| §9.4.3 | Đóng và nối lại khi 8 s không có tin từ server | Đạt | |
| §9.4.4 | `client_id`; uvicorn ping 10 s; nâng `MAX_SESSIONS` | Một phần | §4.3: `client_id` làm hai tab đá nhau; ping cần build lại image; `MAX_SESSIONS` vẫn 4 |
| §9.4.5 | Xin wake lock khi bật mic, báo khi không giữ được | Chưa làm | §4.5 |
| §9.4.6 | Hướng dẫn cho iPhone/iPad | Đạt | |
| §10 | Luôn gửi đủ `targets` | Đạt | |
| §10 | Câu chốt sớm gửi `audio_ms`, `lang_probs` | Đạt | |
| §10 | Lượt dịch lại dùng tên ngôn ngữ | Đạt | |
| §10 | `speech_pad_ms` không được dùng | Chưa làm | |
| §10 | Ưu tiên bản dịch hơn nhận dạng tạm | Chưa làm | Dịch chạy ở llama.cpp, ngoài `AsrScheduler` |
| §11 | `golden_eval.py` | Đạt | Thêm `--device` và chuyển CPU khi hết bộ nhớ GPU; `799502f` sửa lint |

## Phụ lục B — nguồn tham khảo

- 07 · Bắt đúng lời thoại phim, dịch đủ câu, và vì sao Safari có lúc không ra chữ:
  [07-bat-kip-loi-thoai-phim.md](07-bat-kip-loi-thoai-phim.md).
- Python `str` không có `endsWith`; tên đúng là `str.endswith`: [Python docs][py-endswith].
- `localStorage` dùng chung giữa các tab cùng origin, `sessionStorage` thì riêng cho từng tab: [MDN][mdn-storage].
- llama.cpp server — tham số `stop` của `/v1/chat/completions`: [llama.cpp server README][llama-stop].

[c-mt-except]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L672-L677
[c-partial-uid]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L333-L345
[c-store-delete]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/state/useStore.ts#L122-L127
[c-store-delta]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/state/useStore.ts#L156-L170
[c-probsum]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L65-L77
[c-stats]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L155-L160
[c-tail-hold]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L482-L501
[c-tail-merge]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L447-L452
[c-tail-timer]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L542-L552
[c-tail-test]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/tests/unit/test_session.py#L237
[c-flush-vi]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L263-L271
[c-stop]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L195-L200
[c-cutoff]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L576-L579
[c-strip]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L35-L73
[c-partial-start]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L279-L285
[c-rescue]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L405-L417
[c-typeerror]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/scheduler.py#L44-L59
[c-health]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/api/stream.py#L170-L175
[c-limit]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/ai/src/rvt_ai/api/stream.py#L37-L43
[c-foreground]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/net/ws_client.ts#L32-L44
[c-tab-ended]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/net/ws_client.ts#L271
[c-track-ended]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/net/ws_client.ts#L298
[c-clientid]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/net/ws_client.ts#L3-L14
[c-reconnect]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/net/ws_client.ts#L147
[c-wakelock]: https://github.com/superken-python/ai-architecture/blob/873d676fee6a96ee63b343bff5a33a9e684aa602/projects/realtime-voice-translate/web/src/App.tsx#L113-L116
[py-endswith]: https://docs.python.org/3/library/stdtypes.html#str.endswith
[mdn-storage]: https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage
[llama-stop]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
