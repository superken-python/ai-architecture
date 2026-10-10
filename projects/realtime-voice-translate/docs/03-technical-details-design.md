# 03 · Technical Details Design — Realtime Voice Translate

Tài liệu thiết kế chi tiết kỹ thuật hệ thống **Realtime Voice Translate (Nhật ⇄ Anh ⇄ Việt)** chạy trên hạ tầng Docker với 1 GPU NVIDIA 8 GB VRAM.

---

## 1. Kiến trúc tổng thể & Hạ tầng Mạng (System & Network Topology)

```mermaid
flowchart TB
    subgraph CLIENT["Thiết bị Người dùng (Client)"]
        PHONE["Điện thoại di động / Trình duyệt<br/>• AudioWorklet 16 kHz PCM16<br/>• Split-View UI 180° xoay đối diện<br/>• PWA / Screen Wake Lock"]
    end

    subgraph DOCKER_HOST["Hạ tầng Docker (Máy chủ 1 GPU NVIDIA ≤ 8 GB)"]
        subgraph FE_ZONE["Phần Giao diện & Biên mạng (compose.web.yaml)"]
            NGINX["rvt_web (nginx:alpine)<br/>• Port 8443 (HTTPS TLS)<br/>• Port 8080 (HTTP redirect)<br/>• Phục vụ Static SPA Assets<br/>• WSS Proxy (/ws, /v1/stream)<br/>• REST Proxy (/api/)"]
        end

        subgraph NET_WEB["Docker Network: rvt_web_net (Cầu nối FE - AI)"]
        end

        subgraph AI_ZONE["Phần AI Backend (compose.ai.yaml)"]
            AI_GW["rvt_ai (FastAPI Core Gateway)<br/>• WebSocket Endpoint (/ws)<br/>• Silero VAD (ONNX - CPU)<br/>• faster-whisper STT + LID (CUDA)<br/>• Điều phối Session & Scheduler"]
            
            subgraph NET_BACKEND["Docker Network: backend (internal: true)"]
            end

            MT_SRV["rvt_mt (llama.cpp server-cuda)<br/>• Hy-MT2-1.8B / 7B GGUF<br/>• OpenAI-compatible API (:8080)<br/>• Continuous batching, parallel 4"]
        end

        subgraph STORAGE["Bộ lưu trữ Mount Volumes"]
            VOL_TLS[("./config/tls<br/>cert.pem, key.pem")]
            VOL_MODELS[("./models<br/>silero_vad.onnx, mt-model.gguf")]
            VOL_PACKS[("./packs<br/>profiles, languages, glossary")]
            VOL_PROMPTS[("./prompts<br/>templates Jinja2")]
        end
    end

    PHONE <== "WSS / HTTPS :8443" ==> NGINX
    NGINX <== "proxy http://ai:8000" ==> NET_WEB
    NET_WEB <==> AI_GW
    AI_GW <== "chat/completions stream" ==> NET_BACKEND
    NET_BACKEND <==> MT_SRV

    VOL_TLS -.-> NGINX
    VOL_MODELS -.-> AI_GW
    VOL_MODELS -.-> MT_SRV
    VOL_PACKS -.-> AI_GW
    VOL_PROMPTS -.-> AI_GW
```

---

