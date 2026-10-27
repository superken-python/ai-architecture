# 10 · Nghiên cứu lại: nghe một chiều, tiếng Anh và tiếng Việt — Realtime Voice Translate

**Ngày:** 2026-10-14. **Phạm vi:** nghiên cứu, chưa code. Bản hiện tại (2 chiều, nghe dịch video, tiếng Nhật) được đánh
giá là chưa ổn, nên phía UI sẽ làm lại từ đầu. Bước đầu tiên chỉ cần:

- một tab **"Chỉ nghe"**: nghe liên tục từ mic hoặc tab video, hiện chữ lên màn hình để xem có nhận đúng câu nói không;
- **một người hoặc nhiều người nói**, có nhãn người nói khi nhiều người;
- **chỉ tiếng Anh và tiếng Việt**, gồm cả câu tiếng Việt lẫn từ tiếng Anh;
- chưa dịch, chưa hai chiều;
- không giới hạn cấu hình server hay chi phí: chọn theo chất lượng trước.

**Cập nhật 2026-10-15: thu hẹp phạm vi.** Làm trước **độ chính xác của một chiều, một người nói, một phiên**, trên app
hiện tại (không đổi kiến trúc). Nhiều người nói, tách người nói và tab UI mới để sau. Kế hoạch ở mục 10.

Tài liệu này so các cách làm từ tốt nhất tới đơn giản nhất, cả dịch vụ online lẫn model tự host, rồi đề xuất cách thử.

**Lưu ý về nguồn.** Phần lớn số liệu về độ trễ, độ chính xác, ngôn ngữ hỗ trợ là do chính nhà cung cấp công bố, hoặc
từ các trang so sánh không độc lập. Không có bộ đo chung nào cho tiếng Việt nói tự nhiên, nhiều người, có nhạc nền. Vì
vậy kết luận ở đây là **danh sách ứng viên để đo**, không phải bảng xếp hạng cuối. Nguồn ở mục 14.

## 1. Kết luận

1. **Tốt nhất hiện nay là dịch vụ online có cả nhận dạng lẫn tách người nói trong cùng một luồng trực tiếp.** Tự ghép
   hai model (nhận dạng + tách người nói) chạy local vẫn kém hơn về độ trễ và độ ổn định, nhất là với tiếng Việt.
2. **Hai ứng viên đầu bảng cần thử trước: Soniox và Deepgram.** Cả hai công bố có nhận dạng trực tiếp tiếng Việt và
   tiếng Anh, kèm tách người nói ngay trong luồng trực tiếp. Chưa có số đo độc lập cho tiếng Việt.
3. **Nhóm thứ hai, phải kiểm danh sách ngôn ngữ trước:** Speechmatics, Azure AI Speech, OpenAI (`gpt-4o-transcribe`,
   `gpt-4o-transcribe-diarize`), ElevenLabs Scribe v2 Realtime, AWS Transcribe, AssemblyAI. Mỗi dịch vụ có trực tiếp và
   có tách người nói, nhưng chưa xác nhận được tiếng Việt cho cả hai tính năng cùng lúc.
4. **Không chọn Google Chirp 3 cho bước này:** có nhận dạng trực tiếp tiếng Việt, nhưng tách người nói chỉ có ở chế độ
   xử lý file (batch).
5. **Tự host tốt nhất:** Whisper large-v3 qua SimulStreaming (hoặc PhoWhisper / ChunkFormer cho tiếng Việt) cộng
   Streaming Sortformer của NVIDIA để tách người nói. Làm được, nhưng phải tự ghép, tự chỉnh độ trễ, và Sortformer chỉ
   tối đa 4 người ở bản trực tiếp chính.
6. **Bước đầu:** dựng tab "Chỉ nghe" sau một lớp `SttProvider` chung, cắm Soniox và Deepgram trước, đo trên 4–5 bộ
   audio tiếng Anh và tiếng Việt (mục 7). Chọn theo số đo, không theo quảng cáo. Chi tiết phương án tự host ở mục 9.
7. **Trước mắt (mục 10):** tối ưu app hiện tại cho một người nói. Bỏ model dịch khi chỉ nghe để dành GPU cho phần nghe,
   dùng PhoWhisper cho tiếng Việt, làm bộ đo tiếng Anh và tiếng Việt. Song song đo Soniox, Deepgram trên cùng bộ đo để
   có mốc so sánh.
8. **Theo hạ tầng (mục 11):** 8 GB đủ cho model chuyên tiếng Việt cỡ 0,6–1,5B; 24–32 GB cho phép chạy nhiều model,
   model top bảng xếp hạng tiếng Anh và sửa lỗi bằng LLM; 48–80 GB cho fine-tune trên dữ liệu riêng. Muốn gần mức online
   thì cần dữ liệu và bộ đo của mình, không phải AI agent (mục 12).
9. **Dịch video/họp (mục 13):** giữ chế độ dịch, nhưng dịch bằng GPT-5 mini (hoặc gpt-5.4-mini) qua Azure thay cho
   Qwen trên GPU. GPU 8 GB khi đó chỉ còn phần nghe, như chế độ chỉ nghe.

## 2. Bài toán và tiêu chí chọn

| Tiêu chí | Vì sao quan trọng | Đo bằng |
|---|---|---|
| Đúng chữ tiếng Việt | Tiếng Việt có dấu thanh, nhiều từ đơn âm, nói nhanh dễ mất dấu | WER sau chuẩn hoá (giữ dấu) |
| Đúng chữ tiếng Anh, và từ tiếng Anh trong câu Việt | Người Việt hay chen từ Anh ("deadline", "meeting") | WER tiếng Anh; đếm từ chen đúng |
| Tách người nói khi trực tiếp | Cần nhãn S1, S2… ngay trên màn hình, không đợi hết bài | DER, cpWER |
| Độ trễ | Chữ phải hiện gần như ngay khi nói | Thời gian tới chữ tạm đầu tiên, tới câu chốt |
| Chữ tạm ổn định | Chữ nhảy liên tục rất khó đọc | Số lần chữ đã hiện bị sửa |
| Nghe liên tục lâu | Cuộc họp, video dài 1–2 giờ | Có đứt luồng không, có tự nối lại không |
| Tiếng ồn, nhạc nền | Video có nhạc, phòng có tiếng TV | WER trên bộ audio có nhạc |

Không xét: chi phí, cấu hình GPU (theo yêu cầu). Riêng tư (âm thanh gửi ra ngoài) được ghi ở mục 8 để quyết sau.

## 3. Các cách làm, từ cao tới thấp

### Mức 1 — Dịch vụ online: nhận dạng + tách người nói trong một luồng trực tiếp

Một kết nối WebSocket gửi audio, nhận về chữ tạm, câu chốt, nhãn người nói, thời gian từng từ. Không phải tự ghép model.

| Dịch vụ | Trực tiếp | Tách người nói trực tiếp | Tiếng Việt | Ghi chú |
|---|---|---|---|---|
| **Soniox** (`stt-rt-v5`) | Có, công bố dưới 200 ms | Có, ghi rõ trên trang tính năng | Có; công bố WER 5,4% tiếng Việt, 6,5% tiếng Anh | Một luồng nhận nhiều ngôn ngữ. Tách người nói đã tính trong giá. Số liệu do Soniox tự công bố |
| **Deepgram** (Nova-3) | Có, công bố dưới 300 ms | Có (trong luồng trực tiếp) | Có trang riêng cho tiếng Việt trực tiếp, kèm tách người nói | Có chữ tạm, tự nhận hết câu, báo hết lượt nói. Tách người nói là tính năng mua thêm |
| **Speechmatics** | Có | Có | Chưa xác nhận | Có bản chạy on-premise (container) |
| **Azure AI Speech** | Có | Có (GA, audio một kênh) | Chưa xác nhận cho tách người nói | Đổi ngôn ngữ bằng mã locale. Có thể dùng chung tài khoản Azure đã có |
| **OpenAI** Realtime (`gpt-4o-transcribe`, `-diarize`) | Có | Tài liệu mới có liệt kê, nhưng cộng đồng báo trái chiều | Có (model đa ngữ) | Bản `-diarize` không nhận prompt. Cần thử thật |
| **ElevenLabs** Scribe v2 Realtime | Có, công bố khoảng 150 ms | Không rõ: có nguồn nói chỉ có ở batch | Có (công bố) | Nguồn so sánh đều là đối thủ, cần tự kiểm |
| **AWS Transcribe** | Có | Có (tới 30 người) | Chưa xác nhận cho tách người nói trực tiếp | |
| **AssemblyAI** | Có | Có, nhưng bảng của họ chỉ liệt kê 6 ngôn ngữ, không có tiếng Việt | Có ở bản mới, chưa rõ có tách người nói không | |
| **Google** Chirp 3 | Có | **Không** (chỉ batch) | Có | Loại cho bước này |
| FPT.AI, Viettel AI | Chưa thấy API trực tiếp công khai | Không rõ | Chuyên tiếng Việt | FPT.AI có API gửi cả file. Hỏi trực tiếp nếu muốn thử |

**Đánh giá:** Soniox và Deepgram là hai lựa chọn duy nhất có công bố rõ cả ba điều: trực tiếp, tách người nói trực
tiếp, tiếng Việt. Thử hai cái này trước. Speechmatics và Azure là dự phòng, sau khi kiểm danh sách ngôn ngữ.

### Mức 2 — Tự host, ghép model mạnh nhất

