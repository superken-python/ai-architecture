# 06 · Dịch kịp lời nói nhanh (anime, phim, video nói liền) — Realtime Voice Translate

**Ngày:** 2026-10-11. **Đối chiếu với:** code nhánh `main` tại `a82c9fc` (đã có phần triển khai của
[05 · Dịch liên tục cho video và cuộc họp](05-dich-lien-tuc-video-cuoc-hop.md)). **Phạm vi:** vì sao video nói chậm (ví
dụ [video này][yt-slow]) dịch ổn còn anime nói nhanh như One Piece thì dịch không kịp; cần đổi gì để theo kịp; đo trên
server nội bộ thế nào. **Tài liệu chỉ phân tích và đề xuất. Code duy nhất thêm vào là script đo
[`scripts/replay_ws.py`](../scripts/replay_ws.py).**

**Chưa đo được trên server nội bộ.** Môi trường cloud viết tài liệu này không vào được `https://192.168.2.69:8443` (địa
chỉ trong mạng LAN, kết nối hết thời gian chờ). Mọi số liệu dưới đây đo trong sandbox bằng ba cách:

- **Phát lại trên code server thật.** Server chạy từ `main` với VAD Silero, segmenter, `AsrScheduler`, `RVTSession` và
  WebSocket thật. Chỉ Whisper và llama.cpp được thay bằng bản giả lập giữ GPU đúng thời gian giả định. `replay_ws.py`
  gửi audio đúng nhịp thời gian thực như web app.
- **Mô phỏng sự kiện rời rạc (DES).** Cùng VAD và segmenter, hàng đợi một GPU, để thử nhanh các phương án chưa có code.
  Với GPU còn dư, DES khớp phát lại trong khoảng 0,5 s (mục 4.2).
- **Đo tải giao diện.** Bản build production của web app chạy trong Chromium headless.

Mục 6 hướng dẫn chạy `replay_ws.py` trên server thật.

## 1. Kết luận

1. **Anime không kịp chủ yếu vì cách cắt câu, không phải vì GPU yếu.**
   - Server chốt một đoạn khi gặp khoảng lặng. Video nói chậm có khoảng nghỉ 0,6–1,2 s giữa các câu, nên đoạn được chốt
     sau mỗi ~2 s và bản dịch hiện khoảng 1 s sau khi người nói dứt câu.
   - Anime nói liền: câu thoại nối nhau, khoảng nghỉ thường dưới 0,25 s hoặc nói chồng, thêm nhạc nền. Server gần như
     không thấy đủ khoảng lặng, nên đoạn nào cũng chạy tới mốc cắt cứng 10 s (17/18 đoạn khi phát lại) và gom khoảng 6
     câu thoại. Câu thoại đầu đoạn phải chờ ~10 s, rồi cả 6 câu hiện ra một lượt: vừa trễ vừa không kịp đọc.
   - Phát lại trên code server thật, GPU tầm RTX 4060 (giả định): trễ phụ đề tính từ lúc dứt mỗi câu thoại p50 6,3 s,
     p95 11 s, trong khi video nói chậm chỉ 1,0 / 1,1 s. GPU mới bận 46%.
2. **GPU yếu hơn thì bản dịch còn bị nhận dạng tạm chèn ép.** Cứ 0,8 s server nhận dạng lại cả đoạn đang mở (tới 10 s
   audio). Bộ lập lịch chỉ xếp ưu tiên giữa các lượt nhận dạng; phần dịch nằm ngoài, nên phải tranh GPU với nhận dạng tạm
   của đoạn sau. Giả lập GPU chậm gấp đôi: GPU bận 91%, bản dịch hiện 5,5 s sau khi cắt đoạn (GPU tầm RTX 4060: 1,5 s),
   trễ theo câu thoại p50 10,3 s, p95 15 s.
3. **Giao diện chậm dần trên máy yếu.** Server gửi event `vad` mỗi 40 ms và mỗi event làm vẽ lại cả danh sách câu. Với
   CPU chậm gấp 4 và 600 câu trong danh sách, main thread bận 99% và bản dịch hiện muộn thêm 3–5,5 s.
4. **Các thay đổi đề xuất** (chi tiết mục 5; DES, anime nói nhanh, GPU tầm RTX 4060):

   | Thay đổi | Trễ theo câu thoại p50 / p95 | GPU bận |
   |---|---|---|
   | Hiện tại | 5,8 / 10,6 s | 48% |
   | Chỉ sửa profile: đoạn tối đa 4/6 s (không sửa code) | 3,4 / 6,5 s | 41% |
   | Đoạn tối đa 4/6 s, cắt ở chỗ lặng nhất; chỉ dịch 1 ngôn ngữ | 2,7 / 5,0 s | 40% |
   | + chốt và dịch sớm từng câu thoại từ chữ tạm | 1,8 / 4,9 s | 43% |
   | + nhận dạng tạm mỗi 0,5 s (chỉ khi GPU còn dư) | 1,4 / 4,9 s | 58% |

   Phát lại trên code thật cho hai dòng đầu: 6,3 / 11,0 s và 3,8 / 6,8 s.

   Đi kèm: cho bản dịch ưu tiên hơn nhận dạng tạm trên GPU; giảm tải giao diện; cho VAD chạy 1 luồng CPU (hiện một phiên
   tốn ~2,7 nhân). Về sau: nhận dạng streaming thật sự và mô hình ASR tiếng Nhật nhanh hơn, để đưa p95 xuống ~3 s.
5. **Giới hạn của kiến trúc hiện tại.** Phải nghe hết câu thoại mới nhận dạng và dịch được, nên trễ p50 khó xuống dưới
   ~1,5 s. Mục tiêu hợp lý cho anime là bản dịch hiện 1,5–2 s sau mỗi câu thoại, đều đặn từng câu.

### Thử ngay hôm nay (không cần sửa code)