## 2. Luồng Xử lý Âm thanh Thời gian thực (Realtime Cascade Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor UserA as Người A (Nói tiếng Việt)
    participant UI as Client Web UI (AudioWorklet)
    participant Nginx as rvt_web (Nginx Proxy)
    participant Core as rvt_ai (RVTSession)
    participant VAD as Silero VAD (ONNX CPU)
    participant Seg as Segmenter Buffer
    participant ASR as faster-whisper (GPU)
    participant MT as llama.cpp MT (GPU)
    actor UserB as Người B (Đọc tiếng Nhật)

    Note over UserA,UI: Bật MIC A (Touch Event mở AudioContext)
    UI->>Nginx: WSS Connect (subprotocol: rvt.v1, rvt.token.<token>)
    Nginx->>Core: Forward WSS Handshake
    Core-->>UI: session.ready (profile, pack_revision)
    UI->>Core: session.start (16kHz, pcm_s16le, sides: {A: auto, B: auto})
    UI->>Core: turn.start (side: "A")
    
    loop Mỗi khung 40ms (640 mẫu PCM16 LE)
        UI->>Core: Binary Chunk (1.280 bytes)
        Core->>VAD: process(chunk, session_vad_state)
        VAD-->>Core: speaking = true / false
        Core-->>UI: Event vad (side: "A", speaking: true)
        Core->>Seg: add_chunk(chunk, speaking)
        opt Đạt chu kỳ partial (800ms)
            Seg-->>Core: should_partial = true
            Core->>ASR: Transcribe partial audio (Non-blocking)
            ASR-->>Core: text (ví dụ: "mình đi...")
            Core-->>UI: Event asr.partial (text, utterance_id)
        end
    end

    Note over UserA,VAD: Người A ngừng nói (Im lặng ≥ 500ms)
    Seg-->>Core: should_final = true (Cắt câu, trả về full audio buffer)
    
    rect rgb(240, 248, 255)
        Note over Core,ASR: Suy luận ASR Final & Phân loại ngôn ngữ (LID)
        Core->>ASR: transcribe(audio_buffer, beam_size=1)
        ASR-->>Core: transcript="Hôm nay gặp lúc mấy giờ?", lang="vi", probs
        Core->>Core: pick_language(probs, side_prior) -> Quyết định "vi"
        Core-->>UI: Event asr.final (utterance_id, text, lang="vi", uncertain=false)
        UI-->>UserA: Hiện câu gốc tiếng Việt + nhãn [VI 98%]
    end

    rect rgb(255, 245, 238)
        Note over Core,MT: Dịch song song sang 2 ngôn ngữ còn lại (ja, en)
        par Dịch sang tiếng Nhật (Target: ja)
            Core->>MT: POST /v1/chat/completions (Stream: true, target="ja")
            loop Token Deltas
                MT-->>Core: SSE delta ("今日", "は何時", ...)
                Core-->>UI: Event mt.delta (target="ja", delta)
                UI-->>UserB: Stream chữ tiếng Nhật lớn trên nửa B
            end
            MT-->>Core: [DONE]
            Core->>Core: mt_validator.validate(target="ja") -> Pass Kanji/Kana
            Core-->>UI: Event mt.final (target="ja", text="今日は何時に会いましょうか？")
            UI-->>UserB: Hoàn thành câu dịch tiếng Nhật chữ lớn (≥22px)
        and Dịch sang tiếng Anh (Target: en)
            Core->>MT: POST /v1/chat/completions (Stream: true, target="en")
            loop Token Deltas
                MT-->>Core: SSE delta ("What", " time", ...)
                Core-->>UI: Event mt.delta (target="en", delta)
            end
            MT-->>Core: [DONE]
            Core->>Core: mt_validator.validate(target="en") -> Pass Latin
            Core-->>UI: Event mt.final (target="en", text="What time shall we meet today?")
            UI-->>UserA: Hiện bản dịch tiếng Anh nhỏ tự kiểm tra
            UI-->>UserB: Hiện bản dịch tiếng Anh nhỏ bên dưới bản tiếng Nhật
        end
    end
```

---

## 3. Máy trạng thái Cắt câu VAD & Quản lý Bộ đệm (Audio Segmenter State Machine)

```mermaid
stateDiagram-v2
    [*] --> SILENCE_BUFFERING: turn.start (Bắt đầu lượt)

    state SILENCE_BUFFERING {
        [*] --> RingBufferPreroll
        RingBufferPreroll --> RingBufferPreroll: Duy trì tối đa 300ms âm thanh gần nhất
    }

    SILENCE_BUFFERING --> SPEECH_DETECTED: VAD báo có tiếng nói (prob > 0.5)

    state SPEECH_DETECTED {
        [*] --> AccumulateSpeech
        AccumulateSpeech --> CheckMinSpeech: Đo độ dài tiếng nói
        CheckMinSpeech --> EmitPartial: Sau mỗi chu kỳ 800ms
        EmitPartial --> AccumulateSpeech
    }

    SPEECH_DETECTED --> SILENCE_COUNTDOWN: VAD báo hết tiếng nói
    SILENCE_COUNTDOWN --> SPEECH_DETECTED: Có tiếng nói trở lại trước 500ms

    SILENCE_COUNTDOWN --> TRIGGER_FINAL: Im lặng liên tục ≥ 500ms (min_silence)
    SPEECH_DETECTED --> TRIGGER_FINAL: Thời lượng nói ≥ 20s (hard_max)
    SPEECH_DETECTED --> TRIGGER_FINAL: Thời lượng ≥ 15s và có khoảng lặng ≥ 200ms (soft_max)

    SILENCE_COUNTDOWN --> DROP_NOISE: Tiếng nói trước đó < 250ms (ho, gõ bàn)
    DROP_NOISE --> SILENCE_BUFFERING: Reset buffer, tiếp tục nghe

    TRIGGER_FINAL --> ASR_MT_PIPELINE: Gửi audio hoàn chỉnh vào hàng đợi ASR
    ASR_MT_PIPELINE --> SILENCE_BUFFERING: Reset Segmenter, chờ câu kế tiếp

    SILENCE_BUFFERING --> [*]: turn.stop / Đổi bên mic
    SPEECH_DETECTED --> [*]: turn.stop (force_final)
