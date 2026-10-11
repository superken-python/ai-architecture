# 05 · Dịch liên tục cho video và cuộc họp nhiều người — Realtime Voice Translate

**Ngày:** 2026-10-11. **Đối chiếu với:** code nhánh `main` tại `dcae040` (đã có đợt 1 của
[04 · Cải thiện thu âm từ xa](04-cai-thien-thu-am-tu-xa.md)). **Phạm vi:** vì sao lần thử bằng video tiếng Nhật nói liên
tục 2–4 phút không ra chữ; cần thay đổi gì để app nghe và dịch nhanh khi xem video hoặc họp nhiều người cùng nói một thứ
tiếng; mô phỏng và kiểm thử các tình huống đó thế nào. **Tài liệu chỉ phân tích và đề xuất — chưa sửa code.**

Số liệu ở mục 4 là **mô phỏng**: chạy đúng VAD và segmenter đang deploy, còn thời gian ASR dùng mô hình giả định vì
sandbox không tải được model Whisper. Các link tới dòng code trỏ vào commit `dcae040`.

## 1. Kết luận

1. **Lần thử video bị chặn bởi nhiều nguyên nhân cùng lúc.** Ba nguyên nhân khả năng cao nhất:
   - **Khoá sai ngôn ngữ.** Mặc định nửa A khoá tiếng Việt, nửa B khoá tiếng Anh; chưa nửa nào là 日本語 hay Tự động. Server
     ép Whisper đọc tiếng Nhật thành tiếng Việt/Anh, ra chữ vô nghĩa hoặc bị lọc thành rỗng. Mỗi lần nhận dạng còn có thể bị
     giải mã lại tới 6 lần (cơ chế thử lại nhiều mức nhiệt đang bật), nên rất chậm.
   - **Video phát trên cùng thiết bị với app.** Nếu video chạy ở tab khác của Chrome trên cùng laptop, hoặc trong app
     YouTube trên chính điện thoại, bộ khử vọng (`echoCancellation`) xoá tiếng video khỏi micro. Đó đúng là việc nó được thiết
     kế để làm.
   - **Lời nói liên tục làm câu dài 15–20 s và hàng đợi ASR phình ra.** Video gần như không có khoảng lặng ≥ 0,5 s, nên câu
     chỉ được chốt ở mốc 15–20 s. Trong lúc đó, cứ 0,8 s lại có một lần nhận dạng tạm chạy lại toàn bộ đoạn, xếp hàng không
     gộp và không ưu tiên. Chỉ cần mỗi lần nhận dạng chậm hơn một chút (nhạc nền, khoá sai ngôn ngữ), hàng đợi phình liên tục.
     Mô phỏng 3 phút video: chữ của câu cuối trễ khoảng 2,5 phút khi nhận dạng chậm ×3, và khoảng 7,5 phút khi khoá sai
     ngôn ngữ (×6).
2. **Các nguyên nhân này có từ trước đợt 1.** Đợt 1 chỉ sửa VAD và cắt câu, không đổi cách chọn ngôn ngữ, cách xếp hàng
   ASR hay cấu hình micro trên trình duyệt.
3. **Để dịch video/cuộc họp nhanh cần năm thay đổi** (chi tiết ở mục 5):
   - nguồn âm sạch: thu thẳng âm thanh tab/màn hình khi video hay Zoom chạy trên cùng máy tính, và mic chế độ thu xa khi
     nghe trong phòng;
   - chế độ "nghe liên tục" với một ngôn ngữ nguồn cho cả phiên;
   - câu tối đa 6–8 s và hàng đợi ASR có ưu tiên — mô phỏng: trễ p95 giảm từ 156 s xuống 2,4 s;
   - tiếp theo là nhận dạng streaming (LocalAgreement/AlignAtt) và dịch theo từng câu;
   - với nhiều người: gắn nhãn người nói bằng diarization. Khi hai người nói chồng, một micro + Whisper chỉ nghe rõ người
     to nhất, nên cần mic riêng từng người hoặc mảng mic.
4. **Mô phỏng và kiểm thử** (mục 6) dùng ba nguồn dữ liệu — tổng hợp có đáp án chính xác, ghi âm thật có kiểm soát, họp
   nội bộ có ghi âm từng người — và hai công cụ: bộ phát lại thời gian thực qua WebSocket, và mô phỏng offline nhanh không
   cần GPU.

### Thử lại ngay hôm nay (không cần sửa code)

1. Chọn ngôn ngữ của nửa đang bấm mic là **日本語** (hoặc Tự động).
2. Phát video trên **một thiết bị khác** (laptop hoặc TV có loa), đặt điện thoại cách loa 0,5–1 m. Không phát trên chính
   điện thoại hay laptop đang chạy app.