1. **Đo hai video** bằng `replay_ws.py` (mục 6) để có số thật trên server của bạn.
2. **Đoạn tối đa 4/6 s:** thêm `max_ms: 4000` và `hard_max_ms: 6000` vào mục `vad` của `packs/profiles/balanced.yaml`
   trên server, rồi `docker restart rvt_ai` (thư mục `packs` được mount vào container). Phát lại trên code thật: trễ theo
   câu thoại p50 / p95 từ 6,3 / 11,0 s xuống 3,8 / 6,8 s. Hai điều cần biết:
   - thay đổi áp dụng cho mọi chế độ, nên câu dài trong chế độ hội thoại cũng bị cắt ở 4–6 s;
   - với anime, gần như đoạn nào cũng bị cắt cứng ở 6 s, nhiều điểm cắt rơi giữa tiếng nói nên Whisper có thể sai chữ ở
     chỗ cắt. Mục 5.1 sửa triệt để việc này.
3. **GPU yếu hơn RTX 4060:** thêm cả `partial_interval_ms: 1200` để giảm số lần nhận dạng tạm; đổi lại, chữ tạm cập nhật
   thưa hơn. Phát lại với GPU chậm gấp đôi: trễ 10,3 / 15,0 s → 5,5 / 8,6 s khi chỉ đặt đoạn 4/6 s → 4,8 / 7,8 s khi thêm
   `partial_interval_ms: 1200`; GPU bận 91% → 56% (mục 4.2).
4. Khi xem anime, chỉ mở một phiên dịch; phiên khác chạy cùng lúc sẽ tranh GPU.
5. Trong chế độ 📺 Video & Họp, bấm 🗑️ Xóa sau mỗi tập (hoặc mỗi 15–20 phút) để danh sách câu không dài ra. Không mở
   DevTools trong lúc xem.
6. Phát video ở tốc độ 0,75× giúp ít (DES: p50 5,8 → 5,0 s, p95 10,6 → 9,7 s), chủ yếu để dễ đọc hơn.

## 2. Vì sao video chậm dịch ổn còn anime thì không

### 2.1 Server chốt đoạn dựa vào khoảng lặng

