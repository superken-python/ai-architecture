# 02 · Review thiết kế và code hiện tại — Realtime Voice Translate

**Ngày review:** 2026-10-09. **Đối chiếu với:** [01 · Kế hoạch triển khai](01-ke-hoach-trien-khai.md), phiên bản 0.2. **Phạm vi:** toàn bộ mã hiện có trong thư mục dự án, cấu hình Compose/Makefile, các bài test và giao diện. Đây là ảnh chụp trạng thái tại thời điểm review; repo đang có nhiều file chưa được Git theo dõi. Tài liệu này chỉ ghi nhận và đề xuất, không thay đổi code.

## 1. Kết luận và giới hạn kiểm chứng

**Chưa đạt mục tiêu MVP và chưa chạy được luồng dịch từ điện thoại qua bộ Docker hiện tại.** Khung `src/` Python, hợp đồng Pydantic, segmenter, engine giả/thật, React hai nửa và hai file Compose đã có. Tuy nhiên đường đi từ mic → WebSocket → ASR → hai bản dịch bị chặn ở nhiều điểm độc lập. Kể cả khi vá một lỗi, các lỗi còn lại vẫn cản luồng dùng thật.

| Kiểm tra đã thực hiện | Kết quả | Ý nghĩa |
|---|---|---|
| `uv run --project ai pytest ai/tests/unit -q` | **6 passed** | Chỉ chứng minh logic unit đang được test; không kiểm API/WebSocket, audio thực, model thực hay Docker. |
| `cd web && npm run build` | **Thành công** | TypeScript và Vite tạo được bundle; không chứng minh có kết nối hay âm thanh trên điện thoại. |
| `cd web && npm run test -- --run` | **Thất bại: No test files found** | `make test` sẽ không xanh ở bước web. |
| `docker compose -f compose.ai.yaml -f compose.web.yaml config` | **Parse được** | Compose hợp lệ về cú pháp; có network external `rvt_web_net`, không có trên Docker daemon lúc kiểm tra. |
| Import `ClientEvent`, kiểm `hasattr(ClientEvent, 'model_validate')` | **False** | Lệnh text WebSocket hiện bị bắt lỗi và bỏ qua. Thử `TestClient` với `turn.start` ghi log `Invalid message: 'types.UnionType' object has no attribute 'model_validate'`. |
| Kiểm các route FastAPI | Chỉ `/api/health/live`, `/ws` và OpenAPI mặc định | REST theo thiết kế, `/health/ready`, `/metrics` chưa có. |

**Chưa kiểm chứng:** build image/chạy Compose đầy đủ, ASR/MT trên GPU NVIDIA 8 GB, HTTPS trên điện thoại, model Hy-MT2, số liệu SLO. Máy review là macOS, không có model GGUF, certificate hay golden set trong thư mục dự án. Vì vậy các kết luận hiệu năng và độ chính xác dưới đây là **chưa có bằng chứng đạt**, không phải số đo thất bại. Một số rủi ro tương thích model/runtime cần thử trên máy GPU sau khi sửa đường chạy.

### Mức ưu tiên dùng trong tài liệu

- **P0 — chặn chạy/demo hoặc lộ dịch vụ trái thiết kế:** xử lý trước khi thử end-to-end.
- **P1 — sai hành vi cốt lõi hoặc thiếu bảo đảm:** xử lý trước khi gọi là MVP.
- **P2 — hoàn thiện chất lượng, vận hành và trải nghiệm:** làm theo thứ tự khi P0/P1 đã chạy.

## 2. Đối chiếu mục tiêu thiết kế

