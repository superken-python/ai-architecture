# 10 · Nghiên cứu lại: nghe một chiều, tiếng Anh và tiếng Việt — Realtime Voice Translate

**Ngày:** 2026-10-14. **Phạm vi:** nghiên cứu, chưa code. Bản hiện tại (2 chiều, nghe dịch video, tiếng Nhật) được đánh
giá là chưa ổn, nên phía UI sẽ làm lại từ đầu. Bước đầu tiên chỉ cần:

- một tab **"Chỉ nghe"**: nghe liên tục từ mic hoặc tab video, hiện chữ lên màn hình để xem có nhận đúng câu nói không;
- **một người hoặc nhiều người nói**, có nhãn người nói khi nhiều người;
- **chỉ tiếng Anh và tiếng Việt**, gồm cả câu tiếng Việt lẫn từ tiếng Anh;
- chưa dịch, chưa hai chiều;
- không giới hạn cấu hình server hay chi phí: chọn theo chất lượng trước.

Tài liệu này so các cách làm từ tốt nhất tới đơn giản nhất, cả dịch vụ online lẫn model tự host, rồi đề xuất cách thử.

**Lưu ý về nguồn.** Phần lớn số liệu về độ trễ, độ chính xác, ngôn ngữ hỗ trợ là do chính nhà cung cấp công bố, hoặc
từ các trang so sánh không độc lập. Không có bộ đo chung nào cho tiếng Việt nói tự nhiên, nhiều người, có nhạc nền. Vì
vậy kết luận ở đây là **danh sách ứng viên để đo**, không phải bảng xếp hạng cuối. Nguồn ở mục 9.

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
   audio tiếng Anh và tiếng Việt (mục 7). Chọn theo số đo, không theo quảng cáo.

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

## 9. Nguồn

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