3. Giữ trang app luôn hiện trên màn hình: không chuyển app, không khoá máy.
4. Ưu tiên video có lời rõ, nhạc nền nhỏ.
5. Mở log server để xem câu bị mất ở bước nào (bảng ở mục 2.5).

Kể cả làm đúng 1–4, với video nói liền thì chữ chốt chỉ hiện sau mỗi 15–20 s, và có thể trễ dần theo thời gian (mục 2.3)
cho tới khi làm bước 1 ở mục 7.

## 2. Vì sao thử video không ra chữ

### 2.1 Nửa màn hình đang khoá sai ngôn ngữ

- Mặc định nửa A = `vi`, nửa B = `en` ([useStore.ts#L49-L51][c-store]). Lựa chọn tự động hiện là "Tự động (vi)"
  hoặc "Tự động (en)" ([App.tsx#L286][c-app-b], [#L344][c-app-a]), nên dễ tưởng nhầm là đã ở chế độ tự động.
- Khi một nửa đã khoá ngôn ngữ, server ép Whisper dùng đúng ngôn ngữ đó cho cả chữ tạm lẫn câu chốt và bỏ qua bước nhận
  dạng ngôn ngữ ([session.py#L194-L197][c-partial-lang], [#L212-L231][c-final-lang]).
- Bị ép đọc tiếng Nhật thành tiếng Việt hay tiếng Anh, Whisper thường trả về chữ vô nghĩa hoặc một bản "dịch" lệch, kèm
  điểm tin cậy thấp. Kết quả hoặc bị bộ lọc `no_speech`/ảo giác xoá thành rỗng, hoặc hiện chữ sai rồi bị dịch sai.
- **Về tốc độ, còn tệ hơn.** Code không đặt `temperature` ([asr_whisper.py#L88-L98][c-asr-args]), nên faster-whisper dùng
  dãy mặc định 0,0 → 1,0 ([transcribe.py][fw]). Khi `avg_logprob < −1` hoặc chữ bị lặp, nó giải mã lại ở mức nhiệt cao
  hơn, tối đa **6 lần** cho mỗi lần gọi. Thiết kế [01 · Kế hoạch](01-ke-hoach-trien-khai.md) §6.3 đã chốt `temperature=0`,
  nhưng code chưa làm.
- Không có cảnh báo nào kiểu "đang nghe thấy tiếng Nhật nhưng nửa này khoá tiếng Việt".

### 2.2 Video phát trên cùng thiết bị bị bộ khử vọng xoá

- App xin micro với `echoCancellation: true` ([ws_client.ts#L97-L104][c-gum]). Bộ khử vọng (AEC) được thiết kế để xoá
  khỏi micro mọi âm thanh mà chính máy đang phát ra loa.
- Chrome trên Windows, Mac và Linux bật sẵn tính năng **Chrome-wide echo cancellation**: trộn rồi khử mọi âm thanh mà
  Chrome phát ra thiết bị loa, kể cả video YouTube ở tab khác ([media_switches.cc][cr-cwec],
  [media_options.gni][cr-cwec-gni]).
- Trên Android và iPhone, AEC của chế độ cuộc gọi khử âm thanh mà máy đang phát. Ngoài ra, khi chuyển sang app YouTube thì
  trang web chạy nền: iPhone ngừng thu micro của trang, còn Android có thể tiết chế.
- Hệ quả: server gần như không nhận được tiếng video, nên VAD không báo "đang nói" và không có câu nào.

### 2.3 Lời nói liên tục làm câu dài 15–20 s và hàng đợi ASR phình ra

- Segmenter chỉ chốt câu khi có ≥ 0,5 s im lặng. Nếu không, nó chờ tới 15 s (và cần thêm 0,2 s lặng) hoặc cắt cứng ở 20 s
  ([segmenter.py#L12-L13][c-seg-max], [#L94-L101][c-seg-maxcheck]). Video và tin tức thường chỉ nghỉ 0,1–0,35 s giữa các
  câu, nên câu kéo tới mốc tối đa.
- Trong lúc câu còn mở, cứ 0,8 s lại tạo một job nhận dạng tạm chạy lại **toàn bộ** đoạn đã nghe
  ([session.py#L140-L142][c-partial]).
- Mọi job xếp sau một `asyncio.Lock` duy nhất ([scheduler.py#L17-L26][c-sched]): vào trước ra trước, không gộp job tạm cũ,
  không ưu tiên câu chốt. Tham số `is_final` có truyền vào nhưng không được dùng. Thiết kế 01 §5.7 đã ghi "partial được gộp
  và bị bỏ khi bận", nhưng code chưa làm.
- Mỗi phiên có hàng đợi riêng nhưng dùng chung một GPU, nên giữa các phiên không có thứ tự ưu tiên nào.
- Mô phỏng (mục 4) với 3 phút video liên tục:
  - các job tạm phải xử lý tổng cộng 1.819 s audio, gấp khoảng 10 lần độ dài video;
  - nếu mỗi lần nhận dạng chậm ×3 (nhạc nền, nói chồng), chữ của câu cuối trễ khoảng 2,5 phút;
  - nếu khoá sai ngôn ngữ (×6), câu đầu tiên ra sau 90 s, câu cuối trễ khoảng 7,5 phút.

### 2.4 Các bộ lọc có thể xoá câu thật của video

- Mẫu ảo giác tiếng Nhật xoá nguyên câu "ご視聴ありがとうございました", "お疲れ様でした" và mọi câu bắt đầu bằng
  "チャンネル登録" ([asr_whisper.py#L37][c-halluc]). Đây lại là những câu thật rất hay gặp ở cuối video YouTube.
- Đoạn có nhạc nền thường có `no_speech_prob` cao. Bộ lọc riêng của dự án bỏ các segment đó dù Whisper đọc được chữ
  (04 §3.3).
- Engine dịch cố định `max_tokens: 128` ([mt_llama.py#L86-L91][c-mt-tokens]), bỏ qua `max_tokens: 256` ghi trong profile.
  Một đoạn 15–20 s có thể có bản dịch dài hơn mức này và bị cắt cụt.

### 2.5 Chẩn đoán trong 5 phút bằng log server

Trong lúc phát video, chạy trên máy GPU:

```bash
docker logs -f rvt_ai 2>&1 | grep -E "Loading faster-whisper|Falling back|Speech DETECTED|Speech ended|ASR Final|empty text|Filtered|too low|hallucination"
```

| Dấu hiệu trong log | Nguyên nhân | Xử lý |
|---|---|---|
| Không có `🗣️ VAD: Speech DETECTED` khi video đang phát | âm thanh không tới server: AEC xoá, trang chạy nền, sai micro | phát video từ thiết bị khác; giữ app trên màn hình |
| `⏱️ Segmenter: Speech ended, final audio (15000–20000ms)` lặp lại | lời nói liền, câu chạm mốc tối đa | bước 1 ở mục 7 |
| Khoảng cách giữa dòng `Speech ended` và dòng `📝 ASR Final` tương ứng tăng dần | hàng đợi ASR phình | bước 1 ở mục 7 |
| `📝 ASR Final: '…' [lang=vi …]` mà video nói tiếng Nhật, chữ vô nghĩa | khoá sai ngôn ngữ | chọn 日本語 |
| Nhiều `🔇 … empty text` hoặc `Filtered silent/no-speech segment` dù `vad_max` cao | Whisper bỏ đoạn vì nhạc nền hoặc sai ngôn ngữ | chọn đúng ngôn ngữ; video ít nhạc |
| `Discarded known Whisper hallucination: 'ご視聴…'` | câu thật bị lọc nhầm | bước 1 ở mục 7 |
| `Loading faster-whisper model … on cpu` hoặc `Falling back to CPU` | ASR chạy CPU, chậm gấp nhiều lần ([asr_whisper.py#L55-L73][c-asr-device]) | kiểm tra GPU, driver, `runtime: nvidia` |

Thêm một kiểm tra: `nvidia-smi` báo GPU 100% liên tục trong lúc test nghĩa là hàng đợi đang đầy.

## 3. Mục tiêu cho chế độ video và cuộc họp

| Chỉ số | Mục tiêu |
|---|---|
| Chữ tạm đầu tiên sau khi bắt đầu nói | ≤ 1,5 s |
| Chữ chốt sau khi người nói dứt câu (p95) | ≤ 3 s |
| Bản dịch sau khi có chữ chốt (p95) | ≤ 1,5 s |
| Trễ không tăng dần theo thời gian | sau 30 phút tăng ≤ 0,5 s |
| Độ dài câu tối đa | 6–8 s |
| CER tiếng Nhật trên video thu thẳng | không xấu hơn mức đo ở bước 0 (mục 7) |
| Nhãn người nói đúng (khi bật diarization) | ≥ 85% thời lượng nói |

## 4. Số đo mô phỏng

**Cách làm**

- **Giọng nói:** 36 câu tiếng Nhật kiểu họp và báo cáo, tổng hợp bằng TTS offline ([pyopenjtalk-plus][pyopenjtalk]). Bốn
  "người nói" được tạo bằng cách đổi cao độ và tốc độ.
- **Kịch bản:** ghép thành 3 kịch bản dài 3 phút, phát qua mô hình phòng ở khoảng cách 1 m (vang RT60 0,5 s, có nhiễu nền).
- **Code được đo:** đúng `SileroVadEngine` và `Segmenter` với cấu hình profile `balanced` đang deploy. Script ghi lại thời
  điểm tạo từng job nhận dạng tạm và câu chốt.
- **Hàng đợi:** một GPU, mô phỏng sự kiện rời rạc theo hai cách — xếp hàng như `AsrScheduler` hiện tại, và theo đề xuất ở
  mục 5.4.
- **Thời gian mỗi lần nhận dạng (giả định):**
  - "GPU vừa": 0,15 s + 0,04 s cho mỗi giây audio, tức khoảng 0,95 s cho đoạn 20 s;
  - ×3: nhạc nền hoặc nói chồng khiến Whisper giải mã lại vài lần;
  - ×6: khoá sai ngôn ngữ, chạy đủ 6 lần giải mã.
- **Giới hạn:** không chạy Whisper thật. Con số tuyệt đối phải đo lại trên máy GPU, nhưng việc trễ ổn định hay phình ra phụ
  thuộc vào cách xếp hàng, không phụ thuộc giả định thời gian.

**Kết quả cắt câu**

| Kịch bản | Mô tả | Số câu chốt | Độ dài TB / tối đa | Câu có > 1 người |
|---|---|---|---|---|
| Video | 4 người, nghỉ 0,12–0,35 s, nhạc nền thấp hơn lời 18 dB | 11 | 15,7 / 20,4 s | 10/11 |
| Họp lần lượt | đổi người mỗi câu, nghỉ 0,3–1,2 s | 31 | 5,6 / 15,1 s | 5/31 |
| Nói chồng | người sau chen vào sớm 0–1,2 s | 10 | 17,4 / 20,3 s | 10/10 |

**Độ trễ ở kịch bản video.** "Trễ" là khoảng từ lúc câu được chốt đến lúc ASR xong câu đó, chưa tính thời gian dịch (thêm
khoảng 0,3–1 s).

| Thời gian ASR | Cách xếp hàng | Câu chốt đầu tiên | Trễ p50 / p95 | Trễ ở 1/3 cuối |
|---|---|---|---|---|
| GPU vừa | hiện tại | 22 s | 1,1 / 1,7 s | 1,1 s |
| GPU vừa | gộp + ưu tiên + câu ≤ 6–8 s | 9 s | 0,5 / 0,9 s | 0,6 s |
| GPU vừa ×3 | hiện tại | 46 s | 84 / 156 s | 150 s |
| GPU vừa ×3 | gộp job tạm + ưu tiên câu chốt | 25 s | 4,1 / 4,8 s | 4,4 s |
| GPU vừa ×3 | gộp + ưu tiên + câu ≤ 6–8 s | 11 s | 1,7 / 2,4 s | 1,7 s |
| GPU vừa ×6 (sai ngôn ngữ) | hiện tại | 90 s | 257 / 476 s | 455 s |
| GPU vừa ×6 | gộp + ưu tiên + câu ≤ 6–8 s | 14 s | 4,1 / 5,3 s | 4,3 s |

Hai kịch bản còn lại, với thời gian ASR ×3:

- **Họp lần lượt:** cách hiện tại trễ 36 s ở 1/3 cuối; đề xuất giữ khoảng 1,5 s.
- **Nói chồng:** cách hiện tại trễ p50 99 s; đề xuất còn 1,9 s.

**Cách đọc kết quả**

- Độ dài câu quyết định lúc chữ chốt đầu tiên xuất hiện. Câu 15–20 s nghĩa là phải chờ ít nhất chừng đó.
- Cách xếp hàng hiện tại mất ổn định ngay khi tải nhận dạng vượt khả năng GPU. Vì mỗi 0,8 s lại thêm một job chạy lại cả
  đoạn, điều này xảy ra khi đoạn dài hoặc mỗi lần gọi chậm hơn một chút. Từ đó trễ tăng tuyến tính theo thời gian. Gộp job
  tạm và ưu tiên câu chốt giữ trễ ổn định; cắt câu ngắn hạ thêm trễ.
- Khi lời nói liền hoặc nói chồng, gần như mọi câu chứa nhiều người. Muốn tách câu theo người nói thì cần diarization.

## 5. Đề xuất

### 5.1 Nguồn âm: thu đúng thứ cần dịch

| Tình huống | Nguồn âm khuyến nghị | Ghi chú |
|---|---|---|
| Video, YouTube, Zoom, Meet chạy trên cùng máy tính | **Âm thanh tab/màn hình** qua `getDisplayMedia({ audio: true })` | tín hiệu số sạch, không qua loa–phòng–mic, không bị AEC xoá; Chrome/Edge desktop thu được âm tab trên mọi hệ điều hành, âm toàn hệ thống trên Windows/ChromeOS (macOS cần bản Chrome và macOS mới — phải thử) ([getDisplayMedia][gdm]); điện thoại không hỗ trợ |
| Video trên TV hay máy khác, họp tại chỗ | Mic điện thoại ở chế độ thu xa (04, đợt 3): tắt AEC và lọc ồn kiểu cuộc gọi | nguồn này vẫn cần AGC ở server (04, đợt 2) |
| Họp quan trọng, nhiều người | Mic riêng từng người, hoặc loa-mic hội nghị (04 §6.6) | xem 5.6 |

App nên cảnh báo người dùng ở hai lúc:

- khi dùng micro: "Không phát video trên chính máy này";
- khi trang bị ẩn (sự kiện `visibilitychange`): "Đã tạm dừng nghe".

### 5.2 Chế độ "Nghe liên tục" cho video và cuộc họp

- **Khác chế độ hội thoại hai nửa hiện nay:**
  - cả phiên dùng một ngôn ngữ nguồn (日本語 hoặc Tự động);
  - micro hoặc nguồn tab mở liên tục, không phải bấm từng lượt;
  - hiển thị một dòng chữ chạy, dịch sang 1–2 ngôn ngữ đích;
  - có nhãn người nói khi bật diarization.
- **Khoá ngôn ngữ nguồn là cách nhanh nhất:** không cần nhận dạng ngôn ngữ, không giải mã lại. Nếu chọn Tự động thì nhận
  dạng ngôn ngữ một lần ở đầu và kiểm lại sau mỗi vài câu.
- **Phát hiện khoá sai ngôn ngữ:** chạy `detect_language` trên câu chốt. Bước này rẻ vì dùng lại kết quả encoder. Nếu một
  tiếng khác chiếm ưu thế ở ít nhất 2 câu liên tiếp, gợi ý người dùng đổi.
- Chế độ này gần với chế độ "rảnh tay" P5 trong kế hoạch 01 (§7.3 và mục 5.4 của danh sách việc).

### 5.3 Cắt câu cho lời nói liên tục

- Câu tối đa 6–8 s thay vì 15/20 s. Khi gần chạm mốc, cắt tại điểm có xác suất VAD hoặc năng lượng thấp nhất trong 1–2 s
  cuối, thay vì cắt cứng giữa một từ.
- Thời gian im lặng để chốt câu thay đổi theo độ dài câu: 500 ms lúc câu còn ngắn, giảm còn khoảng 200–250 ms khi câu đã
  dài hơn 4 s.
- Nếu buộc phải cắt cứng, giữ 0,3–0,5 s chồng lấn giữa hai đoạn. Phần trùng lặp được loại bằng timestamp từng từ
  (`word_timestamps`) hoặc so khớp chuỗi.
- Chỗ đổi người nói (lấy từ diarization, mục 5.6) cũng là một điểm cắt.

### 5.4 Lập lịch nhận dạng trên GPU

- **Một hàng đợi chung cho cả GPU:**
  - câu chốt luôn chạy trước job tạm;
  - mỗi phiên có tối đa 1 job tạm đang chờ, job tạm mới thay job cũ;
  - bỏ job tạm khi hàng đợi đã trễ hơn 1–1,5 s;
  - chỉ tạo job tạm khi có thêm ít nhất 0,8 s audio mới.
- **Giải mã:**
  - đặt `temperature=0`, hoặc tối đa hai mức [0; 0,4], kèm giới hạn thời gian cho mỗi lần gọi;
  - giữ `compression_ratio_threshold` để phát hiện và bỏ chữ lặp, thay vì giải mã lại;
  - job tạm dùng `beam_size=1`; câu chốt dùng beam 5 nếu đo thấy chính xác hơn.
- **Job tạm tăng dần:** chỉ giải mã phần audio mới, dùng chữ đã chốt làm prompt, thay vì chạy lại toàn bộ buffer.
- **Đo và log:** thời gian chờ trong hàng (`asr_queue_wait_ms`), số job đang chờ, tỉ lệ job tạm bị bỏ. Báo về client khi
  quá tải.
- **Nhiều phiên:** khi có từ 2 phiên trở lên, gom các câu chốt thành một batch (`BatchedInferencePipeline` của
  faster-whisper).

### 5.5 Nhận dạng streaming thật sự (bước sau)

- **Whisper-Streaming** dùng chính sách LocalAgreement-2: buffer trượt được cập nhật khoảng mỗi giây, và chỉ chốt phần đầu
  trùng nhau giữa hai lần chạy liên tiếp. Bài báo gốc báo trễ khoảng 3,3 s trên lời nói dài không phân đoạn
  ([bài báo][ws-paper], [mã nguồn][ws-repo]).
- **SimulStreaming** (2025, chính sách AlignAtt) là bản kế nhiệm của cùng nhóm tác giả và nhanh hơn
  ([mã nguồn][simul], [bài IWSLT 2025][simul-paper]).
- Cách này hợp nhất với video và tin tức nói liền. Chi phí GPU ổn định, vì mỗi lần cập nhật chỉ xử lý một cửa sổ ≤ 15 s.
- **Model:** khi phiên khoá 日本語, chạy thử so sánh large-v3-turbo với [kotoba-whisper v2][kotoba]. Đây là Whisper được
  chưng cất cho tiếng Nhật, decoder chỉ 2 lớp, có bản trọng số cho faster-whisper.

### 5.6 Nhiều người cùng nói một thứ tiếng

| Tình huống | Hiện tại | Đề xuất |
|---|---|---|
| Nói lần lượt (họp, phỏng vấn) | cắt được câu nếu có khoảng lặng; không biết ai nói; người sau chen nhanh thì hai người bị gộp chung một câu | diarization streaming: [Streaming Sortformer][sortformer] (NVIDIA, bản cho tối đa 4 người; kiểm tra giấy phép trên model card) hoặc [diart][diart] (pyannote, cập nhật mỗi 500 ms) → nhãn "Người 1/2/3", cắt câu tại chỗ đổi người |
| Nói chồng (hai người cùng lúc) | Whisper chỉ nhận rõ người to nhất, phần còn lại mất hoặc lẫn vào nhau | mic riêng từng người (mỗi kênh một luồng ASR) là cách chắc nhất; tiếp theo là mảng mic có beamforming; tách nguồn bằng model (MossFormer2, SepFormer) chỉ dùng khi đo thấy CER giảm vì tốn GPU và có artifact; tối thiểu phát hiện được nói chồng và đánh dấu "[nhiều người nói]" |
| Video nhiều người (talk show) | như hai dòng trên | thu thẳng âm tab + diarization; chấp nhận mất các đoạn nói chồng ngắn |
| Một nguồn, nhiều người xem | mỗi điện thoại một phiên, dịch lặp lại | dịch một lần cho mỗi ngôn ngữ đích rồi phát cho nhiều client (dạng "phòng"), tiết kiệm GPU |

### 5.7 Dịch nhanh cho luồng liên tục

- **Dịch theo câu đã chốt**, ngắn, thay vì cả đoạn 20 s. Gửi kèm 1–2 câu trước làm ngữ cảnh: `translate_stream` đã có tham
  số `context` ([mt_llama.py#L69-L70][c-mt-sig]) nhưng session chưa truyền ([session.py#L281][c-mt-call]).
- **`max_tokens` theo độ dài câu nguồn**, ví dụ gấp 3 số token nguồn và tối thiểu 64, thay vì cố định 128. Đồng thời dùng các
  tham số dịch trong profile thay vì giá trị cố định trong code.
- **Câu cuối còn đang thay đổi:** hiện bản dịch tạm rồi dịch lại khi câu chốt. Nếu GPU bận thì chỉ dịch khi câu đã chốt.
- **Không xoá câu chỉ vì khớp mẫu ảo giác** khi VAD và SNR cho thấy có tiếng nói rõ (04 §6.3).

## 6. Mô phỏng và kiểm thử video, cuộc họp

### 6.1 Ba nguồn dữ liệu

| Nguồn | Cách làm | Đáp án có được | Dùng để đo |
|---|---|---|---|
| Tổng hợp từ câu đơn | ghép câu theo tham số ở 6.2. Câu lấy từ TTS (như mục 4) hoặc [FLEURS][fleurs] tiếng Nhật (giọng thật, CC-BY 4.0). Đưa qua mô hình phòng ([pyroomacoustics][pyroom]), thêm nhạc và nhiễu | biết chính xác ai nói gì, lúc nào, chồng lấn bao nhiêu | độ trễ, cắt câu, hàng đợi, diarization; CER nếu dùng FLEURS |
| Ghi thật có kiểm soát | phát video hoặc đoạn họp mẫu qua loa trong phòng thật. Thu cùng lúc bằng điện thoại ở 0,5/1/2 m (chế độ ghi kiểm thử, 04 §7.1) và bằng thu thẳng âm tab | phụ đề do người làm (manual captions) của video, hoặc transcript tự gõ | CER thực tế; so sánh mic với thu thẳng |
| Họp nội bộ, có đồng ý ghi âm | 3–5 người nói tiếng Nhật 10–20 phút. Mỗi người đeo 1 mic cài áo, thêm 1 điện thoại đặt giữa bàn | bản thu từng người cho biết ai nói lúc nào và lúc nào nói chồng | diarization, nói chồng, trễ thật |

TTS chỉ dùng để đo pipeline và độ trễ. Muốn đo độ chính xác phải dùng giọng thật.

### 6.2 Tham số của bộ sinh kịch bản

| Tham số | Giá trị gợi ý |
|---|---|
| Số người nói | 1 · 2 · 4 · 6 |
| Khoảng nghỉ giữa lượt | −1,2–0 s (nói chồng) · 0,1–0,35 s (video) · 0,3–1,2 s (họp) |
| Tỉ lệ thời gian nói chồng | 0% · 10% · 25% |
| Tần suất đổi người | mỗi câu · mỗi 2–4 câu |
| Nhạc, nền | không có · nhạc thấp hơn lời 18 dB · ồn quán thấp hơn lời 10 dB |
| Đường âm | thu thẳng · loa → phòng (RT60 0,3–0,8 s) → mic ở 0,5/1/2/3 m |
| Độ dài | 3 · 10 · 60 phút (bài chạy dài) |
| Số phiên chạy song song | 1 · 2 · 4 |

### 6.3 Bộ phát lại thời gian thực (end-to-end)

- Một client Python mở kết nối WSS tới server thật và gửi khung 40 ms đúng nhịp thời gian thực. Có thể chạy nhanh ×2, ×4
  để ép tải. Client đặt ngôn ngữ theo kịch bản và ghi timestamp của mọi event: `vad`, `asr.partial`, `asr.final`,
  `mt.final`.
- So kết quả với đáp án để tính các chỉ số ở 6.5. Bài tải chạy N client song song, ghi kèm `nvidia-smi dmon` và log hàng
  đợi.
- Có thể phát triển từ `scripts/smoke_ws.py`; script này hiện chỉ gửi 300 ms byte giả.

### 6.4 Mô phỏng offline nhanh (không cần GPU)

- Làm như mục 4: chạy VAD và segmenter thật, còn hàng đợi thì mô phỏng bằng mô hình thời gian ASR. 3 phút audio chỉ mất vài
  giây, đủ nhanh để thử các phương án (độ dài câu tối đa, gộp job tạm, ngưỡng) trước khi chạy trên GPU.
- Đưa vào CI để chặn lỗi hồi quy kiểu "trễ tăng dần".
- Đo thời gian ASR thật trên máy GPU, theo độ dài đoạn, theo ngôn ngữ, có và không có nhạc, để thay mô hình thời gian giả
  định. Script mô phỏng của tài liệu này chưa đưa vào repo; đề xuất đưa vào ở bước 0.

### 6.5 Chỉ số

- **Độ trễ:** chữ tạm đầu tiên; chữ chốt (từ cuối câu tới `asr.final`); bản dịch (tới `mt.final`); độ dốc của trễ theo
  thời gian.
- **Chất lượng:** CER tiếng Nhật, tỉ lệ lời nói bị mất, số câu bịa, số lần cắt giữa từ.
- **Cắt câu:** phân bố độ dài câu, số câu chứa nhiều hơn một người.
- **Người nói:** DER (tỉ lệ lỗi gán người nói), độ chính xác nhãn tính trên từng câu.
- **Tài nguyên:** % GPU, số job đang chờ, tỉ lệ job tạm bị bỏ.

### 6.6 Bộ kịch bản chuẩn

| Mã | Kịch bản | Đạt khi |
|---|---|---|
| K1 | Video tin tức 1 người, nói liền, nhạc nền nhỏ, 10 phút | trễ chữ chốt p95 ≤ 3 s; độ dốc ≤ 0,5 s / 30 phút |
| K2 | Talk show 3–4 người, có chen ngang | như K1; nhãn người nói đúng ≥ 85% |
| K3 | Họp 4 người nói lần lượt, nghỉ 0,3–1,2 s | như K1; số câu chứa nhiều người ≤ 5% |
| K4 | Họp có 20% thời gian nói chồng | không đứng hình; đánh dấu được đoạn nói chồng |
| K5 | Cùng một video, so sánh thu thẳng âm tab với loa → mic 1 m | thu thẳng có CER thấp hơn rõ rệt; có số đo để hướng dẫn người dùng |
| K6 | K1 chạy liền 60 phút | không rò bộ nhớ; trễ không tăng |
| K7 | 4 phiên K1 chạy cùng lúc | trễ p95 ≤ 4 s; không phiên nào bị đói GPU |

## 7. Lộ trình đề xuất

| Bước | Nội dung | Tầng | Công | Xong khi |
|---|---|---|---|---|
| 0 · Bộ đo (làm trước) | 6.3, 6.4; kịch bản K1–K4; đo thời gian ASR thật | eval | 2–3 ngày | có báo cáo mức cơ sở |
| 1 · Hết đứng hình | 5.4 (hàng đợi, `temperature=0`); 5.3 (câu ≤ 8 s); cảnh báo khoá sai ngôn ngữ (5.2); sửa mẫu ảo giác và `max_tokens` (5.7) | server | 2–3 ngày | K1: trễ p95 ≤ 3 s, không tăng sau 30 phút |
| 2 · Nguồn âm và chế độ nghe liên tục | 5.1, 5.2 | web + server | 3–5 ngày | K5 đạt; video trên cùng máy dịch được qua thu thẳng âm tab |
| 3 · Streaming và dịch theo câu | 5.5, 5.7 | server | 1–2 tuần | trễ chữ chốt p95 ≤ 3 s; CER không xấu hơn mức cơ sở |
| 4 · Nhiều người nói | 5.6 | server + web | 1–2 tuần | K2/K3: nhãn đúng ≥ 85%; K4 đánh dấu được nói chồng |

Đợt 2 (AGC ở server) và đợt 3 (chế độ thu xa trên trình duyệt) của tài liệu 04 vẫn cần cho nguồn micro, và có thể làm song
song với bước 1–2.

## 8. Rủi ro và đánh đổi

- **Câu ngắn hơn** cho Whisper và bộ dịch ít ngữ cảnh hơn, nên chất lượng có thể giảm nhẹ. Bù lại bằng cách dùng chữ đã chốt
  làm prompt và truyền ngữ cảnh cho bộ dịch; phải đo CER.
- **Bỏ job tạm khi bận** làm chữ tạm cập nhật thưa hơn, nhưng chữ chốt không còn bị trễ.
- **`temperature=0`** có thể làm chữ lặp nhiều hơn ở đoạn khó. Giữ `compression_ratio_threshold` để phát hiện và bỏ đoạn đó.
- **Thu thẳng âm tab:** chỉ có trên máy tính; người dùng phải tự chọn tab và tick "chia sẻ âm thanh". Video có bản quyền thì
  chỉ dùng thu để kiểm thử nội bộ.
- **Diarization và tách nguồn tốn GPU.** Cần cân với GPU 8 GB đang chạy cả ASR lẫn MT.
- **Mô phỏng dùng giọng tổng hợp và thời gian ASR giả định**, nên chỉ dùng để so sánh các cách làm. Số thật phải đo trên GPU
  ở bước 0.

## Phụ lục — nguồn tham khảo

- Chrome khử vọng cho mọi âm Chrome phát ra (Windows/Mac/Linux): [media_switches.cc][cr-cwec] (`kChromeWideEchoCancellation`),
  [media_options.gni][cr-cwec-gni].
- faster-whisper: dãy nhiệt độ mặc định và điều kiện giải mã lại: [transcribe.py][fw].
- Macháček, Dabre, Bojar (2023), *Turning Whisper into Real-Time Transcription System*: [arXiv 2307.14743][ws-paper].
- SimulStreaming (ufal, 2025): [GitHub][simul]; CUNI tại IWSLT 2025: [arXiv 2506.17077][simul-paper].
- Streaming Sortformer: [arXiv 2507.18446][sortformer]; diart: [GitHub][diart].
- Kotoba-Whisper v2 (tiếng Nhật): [Hugging Face][kotoba].
- Thu âm tab/hệ thống bằng `getDisplayMedia`: [MDN][gdm], [kiểm thử của addpipe][gdm-addpipe].

[c-store]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/web/src/state/useStore.ts#L49-L51
[c-app-b]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/web/src/App.tsx#L286
[c-app-a]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/web/src/App.tsx#L344
[c-partial]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L140-L142
[c-partial-lang]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L194-L197
[c-final-lang]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L212-L231
[c-mt-call]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/session.py#L281
[c-sched]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/scheduler.py#L17-L26
[c-asr-args]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L88-L98
[c-halluc]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L37
[c-asr-device]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/engines/asr_whisper.py#L55-L73
[c-seg-max]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L12-L13
[c-seg-maxcheck]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/pipeline/segmenter.py#L94-L101
[c-mt-sig]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L69-L70
[c-mt-tokens]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/ai/src/rvt_ai/engines/mt_llama.py#L86-L91
[c-gum]: https://github.com/superken-python/ai-architecture/blob/dcae040ae67c1c1b83168b6cd35dec28cc5776fe/projects/realtime-voice-translate/web/src/net/ws_client.ts#L97-L104
[cr-cwec]: https://github.com/chromium/chromium/blob/main/media/base/media_switches.cc
[cr-cwec-gni]: https://github.com/chromium/chromium/blob/main/media/media_options.gni
[fw]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py
[ws-paper]: https://arxiv.org/abs/2307.14743
[ws-repo]: https://github.com/ufal/whisper_streaming
[simul]: https://github.com/ufal/SimulStreaming
[simul-paper]: https://arxiv.org/abs/2506.17077
[sortformer]: https://arxiv.org/abs/2507.18446
[diart]: https://github.com/juanmc2005/diart
[kotoba]: https://huggingface.co/kotoba-tech/kotoba-whisper-v2.2
[gdm]: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia
[gdm-addpipe]: https://addpipe.com/getdisplaymedia-demo/
[fleurs]: https://huggingface.co/datasets/google/fleurs
[pyroom]: https://github.com/LCAV/pyroomacoustics
[pyopenjtalk]: https://github.com/tsukumijima/pyopenjtalk-plus