Chạy trên GPU của mình, âm thanh không ra ngoài. Gồm ba phần:

1. **Nhận dạng trực tiếp:**
   - **Whisper large-v3** (hoặc turbo) qua **SimulStreaming** (ÚFAL, kế thừa whisper_streaming, dùng chính sách
     AlignAtt). whisper_streaming cũ dùng LocalAgreement, độ trễ khoảng 3,3 s trong bài báo 2023. WhisperLiveKit là
     bản đóng gói cả hai chính sách, có WebSocket và tách người nói.
   - **Tiếng Việt chuyên biệt:** **PhoWhisper-large** (VinAI, Whisper fine-tune 844 giờ) hoặc
     **ChunkFormer-CTC-Large-Vie** (khoảng 3 000 giờ). Trên VIVOS, Common Voice, VLSP, hai model gần nhau;
     ChunkFormer nhỉnh hơn theo số tự công bố. PhoWhisper kém hơn Whisper-large-v3 ở đoạn chen tiếng Anh (theo một
     bộ đo y khoa).
   - **Tiếng Anh chuyên biệt:** NVIDIA **Parakeet** streaming (RNNT, 600M, chỉ tiếng Anh), độ trễ thấp.
2. **Tách người nói trực tiếp:** NVIDIA **Streaming Sortformer** (`diar_streaming_sortformer_4spk-v2.1`): đánh số người
   theo thứ tự xuất hiện, bản chính tối đa 4 người. Có thể ghép với **Multitalker Parakeet** để có chữ kèm nhãn người
   (tiếng Anh). Phương án khác: pyannote 3.x / diart (chạy theo khúc).
3. **Chọn ngôn ngữ:** khoá Anh/Việt theo người dùng chọn, hoặc nhận dạng ngôn ngữ cho từng câu.

**Đánh giá:** chất lượng chữ có thể gần dịch vụ online, nhất là tiếng Việt với PhoWhisper/ChunkFormer. Nhưng phải tự
giải những gì app hiện tại đang vấp: cắt câu, chữ tạm nhảy, câu bịa trong đoạn im lặng, ghép nhãn người với từng từ.
Sortformer được huấn luyện chủ yếu trên dữ liệu tiếng Anh. Tách người nói phần lớn dựa vào giọng, nên có thể vẫn dùng
được với tiếng Việt, nhưng chưa có số đo.

### Mức 3 — Giữ khung hiện tại, thêm tách người nói theo câu

Silero VAD + segmenter + faster-whisper turbo như bây giờ, rồi gán người nói cho từng câu đã chốt bằng embedding giọng
(pyannote, ECAPA) và gom cụm trực tiếp.

**Đánh giá:** nhanh có kết quả vì dùng lại code, nhưng thừa hưởng các lỗi đã ghi trong doc 07–09 (VAD bỏ sót, câu bịa,
chữ tạm treo). Nhãn người nói chỉ có ở mức câu, và sai khi hai người nói chồng lên nhau.

### Mức 4 — Nhẹ, chạy CPU hoặc ngay trên máy

**sherpa-onnx** với Zipformer streaming: tiếng Việt khoảng 30M tham số, công bố WER khoảng 7,7% trên GigaSpeech2-vi và
61 ms cho 3,7 s audio (số tự công bố). Có model tiếng Anh tương tự. Không có tách người nói tốt đi kèm.

**Đánh giá:** hợp cho bản chạy offline, điện thoại, hoặc làm phương án dự phòng khi mất mạng. Không phải lựa chọn chất
lượng cao nhất.

## 4. Kỹ thuật nên có, bất kể chọn mức nào

- **Hai lớp chữ:** chữ tạm (xám, có thể đổi) và câu chốt (đậm, không đổi). Dịch vụ online đều trả hai loại này. Tự host
  thì dùng chính sách SimulStreaming/LocalAgreement để chỉ chốt phần đã ổn định.
- **Sửa lại sau (two-pass):** hiện chữ trực tiếp trước, rồi sau vài giây thay câu chốt bằng kết quả của lượt thứ hai tốt
  hơn (model lớn hơn, hoặc gửi cả đoạn dài cho dịch vụ batch có tách người nói). Màn hình đánh dấu câu đã được sửa.
- **Từ khoá, tên riêng:** hầu hết dịch vụ cho gửi danh sách từ (keyterm, custom vocabulary, prompt). Cần cho tên người,
  tên công ty, thuật ngữ.
- **Nhãn người nói ổn định:** đánh số theo thứ tự xuất hiện (S1, S2…). Cho người dùng đổi tên ngay trên UI ("S1 → Lan").
  Tuỳ chọn số người dự kiến, để model không tách nhầm một người thành hai.
- **Giữ khoá API phía server:** trình duyệt gửi audio tới server của mình, server mở luồng tới nhà cung cấp. Nếu nhà
  cung cấp có token ngắn hạn (kiểm tài liệu từng bên), server cấp token để trình duyệt nối thẳng, bớt một chặng mạng.
- **Nối lại khi đứt:** luồng dài 1–2 giờ chắc chắn có lúc đứt. Giữ đệm audio vài giây, nối lại, đánh dấu chỗ hở trên màn
  hình thay vì mất chữ âm thầm.

## 5. Kiến trúc đề xuất cho bước đầu

```text
Trình duyệt (tab "Chỉ nghe")
  mic hoặc audio tab → AudioWorklet, PCM16 16 kHz → WebSocket
        │
Server (FastAPI, như hiện tại)
  SttProvider: soniox | deepgram | speechmatics | azure | local
        │  sự kiện chung: partial, final, speaker, words[], lang, t_start, t_end
        ▼
  ghi lại mọi sự kiện + audio (để đo lại, mục 7)
        │
Trình duyệt: hiện chữ tạm, câu chốt, nhãn người, độ trễ
```

- **Một giao diện `SttProvider` chung.** Mỗi nhà cung cấp là một adapter nhỏ, chuyển kết quả về cùng dạng sự kiện. Đổi
  nhà cung cấp bằng một tuỳ chọn, không sửa UI.
- **Dùng lại phần thu âm của web hiện tại** (AudioWorklet đã có lọc FIR, xử lý Safari, kiểm "đang nghe"). Đây là phần đã
  chạy ổn qua doc 08.
- **Ghi lại audio và sự kiện của mỗi phiên** (khi bật chế độ đo), để so các nhà cung cấp trên cùng một đoạn audio.

## 6. Tab "Chỉ nghe" trên UI

- **Thanh trên:** nguồn audio (mic / tab), ngôn ngữ (Tiếng Việt / English / Tự nhận), số người dự kiến (1, 2–4, không
  biết), nhà cung cấp (khi đang thử nghiệm), nút Bắt đầu / Dừng.
- **Trạng thái:** đồng hồ mức âm thanh, "đang nghe", độ trễ hiện tại (ms), trạng thái kết nối và số lần nối lại.
- **Vùng chữ:** mỗi câu chốt một dòng, gồm nhãn người nói có màu (S1, S2…), giờ bắt đầu, nhãn ngôn ngữ, chữ. Dòng cuối
  là chữ tạm màu xám. Từ có độ tin cậy thấp được gạch chân nhạt.
- **Thao tác:** đổi tên người nói, sao chép, tải về (TXT, SRT, JSON có thời gian từng từ), tự cuộn và nút "về cuối".
- **Chế độ đo (ẩn):** hiện chữ của hai nhà cung cấp cạnh nhau trên cùng luồng audio, để mắt người so trực tiếp.

## 7. Cách đo để chọn

**Bộ audio:**

1. Tiếng Anh, một người, rõ (podcast, bài giảng).
2. Tiếng Việt, một người, rõ (tin tức, bài giảng).
3. Tiếng Việt, 2–4 người nói chuyện, có xen ngang (họp, talkshow).
4. Tiếng Việt chen từ tiếng Anh (họp công nghệ).
5. Video có nhạc nền hoặc tiếng ồn (vlog, phim).

Mỗi bộ 10–20 phút, có bản chép tay chuẩn kèm nhãn người nói. Có thể làm như golden_1 ở doc 08–09.

**Số đo:**

- WER theo từ cho tiếng Việt và tiếng Anh, sau chuẩn hoá (giữ dấu thanh).
- DER và cpWER cho phần tách người nói.
- Độ trễ: tới chữ tạm đầu tiên, tới câu chốt (p50, p95).
- Độ ổn định: số ký tự đã hiện rồi bị đổi, trên mỗi phút.
- Số câu bịa trong đoạn không có lời.
- Có đứt luồng không trong phiên 1 giờ.

**Thứ tự thử:** Soniox, Deepgram → Speechmatics, Azure → OpenAI, ElevenLabs → tự host (Whisper large-v3 hoặc
PhoWhisper + Sortformer) để biết khoảng cách nếu cần chạy hoàn toàn local.

## 8. Rủi ro

- **Số liệu của nhà cung cấp không đáng tin cho tiếng Việt thật:** các bộ đo công khai chủ yếu là giọng đọc rõ (VIVOS,
  Common Voice). Bộ đo của mình (mục 7) là thứ quyết định.
- **Riêng tư:** dùng dịch vụ online thì mọi âm thanh đi qua máy chủ của họ. Cần quyết trước nếu dùng cho họp nội bộ.
  Speechmatics có bản on-premise; Azure có lựa chọn vùng dữ liệu.