Quy tắc hiện tại ([segmenter.py#L59-L106][c-seg]; giá trị mặc định ở [loader.py#L11-L21][c-seg-cfg], profile `balanced`
đặt ngưỡng 0,4/0,25):

- bắt đầu đoạn khi xác suất VAD ≥ 0,4; đang nói thì chỉ coi là lặng khi < 0,25;
- chốt đoạn khi lặng ≥ 500 ms, hoặc ≥ 250 ms nếu đoạn đã dài hơn 4 s;
- đoạn ≥ 7 s thì chốt ngay khi có 200 ms lặng; tới 10 s thì cắt cứng ở bất kỳ đâu.

| | Video nói chậm | Anime nói nhanh |
|---|---|---|
| Mật độ lời | 4,6 ký tự/giây nói | 7,4 ký tự/giây nói |
| Câu thoại trung bình | 4,2 s | 1,9 s |
| Khoảng nghỉ giữa câu thoại | 0,6–1,2 s | −0,3–0,25 s (âm là nói chồng) |
| Nhạc nền, tiếng động | không | nhạc thấp hơn lời 15 dB, 60 tiếng động |
| Đoạn server chốt trong 3 phút | 81, dài TB 2,0 s, dài nhất 3,5 s | 18, dài TB 9,9 s; 17 đoạn cắt cứng ở 10 s |
| Câu thoại trên một đoạn | 0,4 (câu dài bị chia ở chỗ ngắt hơi) | 5,8 |

(Kịch bản TTS mô phỏng, mục 4.1.)

- Trong anime, khoảng nghỉ ngắn giữa hai câu thoại có thể làm xác suất VAD chạm dưới 0,25 trong chốc lát, nhưng hiếm khi
  kéo dài đủ 250 ms liên tục.
- Nhạc nền không phải nguyên nhân chính: nâng `neg_threshold` từ 0,25 lên 0,4 không làm đổi số đoạn.

### 2.2 Trễ = chờ cắt đoạn + nhận dạng + dịch

- Câu thoại ở đầu đoạn 10 s phải chờ ~9 s mới tới lúc cắt; câu ở cuối đoạn chờ ít hơn. Trung bình mỗi câu thoại chờ
  khoảng nửa đoạn.
- Sau khi cắt: nhận dạng đoạn 10 s mất ~0,5 s, dịch thêm ~1 s (phát lại: bản dịch hiện 1,5 s sau khi cắt).
- Tổng cộng p50 6,3 s, p95 11 s. Bản dịch của cả 6 câu thoại hiện cùng lúc, mỗi 10 s một khối ~70 ký tự Nhật.
- Video chậm: đoạn ~2 s, bản dịch hiện 0,4 s sau khi cắt, tức ~1 s sau khi dứt câu.

### 2.3 Nhận dạng tạm chiếm phần lớn GPU và chèn ép bản dịch

- Cứ 0,8 s server nhận dạng lại toàn bộ đoạn đang mở ([segmenter.py#L76-L80][c-partial-int]). Đoạn 10 s nghĩa là ~12
  lượt nhận dạng ngày càng dài. Phát lại anime 3 phút: nhận dạng chiếm 67 s GPU, dịch 16 s.
- Mỗi lượt tốn cố định phần encoder, vì Whisper luôn đệm audio thành 30 s. Lượt nhận dạng tạm đầu tiên của mỗi đoạn
  chạy khi đoạn mới có dưới 1 s audio (p50 0,8 s), vì mốc 0,8 s tính từ lúc chốt đoạn trước chứ không từ lúc bắt đầu
  nói. Lượt đó chứa nhiều nhất vài chữ. Video chậm: 81/188 lượt nhận dạng tạm thuộc loại này.
- `AsrScheduler` chỉ ưu tiên câu chốt so với nhận dạng tạm ([scheduler.py#L44-L73][c-sched]). Phần dịch gọi llama.cpp
  trực tiếp ([session.py#L330][c-mt-call]), không qua bộ lập lịch, nên tranh GPU với nhận dạng tạm của đoạn sau.
- Server dịch mọi câu sang cả hai ngôn ngữ còn lại ([session.py#L310-L316][c-targets]), dù chế độ 📺 Video & Họp chỉ
  hiện một ([App.tsx#L395-L397][c-feed]).

Phát lại anime 3 phút trên code server thật:

| GPU (giả định) | Dịch sang | GPU bận | Bản dịch sau khi cắt đoạn, p50 / p95 | Trễ theo câu thoại, p50 / p95 |
|---|---|---|---|---|
| tầm RTX 4060 | 2 ngôn ngữ (hiện tại) | 46% | 1,5 / 2,0 s | 6,3 / 11,0 s |
| tầm RTX 4060 | chỉ tiếng Việt | 42% | 1,1 / 1,5 s | 5,9 / 10,7 s |
| chậm gấp đôi | 2 ngôn ngữ (hiện tại) | 91% | 5,5 / 6,3 s | 10,3 / 15,0 s |

### 2.4 Giao diện vẽ lại quá nhiều

- Server gửi `vad` cho mọi khung 40 ms ([session.py#L137-L138][c-vad-event]): 25 event/giây/phiên, dù trạng thái nói/lặng
  chỉ đổi vài lần mỗi phút.
- Mỗi event tạo state mới ([useStore.ts#L78-L96][c-store-event]). `App` lấy cả store mà không qua selector
  ([App.tsx#L31-L48][c-app-store]), nên vẽ lại mọi thẻ câu; mỗi thẻ chạy lại `cleanTranslationText` gồm nhiều regex
  ([App.tsx#L395-L397][c-feed]).
- `ws_client` ghi `console.log` cho mọi event ([ws_client.ts#L55][c-log]).
- Chi phí tăng theo số câu trong danh sách. Video chậm tạo ~27 câu/phút. Anime, sau khi chốt từng câu thoại (mục 5.2),
  tạo ~33 câu/phút, tức 600 câu sau ~20 phút. Số đo ở mục 4.4.

### 2.5 Các lỗi nhỏ khác

- **VAD tốn CPU.** `InferenceSession` dùng thiết lập luồng mặc định của ONNX Runtime ([vad_silero.py#L86][c-ort]): một
  nhóm luồng theo số nhân CPU, các luồng quay chờ (spin) sau mỗi lần chạy. Trong sandbox 4 nhân, VAD của một phiên tốn
  268% CPU. Đặt 1 luồng như `OnnxWrapper` của silero-vad thì còn 3%, mỗi khung vẫn ~1 ms. Phần CPU thừa này tranh với
  bước tính đặc trưng âm thanh của Whisper (chạy trên CPU), với llama.cpp và nginx.
- **`max_tokens` của bản dịch tiếng Nhật luôn là 128.** Số token được ước theo số từ tách bằng khoảng trắng
  ([mt_llama.py#L94-L95][c-mt-tokens]), mà tiếng Nhật không có khoảng trắng. Đoạn 10 s nói nhanh có nguy cơ chạm trần.
- **Ngữ cảnh dịch bị lặp.** Câu được thêm vào `recent_context` một lần cho mỗi ngôn ngữ đích ([session.py#L383][c-ctx]).
  Với 2 đích và `maxlen=2`, ngữ cảnh chỉ còn câu ngay trước, lặp hai lần.
- **Ngữ cảnh đứng trước lời dặn trong prompt** ([mt_llama.py#L79-L91][c-mt-prompt]). Phần đầu prompt đổi theo từng câu,
  nên llama.cpp không dùng lại được cache của phần lời dặn cố định. Lợi ích của việc đổi thứ tự là nhỏ.

## 3. Mục tiêu cho video nói nhanh

| Chỉ số | Mục tiêu |
|---|---|
| Trễ phụ đề tính từ lúc dứt câu thoại, p50 | ≤ 2 s |
| Trễ phụ đề, p95 | ≤ 5 s (bước 1–2), ≤ 3,5 s (bước 3) |
| Đoạn dài nhất | ≤ 6 s |
| Điểm cắt rơi vào chỗ lặng | ≥ 90% |
| GPU bận với 1 phiên anime, GPU tầm RTX 4060 | ≤ 45% |
| Trễ không tăng theo thời gian | sau 30 phút tăng ≤ 0,5 s |
| Giao diện sau 30 phút, CPU chậm gấp 4 | main thread bận ≤ 30%; bản dịch muộn thêm ≤ 100 ms |
| CER tiếng Nhật | không xấu hơn mức đo trước khi đổi |

## 4. Số đo

### 4.1 Cách đo

- **Audio:** hai kịch bản 3 phút tổng hợp bằng TTS offline ([pyopenjtalk-plus][pyopenjtalk]):
  - *video nói chậm:* một người, câu giới thiệu dài, tốc độ 0,85, nghỉ 0,6–1,2 s;
  - *anime nói nhanh:* 12 câu thoại kiểu One Piece, 4 giọng luân phiên, tốc độ 1,45–1,75, nghỉ −0,3–0,25 s, nhạc nền
    thấp hơn lời 15 dB, 60 tiếng động ngắn.
- **Phát lại:** server chạy từ `a82c9fc` với profile `balanced` (ngưỡng VAD, preroll, đoạn tối đa 7/10 s). Whisper và
  llama.cpp được thay bằng bản giả lập dùng chung một khoá GPU: nhận dạng giữ GPU cả lượt, dịch giữ GPU theo từng nhóm 8
  token. `replay_ws.py` gửi khung 40 ms đúng nhịp thời gian thực.
- **Thời gian giả định** cho large-v3-turbo int8 và Hy-MT 1.8B Q4 trên GPU tầm RTX 4060:
  - nhận dạng: 0,12 s + 6 ms cho mỗi token chữ;
  - dịch: 0,06 s + 8,3 ms cho mỗi token đầu ra (~120 token/s);
  - "GPU chậm gấp đôi": nhân đôi tất cả.
- **DES:** cùng VAD và segmenter; một GPU; ưu tiên câu chốt > bản dịch > nhận dạng tạm; nhận dạng tạm chỉ giữ job mới
  nhất. Phương án "chốt sớm" giả định Whisper trả cùng một câu, kể cả dấu 。！？, ở hai lần nhận dạng tạm liên tiếp.
- **Giới hạn:**
  - không chạy Whisper và llama.cpp thật;
  - giọng TTS sạch hơn giọng lồng tiếng thật (la hét, thì thầm, nói chồng nhiều hơn);
  - phần cắt đoạn là code thật nên đáng tin; thời gian nhận dạng và dịch phải đo lại bằng mục 6.

### 4.2 Phát lại trên code server thật

| | Video nói chậm | Anime nói nhanh |
|---|---|---|
| Đoạn chốt (dài TB / dài nhất) | 81 (2,0 / 3,5 s) | 18 (9,9 / 10,0 s) |
| Đoạn bị cắt cứng ở 10 s | 0 | 17 |
| Chữ tạm đầu tiên, tính từ lúc bắt đầu đoạn (p50) | 1,5 s | 1,0 s |
| Chữ chốt, tính từ lúc server cắt đoạn (p50 / p95) | 0,2 / 0,2 s | 0,5 / 0,8 s |
| Bản dịch, tính từ lúc server cắt đoạn (p50 / p95) | 0,4 / 0,5 s | 1,5 / 2,0 s |
| Bản dịch, tính từ lúc bắt đầu đoạn (p50 / p95) | 2,3 / 3,8 s | 11,5 / 12,0 s |
| **Trễ theo câu thoại, tính từ lúc dứt câu (p50 / p95)** | **1,0 / 1,1 s** | **6,3 / 11,0 s** |
| Trễ bản dịch 1/3 đầu → 1/3 cuối | 0,4 → 0,4 s | 1,6 → 1,5 s |
| GPU bận | 31% | 46% |
| DES, trễ theo câu thoại (p50 / p95) | 0,9 / 1,0 s | 5,8 / 10,6 s |

- Với GPU tầm RTX 4060, trễ không tăng theo thời gian: hàng đợi không phình. Vấn đề là thời gian chờ cắt đoạn.
- Khi GPU còn dư, DES khớp phát lại trong khoảng 0,5 s, nên dùng được để so phương án ở 4.3. Khi GPU gần đầy, DES lạc
  quan hơn: nó cho bản dịch ưu tiên hơn nhận dạng tạm, còn code hiện tại thì không. Với GPU chậm gấp đôi, DES cho 7,3 /
  12,2 s, phát lại cho 10,3 / 15,0 s.

**Chỉ đổi profile, phát lại anime trên code thật** (trễ theo câu thoại p50 / p95, GPU bận):

| Mục `vad` của profile | GPU tầm RTX 4060 | GPU chậm gấp đôi |
|---|---|---|
| Hiện tại: đoạn tối đa 7/10 s | 6,3 / 11,0 s, 46% | 10,3 / 15,0 s, 91% |
| `max_ms: 4000`, `hard_max_ms: 6000` | 3,8 / 6,8 s, 38% | 5,5 / 8,6 s, 77% |
| như trên + `partial_interval_ms: 1200` | — | 4,8 / 7,8 s, 56% |

Với 4/6 s, cả 30 đoạn đều bị cắt cứng ở 6 s.

### 4.3 So sánh phương án (DES, anime nói nhanh)

| Cắt đoạn | Dịch | Số đoạn (dài TB) | GPU tầm RTX 4060: p50 / p95, GPU bận | GPU chậm gấp đôi: p50 / p95, GPU bận |
|---|---|---|---|---|
| Hiện tại, 7/10 s | 2 ngôn ngữ | 17 (10,0 s) | 5,8 / 10,6 s, 48% | 7,3 / 12,2 s, 88% |
| Hiện tại, 7/10 s | 1 ngôn ngữ | 17 (10,0 s) | 5,8 / 10,6 s, 45% | 7,3 / 12,2 s, 84% |
| Hiện tại, 7/10 s | 1 + chốt sớm | 17 (10,0 s) | 2,1 / 10,3 s, 47% | 2,7 / 11,1 s, 86% |
| 4/6 s, cắt tại chỗ (chỉ sửa profile) | 2 ngôn ngữ | 29 (6,0 s) | 3,4 / 6,5 s, 41% | 4,3 / 7,4 s, 78% |
| 4/6 s, cắt tại chỗ | 1 + chốt sớm | 29 (6,0 s) | 2,0 / 6,3 s, 39% | 2,6 / 7,2 s, 77% |
| 4/6 s, cắt ở chỗ lặng nhất | 1 ngôn ngữ | 38 (4,6 s) | 2,7 / 5,0 s, 40% | 3,3 / 5,8 s, 73% |
| 4/6 s, cắt ở chỗ lặng nhất | 1 + chốt sớm | 38 (4,6 s) | 1,8 / 4,9 s, 43% | 2,3 / 5,7 s, 79% |
| 4/6 s, chỗ lặng nhất, nhận dạng tạm 0,5 s | 1 + chốt sớm | 38 (4,6 s) | 1,4 / 4,9 s, 58% | 1,9 / 5,8 s, 94% |

Video nói chậm không đổi ở mọi phương án (0,9 / 1,0 s), vì đoạn của nó đã ngắn sẵn.

**Điểm cắt rơi vào đâu.** Cắt giữa tiếng nói làm vỡ từ ở hai đầu đoạn, Whisper dễ nghe sai hoặc bịa chữ. "Chỗ lặng" ở
đây là khung có mức âm thấp hơn mức lời ít nhất 10 dB (nhạc nền nằm ở −15 dB).

| Cắt đoạn | Số điểm cắt | Rơi vào chỗ lặng |
|---|---|---|
| Hiện tại, 7/10 s | 16 | 56% |
| 4/6 s, cắt tại chỗ | 28 | 43% |
| 4/6 s, cắt ở chỗ lặng nhất | 37 | 95% |
| 3/5 s, cắt ở chỗ lặng nhất | 47 | 96% |

**Tốc độ phát 0,75×:** 17 → 20 đoạn (dài TB 10,0 → 8,8 s), trễ p50 / p95 5,8 / 10,6 → 5,0 / 9,7 s. Lời vẫn liền, nên
gần như mọi đoạn vẫn bị cắt cứng.

### 4.4 Tải giao diện

Bản build production, chế độ 📺 Video & Họp, Chromium headless. Luồng event đưa vào store giống anime nói nhanh:

- một câu mới mỗi 2,5 s, gồm 3 lần chữ tạm, câu chốt, bản dịch vi và en theo từng token;
- `vad` mỗi 40 ms (tổng ~47 event/giây).

Đo trong 20 s: phần trăm thời gian main thread bận, và `mt.final` được xử lý muộn bao lâu so với lúc đến.

| CPU | Câu trong danh sách | Main thread bận: có / không có `vad` 40 ms | `mt.final` muộn, p95: có / không |
|---|---|---|---|
| như sandbox | 0 | 4,0% / 2,1% | 0 / 2 ms |
| như sandbox | 200 | 11,6% / 5,2% | 2 / 0 ms |
| như sandbox | 600 | 29,9% / 12,3% | 6 / 0 ms |
| chậm gấp 4 | 0 | 16,0% / 9,0% | 4 / 2 ms |
| chậm gấp 4 | 200 | 49,2% / 24,6% | 86 / 1 ms |
| chậm gấp 4 | 600 | 99,3% / 51,2% | 5 533 / 580 ms |

- Chi phí tăng theo số câu, vì mỗi event vẽ lại cả danh sách. Event `vad` mỗi 40 ms làm chi phí tăng gấp đôi.
- CPU chậm gấp 4 (throttling của Chrome DevTools, gần với laptop yếu) và 600 câu: main thread bận gần hết thời gian,
  bản dịch hiện muộn thêm 3–5,5 s. Trong khi đó laptop còn phải phát video.

## 5. Đề xuất

### 5.1 Cắt đoạn ngắn hơn, ở chỗ lặng nhất

- Đặt `max_ms` 4000 và `hard_max_ms` 6000 cho chế độ video. Riêng việc này (chỉ sửa profile) đã đưa p95 từ 10,6 xuống
  6,5 s, nhưng điểm cắt vẫn thường rơi giữa tiếng nói (43% ở chỗ lặng).
- Đổi cách cắt khi đoạn dài quá `max_ms`:
  - lưu xác suất VAD của từng khung trong đoạn đang mở;
  - tìm khung thấp nhất trong 1,5 s gần nhất, bỏ 200 ms cuối;
  - nếu khung đó dưới `neg_threshold` thì cắt ngay tại đó; nếu chưa, chờ tới `hard_max_ms` rồi cắt ở khung thấp nhất;
  - phần audio sau điểm cắt giữ lại làm đầu đoạn kế tiếp, không mất chữ.
- DES: p50 / p95 2,7 / 5,0 s; 95% điểm cắt rơi vào chỗ lặng.

```python
# Phác thảo trong Segmenter.add_chunk, nhánh đang nói. self.frame_probs: xác suất VAD từng khung của đoạn đang mở.
if duration_ms >= self.config.max_ms:
    n = len(self.frame_probs)
    k = min(range(max(0, n - 1500 // chunk_ms), n - 200 // chunk_ms), key=self.frame_probs.__getitem__)
    if self.frame_probs[k] < self.config.neg_threshold or duration_ms >= self.config.hard_max_ms:
        cut = preroll_bytes + (k + 1) * chunk_bytes  # vị trí trong buffer, tính cả phần preroll ở đầu
        final_audio, self.buffer = bytes(self.buffer[:cut]), self.buffer[cut:]
        self.frame_probs = self.frame_probs[k + 1 :]
        self.speech_start_ms = self.current_time_ms - len(self.frame_probs) * chunk_ms  # vẫn đang nói
        should_final = True
```

### 5.2 Chốt và dịch sớm từng câu thoại từ chữ tạm

- **Ý tưởng** (LocalAgreement, như [Whisper-Streaming][ws-repo]): mỗi lần nhận dạng tạm chạy lại cả đoạn đang mở. Khi
  một câu hoàn chỉnh (kết thúc bằng 。！？!?) xuất hiện giống hệt ở hai lần nhận dạng tạm liên tiếp, câu đó gần như sẽ
  không đổi nữa. Chốt luôn câu đó: gửi `asr.final` với `utterance_id` mới và dịch ngay. Khi đoạn bị cắt, chỉ dịch phần
  chưa chốt.

```python
SENTENCE_END = re.compile(r"[。！？!?]")


def stable_prefix(prev: str, curr: str, committed: int) -> int:
    """Vị trí hết câu hoàn chỉnh cuối cùng mà hai lần nhận dạng tạm liên tiếp cùng có, không lùi so với committed."""
    common = 0
    for a, b in zip(prev, curr, strict=False):
        if a != b:
            break
        common += 1
    return max([committed, *(m.end() for m in SENTENCE_END.finditer(curr, 0, common))])
```

- **Gắn vào `RVTSession`:**
  - `_process_partial_audio`: tính `end = stable_prefix(prev_text, text, committed)`. Nếu `end > committed`, gửi
    `asr.final` cho `text[committed:end]` với uid hiện tại, tăng `utterance_id_counter`, chạy dịch, rồi đặt
    `committed = end`. Chữ tạm gửi cho client chỉ còn `text[committed:]`, mang uid mới.
  - `_process_final_audio`: bỏ phần đã chốt khỏi chữ chốt bằng cách căn chuỗi (`difflib.SequenceMatcher`), vì Whisper có
    thể sửa nhẹ phần đầu khi nghe thêm audio. Chỉ gửi và dịch phần còn lại, rồi đặt lại `committed` và `prev_text` cho
    đoạn mới.
  - So sánh sau khi bỏ khoảng trắng; Whisper đôi khi chèn khoảng trắng vào tiếng Nhật.
  - Không đổi giao thức: client đã xử lý được nhiều `asr.final` với uid khác nhau.
- **DES:** kết hợp với 5.1, p50 1,8 s, p95 4,9 s. Nhận dạng tạm mỗi 0,5 s cho p50 1,4 s nhưng GPU bận 58%, chỉ nên bật
  khi GPU còn dư.
- **Cần đo với Whisper thật:** tỉ lệ câu được chốt sớm, và số câu Whisper sửa lại sau khi đã chốt.

### 5.3 Dịch đúng thứ đang hiển thị, bản dịch đi trước nhận dạng tạm

- **Chỉ dịch ngôn ngữ cần hiện.** Thêm trường tuỳ chọn `targets` vào `session.start` và `sides.update`. Chế độ 📺 Video &
  Họp gửi `[sideBLang]`; chế độ hội thoại gửi cả hai ngôn ngữ khi đang bật hiện ngôn ngữ thứ ba. Server dùng `targets`
  nếu có, mặc định giữ như cũ. Phát lại: bản dịch hiện sau khi cắt đoạn nhanh hơn (1,5 → 1,1 s), GPU 46 → 42%.
- **Bản dịch ưu tiên hơn nhận dạng tạm.** Khi đang có bản dịch cho ngôn ngữ cần hiện, `AsrScheduler` tạm giữ các job
  nhận dạng tạm, chỉ chạy câu chốt. Thứ tự ưu tiên: câu chốt > bản dịch > nhận dạng tạm. DES đã giả định thứ tự này;
  thiếu nó, với GPU chậm gấp đôi, trễ theo câu thoại là 10,3 / 15 s thay vì 7,3 / 12,2 s.
- **Bỏ lượt nhận dạng tạm khi đoạn chưa có 1 s audio:** đặt mốc nhận dạng tạm theo lúc bắt đầu nói.
- **Giãn nhận dạng tạm khi GPU bận,** ví dụ từ 0,8 lên 1,6 s khi đang có câu chốt chờ.

### 5.4 Giảm tải giao diện

- **Server:** chỉ gửi `vad` khi trạng thái đổi (và khi bắt đầu lượt nói). Từ 25 event/giây xuống vài event mỗi phút.
- **Store:** event `vad` không đụng tới `utterances`. Component lấy state qua selector, ví dụ
  `useStore((s) => s.vadSpeaking)`.
- **Danh sách:**
  - tách thẻ câu thành component `React.memo` theo `utterance_id`;
  - chạy `cleanTranslationText` một lần khi nhận `mt.final` rồi lưu kết quả;
  - chỉ vẽ 100–200 câu gần nhất, hoặc dùng danh sách ảo.
- **Log:** bỏ `console.log` cho từng event, chỉ bật khi gỡ lỗi (ví dụ `?debug=1`).
- `replay_ws.py` vẫn đo được sau khi server chỉ gửi `vad` lúc đổi trạng thái: script tự suy ranh giới đoạn từ thời điểm
  nhận event (đã thử, kết quả trùng với cách đếm từng khung).

### 5.5 VAD chạy 1 luồng

```python
opts = ort.SessionOptions()
opts.intra_op_num_threads = 1
opts.inter_op_num_threads = 1
self.session = ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])
```

Sandbox 4 nhân: CPU cho VAD của một phiên giảm từ 268% xuống 3%; mỗi khung vẫn ~1 ms (p99 2,6 ms).

### 5.6 Sửa nhỏ ở phần dịch

- **`max_tokens`:** văn bản không có khoảng trắng (tiếng Nhật) thì đếm theo ký tự, ví dụ
  `max(128, min(512, len(text) * 3))`.
- **Ngữ cảnh:** thêm câu nguồn vào `recent_context` một lần cho mỗi câu, lúc có chữ chốt, thay vì một lần cho mỗi ngôn
  ngữ đích. Khi đã chốt từng câu thoại (5.2), giữ 2–3 câu gần nhất.
- **Prompt:** lời dặn cố định đặt đầu, rồi đến ngữ cảnh, rồi câu cần dịch, để llama.cpp dùng lại cache phần đầu
  ([`cache_prompt`][llama-server]).

### 5.7 Bước sau: nhận dạng streaming thật sự, mô hình nhanh hơn

- **Cắt bỏ audio đã chốt.** Sau 5.2, bỏ phần audio của các câu đã chốt khỏi buffer, dựa vào mốc thời gian theo đoạn của
  Whisper (`without_timestamps=False`). Mỗi lần nhận dạng tạm chỉ còn 2–4 s audio thay vì tới 10 s: GPU nhẹ hơn và
  không còn phải cắt cứng. Đây là cách Whisper-Streaming làm (LocalAgreement và cắt buffer; [bài báo][ws-paper] đo trễ
  ~3,3 s trên lời nói dài). SimulStreaming (AlignAtt) là phương án tiếp theo, đã nêu ở
  [05 §5.5](05-dich-lien-tuc-video-cuoc-hop.md#55-nhận-dạng-streaming-thật-sự-bước-sau).
- **Mô hình ASR tiếng Nhật nhanh hơn.** Phải đo CER trên đoạn anime thật trước khi đổi:
  - [Kotoba-Whisper v2][kotoba]: chưng cất từ large-v3, decoder 2 lớp, huấn luyện trên dữ liệu ReazonSpeech (truyền hình
    Nhật);
  - [ReazonSpeech k2 v2][reazon-k2]: Zipformer transducer 159M tham số, giấy phép Apache-2.0, chạy CPU bằng
    [sherpa-onnx][sherpa], để GPU dành cho phần dịch. Cần kiểm tra mô hình có ra dấu câu không, vì 5.2 dựa vào dấu câu.

### 5.8 Hiển thị cho video nhanh

- **Chế độ phụ đề:** chỉ hiện 2–3 câu dịch mới nhất, chữ to; câu mới đẩy câu cũ lên; chữ gốc ẩn hoặc để nhỏ. Mỗi câu
  thoại một dòng (cần 5.2).
- **Báo trễ:** khi bản dịch trễ hơn 3 s so với lời, hiện "đang bắt kịp", để người xem không tưởng app bị treo.
- **Tên nhân vật:** `packs/glossary/default.yaml` có sẵn nhưng prompt dịch chưa dùng. Thêm thuật ngữ (ルフィ → Luffy,
  ゾロ → Zoro…) giúp bản dịch ổn định hơn; không ảnh hưởng tốc độ.

## 6. Đo trên server nội bộ

### 6.1 Chuẩn bị audio

Cần file audio 2–3 phút của một đoạn có thoại liên tục. Nếu có file video gốc thì cắt bằng ffmpeg. Nếu chỉ xem trên
YouTube, có thể lấy audio bằng [yt-dlp][ytdlp] để kiểm thử nội bộ, trong phạm vi điều khoản và bản quyền cho phép.

```bash
# Video nói chậm trong yêu cầu
yt-dlp -x --audio-format wav -o "slow.%(ext)s" "https://www.youtube.com/watch?v=hRjM7PCqt6Y"
ffmpeg -i slow.wav -ss 0 -t 180 -ac 1 -ar 16000 -sample_fmt s16 slow16k.wav

# Một đoạn anime 3 phút nhiều thoại
ffmpeg -i onepiece.mp4 -ss 300 -t 180 -ac 1 -ar 16000 -sample_fmt s16 onepiece16k.wav
```

### 6.2 Chạy

Chạy trên một máy trong mạng LAN có Python 3.11+ và [uv](https://docs.astral.sh/uv/) (lệnh dạng bash; trên PowerShell
viết mỗi lệnh trên một dòng):

```bash
cd projects/realtime-voice-translate
uv run --with websockets python scripts/replay_ws.py --url wss://192.168.2.69:8443/ws --insecure \
    --wav slow16k.wav --lang ja --target vi --out slow.json
uv run --with websockets python scripts/replay_ws.py --url wss://192.168.2.69:8443/ws --insecure \
    --wav onepiece16k.wav --lang ja --target vi --out onepiece.json
```

- `--insecure` vì server dùng chứng chỉ tự ký.
- Script mở một phiên như web app: nửa A khoá `--lang`, nửa B là `--target`. Nó gửi khung 40 ms đúng nhịp thời gian thực,
  thêm 3 s lặng ở cuối, rồi chờ server xử lý xong.
- Đừng chạy phiên dịch khác cùng lúc, trừ khi muốn đo lúc có tải. `--speed 1.5` gửi nhanh hơn thời gian thực để ép tải.
- Nếu profile server đã đổi `min_speech_ms`, `min_silence_ms`, `preroll_ms`, `max_ms` hoặc `hard_max_ms`, truyền giá
  trị tương ứng qua `--min-speech-ms`, `--min-silence-ms`, `--preroll-ms`, `--max-ms`, `--hard-max-ms`. Ví dụ sau khi
  đặt đoạn tối đa 4/6 s: thêm `--max-ms 4000 --hard-max-ms 6000`.
- Chạy kèm `nvidia-smi dmon -s u` trên server để xem GPU, và `docker logs -f rvt_ai` để xem log từng câu.
- Đo trước và sau mỗi thay đổi (ví dụ trước và sau khi đặt đoạn tối đa 4/6 s), giữ nguyên file audio.

Kết quả mẫu (đoạn anime mô phỏng ở mục 4.2):

```text
=== Kết quả ===
Audio 183.0 s · câu: 18 (có chữ 18, rỗng/không về 0) · đoạn quá ngắn bị bỏ: 0 · lỗi: 0
Độ dài câu: TB 9.9 s, dài nhất 10.0 s · dài 7–10 s: 1, bị cắt cứng ở 10 s: 17 · mật độ chữ: 7.4 ký tự/giây
Chữ tạm đầu tiên, tính từ lúc bắt đầu câu (p50): 1.0 s
Chữ chốt, tính từ lúc server cắt câu: p50 0.5 s, p95 0.8 s
Bản dịch 'vi', tính từ lúc server cắt câu: p50 1.5 s, p95 2.0 s
Bản dịch 'vi', tính từ lúc BẮT ĐẦU câu: p50 11.5 s, p95 12.0 s
Trễ bản dịch 1/3 đầu → 1/3 cuối: 1.6 s → 1.5 s
```

### 6.3 Đọc kết quả

| Dấu hiệu | Nghĩa là | Làm gì |
|---|---|---|
| Nhiều đoạn "bị cắt cứng"; trễ "từ lúc BẮT ĐẦU câu" lớn hơn nhiều so với "từ lúc server cắt câu" | lời nói liền, đoạn bị gộp dài | 5.1, 5.2; thử ngay: đoạn tối đa 4/6 s |
| Bản dịch "từ lúc server cắt câu" > 2 s, GPU gần 100% | GPU không kịp | 5.3; giãn nhận dạng tạm; xem lại GPU |
| Trễ ở 1/3 cuối lớn hơn rõ rệt so với 1/3 đầu | hàng đợi phình dần | như trên; kiểm tra có phiên khác đang chạy không |
| Nhiều câu "rỗng/không về" | nhận dạng ra rỗng (lọc im lặng, lọc ảo giác) | xem các dòng `🔇` trong `docker logs rvt_ai` |
| Số đo tốt nhưng xem trên laptop vẫn trễ | giao diện | 5.4; bấm 🗑️ Xóa |
| Cảnh báo "ghép câu có thể lệch" | profile server khác giá trị mặc định của script | truyền `--min-speech-ms`… theo profile |

File JSON (`--out`) có từng câu: vị trí trong audio, độ dài, các mốc trễ, chữ nhận dạng và bản dịch, để đối chiếu với
video.

### 6.4 Để Claude đo trực tiếp lần sau

`192.168.2.69` là địa chỉ trong mạng LAN, môi trường cloud không tới được. Có hai cách:

- Chạy `replay_ws.py` trong mạng LAN rồi gửi lại file JSON. Cách này đơn giản và không phải mở server ra ngoài.
- Đưa server ra một tên miền công khai tạm thời (tunnel), rồi thêm tên miền đó vào **Allowed domains** trong phần Network
  access của môi trường cloud: menu môi trường trên thanh tiêu đề phiên → Edit ([hướng dẫn][cloud-net]). Cân nhắc bảo
  mật: web app hiện chưa có đăng nhập.

## 7. Lộ trình đề xuất

| Bước | Nội dung | Tầng | Công | Xong khi |
|---|---|---|---|---|
| 0 · Đo | mục 6 với 2 video; thử đoạn tối đa 4/6 s bằng profile | vận hành | 0,5 ngày | có số thật trước và sau |
| 1 · Nhanh, ít rủi ro | 5.1 (cắt ở chỗ lặng nhất), 5.3, 5.4, 5.5, 5.6 | server + web | 3–4 ngày | anime: p95 ≤ 5 s; GPU ≤ 45%; giao diện đạt mục 3 |
| 2 · Chốt sớm từng câu | 5.2; chế độ phụ đề (5.8) | server + web | 3–5 ngày | anime: p50 ≤ 2 s; mỗi câu thoại một dòng |
| 3 · Streaming | 5.7 | server | 1–2 tuần | p95 ≤ 3,5 s; CER không xấu hơn |

Thêm một kịch bản vào bộ kịch bản chuẩn của
[05 §6.6](05-dich-lien-tuc-video-cuoc-hop.md#66-bộ-kịch-bản-chuẩn): **K8 · Anime hoặc phim nói nhanh 25 phút, có nhạc
nền** — đạt khi trễ theo câu thoại p50 ≤ 2 s, p95 ≤ 5 s, không đoạn nào dài quá 6 s và trễ không tăng theo thời gian.

## 8. Rủi ro và đánh đổi

- **Đoạn ngắn hơn** cho Whisper và bộ dịch ít ngữ cảnh hơn. Bù bằng ngữ cảnh dịch (5.6) và đo CER.
- **Chốt sớm** có thể chốt một câu mà Whisper sửa lại sau. Căn chuỗi ở chữ chốt để không lặp hay mất chữ, và đo tỉ lệ
  phải sửa.
- **Nhận dạng tạm dày hơn** (0,5 s) tốn GPU; chỉ bật khi GPU còn dư.
- **Chỉ dịch một ngôn ngữ:** đổi ngôn ngữ hiển thị giữa chừng thì các câu cũ không có bản dịch sang ngôn ngữ mới.
- **Số liệu là mô phỏng:** TTS sạch hơn anime thật, thời gian nhận dạng và dịch là giả định. Phải đo bằng mục 6 trước và
  sau mỗi bước.

## Phụ lục — nguồn tham khảo

- Macháček, Dabre, Bojar (2023), *Turning Whisper into Real-Time Transcription System*: [arXiv 2307.14743][ws-paper];
  mã nguồn [Whisper-Streaming][ws-repo].
- SimulStreaming (ufal, 2025): [GitHub][simul].
- silero-vad tạo phiên ONNX với 1 luồng: [utils_vad.py][silero-wrapper]. ONNX Runtime, thiết lập luồng:
  [tài liệu][ort-threads].
- llama.cpp server, tuỳ chọn `cache_prompt`: [README][llama-server].
- Kotoba-Whisper: [Hugging Face][kotoba]; ReazonSpeech k2 v2: [Hugging Face][reazon-k2]; [sherpa-onnx][sherpa].
- Công cụ: [pyopenjtalk-plus][pyopenjtalk] (TTS dùng trong mô phỏng), [yt-dlp][ytdlp].

[yt-slow]: https://www.youtube.com/watch?v=hRjM7PCqt6Y
[c-seg]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L59-L106
[c-seg-cfg]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/packs/loader.py#L11-L21
[c-partial-int]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L76-L80
[c-sched]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/scheduler.py#L44-L73
[c-mt-call]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L330
[c-targets]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L310-L316
[c-vad-event]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L137-L138
[c-ctx]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L383
[c-ort]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/engines/vad_silero.py#L86
[c-mt-prompt]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L79-L91
[c-mt-tokens]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L94-L95
[c-store-event]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/web/src/state/useStore.ts#L78-L96
[c-app-store]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/web/src/App.tsx#L31-L48
[c-feed]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/web/src/App.tsx#L395-L397
[c-log]: https://github.com/superken-python/ai-architecture/blob/a82c9fcd65b4a8ede4c32fa6ab6c092882e40f1c/projects/realtime-voice-translate/web/src/net/ws_client.ts#L55
[ws-paper]: https://arxiv.org/abs/2307.14743
[ws-repo]: https://github.com/ufal/whisper_streaming
[simul]: https://github.com/ufal/SimulStreaming
[silero-wrapper]: https://github.com/snakers4/silero-vad/blob/v6.2.1/src/silero_vad/utils_vad.py
[ort-threads]: https://onnxruntime.ai/docs/performance/tune-performance/threading.html
[llama-server]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
[kotoba]: https://huggingface.co/kotoba-tech/kotoba-whisper-v2.2
[reazon-k2]: https://huggingface.co/reazon-research/reazonspeech-k2-v2
[sherpa]: https://github.com/k2-fsa/sherpa-onnx
[pyopenjtalk]: https://github.com/tsukumijima/pyopenjtalk-plus
[ytdlp]: https://github.com/yt-dlp/yt-dlp
[cloud-net]: https://code.claude.com/docs/en/cloud-environments#network-access
