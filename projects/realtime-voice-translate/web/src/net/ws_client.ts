import { useStore, Side, SupportedLang } from '../state/useStore';

function getClientId(): string {
  try {
    let id = localStorage.getItem('rvt_client_id');
    if (!id) {
      id = 'cli-' + Math.random().toString(36).substring(2, 10);
      localStorage.setItem('rvt_client_id', id);
    }
    return id;
  } catch {
    return 'cli-default';
  }
}

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

  constructor() {
    if (typeof document !== 'undefined') {
      const checkStateOnForeground = () => {
        const store = useStore.getState();
        if (store.isMicActive) {
          if (this.audioContext && (this.audioContext.state === 'suspended' || (this.audioContext.state as any) === 'interrupted')) {
            this.audioContext.resume().catch(() => {});
            useStore.getState().setCaptureWarning("Trang vừa quay lại từ chế độ nền. Chạm vào màn hình để tiếp tục nghe.");
          }
          const track = this.mediaStream?.getAudioTracks()[0];
          if (track && (track.muted || track.readyState === 'ended')) {
            useStore.getState().setCaptureWarning("Microphone đã bị gián đoạn khi chuyển ứng dụng. Chạm để bật lại.");
          }
        }
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

    try {
      this.ws = new WebSocket(url, "rvt.v1");
      this.ws.binaryType = "arraybuffer";

      this.ws.onopen = () => {
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
          client_id: getClientId(),
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
              this.ws.close();
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

      this.ws.onclose = (event: CloseEvent) => {
        useStore.getState().setConnected(false);
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
          this.pingInterval = null;
        }
        if (this.healthInterval) {
          clearInterval(this.healthInterval);
          this.healthInterval = null;
        }

        if (event.code === 4429) {
          useStore.getState().setError("Máy chủ hiện đang đầy phiên xử lý (tối đa 4 phiên). Vui lòng thử lại sau giây lát.");
        }

        // Do NOT destroy audio capture if mic is still active; allow seamless reconnect
        if (!useStore.getState().isMicActive) {
          this.stopAudio();
        }

        // Auto-reconnect with 2s backoff
        this.reconnectTimer = setTimeout(() => {
          this.connect(this.url);
        }, 2000);
      };

      this.ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        useStore.getState().setError("Lỗi kết nối WebSocket tới máy chủ. Vui lòng kiểm tra lại chứng chỉ SSL hoặc kết nối mạng.");
      };

      const isDebug = typeof window !== 'undefined' && window.location.search.includes('debug=1');

      this.ws.onmessage = (event) => {
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
        audioTracks[0].onended = () => {
          this.stopAudio();
        };
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

      // Ensure AudioContext wakes up if hardware track un-mutes or warn if muted/ended
      this.mediaStream.getTracks().forEach((track) => {
        track.onmute = () => {
          console.warn("Audio track MUTED by browser/system");
          useStore.getState().setCaptureWarning("Microphone đã bị tạm dừng bởi hệ thống hoặc tab khác. Chạm vào màn hình để tiếp tục nghe.");
        };
        track.onunmute = () => {
          console.log("Audio track UNMUTED");
          useStore.getState().setCaptureWarning(null);
          if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume().catch(() => {});
          }
        };
        track.onended = () => {
          console.warn("Audio track ENDED");
          useStore.getState().setCaptureWarning("Microphone đã bị đóng. Chạm để bật lại.");
        };
      });

      if (!this.workletLoaded) {
        await this.audioContext.audioWorklet.addModule('/audio-processor.js');
        this.workletLoaded = true;
      }

      const audioSourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.audioProcessor = new AudioWorkletNode(this.audioContext, 'audio-processor');

      let chunkCount = 0;
      let silentChunkCount = 0;
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

        if (energy > 0) {
          if (silentChunkCount >= 50 && useStore.getState().captureWarning?.includes("im lặng số")) {
            useStore.getState().setCaptureWarning(null);
          }
          silentChunkCount = 0;
        } else {
          silentChunkCount++;
          if (silentChunkCount === 50) {
            console.warn("Received 2s of continuous digital zero audio. Track may be muted by OS.");
            useStore.getState().setCaptureWarning("Microphone đang nhận toàn số 0 (im lặng số). Chạm để khôi phục thu âm.");
          }
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
    } catch (err) {
      console.error("Audio capture failed:", err);
      useStore.getState().setError(`Lỗi thu âm: ${(err as Error).message || "Không thể truy cập nguồn âm"}`);
      useStore.getState().setMicActive(false);
      useStore.getState().setActiveSide(null);
    }
  }

  async resumeCapture() {
    useStore.getState().setCaptureWarning(null);
    if (this.audioContext && (this.audioContext.state === 'suspended' || (this.audioContext.state as any) === 'interrupted')) {
      await this.audioContext.resume().catch(() => {});
    }
    const store = useStore.getState();
    const track = this.mediaStream?.getAudioTracks()[0];
    if (!track || track.readyState === 'ended') {
      if (store.activeSide) {
        await this.startAudio(store.activeSide, store.audioSource);
      }
    }
  }

  stopAudio() {
    useStore.getState().setCaptureWarning(null);
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