- **Phụ thuộc nhà cung cấp:** giữ lớp `SttProvider` và định dạng sự kiện chung, để đổi được trong một ngày.
- **Tách người nói khi nói chồng:** mọi hệ thống đều kém hơn rõ khi hai người nói cùng lúc. Nên hiển thị là "nhiều
  người" thay vì gán nhầm.
- **Tự host:** Sortformer chính chỉ 4 người, chưa có số đo tiếng Việt. Ghép nhãn người với từng từ phải tự làm.

## 9. Chi tiết phương án tự host mạnh nhất (Mức 2)

Mục này nói rõ Mức 2 chạy thế nào, cấu hình ra sao, tốn bao nhiêu. Các con số độ trễ, VRAM, DER lấy từ tài liệu của
dự án gốc hoặc bài báo, đo trên dữ liệu tiếng Anh; **chưa có số nào cho tiếng Việt**. Nguồn ở mục 14.

### 9.1 Các thành phần

| Phần | Chọn | Vai trò |
|---|---|---|
| Nhận dạng tiếng Anh, câu chen | Whisper large-v3 qua **SimulStreaming** | Nhận dạng trực tiếp, chỉ chốt chữ đã ổn định |
| Nhận dạng tiếng Việt | **ChunkFormer-CTC-Large-Vie** (có phiên streaming, xuất ONNX) hoặc **PhoWhisper-large** | Model chuyên tiếng Việt, đúng chữ hơn Whisper trên các bộ đo chuẩn |
| Tách người nói | NVIDIA **Streaming Sortformer 4spk v2.1** (NeMo) | Mỗi khung 80 ms cho xác suất của 4 "chỗ" người nói, đánh số theo thứ tự xuất hiện |
| Lọc đoạn không lời | Silero VAD (như app hiện tại) | Không gửi đoạn im lặng, nhạc vào Whisper, tránh câu bịa |
| Ghép chữ với người nói | Code tự viết | Gán nhãn người cho từng từ theo thời gian |
| Khung chạy sẵn để thử nhanh | **WhisperLiveKit** | Đã có WebSocket, backend SimulStreaming, `--diarization` dùng Sortformer |

**Số liệu tiếng Việt đã công bố** (WER, càng thấp càng tốt; mỗi bên tự đo, cách chuẩn hoá khác nhau):

| Bộ đo | PhoWhisper-large | ChunkFormer-CTC-Large-Vie |
|---|---|---|
| VIVOS | 4,67 | 4,18 |
| Common Voice vi | 8,14 | 6,66 |
| VLSP 2020 Task 1 | 13,75 | 14,09 |
| VLSP 2020 Task 2 | 26,68 | — |

Đây là giọng đọc, thu sạch. Giọng nói chuyện, nhiều người, có nhạc sẽ kém hơn nhiều: một bộ đo năm 2026 trên dữ liệu
riêng cho WER khoảng 32–34% (cách tính gốc) với cả hai họ model. Whisper large-v3 nhận đoạn tiếng Anh chen trong câu
Việt tốt hơn PhoWhisper (bộ đo ViMedCSS).

### 9.2 Cách hoạt động

```text
Trình duyệt ── PCM16 16 kHz, khung 40 ms ──► Server
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
             Silero VAD               Streaming Sortformer        bộ đệm audio
          (có lời / không)         (80 ms/khung, 4 người)       (ghi lại để đo)
                    │                         │
                    ▼                         │
   Nhận dạng: Whisper large-v3 (SimulStreaming)│
       hoặc ChunkFormer / PhoWhisper (tiếng Việt)
                    │  chữ tạm, chữ chốt, thời gian từng từ
                    ▼                         ▼
             Ghép: mỗi từ lấy người nói chiếm nhiều khung nhất trong khoảng thời gian của từ
                    │
                    ▼
     Sự kiện gửi trình duyệt: partial / final, speaker, words[], lang
```

1. **Nhận dạng trực tiếp với SimulStreaming.** Audio được nạp liên tục vào cửa sổ tối đa 30 s. Sau mỗi khúc mới, Whisper
   giải mã lại, nhưng chính sách **AlignAtt** chỉ cho chốt những từ mà sự chú ý (attention) của model còn nằm cách xa
   cuối bộ đệm. Từ nào model đang "nhìn" sát cuối audio thì chưa chốt, vì còn có thể đổi khi nghe thêm. Cách này thay
   cho LocalAgreement (so khớp giữa hai lần giải mã) của whisper_streaming cũ, có độ trễ thấp hơn.
2. **Tiếng Việt với ChunkFormer.** Model CTC xử lý theo khúc, có ngữ cảnh bên phải. Phiên streaming nhận audio dần dần
   và trả chữ theo khúc. Model CTC thường không bịa câu dài trong đoạn im lặng như Whisper, nhưng thường không có dấu
   câu (cần kiểm).
3. **Tách người nói với Sortformer.** Mỗi khung 80 ms, model trả xác suất cho 4 chỗ người nói. Một bộ nhớ đệm (speaker
   cache) giữ đặc trưng giọng của những người đã gặp, nên S1 vẫn là S1 sau vài phút im lặng. Hai chỗ cùng cao nghĩa là
   hai người nói chồng.
4. **Ghép.** Với mỗi từ có thời gian bắt đầu, kết thúc, lấy người nói chiếm nhiều khung nhất trong khoảng đó. Câu chốt
   lấy người nói của đa số từ. Đổi người giữa câu thì cắt câu tại đó. Nếu hai người cùng cao, hiện nhãn "nhiều người".
5. **Chọn ngôn ngữ.** Người dùng chọn Tiếng Việt hoặc English: đi thẳng vào model tương ứng. Chế độ "Tự nhận": Whisper
   nhận ngôn ngữ từng đoạn, đoạn tiếng Việt đi qua ChunkFormer/PhoWhisper, đoạn tiếng Anh và đoạn trộn đi qua Whisper.

### 9.3 Cấu hình

**SimulStreaming / WhisperLiveKit:**

| Tham số | Giá trị đề xuất ban đầu | Ảnh hưởng |
|---|---|---|
| Model | `large-v3` | README cần GPU từ 10 GB VRAM. CPU chạy được nhưng quá chậm cho trực tiếp |
| `--frame-threshold` (AlignAtt) | 25 (mặc định) | Thấp hơn: chốt sớm hơn, sai nhiều hơn. Cao hơn: chậm hơn, đúng hơn |
| `--beams` | 1, thử thêm 4 | Beam lớn đúng hơn nhưng tốn GPU, tăng độ trễ |
| Prompt | Tên người, tên công ty, thuật ngữ | SimulStreaming hỗ trợ prompt thuật ngữ theo lĩnh vực |
| Ngôn ngữ | Khoá `vi` hoặc `en` khi biết trước | Bớt lỗi nhận nhầm ngôn ngữ |
| `--diarization` | Bật, backend Sortformer | Cần cài NeMo từ git. Diart bị đánh dấu "không khuyên dùng" |

Bài báo của nhóm SimulStreaming (IWSLT 2025) chạy hai mức độ trễ: khoảng **2 s** (thấp) và **4–5 s** (cao).

**Streaming Sortformer v2.1** (bảng trong model card của NVIDIA; độ trễ là kích thước bộ đệm đầu vào, chưa tính thời
gian tính toán; RTF đo trên RTX 6000 Ada, batch 1):

| Chế độ | chunk | right ctx | FIFO | update | cache | Độ trễ | RTF | DER DIHARD III | DER CALLHOME |
|---|---|---|---|---|---|---|---|---|---|
| Độ trễ thấp (đề xuất) | 6 | 7 | 188 | 144 | 188 | 1,04 s | 0,093 | 19,60 | 11,31 |
| Độ trễ rất cao | 340 | 40 | 40 | 300 | 188 | 30,4 s | 0,002 | 19,09 | 10,32 |

Ở bản v2 còn có chế độ 0,32 s (DER DIHARD III 19,85). Độ trễ 1,04 s chỉ kém chế độ 30 s khoảng 0,5 điểm DER, nên dùng
được cho tab trực tiếp. RTF 0,093 nghĩa là 1 giây audio tốn khoảng 0,09 giây GPU.

**Ngân sách độ trễ:** chữ chốt đến sau khoảng 2 s (SimulStreaming), nhãn người nói đến sau khoảng 1,1 s (Sortformer).
Nhận dạng là phần chậm nhất, nên nhãn người nói có sẵn khi câu chốt tới. Chữ tạm hiện sớm hơn, khoảng dưới 1 s, nhưng
chưa có nhãn.

**Phần cứng:**

- **Tối thiểu cho 1 luồng:** 1 GPU 24 GB (L4, RTX 4090, A10). Whisper large-v3 cần từ 10 GB theo README, còn lại cho
  Sortformer, ChunkFormer, VAD và bộ đệm.
- **GPU 8 GB của server hiện tại không đủ** cho large-v3 cùng Sortformer theo mức tối thiểu 10 GB của README.
- **Nhiều luồng cùng lúc:** L40S 48 GB hoặc A100 80 GB. Phải đo số luồng thật, vì SimulStreaming giải mã lại liên tục và
  tốn GPU hơn nhận dạng theo câu.

**Phần mềm:** Python, PyTorch CUDA, NVIDIA NeMo (bản git), SimulStreaming hoặc WhisperLiveKit, gói `chunkformer`.
PhoWhisper có checkpoint dạng Hugging Face; muốn chạy trong SimulStreaming phải chuyển sang định dạng `.pt` của
openai-whisper. Bước này chưa được kiểm.

