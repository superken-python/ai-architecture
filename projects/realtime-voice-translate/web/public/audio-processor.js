class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetRate = 16000;
    this.bufferSize = 640; // 40ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;
    this.resamplePhase = 0.0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }

    const channel = input[0];
    if (!channel || channel.length === 0) {
      return true;
    }

    const sourceRate = sampleRate; // Global AudioWorklet sampleRate
    const ratio = sourceRate / this.targetRate;

    if (Math.abs(ratio - 1.0) < 0.01) {
      // Direct copy (already 16kHz)
      for (let i = 0; i < channel.length; i++) {
        let s = Math.max(-1, Math.min(1, channel[i]));
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        if (this.bufferIndex >= this.bufferSize) {
          this.port.postMessage(this.buffer.buffer, [this.buffer.buffer]);
          this.buffer = new Int16Array(this.bufferSize);
          this.bufferIndex = 0;
        }
      }
    } else {
      // Linear interpolation resampler
      let phase = this.resamplePhase;
      const inputLen = channel.length;

      while (phase < inputLen) {
        const i0 = Math.floor(phase);
        const i1 = Math.min(i0 + 1, inputLen - 1);
        const frac = phase - i0;
        const s0 = channel[i0];
        const s1 = channel[i1];
        let s = s0 + frac * (s1 - s0);

        s = Math.max(-1, Math.min(1, s));
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

        if (this.bufferIndex >= this.bufferSize) {
          this.port.postMessage(this.buffer.buffer, [this.buffer.buffer]);
          this.buffer = new Int16Array(this.bufferSize);
          this.bufferIndex = 0;
        }

        phase += ratio;
      }
      this.resamplePhase = phase - inputLen;
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
