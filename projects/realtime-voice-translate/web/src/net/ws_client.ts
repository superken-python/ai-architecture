import { useStore, Side, SupportedLang } from '../state/useStore';
import { isWakeLockHeld, requestWakeLock } from '../audio/wake-lock';
import type { CaptureProblem, CaptureSource } from './capture_health';
import {
  REPLACED_CLOSE_CODE,
  captureMessage,
  detectCaptureProblem,
  needsNewCapture,
  newClientId,
  wsUrlWithClientId,
} from './capture_health';

class RVTClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioProcessor: AudioWorkletNode | null = null;
  private reconnectTimer: any = null;
  private pingInterval: any = null;
  private healthInterval: any = null;
  private audioWatchdog: any = null;
  private url: string = "";
  private lastServerMessageAt: number = 0;
  private totalChunksSent: number = 0;
  private lastRmsDbfs: number | null = null;
  // Mỗi trang một mã, chỉ trong bộ nhớ (docs 08 §4.3): để chính trang này thay được kết nối "chết" của mình khi nối lại.
  // Bản cũ lưu trong localStorage nên mọi tab dùng chung một mã và đá nhau mỗi 2 s.
  private readonly clientId: string = newClientId();
  private captureSource: CaptureSource = 'mic';
  private zeroSince: number = 0;
  private contextBadSince: number = 0;
  private listenTimer: any = null;

  constructor() {
    if (typeof document !== 'undefined') {
      // Trang quay lại từ nền: thử chạy lại AudioContext (có trình duyệt cho phép không cần chạm), rồi để phép kiểm
      // "đang nghe" quyết định có cần hiện "Chạm để tiếp tục" hay không (docs 08 §4.1)
      const checkStateOnForeground = () => {
        if (!useStore.getState().isMicActive) return;
        if (this.audioContext && this.audioContext.state !== 'running') {
          this.audioContext.resume().catch(() => {});
        }
        setTimeout(() => this.checkListening(), 300);
      };
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          checkStateOnForeground();
        }
      });
      window.addEventListener('pageshow', checkStateOnForeground);
    }
  }

  async connect(url: string) {
    this.url = url;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Đóng kết nối cũ nếu còn (ví dụ React StrictMode gọi connect hai lần): sự kiện của nó sẽ bị bỏ qua
    if (this.ws) {
      const previous = this.ws;
      this.ws = null;
      try {
        previous.close();
      } catch (_) {}
    }

    try {
      const socket = new WebSocket(wsUrlWithClientId(url, this.clientId), "rvt.v1");
      socket.binaryType = "arraybuffer";
      this.ws = socket;

      // Mọi handler bỏ qua sự kiện của một kết nối đã bị thay (watchdog, nối lại): sự kiện close đến muộn của kết nối cũ
      // không được làm mất kết nối hiện tại
      socket.onopen = () => {
        if (this.ws !== socket) return;
        useStore.getState().setConnected(true);
        this.lastServerMessageAt = Date.now();
        // Send session.start
        const store = useStore.getState();
        const targets = store.meetingMode && store.sideBLang !== 'auto'
          ? [store.sideBLang]
          : ['ja', 'en', 'vi'];

        this.send({
          type: "session.start",
          protocol: 1,
          client_id: this.clientId,
          audio: { rate: 16000, format: "pcm_s16le" },
          sides: {
            A: { lang: store.sideALang },
            B: { lang: store.sideBLang }
          },
          targets
        });

        // If mic/turn was active before reconnect, re-register turn immediately
        if (store.isMicActive && store.activeSide) {
          console.log(`🎙️ WebSocket reconnected: re-issuing turn.start on Side ${store.activeSide}`);
          this.send({ type: "turn.start", side: store.activeSide });
        }

        // Heartbeat ping every 2.5s to keep connection alive and detect half-open sockets
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
        }
        this.pingInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({ type: "ping", t: Date.now() });
            if (this.lastServerMessageAt > 0 && Date.now() - this.lastServerMessageAt > 8000) {
              console.warn("Watchdog: No server message in 8s. Connection dead, reconnecting...");
              // Không chờ sự kiện close: với kết nối nửa mở, trình duyệt có thể rất lâu mới báo đóng
              const dead = this.ws;
              this.handleDisconnect(1006);
              try {
                dead.close();
              } catch (_) {}
            }
          }
        }, 2500);

        // Health telemetry every 5s (Mục 9.3 docs 07)
        if (this.healthInterval) {
          clearInterval(this.healthInterval);
        }
        this.healthInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const track = this.mediaStream?.getAudioTracks()[0];
            this.send({
              type: "client.health",
              audio_context_state: this.audioContext?.state || "none",
              track_muted: track ? track.muted : false,
              track_ended: track ? track.readyState === 'ended' : false,
              rms_dbfs: this.lastRmsDbfs,
              chunks_sent: this.totalChunksSent,
              document_visible: typeof document !== 'undefined' ? document.visibilityState === 'visible' : true
            });
          }
        }, 5000);
      };

      socket.onclose = (event: CloseEvent) => {
        if (this.ws !== socket) return;
        this.handleDisconnect(event.code);
      };

      socket.onerror = (err) => {
        if (this.ws !== socket) return;
        console.error("WebSocket error:", err);
        useStore.getState().setError("Lỗi kết nối WebSocket tới máy chủ. Vui lòng kiểm tra lại chứng chỉ SSL hoặc kết nối mạng.");
      };

      const isDebug = typeof window !== 'undefined' && window.location.search.includes('debug=1');

      socket.onmessage = (event) => {
        if (this.ws !== socket) return;
        this.lastServerMessageAt = Date.now();
        if (typeof event.data === "string") {
          try {
            const payload = JSON.parse(event.data);
            if (isDebug) {
              console.log("📩 [Server Event]", payload.type, payload);
            }
            useStore.getState().handleServerEvent(payload);
          } catch (e) {
            console.error("Failed to parse server message:", e);
          }
        }
      };
    } catch (e) {
      console.error("WebSocket connection failure:", e);
      useStore.getState().setError(`Lỗi kết nối: ${(e as Error).message}`);
    }
  }

  private handleDisconnect(code: number) {
    this.ws = null;
    useStore.getState().setConnected(false);
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.healthInterval) {
      clearInterval(this.healthInterval);
      this.healthInterval = null;
    }

    if (code === 4429) {
      useStore.getState().setError("Máy chủ hiện đang đầy phiên xử lý (tối đa 4 phiên). Vui lòng thử lại sau giây lát.");
    }
    if (code === REPLACED_CLOSE_CODE) {
      // Server đã thay kết nối này bằng một kết nối mới cùng mã: tự nối lại thì hai bên sẽ đá nhau mãi (docs 08 §4.3)
      useStore.getState().setError("Phiên này đã được mở lại ở một kết nối khác. Tải lại trang để tiếp tục dùng ở đây.");
      this.stopAudio();
      return;
    }

    // Do NOT destroy audio capture if mic is still active; allow seamless reconnect
    if (!useStore.getState().isMicActive) {
      this.stopAudio();
    }

    // Auto-reconnect with 2s backoff
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.url);
    }, 2000);
  }

  send(data: object) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const isDebug = typeof window !== 'undefined' && window.location.search.includes('debug=1');
      if (isDebug) {
        console.log("📤 [Client Send]", (data as any).type || "raw", data);
      }
      this.ws.send(JSON.stringify(data));
    }
  }

  sendAudioChunk(data: ArrayBuffer) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  private workletLoaded: boolean = false;

  private lastChunkTime: number = 0;

  async startAudio(side: Side, source: 'mic' | 'tab' = 'mic') {
    try {
      // Xin giữ màn hình sáng ngay trong lần chạm bật mic: iOS có thể từ chối khi không có thao tác (docs 08 §4.5)
      void requestWakeLock();

      // Clean up any ongoing audio stream first
      this.stopAudio();
      this.lastChunkTime = 0;

      // 1. Initialize AudioContext immediately on user gesture (required for iOS Safari)
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new AudioCtx();
      }
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Auto-resume AudioContext if browser suspends it during silence/inactivity
      this.audioContext.onstatechange = () => {
        const state = this.audioContext?.state;
        if (useStore.getState().isMicActive && (state === 'suspended' || (state as any) === 'interrupted')) {
          console.log("AudioContext suspended/interrupted during silence, auto-resuming...");
          this.audioContext?.resume().catch((e) => console.warn("Failed to auto-resume AudioContext:", e));
        }
      };

      // Periodic watchdog (every 1.5s) to guarantee AudioContext and Worklet don't sleep during silence in Safari
      if (this.audioWatchdog) {
        clearInterval(this.audioWatchdog);
      }
      this.audioWatchdog = setInterval(() => {
        if (useStore.getState().isMicActive && this.audioContext) {
          const state = this.audioContext.state;
          if (state === 'suspended' || (state as any) === 'interrupted') {
            console.log("Watchdog: waking up suspended AudioContext after silence...");
            this.audioContext.resume().catch(() => {});
          }

          // Safari keep-alive: check if audio chunks stalled during quiet scene
          const now = Date.now();
          if (this.lastChunkTime > 0 && now - this.lastChunkTime > 2000) {
            console.warn("Watchdog: audio chunks stalled during quiet period. Pinging worklet & resuming AudioContext...");
            this.audioContext.resume().catch(() => {});
            try {
              this.audioProcessor?.port.postMessage('ping');
            } catch (_) {}
          }
        }
      }, 1500);

      // 2. Notify backend immediately that turn started
      this.send({ type: "turn.start", side });
      useStore.getState().setMicActive(true);
      useStore.getState().setActiveSide(side);

      // 3. Request audio source (mic or tab/screen audio)
      if (source === 'tab') {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
          throw new Error("Trình duyệt không hỗ trợ chia sẻ âm thanh Tab/Màn hình (chỉ hỗ trợ trên máy tính)");
        }
        this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: {
            channelCount: 1,
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
          }
        });
        const audioTracks = this.mediaStream.getAudioTracks();
        if (audioTracks.length === 0) {
          this.stopAudio();
          throw new Error("Bạn chưa tích chọn ô 'Chia sẻ âm thanh' (Share audio) của tab!");
        }
      } else {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      }

      // Track đổi trạng thái thì kiểm lại ngay, không đợi lượt kiểm mỗi giây (docs 08 §4.1). Thu âm tab: bấm "Dừng chia
      // sẻ" của trình duyệt thì tắt thu như trước (docs 08 §4.2).
      this.mediaStream.getTracks().forEach((track) => {
        track.onmute = () => {
          console.warn(`${track.kind} track MUTED by browser/system`);
          this.checkListening();
        };
        track.onunmute = () => {
          console.log(`${track.kind} track UNMUTED`);
          if (this.audioContext && this.audioContext.state !== 'running') {
            this.audioContext.resume().catch(() => {});
          }
          this.checkListening();
        };
        track.onended = () => {
          console.warn(`${track.kind} track ENDED`);
          if (source === 'tab') {
            this.stopAudio();
          } else {
            this.checkListening();
          }
        };
      });

      if (!this.workletLoaded) {
        await this.audioContext.audioWorklet.addModule('/audio-processor.js');
        this.workletLoaded = true;
      }

      const audioSourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.audioProcessor = new AudioWorkletNode(this.audioContext, 'audio-processor');

      let chunkCount = 0;
      this.audioProcessor.port.onmessage = (event) => {
        this.lastChunkTime = Date.now();
        const pcm = new Int16Array(event.data);
        let sumSq = 0;
        let energy = 0;
        for (let i = 0; i < pcm.length; i++) {
          energy += Math.abs(pcm[i]);
          const norm = pcm[i] / 32768.0;
          sumSq += norm * norm;
        }
        const rms = Math.sqrt(sumSq / Math.max(1, pcm.length));
        this.lastRmsDbfs = rms > 1e-5 ? Math.round(20 * Math.log10(rms)) : -96;

        // Chuỗi khung toàn số 0: phép kiểm "đang nghe" báo sau 2 s (chỉ với mic)
        if (energy > 0) {
          this.zeroSince = 0;
        } else if (this.zeroSince === 0) {
          this.zeroSince = this.lastChunkTime;
        }

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(event.data); // ArrayBuffer PCM16 LE 40ms
          chunkCount++;
          this.totalChunksSent++;
          if (chunkCount === 1) {
            console.log("🎙 First audio chunk sent successfully to WebSocket server");
          } else if (chunkCount % 25 === 0) {
            console.log(`🎙 Đang gửi audio: ${chunkCount} chunks (${(chunkCount * 0.04).toFixed(1)}s, ${this.lastRmsDbfs}dBFS)`);
          }
        }
      };

      // Connect through a near-zero node (0.00001 = -100dB) to prevent WebKit from pruning the render quantum on silence
      const muteGain = this.audioContext.createGain();
      muteGain.gain.value = 0.00001;
      audioSourceNode.connect(this.audioProcessor);
      this.audioProcessor.connect(muteGain);
      muteGain.connect(this.audioContext.destination);

      // Phép kiểm "đang nghe" mỗi giây (docs 08 §4.1)
      this.captureSource = source;
      this.lastChunkTime = Date.now();
      this.zeroSince = 0;
      this.contextBadSince = 0;
      if (this.listenTimer) {
        clearInterval(this.listenTimer);
      }
      this.listenTimer = setInterval(() => this.checkListening(), 1000);
    } catch (err) {
      console.error("Audio capture failed:", err);
      useStore.getState().setError(`Lỗi thu âm: ${(err as Error).message || "Không thể truy cập nguồn âm"}`);
      useStore.getState().setMicActive(false);
      useStore.getState().setActiveSide(null);
    }
  }

  private currentProblem(): CaptureProblem | null {
    if (!this.mediaStream) return null;
    const now = Date.now();
    const contextState = (this.audioContext?.state as string | undefined) ?? 'none';
    if (contextState === 'running') {
      this.contextBadSince = 0;
    } else if (this.contextBadSince === 0) {
      this.contextBadSince = now;
    }
    const track = this.mediaStream.getAudioTracks()[0];
    return detectCaptureProblem({
      source: this.captureSource,
      trackState: !track ? 'none' : track.readyState === 'ended' ? 'ended' : 'live',
      trackMuted: !!track?.muted,
      contextState,
      now,
      lastChunkAt: this.lastChunkTime,
      zeroSince: this.zeroSince,
      contextBadSince: this.contextBadSince,
    });
  }

  // Phép kiểm "đang nghe" (docs 08 §4.1): chạy mỗi giây và ngay khi track đổi trạng thái. Cảnh báo còn hiện chừng nào
  // lỗi còn, và tự tắt khi hết lỗi — không còn cảnh báo một lần rồi thôi.
  private checkListening() {
    const store = useStore.getState();
    if (!store.isMicActive || !this.mediaStream) return;
    const problem = this.currentProblem();
    const message = problem ? captureMessage(problem, this.captureSource) : null;
    if (store.captureWarning !== message) {
      store.setCaptureWarning(message);
    }
    const held = isWakeLockHeld();
    if (store.wakeLockHeld !== held) {
      store.setWakeLockHeld(held);
    }
  }

  // Gọi trong lần chạm vào cảnh báo: iOS chỉ cho chạy lại AudioContext và xin lại mic khi có thao tác của người dùng
  async resumeCapture() {
    const store = useStore.getState();
    if (!store.isMicActive || !store.activeSide) {
      store.setCaptureWarning(null);
      return;
    }
    const problem = this.currentProblem();
    void requestWakeLock();
    if (this.audioContext && this.audioContext.state !== 'running') {
      await this.audioContext.resume().catch(() => {});
    }
    if (needsNewCapture(problem)) {
      // Dừng luồng cũ rồi xin lại mic/tab ngay trong lần chạm: trên Safari đây là cách lấy lại mic từ trang/app khác
      await this.startAudio(store.activeSide, this.captureSource);
    }
    this.checkListening();
    setTimeout(() => this.checkListening(), 1500);
  }

  stopAudio() {
    useStore.getState().setCaptureWarning(null);
    if (this.listenTimer) {
      clearInterval(this.listenTimer);
      this.listenTimer = null;
    }
    if (this.audioWatchdog) {
      clearInterval(this.audioWatchdog);
      this.audioWatchdog = null;
    }
    if (this.audioProcessor) {
      this.audioProcessor.disconnect();
      this.audioProcessor = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
      this.workletLoaded = false;
    }

    useStore.getState().setMicActive(false);
    useStore.getState().setActiveSide(null);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.send({ type: "turn.stop" });
    }
  }

  updateSides(sideA: SupportedLang, sideB: SupportedLang) {
    const store = useStore.getState();
    const targets = store.meetingMode && sideB !== 'auto'
      ? [sideB]
      : ['ja', 'en', 'vi'];

    this.send({
      type: "sides.update",
      sides: {
        A: { lang: sideA },
        B: { lang: sideB }
      },
      targets
    });
  }

  overrideLang(utteranceId: number, lang: "ja" | "en" | "vi") {
    this.send({
      type: "utterance.override_lang",
      utterance_id: utteranceId,
      lang: lang
    });
  }

  getDebugStats() {
    const track = this.mediaStream?.getAudioTracks()[0];
    return {
      audioContextState: this.audioContext?.state || "none",
      trackReadyState: track?.readyState || "none",
      trackMuted: track?.muted || false,
      trackEnabled: track?.enabled || false,
      chunksSent: this.totalChunksSent,
      rmsDbfs: this.lastRmsDbfs,
      wsState: this.ws ? (this.ws.readyState === 1 ? "OPEN" : this.ws.readyState === 0 ? "CONNECTING" : "CLOSED") : "NONE",
      lastServerMsgSecAgo: this.lastServerMessageAt > 0 ? ((Date.now() - this.lastServerMessageAt) / 1000).toFixed(1) : "none",
      docVisible: typeof document !== 'undefined' ? document.visibilityState : "unknown"
    };
  }
}

export const rvtClient = new RVTClient();
