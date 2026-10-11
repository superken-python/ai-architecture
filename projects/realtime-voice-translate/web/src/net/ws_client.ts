import { useStore, Side, SupportedLang } from '../state/useStore';

class RVTClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioProcessor: AudioWorkletNode | null = null;
  private reconnectTimer: any = null;
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
        this.send({
          type: "session.start",
          protocol: 1,
          audio: { rate: 16000, format: "pcm_s16le" },
          sides: {
            A: { lang: store.sideALang },
            B: { lang: store.sideBLang }
          }
        });
      };

      this.ws.onclose = () => {
        useStore.getState().setConnected(false);
        this.stopAudio();
        // Auto-reconnect with 2s backoff
        this.reconnectTimer = setTimeout(() => {
          this.connect(this.url);
        }, 2000);
      };

      this.ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        useStore.getState().setError("Lỗi kết nối WebSocket tới máy chủ. Vui lòng kiểm tra lại chứng chỉ SSL hoặc kết nối mạng.");
      };

      this.ws.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const payload = JSON.parse(event.data);
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
      this.ws.send(JSON.stringify(data));
    }
  }

  async startAudio(side: Side) {
    try {
      // Clean up any ongoing audio stream first
      this.stopAudio();

      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.audioContext = new AudioContext();
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      await this.audioContext.audioWorklet.addModule('/audio-processor.js');

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.audioProcessor = new AudioWorkletNode(this.audioContext, 'audio-processor');

      let chunkCount = 0;
      this.audioProcessor.port.onmessage = (event) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(event.data); // ArrayBuffer PCM16 LE 40ms
          chunkCount++;
          if (chunkCount === 1) {
            console.log("🎙 First audio chunk sent successfully to WebSocket server");
          }
        }
      };

      // Connect through a zero-gain node to keep audio engine active without echo feedback
      const muteGain = this.audioContext.createGain();
      muteGain.gain.value = 0;
      source.connect(this.audioProcessor);
      this.audioProcessor.connect(muteGain);
      muteGain.connect(this.audioContext.destination);

      useStore.getState().setMicActive(true);
      useStore.getState().setActiveSide(side);

      // Notify backend that turn started
      this.send({ type: "turn.start", side });
    } catch (err) {
      console.error("Microphone capture failed:", err);
      useStore.getState().setError(`Lỗi Micro: ${(err as Error).message || "Không thể truy cập microphone"}`);
      useStore.getState().setMicActive(false);
      useStore.getState().setActiveSide(null);
    }
  }

  stopAudio() {
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
    }

    useStore.getState().setMicActive(false);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.send({ type: "turn.stop" });
    }
  }

  updateSides(sideA: SupportedLang, sideB: SupportedLang) {
    this.send({
      type: "sides.update",
      sides: {
        A: { lang: sideA },
        B: { lang: sideB }
      }
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
