import { useStore, Side, SupportedLang } from '../state/useStore';

class RVTClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioProcessor: AudioWorkletNode | null = null;
  private reconnectTimer: any = null;
  private pingInterval: any = null;
  private audioWatchdog: any = null;
  private url: string = "";

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
        // Send session.start
        const store = useStore.getState();
        const targets = store.meetingMode && store.sideBLang !== 'auto'
          ? [store.sideBLang]
          : undefined;

        this.send({
          type: "session.start",
          protocol: 1,
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

        // Heartbeat ping every 10s to keep connection alive through long pauses/silence
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
        }
        this.pingInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({ type: "ping", t: Date.now() });
          }
        }, 10000);
      };

      this.ws.onclose = () => {
        useStore.getState().setConnected(false);
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
          this.pingInterval = null;
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

  async startAudio(side: Side, source: 'mic' | 'tab' = 'mic') {
    try {
      // Clean up any ongoing audio stream first
      this.stopAudio();

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

      // Periodic watchdog (every 2.5s) to guarantee AudioContext doesn't stay suspended during silence
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
        }
      }, 2500);

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

      // Ensure AudioContext wakes up if hardware track un-mutes
      this.mediaStream.getTracks().forEach((track) => {
        track.onunmute = () => {
          console.log("Audio track unmuted, ensuring AudioContext running...");
          if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume().catch(() => {});
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
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(event.data); // ArrayBuffer PCM16 LE 40ms
          chunkCount++;
          if (chunkCount === 1) {
            console.log("🎙 First audio chunk sent successfully to WebSocket server");
          } else if (chunkCount % 25 === 0) {
            console.log(`🎙 Đang gửi audio: ${chunkCount} chunks (${(chunkCount * 0.04).toFixed(1)}s)`);
          }
        }
      };

      // Connect through a zero-gain node to keep audio engine active without echo feedback
      const muteGain = this.audioContext.createGain();
      muteGain.gain.value = 0;
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

  stopAudio() {
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
      : undefined;

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
}

export const rvtClient = new RVTClient();