### 9.4 Chi phí

Theo yêu cầu không xét chi phí khi chọn, nhưng ghi lại để so.

**Thuê GPU theo giờ** (giá on-demand năm 2026 từ các trang so sánh, không phải bảng giá chính thức; thay đổi theo vùng):

| GPU | Neocloud (RunPod, Lambda…) | Hyperscaler (AWS, GCP, Azure) |
|---|---|---|
| L4 24 GB | 0,20–0,50 USD/giờ | từ 0,71 USD/giờ (GCP G2) |
| L40S 48 GB | 0,92–0,99 USD/giờ | 1,20–2,50 USD/giờ |
| A100 80 GB | 1,39–1,49 USD/giờ | 3,67–5,03 USD/giờ |
| H100 80 GB | 2,64–3,99 USD/giờ | 6,88–12,29 USD/giờ |

- **Chạy liên tục 24/7:** một L4 trên GCP khoảng 0,71 × 24 × 30 ≈ **510 USD/tháng**, một L40S trên neocloud khoảng
  **700 USD/tháng**. Giá trên mỗi giờ nghe bằng giá GPU chia cho số luồng chạy cùng lúc.
- **So với dịch vụ online:** Soniox công bố khoảng 0,12 USD cho mỗi giờ nghe tiếng Việt trực tiếp. Ở mức đó, tự host chỉ
  rẻ hơn khi rất nhiều luồng chạy cùng lúc, hoặc khi đã có sẵn máy.
- **Máy riêng:** chỉ tốn phần cứng một lần và điện, không tính theo giờ nghe.
- **Chi phí lớn nhất là công làm:** ghép nhận dạng với tách người nói, chọn model theo ngôn ngữ, chỉnh độ trễ, xử lý câu
  bịa và đứt luồng, làm bộ đo. Ước tính 2–4 tuần cho bản dùng được, chưa tính tối ưu nhiều luồng. Đây là ước tính, chưa
  có số đo.

### 9.5 Cách thử, theo thứ tự

1. **Chạy WhisperLiveKit nguyên bản** trên 1 GPU 24 GB: backend SimulStreaming, `large-v3`, bật `--diarization` với
   Sortformer. Đưa 5 bộ audio ở mục 7 qua, đo WER, DER, độ trễ.
2. **Thay phần tiếng Việt:** chạy ChunkFormer streaming (và PhoWhisper nếu chuyển được định dạng) trên cùng audio tiếng
   Việt, so WER với Whisper large-v3.
3. **Đo Sortformer với giọng Việt:** bộ 3 (2–4 người) ở mục 7, so DER với số tiếng Anh ở bảng trên.
4. **So với Soniox, Deepgram** trên cùng audio. Chỉ giữ Mức 2 nếu chữ tiếng Việt không kém rõ, hoặc khi buộc phải chạy
   local vì riêng tư.

### 9.6 Rủi ro riêng của Mức 2

- **Giấy phép:** WhisperLiveKit ghi SimulStreaming theo giấy phép kép; phải kiểm trước khi dùng cho sản phẩm. Kiểm thêm
  giấy phép của PhoWhisper, ChunkFormer, model Sortformer.
- **Tối đa 4 người** ở bản Sortformer chính. Người thứ năm sẽ bị gán vào một trong 4 chỗ.
- **Chưa có số cho tiếng Việt** ở cả Sortformer lẫn SimulStreaming.
- **NeMo cài từ git:** dễ vỡ khi cập nhật; nên đóng băng phiên bản trong Docker image.
- **Whisper vẫn bịa câu** ở đoạn nhạc, im lặng. Vẫn cần VAD và bộ lọc như app hiện tại (doc 08 §3.3).
- **GPU hiện có 8 GB không đủ:** cần GPU mới hoặc thuê cloud trước khi thử.

## 10. Kế hoạch trước mắt: app hiện tại, một chiều, một người nói, một phiên

**Mục tiêu:** chữ hiện ra đúng nhất có thể khi một người nói liên tục bằng tiếng Việt hoặc tiếng Anh, trong một phiên.
Giữ nguyên kiến trúc hiện tại: web thu âm → WebSocket → Silero VAD + segmenter → faster-whisper. Chưa làm tách người nói
(việc 3) và tab UI mới (việc 4); hai việc này để sau khi có số đo.

**Vì sao app hiện tại thua các phương án ở mục 3:**

- GPU 8 GB đang chia cho model dịch Qwen2.5-7B Q5_K_M (khoảng 5,4 GB), nên phần nghe chỉ dùng được large-v3-turbo int8.
- Một model cho mọi ngôn ngữ, chưa có model chuyên tiếng Việt.
- Mọi lần chỉnh trước đây (doc 07–09) đều đo trên một video phim tiếng Nhật (golden_1). Chưa có số nào cho tiếng Việt
  hay tiếng Anh.

**Cập nhật 2026-10-15: đã làm bước B, C và phần chấm WER của bước A**, có test. Chưa chạy trên GPU thật, chưa có số.

- **Profile `listen`** ([`packs/profiles/listen.yaml`](../packs/profiles/listen.yaml)): `mt.engine: none`, tiếng Việt
  dùng `phowhisper-large-ct2`, tiếng Anh dùng `large-v3-turbo`, `int8_float16`.
  - Server không tạo bộ dịch; session chỉ gửi chữ nhận dạng. API `/v1/translate` trả 503.
  - [`LanguageRoutedAsrEngine`](../ai/src/rvt_ai/engines/asr_routed.py) nạp mọi model lúc khởi động và chọn model theo
    ngôn ngữ khoá của phiên. Thiếu thư mục PhoWhisper thì tiếng Việt tạm dùng large-v3-turbo, có cảnh báo trong log.
  - `RVT_ASR_FINAL_BEAM_SIZE` (mặc định 1) đặt beam cho câu chốt, để thử ở bước D.
  - Web nhận `models.mt = "none"` trong `session.ready` và hiện chữ gốc thay cho "… đang dịch".
- **Chạy** (trên máy GPU):

  ```bash
  ./scripts/prepare_listen_models.sh   # Silero VAD, PhoWhisper-large → CTranslate2, large-v3-turbo
  ./start.sh --listen --build          # chỉ container ai và web, không có container dịch
  ./scripts/remove_unused_models.sh    # liệt kê model không dùng (Qwen .gguf, model Whisper cũ)
  ./scripts/remove_unused_models.sh --yes
  ```

  Trên web: khoá nửa A là Tiếng Việt hoặc English, rồi bật mic. `prepare_listen_models.sh` cần `uv` trên máy và mạng
  tới Hugging Face; lần đầu tải torch CPU và PhoWhisper (khoảng 3 GB). Chưa chạy thử được ở đây.
- **Bộ đo:** [`eval/wer.py`](../eval/wer.py) tính WER theo từ và CER, giữ dấu thanh. `golden_session.py` tự thêm `wer`,
  `cer` khi `--side-lang vi` hoặc `en`, và dùng được profile `listen`. Còn thiếu chính bộ audio có bản chép tay (bộ 1,
  bộ 2): xem danh sách nguồn ở mục 10.2 và `eval/fetch_golden.py`.
- **Chưa làm:** Parakeet-CTC-0.6B Vietnamese (mục 11.1) cần NeMo và một engine mới; làm sau khi có số của PhoWhisper.
- **Giấy phép PhoWhisper:** file LICENSE trong repo GitHub VinAIResearch/PhoWhisper là BSD 3-Clause (Copyright 2024
  VinAI). Model card trên Hugging Face chưa đọc được trực tiếp. PhoWhisper fine-tune từ Whisper (MIT). README yêu cầu
  trích dẫn bài báo khi dùng để công bố kết quả hoặc đưa vào phần mềm khác.

### 10.1 Thứ tự làm

| Bước | Việc | Thay đổi | Xong khi |
|---|---|---|---|
| A | Bộ đo tiếng Việt, tiếng Anh (một người) | eval | Có WER, CER, độ trễ của bản hiện tại trên 2 bộ audio |
| B | Chế độ chỉ nghe: không nạp, không gọi model dịch | server, cấu hình | GPU chỉ còn phần nghe; số ở bước A không giảm |
| C | Tiếng Việt dùng PhoWhisper-large; tiếng Anh giữ large-v3-turbo hoặc thử large-v3 | server, model | WER tiếng Việt giảm rõ so với bước A |
| D | Chỉnh tham số cho một người nói (mục 10.4) | cấu hình | Mỗi thay đổi được giữ chỉ khi WER giảm mà độ trễ không tăng quá mức đặt ra |
| E (song song) | Đo Soniox, Deepgram trên cùng 2 bộ audio | eval | Có mốc chữ tốt nhất để so với bước C, D |

Bước A làm trước vì mọi bước sau đều cần số để biết có lợi hay không. Đây là thứ tự đã chọn (việc 1, 2, 5 ở trao đổi
ngày 2026-10-14), chỉ đổi lên làm bộ đo trước.

### 10.2 Bước A — Bộ đo một người nói

- **Bộ 1:** tiếng Anh, một người, 10–20 phút (podcast, bài giảng), có bản chép tay do người làm, không dùng phụ đề tự
  động.