| Mục tiêu trong thiết kế | Hiện trạng code | Đánh giá |
|---|---|---|
| Mic điện thoại → PCM16 LE mono 16 kHz, khung 40 ms qua WSS cùng origin | Có AudioWorklet và gửi binary, nhưng giả định AudioContext 16 kHz, khung 2.048 mẫu = 128 ms ở 16 kHz; UI dùng `ws://<host>:8000/ws` | **Chưa đúng; đường HTTPS bị chặn** |
| VAD Silero từng phiên, chốt câu với preroll/pad/giới hạn 20 s | Có adapter ONNX và segmenter đơn giản; VAD dùng chung state cho mọi phiên; không có preroll/pad, hard max, reset theo lượt | **Chưa đúng** |
| ASR Whisper turbo + LID ja/en/vi, partial thật, sửa ngôn ngữ | Có faster-whisper final và hàm LID; partial là chuỗi giả; `session.start`, `sides.update`, `override_lang` không được xử lý | **Một phần** |
| Hai bản dịch Hy-MT2 stream song song, prompt theo model, kiểm chứng/retry/cache | Có hai task MT; prompt generic, không có kiểm chứng, retry/cache/context/timeout 5 s, không pin model | **Một phần** |
| Giao diện hai người, người nào đọc tiếng chủ của mình, luôn thấy transcript + đủ hai bản dịch | Có bố cục xoay 180° và nút mic; render cố định A→ja, B→vi; tiếng thứ ba không hiển thị; thiếu nhiều trạng thái | **Một phần, sai quy tắc hiển thị** |
| Hai phần Docker, AI nội bộ, nginx HTTPS proxy `/api` + `/ws` | Có hai Compose, nhưng nginx chỉ phục vụ tệp; AI port 8000 publish mọi interface; FE/AI không chia sẻ network dùng được | **Chưa đúng; không thông luồng** |
| `make tls/models/up/deploy/rollback`, image tag theo commit, smoke và rollback | Chỉ có `tls`, `setup`, `test`, `up`, `down`; image AI hiện thiếu file lock trong build context | **Chưa có** |
| SLO latency/LID/ASR/MT/VRAM, golden set và eval | Không có golden set, eval, load/smoke/live test hay đo metrics | **Không thể xác nhận** |
| Auth, giới hạn phiên/tài nguyên, riêng tư | Có biến mẫu nhưng không được đọc; WS/AI mở không auth, CORS `*`, port AI lộ; không có giới hạn | **Chưa đúng** |

## 3. Phát hiện P0 — chặn đường chạy

### P0-01 · Mọi message text WebSocket bị bỏ qua