```

---

## 4. Kiến trúc Hexagonal (Ports & Adapters) và Data Flow Backend

```mermaid
classDiagram
    direction TB

    namespace Contracts {
        class ClientEvent {
            <<Union Discriminator>>
            +SessionStart session_start
            +TurnStart turn_start
            +TurnStop turn_stop
            +UtteranceOverrideLang override_lang
            +SidesUpdate sides_update
            +Ping ping
        }

        class ServerEvent {
            <<Union Discriminator>>
            +SessionReady session_ready
            +Vad vad
            +AsrPartial asr_partial
            +AsrFinal asr_final
            +MtDelta mt_delta
            +MtFinal mt_final
            +ErrorEvent error
            +Pong pong
        }
    }

    namespace Ports_Protocols {
        class VadEngine {
            <<interface>>
            +create_state() VadState
            +process(chunk: bytes, state: VadState) bool
        }
        class AsrEngine {
            <<interface>>
            +transcribe(audio: bytes, language: Lang) Tuple
        }
        class MtEngine {
            <<interface>>
            +translate_stream(text: str, source: Lang, target: Lang) AsyncGenerator
        }
    }

    namespace Adapters_Engines {
        class SileroVadEngine {
            -session: ort.InferenceSession
            -window_size: 512
            +process(chunk, state) bool
        }
        class FasterWhisperEngine {
            -model: WhisperModel
            +transcribe(audio, language) Tuple
        }
        class LlamaCppMtEngine {
            -client: httpx.AsyncClient
            -timeout_sec: 5.0
            +translate_stream(text, src, tgt) AsyncGenerator
        }
        class FakeVadEngine { +process() bool }
        class FakeAsrEngine { +transcribe() Tuple }
        class FakeMtEngine { +translate_stream() AsyncGenerator }
    }

    namespace Core_Pipeline {
        class RVTSession {
            -session_id: str
            -vad_state: VadState
            -scheduler: AsrScheduler
            -segmenter: Segmenter
            -recent_audio: OrderedDict[int, bytes]
            +handle_session_start()
            +handle_audio_chunk()
            +handle_override_lang()
            +close()
        }
        class AsrScheduler {
            -_lock: asyncio.Lock
            +execute_transcribe(audio, force_lang, is_final)
        }
        class MtValidator {
            -_exact_cache: dict
            +validate(orig, src, tgt, raw) ValidationResult
        }
        class PackRegistry {
            +profiles: dict
            +revision: str
            +get_profile(name) ProfileConfig
        }
    }

    VadEngine <|.. SileroVadEngine
    VadEngine <|.. FakeVadEngine
    AsrEngine <|.. FasterWhisperEngine
    AsrEngine <|.. FakeAsrEngine
    MtEngine <|.. LlamaCppMtEngine
    MtEngine <|.. FakeMtEngine

    RVTSession --> VadEngine
    RVTSession --> AsrEngine
    RVTSession --> MtEngine
    RVTSession --> AsrScheduler
    RVTSession --> MtValidator
    RVTSession ..> ServerEvent : Emits
    RVTSession <.. ClientEvent : Consumes