- **Bộ 2:** tiếng Việt, một người, 10–20 phút (tin tức, bài giảng), cũng có bản chép tay chuẩn.
- Nên có thêm một đoạn ngắn đọc qua mic thật ở khoảng 1–2 m, vì đó là cách người dùng sẽ nói.
- **Số đo:**
  - WER theo từ, sau chuẩn hoá chữ thường và bỏ dấu câu, **giữ dấu thanh** tiếng Việt. Thêm CER để so với các số cũ.
  - Độ trễ: tới chữ tạm đầu tiên, tới câu chốt (p50, p95).
  - Độ ổn định: số ký tự đã hiện bị sửa trên mỗi phút.
  - Số câu bịa (chữ hiện ra ở đoạn không có lời).
- **Công cụ:** `eval/golden_session.py` đã chạy cả phiên theo đồng hồ ảo, nhận `--side-lang vi` hoặc `en`. Phần chấm
  hiện dùng CER theo ký tự (dành cho tiếng Nhật), cần thêm WER cho tiếng Việt và tiếng Anh.

**Nguồn audio có bản chép tay do người làm** (cập nhật 2026-10-15). YouTube dùng được, với một điều kiện: video phải
có **phụ đề do người tải lên**, không phải phụ đề tự động. Phụ đề tự động là đầu ra của một model nhận dạng khác, không
dùng làm đáp án được. [`eval/fetch_golden.py`](../eval/fetch_golden.py) kiểm điều này, tải audio cùng phụ đề người làm,
và dừng nếu chỉ có phụ đề tự động:

```bash
uv run --no-project --with yt-dlp python eval/fetch_golden.py URL --list            # xem có phụ đề người làm không
uv run --no-project --with yt-dlp python eval/fetch_golden.py URL --lang vi --name golden_vi_1
```

Script cũng nhận link ted.com. Audio không commit (`eval/.gitignore`); phụ đề, `url.txt`, `source.json` thì commit.
Chưa chạy được ở đây vì sandbox không vào được YouTube, TED. Sau khi tải, nên nghe lại vài đoạn để chắc phụ đề khớp lời.

| Bộ | Ứng viên | Độ dài | Bản chép tay | Giấy phép, ghi chú |
|---|---|---|---|---|
| 1 · Tiếng Anh | TED "Inside the mind of a master procrastinator" (Tim Urban) | khoảng 14 phút | Bản ghi của TED, trên ted.com và kênh YouTube TED | TED: CC BY-NC-ND (chỉ dùng phi thương mại, không sửa) |
| 1 · Tiếng Anh | TED "The power of vulnerability" (Brené Brown) | khoảng 20 phút | Như trên | Như trên |
| 1 · Tiếng Anh, dự phòng | TED-LIUM 3, phần test dài (11 bài TED nguyên bài) | mỗi bài 10–20 phút | Chép tay, dùng làm bộ đo dài trong các bài báo | CC BY-NC-ND 3.0, tải ở OpenSLR 51 |
| 2 · Tiếng Việt (ưu tiên) | Bài TED của Trần Văn Phúc, `https://www.ted.com/talks/van_phuc_tr_n_di_b…` (link chưa đầy đủ) | chưa rõ | Người dùng xác nhận nói 100% tiếng Việt; chạy `--list` để kiểm có transcript tiếng Việt do người làm | Như TED |
| 2 · Tiếng Việt | TEDxUAH "Viết mới biết" (Huỳnh Vĩnh Sơn, 2022) | khoảng 20 phút | Có trang transcript trên ted.com; phải kiểm đó là bản tiếng Việt (một nguồn cho thấy bản tiếng Anh) | Như TED; có chen từ tiếng Anh |
| 2 · Tiếng Việt | TEDxHoangMinhGiamSt "Tại sao người cao tuổi lại là đại dương xanh ở Việt Nam?" (2022) | chưa rõ | Transcript tiếng Việt trên ted.com | Như TED |
| 2 · Tiếng Việt, dự phòng | VietMed (hội thoại y khoa) | 16 giờ có nhãn | Chép tay | CC BY 4.0; lĩnh vực hẹp |
| 2 · Tiếng Việt, dự phòng | FLEURS tiếng Việt, ghép các câu test thành 10–15 phút | câu ngắn | Chép tay | Giọng đọc, không phải nói tự nhiên; giấy phép cần kiểm trên model card |
| 2 · Tiếng Việt, dự phòng | VLSP 2020/2021 | — | Chép tay | Phải đăng ký, chỉ dùng nghiên cứu |

Ghi chú:
- Bản ghi TEDx do tình nguyện viên làm và có người duyệt trước khi đăng. Chương trình TED Translators đang tạm dừng để
  chuyển sang CaptionHub, nên một số bài có thể chưa có transcript.
- Kênh TEDx trên YouTube thường chỉ có phụ đề tự động, nên tải qua link ted.com hoặc chạy `--list` để kiểm trước.
- Tải video YouTube có thể trái điều khoản của YouTube. Chỉ dùng để đo nội bộ, ưu tiên video TED hoặc video gắn giấy
  phép Creative Commons.

### 10.3 Bước B, C — Chế độ chỉ nghe và model theo ngôn ngữ

- **Chỉ nghe:** phiên không có ngôn ngữ đích thì không gọi bộ dịch. Server khởi động không có container `mt`, nên GPU
  chỉ còn faster-whisper và Silero VAD.
- **Khoá ngôn ngữ cho phiên:** người dùng chọn Tiếng Việt hoặc English. Không tự nhận ngôn ngữ, vì với một người nói
  một phiên thì việc này chỉ thêm rủi ro nhận nhầm.
- **Tiếng Việt: PhoWhisper-large.** Cùng kiến trúc Whisper, nên chuyển được sang CTranslate2 và chạy bằng
  `FasterWhisperEngine` hiện có:

  ```bash
  ct2-transformers-converter --model vinai/PhoWhisper-large --output_dir models/phowhisper-large-ct2 \
      --quantization int8_float16
  ```

  Chưa chạy thử ở đây. Phải kiểm: file tokenizer có đủ không, VRAM, tốc độ mỗi lượt nhận dạng (PhoWhisper-large không
  có bản turbo, nên chậm hơn large-v3-turbo).
- **Tiếng Anh:** giữ large-v3-turbo. Khi đã bỏ model dịch, thử thêm large-v3 (không turbo) và so trên bộ 1.
- **Phương án dự phòng cho tiếng Việt:** ChunkFormer-CTC-Large-Vie. Cần thêm một engine mới (CTC, không phải Whisper),
  nên chỉ làm nếu PhoWhisper không đạt.

### 10.4 Bước D — Chỉnh cho một người nói

Mỗi mục là một phép thử riêng, đo bằng bước A, giữ khi có lợi:

| Thử | Lý do | Rủi ro |
|---|---|---|
| Đoạn dài hơn: `max_ms` 4 000 → 6 000–8 000 ms | Một người nói liền; Whisper đúng hơn khi có nhiều ngữ cảnh, ít cắt giữa từ | Câu chốt đến muộn hơn |
| `beam_size` 5 cho câu chốt (chữ tạm giữ 1) | Đã bỏ model dịch nên GPU còn dư. Trên golden_1 tiếng Nhật không có lợi (doc 09 §4.3), nhưng giọng rõ một người có thể khác | Chậm hơn mỗi lượt |
| Prompt ngữ cảnh 2 câu trước (đã có) cộng danh sách tên riêng của phiên | Tên người, tên công ty, thuật ngữ | Trên golden_1 có thêm câu bịa (doc 09 §4.2); phải đo lại |
| Ngưỡng VAD cho mic 1–2 m | Ngưỡng 0,4/0,25 hiện tại chọn cho tiếng Nhật trong phim | Bắt nhầm tiếng ồn |
| Sửa lại sau (two-pass): sau mỗi 15–20 s, nhận dạng lại cả đoạn với beam lớn, thay các câu chốt gần nhất | Lượt dài hơn, nhiều ngữ cảnh hơn thì đúng hơn | Chữ đã chốt vẫn đổi; UI cần đánh dấu câu đã sửa |

### 10.5 Bước E — Mốc so sánh online

- Gửi đúng audio của bộ 1, 2 qua luồng trực tiếp của Soniox và Deepgram, chấm bằng cùng cách ở bước A.
- Không cần sửa app: một script đo riêng, gửi audio theo nhịp thời gian thật như `scripts/replay_ws.py`.
- **Quy tắc quyết định (đề xuất):** nếu WER tiếng Việt của bản local sau bước C, D kém mốc online tốt nhất quá vài điểm
  tuyệt đối, cân nhắc dùng online cho tiếng Việt. Ngưỡng cụ thể chốt sau khi thấy số ở bước A.

### 10.6 Chưa làm ở giai đoạn này

- Tách người nói, nhãn S1, S2 (việc 3).
- Tab "Chỉ nghe" mới (việc 4). Trước mắt dùng màn hình hiện tại, khoá nửa A theo ngôn ngữ cần đo, không chọn ngôn ngữ
  đích.
- Lớp `SttProvider` trong app (việc 6). Bước E chỉ cần script đo, chưa cần cắm vào app.
- GPU 24 GB, SimulStreaming, Sortformer (mục 9).

## 11. Lộ trình theo hạ tầng: chỉ phần nghe, một người nói, độ chính xác cao nhất

Giả định: chế độ chỉ nghe, không chạy model dịch, cả GPU dành cho phần nghe. Các con số VRAM là ước tính từ số tham số,
**phải đo lại** trên máy thật. Thứ hạng trên bảng xếp hạng chỉ là điểm xuất phát; quyết định theo bộ đo của mình (mục
10.2).