**Bằng chứng:** [main.py](../ai/src/rvt_ai/main.py#L74-L90) gọi `ClientEvent.model_validate(payload)`. `ClientEvent` tại [messages.py](../ai/src/rvt_contracts/messages.py#L102-L105) là `Annotated[Union, Field(...)]`, không phải lớp `BaseModel`, nên không có `model_validate`. `except Exception` chỉ `print` rồi tiếp tục. Repro trực tiếp trả về `False` khi kiểm thuộc tính; gửi `turn.start` qua TestClient in lỗi trên. Hậu quả: `turn.start`, `turn.stop`, `ping` đều không tác dụng; `current_side` luôn `None`, binary bị bỏ tại [session.py](../ai/src/rvt_ai/pipeline/session.py#L37-L39). Chỉ thấy `session.ready`, không có VAD/ASR/MT.

**Hướng sửa:** dùng `TypeAdapter(ClientEvent).validate_python(payload)` hoặc một wrapper model tương ứng; xử lý lỗi validation bằng `error` rõ ràng. Test ở **route WebSocket thật** (không chỉ gọi trực tiếp `RVTSession`) phải gửi `session.start`, `turn.start`, audio, `turn.stop` và nhận `asr.final` + 2 `mt.final` bằng fake engine. Kiểm luôn message không hợp lệ trả error, không làm rơi kết nối.

### P0-02 · Frontend không thể nối backend khi chạy HTTPS

**Bằng chứng:** [App.tsx](../web/src/App.tsx#L8-L12) hardcode `ws://${window.location.hostname}:8000/ws`. Trang ở `https://<IP>:8443` sẽ gọi WebSocket không mã hóa từ secure page và bị trình duyệt chặn như mixed content. [nginx.conf.template](../web/nginx.conf.template#L1-L24) không có proxy `/ws` hay `/api`; [main.py](../ai/src/rvt_ai/main.py#L45-L50) dùng route `/ws`, khác `/v1/stream` trong thiết kế. Ngay cả khi URL được sửa sang `wss://...:8443/ws`, nginx hiện vẫn chỉ trả nội dung tĩnh.

**Hướng sửa:** chốt hợp đồng route (`/ws` ở biên → `/v1/stream` ở AI, hoặc đổi thiết kế nhất quán), proxy cả WebSocket và `/api`, và cho client tạo WSS theo cùng origin (`location.host`). Kiểm từ điện thoại/trình duyệt thật: trang HTTPS mở được WS, `session.ready`, ping/pong và audio chạy qua cổng 8443, không gọi cổng 8000.

### P0-03 · Backend Docker image không build theo Dockerfile hiện tại

**Bằng chứng:** [ai/Dockerfile](../ai/Dockerfile#L11-L12) `COPY pyproject.toml uv.lock ./`, trong khi `ai/uv.lock` **không tồn tại**. File `uv.lock` nằm ở gốc workspace cha, ngoài build context `./ai` của [compose.ai.yaml](../compose.ai.yaml#L26-L30). `COPY` không thể lấy file ngoài context, nên build AI sẽ dừng trước khi chạy `uv sync`. Image còn dùng CUDA 12.1/cuDNN 8 Ubuntu 22.04 và `apt-get install python3.12`; thiết kế yêu cầu CUDA 12/cuDNN 9 và Python 3.12 trên Ubuntu 24.04. Vấn đề `apt` và runtime cần kiểm khi build thật, còn thiếu `uv.lock` là lỗi chắc chắn.

**Hướng sửa:** thống nhất mô hình `uv` workspace/lockfile và build context với repo cha, hoặc khóa dependency riêng cho `ai`; chọn base image/Python khớp faster-whisper/CTranslate2 đã pin; build bằng `docker compose build ai` trên máy đích, sau đó import/nạp ASR thật. Không đưa model và secret vào image.

### P0-04 · Compose không nối được FE với AI và không có model đầu vào

**Bằng chứng:** [compose.web.yaml](../compose.web.yaml#L12-L17) yêu cầu network `rvt_web_net` là **external**. `docker network inspect rvt_web_net` báo không tồn tại ở môi trường review; định nghĩa network cùng tên ở [compose.ai.yaml](../compose.ai.yaml#L49-L53) bị Compose merge thành external (xem `docker compose config`). Vì vậy `make up` trên máy sạch sẽ không tự tạo network đó. nginx cũng không proxy AI. `mt` đòi `/models/mt-model.gguf` tại [compose.ai.yaml](../compose.ai.yaml#L6-L15), nhưng không có file hoặc `models-init`; `models/` không tồn tại lúc review. [Makefile](../Makefile#L25-L29) không tạo network hay tải model trước.

**Hướng sửa:** định nghĩa chung một network Compose không external cho web↔ai và network nội bộ ai↔mt, hoặc nếu cố ý external thì phải có bước tạo rõ ràng. Thêm model registry, bước tải + checksum và mount volume bền vững theo thiết kế; kiểm `make models && make up` từ checkout sạch trên máy GPU. Healthcheck phải phản ánh cả AI sẵn sàng và MT sẵn sàng, không chỉ tiến trình nginx.

### P0-05 · Bề mặt mạng và xác thực trái ranh giới tin cậy

**Bằng chứng:** [compose.ai.yaml](../compose.ai.yaml#L32-L36) publish `8000:8000` trên mọi interface; [compose.web.yaml](../compose.web.yaml#L7-L9) publish HTTP `8080` và HTTPS `8443` trên mọi interface. [main.py](../ai/src/rvt_ai/main.py#L20-L26) mở CORS `*`, [main.py](../ai/src/rvt_ai/main.py#L49-L52) accept WebSocket không token. [ws_client.ts](../web/src/net/ws_client.ts#L9-L21) chỉ gửi `rvt.v1`; không có `rvt.token.<token>`. `.env.example` có `RVT_API_KEY`, `RVT_MAX_SESSIONS` nhưng code không đọc. Trong LAN, bất kỳ máy nào đến được port AI đều có thể mở phiên/đẩy audio, trái mục 4.3, 6.6, 12.2.

**Hướng sửa:** dừng publish AI, cho web gọi AI qua Docker network; bind HTTP vào localhost và HTTPS vào `RVT_LAN_IP`; triển khai `/v1/session`, access code → token HMAC có TTL, kiểm token trước WS, Bearer cho REST test; giới hạn thử mã và phiên. Khi auth đã có, bỏ CORS rộng nếu chỉ same origin. Kiểm từ máy LAN: port 8000 không vào được, WS không token bị từ chối, token hợp lệ chạy được.

### P0-06 · Pipeline audio chưa đúng định dạng/thời gian mà model cần

**Bằng chứng:** [audio-processor.js](../web/public/audio-processor.js#L3-L24) gửi mỗi **2.048 mẫu**; ở 16 kHz tương ứng **128 ms**, không phải 640 mẫu/40 ms. [ws_client.ts](../web/src/net/ws_client.ts#L39-L45) yêu cầu `AudioContext({sampleRate:16000})` nhưng không tự resample hoặc kiểm `audioContext.sampleRate` thực tế; nếu trình duyệt chạy 44,1/48 kHz thì server vẫn hiểu PCM là 16 kHz. [vad_silero.py](../ai/src/rvt_ai/engines/vad_silero.py#L25-L40) đưa nguyên chunk vào ONNX, trong khi thiết kế đòi các cửa sổ 32 ms; chưa kiểm kích thước/tên input của đúng revision Silero được tải. [ws_client.ts](../web/src/net/ws_client.ts#L16-L20) còn khai báo format `pcm16` thay vì `pcm_s16le` theo giao thức thiết kế, và server không validate.

**Hướng sửa:** resample thực sự từ sample rate thiết bị, kiểm định bằng tín hiệu thử 44,1/48 kHz; worklet xuất chính xác PCM16 LE mono khung 640 mẫu, server gom/chia thành cửa sổ VAD phù hợp model đã pin. Validate protocol/rate/format/frame size ở `session.start` và binary. Kiểm WAV ja/en/vi qua browser giả + WS, đo số mẫu, thời lượng và transcript.

## 4. Phát hiện P1 — sai logic hoặc thiếu bảo đảm cốt lõi

### P1-01 · State Silero VAD dùng chung giữa các phiên và lượt nói

[main.py](../ai/src/rvt_ai/main.py#L28-L43) tạo một `vad_engine` toàn cục rồi truyền cho mọi `RVTSession`; [vad_silero.py](../ai/src/rvt_ai/engines/vad_silero.py#L20-L41) lưu `_h`, `_c` mutable trong engine. Hai phiên xen kẽ sẽ dùng chung trạng thái hồi tiếp, làm VAD của phiên này phụ thuộc audio phiên kia. `reset_states()` chỉ gọi lúc khởi tạo, không gọi khi chốt câu/đổi lượt. Cần state VAD riêng theo phiên, reset ở ranh giới câu/lượt, test hai session xen kẽ với audio khác nhau. Đồng thời pin revision ONNX và xác nhận signature input/output của chính file đó; URL `master` hiện không pin và không checksum.

### P1-02 · Segmenter giữ âm thanh không giới hạn khi im lặng và chưa chốt câu đúng thiết kế

[segmenter.py](../ai/src/rvt_ai/pipeline/segmenter.py#L31-L39) `buffer.extend(chunk)` trước cả khi phát hiện tiếng; không có ring buffer 300 ms. Mở mic trong phòng im lặng vài phút tích lũy toàn bộ audio, rồi đưa cả khoảng im lặng vào ASR khi có câu đầu. `speech_pad_ms`, `preroll_ms` chỉ có trong config nhưng không được sử dụng; hard max 20 s/cắt mềm 15 s chưa có. Điều kiện max tại [segmenter.py](../ai/src/rvt_ai/pipeline/segmenter.py#L65-L66) dùng `if self.speech_start_ms` nên bỏ qua trường hợp bắt đầu ở thời điểm 0. `force_final()` tại [segmenter.py](../ai/src/rvt_ai/pipeline/segmenter.py#L81-L84) không kiểm min speech. Nên dùng ring buffer cố định, giữ đúng preroll/pad, kiểm min/max trong mọi đường final, và test im lặng dài, nói ngắn, nói liên tục >20 s, đổi lượt.

### P1-03 · ASR đồng bộ đang chặn event loop; partial chỉ là placeholder

[session.py](../ai/src/rvt_ai/pipeline/session.py#L47-L56) gửi `"... (đang nghe)"` thay vì ASR tạm. [session.py](../ai/src/rvt_ai/pipeline/session.py#L64-L73) gọi `self.asr.transcribe()` đồng bộ ngay trong coroutine nhận WS; khi Whisper mất vài trăm ms đến vài giây, event loop không xử lý audio/message của phiên khác. Chưa có scheduler một worker GPU, ưu tiên final, gộp partial, timeout drop như mục 6.5. Cần luồng/queue riêng cho inference, test hai session đồng thời và xác nhận partial là transcript thực; phân biệt partial, final bằng `utterance_id` ổn định.

### P1-04 · LID và transcript có thể chỉ hai ngôn ngữ khác nhau

[asr_whisper.py](../ai/src/rvt_ai/engines/asr_whisper.py#L26-L49) Whisper tự chọn ngôn ngữ rồi decode; [session.py](../ai/src/rvt_ai/pipeline/session.py#L75-L96) lại có thể chọn `final_lang` khác qua prior nhưng **không decode lại** bằng ngôn ngữ đó. `asr.final.lang_probs` gửi xác suất ASR thô, trong khi nhãn `uncertain` tính từ posterior của `pick_language`; UI không thể hiện đúng xác suất đã quyết định. `detected_lang` có thể nằm ngoài ja/en/vi nhưng type ghi `Lang`. Prior cập nhật bằng `+1.0` mỗi câu và không chuẩn hóa/giới hạn, dần áp đảo bằng chứng audio; thiết kế định dùng trung bình trượt và `prior_weight` trong profile (0.4). Nên giữ cả raw và posterior rõ nghĩa, re-decode khi quyết định LID khác, chốt threshold bằng eval câu ngắn, và test trường hợp ASR nhầm tiếng hoặc tiếng ngoài 3 mục tiêu.

### P1-05 · Message giao thức được khai báo nhưng phần lớn chưa có hành vi

[messages.py](../ai/src/rvt_contracts/messages.py#L7-L38) có `session.start`, `sides.update`, `utterance.override_lang`, `ping`; [main.py](../ai/src/rvt_ai/main.py#L80-L85) chỉ xử lý ping/start/stop, mà hiện cả ba còn bị P0-01 chặn. Không validate `protocol=1`, rate/format, ngôn ngữ của mỗi nửa; `SideConfig.lang` là `str` tự do, `SessionStart.sides` có thể thiếu A/B. Không có lưu audio theo `utterance_id` để nhận dạng lại khi override. Cần state machine phiên/lượt rõ ràng, message không hợp lệ trả `error`, có test cho cập nhật ngôn ngữ và reprocess câu đã chốt.

### P1-06 · Lỗi MT có thể mất kết quả mà client không biết

[session.py](../ai/src/rvt_ai/pipeline/session.py#L99-L120) tạo hai task nền không giữ handle/cancel, không `try/except`; một task lỗi sẽ không có `mt.final` hoặc `error`. [mt_llama.py](../ai/src/rvt_ai/engines/mt_llama.py#L33-L45) không `raise_for_status`, có thể bỏ qua JSON/SSE lỗi trong `except Exception: pass`, timeout 30 s thay vì 5 s. Với HTTP 4xx/5xx hoặc SSE sai, có khả năng phát `mt.final` rỗng như thành công. Cần kiểm status, schema/finish reason, timeout từng request, error event theo target, cleanup task khi disconnect; kiểm thử lỗi 401/500/timeout/SSE hỏng. Giữ transcript nếu một hoặc hai bản dịch lỗi.

### P1-07 · Prompt và model MT chưa khớp thiết kế

[mt_llama.py](../ai/src/rvt_ai/engines/mt_llama.py#L11-L31) dùng prompt generic, `temperature=0.1`, `top_p=0.95`, `max_tokens=256`, không có template Hy-MT2, glossary, 2 câu ngữ cảnh, max token theo độ dài, kiểm chứng chữ viết/độ dài, greedy retry hay exact cache. [compose.ai.yaml](../compose.ai.yaml#L3-L13) không pin image/version/sha, không `-ngl 99`, api key hay metrics; profile chưa điều khiển config. Chất lượng sáu chiều dịch hiện **không thể kết luận** và chưa có cơ sở để áp SLO. Nên ưu tiên model + template pin revision, rồi eval trên golden set trước khi tinh chỉnh sampling; không coi generic prompt là baseline Hy-MT2.

### P1-08 · Chọn profile/model chưa vận hành theo thiết kế 8 GB

[main.py](../ai/src/rvt_ai/main.py#L28-L40) mặc định fake khi chạy ngoài Docker, nhưng Docker đặt `RVT_USE_FAKE=0` và luôn load `large-v3-turbo`; [asr_whisper.py](../ai/src/rvt_ai/engines/asr_whisper.py#L7-L19) mặc định `float16`, không phải `int8_float16`, và bắt **mọi** lỗi CUDA rồi âm thầm tải model lớn sang CPU. Điều này có thể khiến startup rất chậm và che lỗi VRAM/runtime. Không có `RVT_PROFILE`, `cpu-dev`, `fast`, `balanced`, `quality`, pack YAML hay giới hạn NVML. Nên fail fast với lỗi rõ ở profile GPU, dùng đúng compute type theo profile, chỉ fallback CPU khi profile cho phép; đo VRAM 1/2 phiên trên phần cứng thật.

### P1-09 · UI không xử lý hai nửa và ba ngôn ngữ đúng quy tắc

[App.tsx](../web/src/App.tsx#L39-L57) luôn cho nửa B đọc `translations.ja` khi A nói và nửa A đọc `translations.vi` khi B nói. Nếu A/B đổi tiếng chủ hoặc có người nói tiếng Anh, nội dung có thể sai hoặc trống; không hiển thị bản dịch thứ ba, nhãn ngôn ngữ/xác suất, uncertain, lịch sử câu, cỡ chữ, chọn/khóa ngôn ngữ. [useStore.ts](../web/src/state/useStore.ts#L42-L92) bỏ qua `session.ready`, `vad`, `error`, `utterance.metrics`; `vad` không đổi trạng thái UI. Cần state của mỗi nửa (ngôn ngữ chủ auto/locked), selector hiển thị theo mục 7.2, dùng cả hai MT final; test đủ 6 chiều và trường hợp chưa xác định ngôn ngữ chủ.

### P1-10 · Đổi mic A/B có thể tạo nhiều luồng audio cùng lúc

[App.tsx](../web/src/App.tsx#L14-L22) gọi `startAudio(B)` ngay khi A đang mở mà không `stopAudio(A)`. [ws_client.ts](../web/src/net/ws_client.ts#L37-L58) tạo `MediaStream`, `AudioContext`, `AudioWorkletNode` mới rồi ghi đè các tham chiếu cũ. Luồng A cũ không được stop và vẫn có thể gửi bytes; server vừa đổi current side sang B nên gán nhầm tiếng A thành B. Cần tuần tự stop/flush A, giải phóng track/worklet, rồi start B; trạng thái mic chỉ bật sau khi WS sẵn sàng và capture thành công. Test switch liên tiếp và kiểm số track sống luôn ≤1.

### P1-11 · Chưa kiểm soát vòng đời session, task và tài nguyên

[main.py](../ai/src/rvt_ai/main.py#L43-L94) thêm session vô hạn; chỉ xóa khi đúng `WebSocketDisconnect`. Trong TestClient đã quan sát lúc client đóng, `websocket.receive()` có thể ném `WebSocketDisconnected`, làm cleanup hiện tại không chạy. Không có idle timeout 5 phút, TTL 2 giờ, frame ≤64 KB, câu ≤20 s, `RVT_MAX_SESSIONS`; không close `httpx.AsyncClient`. Cần `try/finally` cleanup bất kể lỗi, cancel/join MT task, close socket/client đúng lifecycle; từ chối phiên vượt quota bằng error/close code có nghĩa. Test disconnect khi ASR/MT đang chạy và load nhiều session.

### P1-12 · Docker/HTTPS/Makefile chưa có đường triển khai tái lập

[Makefile](../Makefile#L11-L29) `tls` lấy IP từ `hostname -I` thay vì `RVT_LAN_IP`, không có `models`, `status`, `dev-fake`, `eval`, `deploy`, `rollback`, smoke hay image tag commit; các tên `eval deploy` trong `.PHONY` không có recipe. [web/Dockerfile](../web/Dockerfile#L1-L15) dùng `npm install` thay vì frozen lock và nginx root image, khác thiết kế. [compose.ai.yaml](../compose.ai.yaml#L18-L47) thiếu health AI, restart, logging, resource cap; web không có readiness dependency. Chưa có hướng dẫn cài CA cho điện thoại; `config/tls` trống. Nên làm runbook trên máy GPU sạch, `make tls && make models && make up`, rồi mới `deploy/rollback` với smoke. Không gọi deploy hoàn tất chỉ vì container process đang chạy.

## 5. Thiếu theo pha P0–P6 và các cải tiến tiếp theo

| Pha | Đã thấy | Còn thiếu / tiêu chí đóng pha |
|---|---|---|
| **P0 — spike** | Có danh sách model trong thiết kế | Chưa có `golden-v0`, manifest/checksum, benchmark ASR/LID/MT, giấy phép/model revision, VRAM và latency 2 phiên, ADR dựa số liệu. **Đóng băng tập eval trước thử model** như thiết kế. |
| **P1 — lõi AI** | `src/`, contracts, vài engine, 6 unit test | Pack/profile/prompt loader và revision, REST, auth, scheduler, partial thật, override, MT validation/cache/retry, warm-up/readiness/metrics, integration/smoke test. |
| **P2 — web** | Vite/React/TS/Zustand, nút mic, layout xoay | Resampler và 40 ms, WSS token/reconnect, UI theo ngôn ngữ chủ, error states, PWA/manifest/service worker, wake lock, nhãn vi/en/ja, lưu/xóa lịch sử, test Vitest/Playwright trên iPhone/Android. |
| **P3 — Docker/HTTPS** | Hai compose và hai Dockerfile ban đầu | `models-init`, network đúng, proxy, TLS theo LAN IP, model volume/checksum, healthcheck; build sạch và dùng micro qua HTTPS. |
| **P4 — deploy** | Chưa có | `make deploy` tag commit + dirty check + smoke + history + rollback, restart/log rotation/status/runbook. |
| **P5 — tinh chỉnh** | Chưa có | Phân tích lỗi golden set, so mẫu trước/sau, cải thiện LID/ASR/MT, đạt SLO kèm khoảng tin cậy. |
| **P6 — vận hành** | Chưa có | Load test 1–4 phiên, dashboard/cảnh báo, rà bảo mật, tài liệu xử lý hết VRAM/đổi cert và giới hạn Wi-Fi. |

### Lỗ hổng test hiện tại

Ba file unit Python kiểm phần tách rời, không đi qua `main.py`; vì thế P0-01 vẫn lọt khi 6 test xanh. Không có test nào cho frontend; `web/tests` trống, làm `make test` thất bại. Chưa có integration TestClient WS, test resampler, giả lập SSE MT lỗi, E2E mic giả, smoke 3 WAV, test GPU/thiết bị thật và eval. Tối thiểu nên thêm **một bài test hợp đồng xuyên từ WS tới hai `mt.final`** bằng fake engine trước các test nhỏ khác; đó là đường chạy mà người dùng thật cần. Test thật không cần tạo thêm bài test chỉ lặp lại dòng code.

### Quản lý mã nguồn và cấu hình

- Root `.gitignore` hiện không ignore `web/node_modules/`; `git status --short --untracked-files=all` liệt kê nhiều file dependency. Cần ignore `node_modules/`, `web/dist/`, `models/`, `*.gguf`, `.deploy/`, certificate/secret và cache theo thiết kế trước khi commit. Chỉ commit lockfile, schema/type generated đã kiểm drift, config mẫu an toàn.
- [scripts/generate_ts.py](../scripts/generate_ts.py#L6-L21) chỉ sinh JSON Schema; TS hiện có file generated nhưng không có lệnh sinh/kiểm drift trong `make test` hoặc CI. `AudioConfig` và `SideConfig` trong Python quá rộng, TS kế thừa `string` thay vì literal; hãy ràng buộc ngay tại hợp đồng nguồn.
- [README.md](../README.md) và dòng trạng thái trong thiết kế còn ghi “chưa có code”; cập nhật khi đã có demo đạt smoke, kèm lệnh setup chính xác, phiên bản model, baseline và giới hạn đã đo. Đây là việc tài liệu, sau khi hành vi chạy thật được xác minh.

### Điểm cần làm rõ ngay trong thiết kế 01

Các điểm này là **rủi ro/chi tiết chưa chốt của bản thiết kế**, không phải lỗi code đã đo:

1. **Ngân sách độ trễ rất sít.** Mục 5.6 dự tính 500 ms chỉ để chờ VAD, thêm ASR 200–350 ms và hai MT 200–400 ms; p50 mục 3 là 1,3 s. Cần định nghĩa chính xác mốc “ngừng nói” lấy từ waveform hay lúc VAD báo hết tiếng; đo end-to-end bằng đồng hồ client và từng stage server, gồm queue wait, warm/cold, câu ngắn/dài và 1/2/3 cuộc hội thoại. Không được kết luận đạt chỉ từ thời gian suy luận riêng model.
2. **Tải đồng thời và VRAM phụ thuộc cấu hình MT.** Thiết kế nói 1–3 cuộc hội thoại và `--parallel 4`; mỗi câu cần hai slot MT, nên hai câu đồng thời đã lấp bốn slot. Câu thứ ba sẽ chờ, ảnh hưởng p95 và KV cache. P0/P6 cần load test 2 và 3 phiên với câu nói chồng thời điểm, ghi cả queue latency và VRAM đỉnh trước khi chốt `RVT_MAX_SESSIONS=4`.
3. **Vòng đời token khi hội thoại 15–60 phút.** Mục 12.2 đặt token TTL 15 phút, mục 7.4 muốn reconnect giữ session. Cần chốt token chỉ kiểm lúc bắt tay hay hết hạn trong phiên, endpoint refresh/đổi lại access code và cách nối lại session/utterance an toàn sau 15 phút; sau reconnect không thể giả định session state trong RAM vẫn tồn tại.
4. **Hợp đồng audio/VAD phải quy định chính xác.** Mục 6.1 phát khung 40 ms, mục 6.2 chạy Silero cửa sổ 32 ms; server cần định nghĩa buffer/chia cửa sổ liên tục, timestamp mẫu, xử lý khung cuối khi `turn.stop`, và reset state VAD lúc đổi lượt. Nếu không, các adapter có thể đều “đúng” riêng lẻ nhưng làm mất/nhân đôi mẫu tại ranh giới.
5. **Sửa ngôn ngữ cần giữ audio một cách có giới hạn.** Mục 6.3/6.6 yêu cầu `utterance.override_lang` nhận dạng lại câu cũ, trong khi mục 12.3 nói server không lưu âm thanh. Hai yêu cầu có thể cùng đúng nếu chỉ giữ buffer tạm trong RAM với TTL/ngưỡng dung lượng và xóa sau override hoặc hết thời hạn; cần ghi rõ để implement và kiểm quyền riêng tư. Đồng thời chọn cách thay thế kết quả MT cũ trên UI nếu override đến khi bản dịch cũ vẫn đang stream.
6. **Cổng chất lượng cần gắn vào một đường triển khai tái lập.** Mục 11/13 đòi đóng băng golden set và so với baseline trước deploy, nhưng P4 `make deploy` minh họa chỉ chạy smoke. Cần nói rõ khi nào bắt buộc `make eval`, cách ghi model/pack revision + commit vào báo cáo, ngưỡng từ chối và liệu rollback cả model volume/prompt/config hay chỉ image. Smoke ba WAV không thay thế đánh giá sáu chiều dịch.

## 6. Thứ tự tự triển khai đề xuất và tiêu chí nghiệm thu

1. **Thông luồng fake qua browser:** sửa parser WS, route/proxy WSS cùng origin, Compose network, `ai/Dockerfile` build được; fake engine phải cho `session.ready → vad → asr.final → 2 mt.final` từ browser HTTPS. Đây là cổng đầu tiên, chưa cần GPU.
2. **Chuẩn hóa audio và state:** resampler + frame 40 ms, VAD per-session, ring buffer/preroll/pad/max, stop/switch mic; test trên 44,1/48 kHz và hai session xen kẽ.
3. **Bảo đảm kết quả:** LID/re-decode, partial thật, MT model template + error/timeout/validate, session cleanup và quota; test lỗi/timeout rõ ràng, không có `mt.final` rỗng báo thành công.
4. **Đóng P0 model/eval và tích hợp GPU:** pin model/sha/license, golden set, benchmark 6 chiều, VRAM/latency 1–2 phiên; chỉ công bố profile `balanced` khi số đo thật đạt mục 3 của thiết kế.
5. **Hoàn thiện UI, auth và deploy:** quy tắc hiển thị hai nửa/ba tiếng, access code, TLS nội bộ, health/metrics, smoke + rollback, test iPhone/Android. `make test` và `make deploy` phải chạy xanh trên checkout sạch của máy GPU.

**Điều kiện để tuyên bố “đúng thiết kế”:** từ một điện thoại cùng LAN mở HTTPS và chấp nhận CA, hai người đổi lượt A/B nói ja/en/vi, mỗi câu hiện transcript đúng ngôn ngữ và **đủ hai bản dịch**, lỗi mạng/model hiển thị rõ; 3 WAV smoke đúng LID/đủ 2 MT; p50/p95, WER/CER, đánh giá dịch, hallucination và VRAM được báo bằng dữ liệu golden set với revision/commit. Trước các bằng chứng này, status phù hợp là **prototype chưa end-to-end**, không phải MVP đạt SLO.