```

---

## 5. Ma trận Quy tắc Hiển thị 3 Ngôn ngữ trên Web UI (Split-View Display Rules)

```mermaid
flowchart TD
    START(["Nhận sự kiện asr.final & mt.final"]) --> CHECK_LANG{"Ngôn ngữ phát hiện (L)<br/>thuộc tiếng chủ nào?"}

    CHECK_LANG -- "L trùng ngôn ngữ chủ Nửa A (ví dụ: vi)" --> CASE_A["Trường hợp A nói:"]
    CASE_A --> DISP_A1["Nửa A (Người nói):<br/>• Câu gốc tiếng Việt<br/>• Nhãn độ tin cậy [VI 98%]<br/>• Tiếng thứ ba (en) chữ nhỏ"]
    CASE_A --> DISP_B1["Nửa B (Người nghe):<br/>• Bản dịch tiếng Nhật CHỮ LỚN (≥22px)<br/>• Tiếng thứ ba (en) chữ nhỏ bên dưới"]

    CHECK_LANG -- "L trùng ngôn ngữ chủ Nửa B (ví dụ: ja)" --> CASE_B["Trường hợp B nói:"]
    CASE_B --> DISP_B2["Nửa B (Người nói):<br/>• Câu gốc tiếng Nhật<br/>• Nhãn độ tin cậy [JA 99%]<br/>• Tiếng thứ ba (en) chữ nhỏ"]
    CASE_B --> DISP_A2["Nửa A (Người nghe):<br/>• Bản dịch tiếng Việt CHỮ LỚN (≥22px)<br/>• Tiếng thứ ba (en) chữ nhỏ bên dưới"]

    CHECK_LANG -- "L là tiếng thứ ba (ví dụ: en)<br/>Không nửa nào sở hữu" --> CASE_C["Trường hợp nói tiếng thứ ba:"]
    CASE_C --> DISP_A3["Nửa A: Bản dịch tiếng Việt CHỮ LỚN<br/>(kèm câu gốc tiếng Anh chữ nhỏ)"]
    CASE_C --> DISP_B3["Nửa B: Bản dịch tiếng Nhật CHỮ LỚN<br/>(kèm câu gốc tiếng Anh chữ nhỏ)"]

    subgraph OVERRIDE["Chức năng Chạm để Sửa Ngôn ngữ (Language Override)"]
        TAP["Chạm vào nhãn [VI ?] hoặc badge"] --> MODAL["Hiện Modal: chọn lại tiếng (VI / JA / EN)"]
        MODAL --> SEND_OVERRIDE["Gửi utterance.override_lang"]
        SEND_OVERRIDE --> RE_ASR["Server lấy audio đệm LRU -> Re-decode ASR -> Re-translate 2 MT"]
        RE_ASR --> UPDATE_UI["Cập nhật lại toàn bộ chữ trên cả hai nửa"]
    end
```

---

## 6. Quy trình Triển khai & Khởi động Dự án (Deployment Lifecycle)

```mermaid
flowchart LR
    subgraph PREPARE["1. Chuẩn bị môi trường"]
        STEP1["make setup<br/>• uv sync (ai)<br/>• npm install (web)"]
        STEP2["make tls<br/>• Tạo cert.pem & key.pem<br/>• Cấp cho LAN IP máy GPU"]
        STEP3["Tải Models<br/>• silero_vad.onnx<br/>• mt-model.gguf"]
    end

    subgraph DOCKER_BUILD["2. Khởi tạo Container"]
        BUILD_AI["Build rvt_ai<br/>• CUDA 12.1 runtime<br/>• Python 3.12 + uv"]
        BUILD_WEB["Build rvt_web<br/>• Multi-stage Node 22 -> Nginx"]
        RUN_MT["Khởi động rvt_mt<br/>• llama.cpp server-cuda<br/>• GPU :8080"]
    end

    subgraph HEALTH_CHECK["3. Kiểm tra Readiness"]
        HC_MT["Health MT: curl /health"]
        HC_AI["Health AI: /health/ready"]
        HC_WEB["Nginx sẵn sàng :8443"]
    end

    subgraph VERIFY["4. Nghiệm thu Chất lượng"]
        TEST_INT["make test<br/>• 13 Pytest (100% Pass)<br/>• 3 Vitest (100% Pass)"]
        TEST_E2E["make test-e2e<br/>• Playwright Chromium (Pass)"]
        SMOKE["make smoke<br/>• WebSocket Live Round-trip"]
    end

    PREPARE --> DOCKER_BUILD
    DOCKER_BUILD --> HEALTH_CHECK
    HEALTH_CHECK --> VERIFY
```