### 11.1 VRAM 8 GB (GPU hiện tại)

| Ngôn ngữ | Ứng viên | Ghi chú |
|---|---|---|
| Tiếng Việt | **Parakeet-CTC-0.6B Vietnamese** (NVIDIA) | Huấn luyện trên hơn 4 000 giờ tiếng Việt, có dấu câu và thời gian từng từ, kèm n-gram LM (KenLM). Trên Vietnamese Open ASR Leaderboard, phần bảng xem được: O-WER trung bình 13,39, thấp nhất trong các dòng hiển thị (PhoWhisper-medium 17,98, Qwen3-ASR-1.7B 20,45). Chạy bằng NeMo, cần thêm engine mới. Giấy phép NVIDIA Community Model License |
| Tiếng Việt | **PhoWhisper-large** qua CTranslate2 | Dùng được engine hiện có (mục 10.3) |
| Tiếng Việt | ChunkFormer-CTC-Large-Vie | Dự phòng; cần engine CTC |
| Tiếng Anh | Whisper large-v3 hoặc large-v3-turbo (int8_float16) | Đang dùng turbo |
| Tiếng Anh | Parakeet-TDT-0.6B (NVIDIA) | Nhanh; một nguồn năm 2026 xếp nó đứng đầu trung bình WER, các nguồn khác xếp sau Cohere, IBM |

Cách chạy: như app hiện tại (VAD cắt đoạn, chữ tạm 800 ms – 1,2 s, câu chốt), cộng các phép thử ở mục 10.4. Khoá ngôn
ngữ theo phiên, chỉ nạp model của ngôn ngữ đó.

### 11.2 VRAM 24 GB (L4, RTX 4090, A10)

- **Hai tầng model:** model nhanh cho chữ tạm (Parakeet, turbo), model chính xác hơn cho câu chốt.
- **Tiếng Anh, câu chốt:** các model đầu bảng Open ASR Leaderboard (mức WER trung bình khoảng 5,3–5,6%, cách nhau dưới
  một điểm): **Granite Speech 4.1 2B** (IBM), **Cohere Transcribe 2B**, **Canary-Qwen-2.5B** (NVIDIA). Đều là encoder
  Conformer cộng bộ giải mã LLM, chính xác hơn nhưng chậm hơn CTC/TDT. Phải kiểm giấy phép và tốc độ trên mỗi câu.
- **Tiếng Việt:** chạy song song hai model (ví dụ Parakeet-vi và PhoWhisper-large), chọn hoặc gộp kết quả câu chốt (gộp
  kiểu ROVER, hoặc chấm lại bằng n-gram LM tiếng Việt). Lợi ích phải đo; không có số công bố cho tiếng Việt.
- **Nghe trực tiếp mượt hơn:** SimulStreaming với Whisper large-v3 (cần từ 10 GB) cho chế độ trộn Anh–Việt.
- **Sửa lỗi bằng LLM (thử nghiệm):** một LLM 7–8B lượng tử 4-bit sửa dấu câu, chữ hoa, tên riêng theo danh sách của
  phiên, dựa trên vài câu trước. Các nghiên cứu "generative error correction" cho thấy giảm WER, nhưng chưa có số riêng
  cho tiếng Việt, và LLM có thể đổi đúng thành sai. Chỉ cho sửa dấu câu, chữ hoa và tên trong danh sách, giữ bản gốc để
  so.

### 11.3 VRAM 32 GB (RTX 5090)

Như 24 GB, cộng:

- LLM sửa lỗi lớn hơn (khoảng 14B, 4-bit) và vẫn đủ chỗ cho hai model nghe.
- **Fine-tune ngay trên máy** các model 0,6–1,5B (Parakeet-vi, PhoWhisper, Whisper) bằng LoRA trên dữ liệu của mình. Đây
  là bước tăng độ chính xác lớn nhất có thể làm local (mục 12).

### 11.4 VRAM 48–80 GB (L40S, A100, H100)

- **Fine-tune đầy đủ** Whisper large-v3 hoặc PhoWhisper-large trên vài trăm giờ dữ liệu cùng lĩnh vực.
- Chạy nhiều model cùng lúc để gộp kết quả, LLM sửa lỗi cỡ lớn, nhiều phiên song song.
- Model audio-LLM đa ngôn ngữ như Qwen3-ASR (0,6B và 1,7B, 52 ngôn ngữ). Trên bảng tiếng Việt kể trên, Qwen3-ASR-1.7B
  kém Parakeet-vi và PhoWhisper, nên không ưu tiên cho tiếng Việt.

### 11.5 Online API (mức cao nhất, không cần GPU)

| Thứ tự thử | Dịch vụ | Lý do |
|---|---|---|
| 1 | **Soniox** (`stt-rt-v5`) | Công bố WER tiếng Việt 5,4%, tiếng Anh 6,5%, trực tiếp dưới 200 ms (số tự công bố) |
| 2 | **Deepgram** (Nova-3) | Có trang riêng cho tiếng Việt trực tiếp, dưới 300 ms |
| 3 | OpenAI `gpt-4o-transcribe` / `gpt-realtime-whisper`, Azure, Speechmatics, ElevenLabs | Một người nói thì không cần tách người, nên nhóm này cũng dùng được; chất lượng tiếng Việt phải đo |

Với một người nói, tiêu chí tách người nói ở mục 3 không còn quan trọng, nên nhóm 3 trở thành ứng viên ngang hàng. Chọn
theo WER trên bộ 1, 2 (mục 10.2).

**Bảng tổng hợp:**

| Hạ tầng | Tiếng Việt | Tiếng Anh | Kỹ thuật thêm | Công làm |
|---|---|---|---|---|
| 8 GB | Parakeet-vi hoặc PhoWhisper-large | large-v3 / turbo | Khoá ngôn ngữ, beam 5 câu chốt, đoạn dài hơn, two-pass | Nhỏ–vừa |
| 24 GB | Hai model, gộp kết quả | Granite / Cohere / Canary cho câu chốt | Hai tầng model, SimulStreaming, LLM sửa dấu câu và tên | Vừa |
| 32 GB | Như trên, fine-tune LoRA | Như trên | LLM sửa lỗi lớn hơn | Vừa–lớn |
| 48–80 GB | Fine-tune đầy đủ | Fine-tune đầy đủ | Gộp nhiều model | Lớn |
| Online | Soniox, Deepgram | Soniox, Deepgram, OpenAI | Danh sách từ khoá của dịch vụ | Nhỏ |

## 12. Kỹ năng và cách làm để đạt gần mức online

**Không cần "AI agent" để tăng độ chính xác.** Độ chính xác đến từ bốn thứ: model, dữ liệu, bộ đo và chất lượng audio
đầu vào. Agent không thay được thứ nào trong đó.

**Các dịch vụ online có lợi thế gì:** dữ liệu gán nhãn rất lớn, huấn luyện lại liên tục, model viết riêng cho chế độ
trực tiếp, và đội ngũ chuyên làm việc này. Với tiếng Việt nói chung, khó vượt họ bằng model công khai. Nhưng trong **một
lĩnh vực hẹp** (cùng kiểu người nói, cùng thuật ngữ), model nhỏ fine-tune trên dữ liệu của mình có thể bằng hoặc hơn. Ví
dụ: VietASR báo cáo đạt chất lượng ngang công nghiệp chỉ với 50 giờ tiếng Việt có nhãn, cộng tiền huấn luyện trên lượng
lớn audio không nhãn. Đây là đánh giá, phải kiểm bằng bộ đo.

**Kỹ năng cần, theo thứ tự quan trọng:**

1. **Đo lường:** làm bộ đo (bản chép tay chuẩn), tính WER đúng cách cho tiếng Việt, chạy lại tự động sau mỗi thay đổi.
   Không có bước này thì mọi thay đổi đều là đoán.
2. **Audio đầu vào:** mức thu, AGC, giảm ồn, chọn ngưỡng VAD, xử lý mic xa. Lỗi ở đây không model nào sửa được.
3. **Phục vụ model:** NeMo, CTranslate2, có thể TensorRT; quản lý VRAM; chế độ trực tiếp (cắt đoạn, chữ tạm, chốt câu).
4. **Dữ liệu:** thu và gán nhãn 50–500 giờ audio đúng lĩnh vực; quy chuẩn chép tay (số, từ tiếng Anh, tên riêng).
5. **Fine-tune:** LoRA hoặc fine-tune đầy đủ cho Whisper, Parakeet; tránh model quên kiến thức chung.
6. **LLM sửa lỗi có rào chắn:** chỉ cho sửa những gì được phép, luôn so với bản gốc.

**AI giúp được ở đâu:**

- **Agent viết code** (như Claude Code): viết nhanh engine mới, script đo, script fine-tune, chạy thử nghiệm hàng loạt.
  Tăng tốc độ làm, không tăng độ chính xác của model.
- **Model mạnh chép nháp dữ liệu:** dùng dịch vụ online tốt nhất chép nháp audio của mình, rồi người sửa lại. Cách này
  làm dữ liệu fine-tune và bộ đo nhanh hơn nhiều so với chép tay từ đầu. Cần kiểm điều khoản dịch vụ khi dùng kết quả để
  huấn luyện.
- **LLM sửa lỗi sau nhận dạng:** là một kỹ thuật trong pipeline (mục 11.2), không phải agent.

**Nhân lực tối thiểu:** một người làm ML/speech (đo, phục vụ model, fine-tune), một người backend/web, ngân sách gán
nhãn dữ liệu.

## 13. Dịch video/họp: nghe trên GPU 8 GB, dịch bằng GPT-5 mini qua Azure

**Cập nhật 2026-10-27.** Chế độ "Video & Họp" vẫn cần dịch. Thay vì chạy Qwen2.5-7B trên cùng GPU, bản dịch gọi một
deployment GPT-5 mini (ví dụ `gpt-5.4-mini`) trên Azure. Profile mới: `api-mt`.

### 13.1 Tiết kiệm được gì

- **VRAM:** không còn container `mt`. Qwen2.5-7B Q5_K_M nặng 5,44 GB, cộng KV cache khoảng 0,47 GB với `-c 8192` và
  phần CUDA của llama.cpp (chưa đo). Tổng cộng giải phóng khoảng 6 GB.
- GPU 8 GB khi đó chỉ chạy phần nghe như profile `listen`: PhoWhisper-large cho nửa khoá tiếng Việt, large-v3-turbo
  cho tiếng Nhật, tiếng Anh và chế độ "Tự động". Hai model này ở `int8_float16` ước tính vừa 8 GB; đo lại bằng
  `nvidia-smi`.
- Cũng xoá được file Qwen: `./scripts/remove_unused_models.sh --yes`.

**Đổi lại:**
- **Mạng:** mỗi câu một lượt gọi API qua Internet.
- **Chi phí:** tính theo token.
- **Dữ liệu ra ngoài:** chữ của cuộc họp đi tới Azure. Audio vẫn ở trong máy.
- **Lọc nội dung:** Azure có thể chặn một số câu (phim có cảnh bạo lực…), khi đó thẻ hiện "[Lỗi dịch vi]".

### 13.2 Cách chạy

```bash
# .env ở thư mục dự án (git bỏ qua file này). Dán nguyên "Target URI" của deployment, trong ngoặc kép vì có dấu "?"
RVT_MT_API_URL="https://<resource>.cognitiveservices.azure.com/openai/deployments/gpt-5.4-mini/chat/completions?api-version=2024-12-01-preview"
RVT_MT_API_KEY=<khoá, chỉ đặt khi chạy>
```

```bash
./scripts/prepare_listen_models.sh     # PhoWhisper-large, large-v3-turbo, Silero VAD (nếu chưa có)
./start.sh --api-mt --build            # container ai + web, không có container Qwen
./scripts/remove_unused_models.sh      # xem trước; thêm --yes để xoá Qwen và model Whisper cũ
```

- **OpenAI trực tiếp:** `RVT_MT_API_URL=https://api.openai.com/v1` và `RVT_MT_MODEL=gpt-5-mini`.
- **Azure kiểu v1:** `RVT_MT_API_URL=https://<resource>.openai.azure.com/openai/v1` và `RVT_MT_MODEL=<tên deployment>`.
- `start.sh` đọc `.env` ở thư mục dự án và cảnh báo nếu thiếu URL hoặc khoá.
- Log của container `ai` có dòng `MT via azure API: model=…, reasoning_effort=…` để kiểm.

### 13.3 Engine gọi API thế nào

[`mt_llama.py`](../ai/src/rvt_ai/engines/mt_llama.py) dùng chung prompt, glossary, ngữ cảnh 2 câu trước, bộ kiểm và
bước dịch lại như khi dùng Qwen.

- **URL và khoá:**
  - URL có `/chat/completions` (Target URI của Azure) được dùng nguyên, kể cả `api-version`.
  - Tên deployment lấy từ đường dẫn; khoá gửi qua header `api-key`.
  - Với OpenAI, khoá đi qua `Authorization: Bearer`.
- **Chỉ gửi tham số model GPT-5 nhận:** không gửi `temperature`, `top_p`, `max_tokens`, `stop`. Có
  `max_completion_tokens` (giới hạn tính cả token suy luận) và `reasoning_effort`.
- **Mức suy luận** (`RVT_MT_REASONING_EFFORT=auto`) đoán theo tên model:
  - `gpt-5.4-mini` và các bản 5.1 trở đi dùng `none`. Đây là giá trị thấp nhất, cũng là mặc định của các bản này; có một
    báo cáo cho rằng `max_completion_tokens` làm `none` bị bỏ qua, nên khi dùng `none` thì không gửi giới hạn.
  - `gpt-5-mini` dùng `minimal`; mặc định của bản này là `medium`, chậm.
  - Model khác: không gửi.
  - Đặt tên deployment khác kiểu này thì ghi rõ giá trị trong `RVT_MT_REASONING_EFFORT`.
- **Tự sửa khi bị từ chối:** API trả lỗi 400 chỉ đúng một tham số không nhận thì engine bỏ tham số đó, hoặc đổi
  `reasoning_effort` sang giá trị mà thông báo lỗi liệt kê, rồi gửi lại. Các lượt sau không gửi sai nữa. Lỗi khác (sai
  khoá, lọc nội dung) không gửi lại.
- **Chỉ lấy dòng đầu:** không có chuỗi dừng, nên engine thôi đọc ở cuối dòng đầu tiên. Ghi chú thừa của model không hiện
  ra, và câu chốt không phải chờ model viết hết.
- **Thời gian chờ:** 20 s (`RVT_MT_TIMEOUT_SEC`), thay vì 5 s như với llama.cpp trong máy.

### 13.4 Sửa hai lỗi thấy trong ảnh chụp

Ảnh chụp chế độ Video & Họp ngày 2026-10-27: nửa nói khoá "日本語", nhưng người nói tiếng Việt.

1. **Nhãn sai, dịch tiếng Việt sang tiếng Việt.** Whisper bị ép tiếng Nhật vẫn chép ra tiếng Việt ("Vì cái đó nó tiểu
   như so với phần mềm…"). Thẻ ghi "JA 100%", và bộ dịch viết lại câu ("tiểu như" → "nhỏ hơn").
   - Nay chữ nhận dạng mâu thuẫn hẳn với ngôn ngữ đã khoá thì tin vào chữ
     ([`correct_language`](../ai/src/rvt_ai/pipeline/lid_policy.py)):
     - có chữ Nhật thì là tiếng Nhật;
     - có dấu tiếng Việt thì là tiếng Việt;
     - chữ Latin không dấu thì là tiếng Anh, nhưng nếu nửa đó khoá tiếng Việt thì giữ nguyên.
   - Câu tiếng Việt khi đó được ghi "VI" và không đem dịch sang tiếng Việt nữa.
2. **Câu không có chữ cũng đem dịch.** "2" thành "Được rồi.". Nay câu không có chữ cái thì không dịch, thẻ hiện nguyên
   câu.

Với cuộc họp có cả người Nhật lẫn người Việt, nên đặt **Nói: Tự động, Dịch sang: Tiếng Việt**. Câu tiếng Nhật sẽ được
dịch, câu tiếng Việt hiện nguyên văn. Để "日本語" thì nay vẫn đúng nhờ bước 1, nhưng tiếng Việt khi đó do large-v3-turbo
nghe, không phải PhoWhisper.

### 13.5 Chi phí và độ trễ (ước tính, chưa đo)

**Giả định:**

- Mỗi câu gửi khoảng 600–900 token: hướng dẫn, ví dụ, glossary, 2 câu trước kèm bản dịch. Một câu họp mẫu khoảng
  1 700 ký tự.
- Bản dịch khoảng 30 token.
- Video dày thoại như golden_1 có khoảng 900 câu mỗi giờ; cuộc họp thường ít hơn.

**Chi phí mỗi giờ, cho một ngôn ngữ đích:**

| Model | Giá (USD / 1 triệu token, vào / ra) | Chi phí mỗi giờ |
|---|---|---|
| gpt-5-mini | 0,25 / 2,00 (trang tổng hợp, theo bảng giá OpenAI) | khoảng 0,2–0,3 USD |
| gpt-5.4-mini | 0,75 / 4,50 (trang tổng hợp) | khoảng 0,5–0,7 USD |

Giá Azure có thể khác theo vùng và kiểu deployment; kiểm trên bảng giá Azure.

**Độ trễ:** chưa có số; phụ thuộc vùng Azure và tải của deployment. Đo bằng bộ đo dịch, xem `latency_p50_s` và
`latency_p95_s`. Container `ai` đã có sẵn URL và khoá, nên không cần truyền lại:

```bash
docker exec -it rvt_ai uv run python eval/mt_eval.py --golden eval/golden_1 --label gpt-5.4-mini \
    --out /tmp/mt_api.json
```

So chất lượng với Qwen bằng `eval/mt_compare.py` (doc 09 §5.6).

### 13.6 Đã kiểm, chưa kiểm

- **Đã kiểm trong sandbox:**
  - test cho URL, header, tham số, tự đổi tham số, chỉ lấy dòng đầu, sửa nhãn ngôn ngữ;
  - một server giả lập deployment Azure: server RVT profile `api-mt`, phiên Video & Họp gửi audio qua WebSocket.
    Kết quả: Azure giả nhận đúng `api-key`, deployment, `api-version`; body chỉ có `messages`, `reasoning_effort`,
    `stream`; bản dịch chỉ còn dòng đầu; ép `minimal` thì engine tự chuyển sang `none`.
- **Chưa kiểm:**
  - Azure thật: chưa có khoá, và sandbox không ra được Azure.
  - Độ trễ, chi phí và chất lượng dịch thật của GPT-5 mini so với Qwen.
  - VRAM thật của hai model nghe.

## 14. Nguồn

Dịch vụ online:

- So sánh chung (phần lớn do nhà cung cấp hoặc trang tổng hợp viết):
  [AssemblyAI blog](https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription),
  [Gladia blog](https://www.gladia.io/blog/best-speech-to-text-apis),
  [Cleanvoice](https://cleanvoice.ai/blog/speaker-diarization-api/),
  [Smallest.ai](https://smallest.ai/blog/most-accurate-real-time-transcription-apis-in-2026),
  [Retell AI](https://www.retellai.com/blog/best-speech-to-text-models),
  [Future AGI](https://futureagi.substack.com/p/speech-to-text-apis-in-2026-benchmarks),
  [Inworld](https://inworld.ai/resources/best-speech-to-text-apis).
- Soniox: [tiếng Việt](https://soniox.com/speech-to-text/vietnamese),
  [tách người nói](https://soniox.com/speech-to-text/features/diarization),
  [Anh → Việt](https://soniox.com/speech-translation/english/vietnamese),
  [so với ElevenLabs](https://soniox.com/compare-stt/soniox-vs-elevenlabs/vietnamese).
- Deepgram: [tiếng Việt](https://deepgram.com/product/speech-to-text/vietnamese),
  [API trực tiếp](https://deepgram.com/learn/streaming-speech-recognition-api).
- AssemblyAI: [trực tiếp](https://www.assemblyai.com/products/streaming-speech-to-text).
- Speechmatics: [so với ElevenLabs Scribe](https://www.speechmatics.com/how-we-compare/elevenlabs-scribe-alternative).
- Azure: [tách người nói trực tiếp](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-stt-diarization).
- OpenAI: [Realtime API](https://developers.openai.com/api/docs/api-reference/realtime),
  [gpt-4o-transcribe-diarize trên Azure](https://ai.azure.com/catalog/models/gpt-4o-transcribe-diarize),
  [bài viết về diarize](https://ndurner.substack.com/p/gpt-4o-diarize).
- Google Chirp 3: [tài liệu](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3).
- AWS Transcribe: [tách người nói](https://docs.aws.amazon.com/transcribe/latest/dg/diarization.html),
  [trực tiếp](https://docs.aws.amazon.com/transcribe/latest/dg/conversation-diarization-streaming-med.html).
- FPT.AI: [speech to text](https://docs.fpt.ai/docs/en/speech/api/speech-to-text);
  Viettel AI: [speech to text](https://viettelai.vn/en/speech-to-text).

Tự host:

- [whisper_streaming](https://github.com/ufal/whisper_streaming) và
  [bài báo](https://alphaxiv.org/abs/2307.14743); [SimulStreaming / IWSLT 2025](https://web3.arxiv.org/pdf/2506.17077);
  [WhisperLiveKit](https://huggingface.co/spaces/langtech-innovation/WhisperLiveKitDiarization/blob/260b1f8f88fd17320dc1bb55e45c6d033201ca54/README.md).
- [PhoWhisper](https://arxiv.org/abs/2406.02555);
  [ChunkFormer-CTC-Large-Vie](https://huggingface.co/khanhld/chunkformer-ctc-large-vie);
  [Vietnamese ASR: A Revisit (2026)](https://arxiv.org/html/2603.14779);
  [ViMedCSS](https://arxiv.org/pdf/2602.12911); [VietLyrics](https://arxiv.org/pdf/2510.22295).
- [Streaming Sortformer](https://arxiv.org/pdf/2507.18446);
  [Multitalker Parakeet](https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1/raw/main/README.md);
  [Modal: Parakeet multitalker](https://modal.com/docs/examples/parakeet_multitalker);
  [NVIDIA Nemotron ASR streaming](https://catalog.ngc.nvidia.com/orgs/nvidia/collections/nemotron-asr-streaming).
- [phostt (sherpa-onnx Zipformer tiếng Việt)](https://docs.rs/crate/phostt/latest).

Chi tiết tự host (mục 9):

- [SimulStreaming](https://github.com/ufal/SimulStreaming); [bài báo CUNI IWSLT 2025](https://arxiv.org/html/2506.17077);
  [WhisperLiveKit](https://github.com/QuentinFuxa/WhisperLiveKit);
  [README WhisperLiveKit](https://cdn.jsdelivr.net/gh/quentinfuxa/whisperlivekit@main/README.md).
- [Streaming Sortformer 4spk v2.1](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1);
  [v2](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2);
  [Nemotron-3-Diarization](https://huggingface.co/nvidia/Nemotron-3-Diarization);
  [Modal: Sortformer 2.1](https://modal.com/docs/examples/sortformer2_1_speaker_diarization).
- [PhoWhisper (GitHub)](https://github.com/VinAIResearch/PhoWhisper);
  [VietASR (chunk 640 ms)](https://arxiv.org/pdf/2505.21527).
- Giá GPU: [Hostinger](https://www.hostinger.com/tutorials/?p=158956), [D-Central](https://d-central.tech/cloud-gpu-pricing/),
  [Jarvislabs](https://jarvislabs.ai/blog/a100-price), [Spheron](https://www.spheron.network/blog/h100-price-per-hour-2026/),
  [GPUnex](https://www.gpunex.com/blog/cloud-gpu-pricing-comparison-2026).

Lộ trình theo hạ tầng và kỹ năng (mục 11, 12):

- Parakeet tiếng Việt: [model card](https://build.nvidia.com/nvidia/parakeet-ctc-0_6b-vi/modelcard),
  [NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/-/collections/parakeet-ctc-0.6b-vi/-),
  [diễn đàn NVIDIA](https://forums.developer.nvidia.com/t/parakeet-ctc-vietnamese-is-the-original-arpa-lm-available-for-n-gram-lm-interpolation-fine-tuning/365453).
- [Vietnamese Open ASR Leaderboard](https://vietaudio-team-vietnamese-asr-leaderboard.hf.space/);
  [Handy: model theo ngôn ngữ](https://models.handy.computer/languages/vi).
- Open ASR Leaderboard: [GitHub](https://github.com/huggingface/open_asr_leaderboard),
  [The Decoder](https://the-decoder.com/open-asr-leaderboard-tests-more-than-60-speech-recognition-models-for-accuracy-and-speed/),
  [Cohere Transcribe](https://rits.shanghai.nyu.edu/ai/cohere-transcribe-2b-open-source-asr-model-takes-1-on-leaderboard/),
  [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks),
  [Slator](https://tech.slator.com/?p=109142).
- [Gladia: model mã nguồn mở 2026](https://www.gladia.io/blog/best-open-source-speech-to-text-models) (Qwen3-ASR).
- Sửa lỗi bằng LLM: [CoVoGER](https://preview.aclanthology.org/setup/2025.emnlp-main.320),
  [LLM-based ASR và Whisper, có tiếng Việt](https://arxiv.org/pdf/2412.00721),
  [GER với LLM](https://arxiv.org/html/2307.04172v1).
- [VietASR: 50 giờ có nhãn](https://arxiv.org/abs/2505.21527v2).

Nguồn audio để đo, giấy phép PhoWhisper (mục 10):

- [PhoWhisper GitHub](https://github.com/VinAIResearch/PhoWhisper),
  [LICENSE](https://raw.githubusercontent.com/VinAIResearch/PhoWhisper/main/LICENSE).
- TED: [Tim Urban](https://amara.org/videos/135ZqIglxZ0K/info/inside-the-mind-of-a-master-procrastinator-tim-urban),
  [Viết mới biết](https://www.ted.com/talks/son_huynh_vinh_write_to_know_vi_t_m_i_bi_t),
  [Đại dương xanh](https://www.ted.com/talks/anh_ngo_thuy_why_is_elderly_people_market_a_blue_ocean_in_vietnam),
  [TEDx translations](https://www.ted.com/pages/tedx-translations),
  [điều khoản TED Translators](https://www.ted.com/participate/translate/translator-resources/otp-terms-and-conditions).
- [TED-LIUM 3](https://voxkitchen.readthedocs.io/en/latest/datasets/tedlium3/),
  [long-form benchmarks](https://arxiv.org/pdf/2309.15013).
- [VietMed](https://arxiv.org/html/2404.05659);
  [danh sách dữ liệu tiếng Việt](https://github.com/lienlt10/awesome-vietnamese-speech-datasets).
- [YouTube Creative Commons](https://support.google.com/youtube/answer/2797468?hl=en-GB).

Dịch qua API (mục 13):

- Tham số GPT-5: [GPT-5.4 mini](https://developers.openai.com/docs/models/gpt-5.4-mini),
  [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning.md),
  [stop với gpt-5.1](https://community.openai.com/t/stop-sequence-doesnt-work-with-gpt-5-1-chat-latest/1366918),
  [none và max_completion_tokens](https://community.openai.com/t/gpt-5-4-ignores-reasoning-effort-none-when-max-completion-tokens-is-used/1378362),
  [temperature với GPT-5](https://github.com/getzep/graphiti/issues/878).
- Azure: [v1 API](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle),
  [chat completions](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/chatgpt),
  [header api-key](https://devopscube.com/setup-azure-openai/).
- Giá: [gpt-5-mini](https://futureagi.com/llm-cost-calculator/openai/gpt-5-mini),
  [gpt-5.4-mini](https://pricepertoken.com/pricing-page/model/openai-gpt-5.4-mini).
