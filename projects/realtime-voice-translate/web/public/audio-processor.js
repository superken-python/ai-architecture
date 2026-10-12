class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetRate = 16000;
    this.bufferSize = 640; // 40ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;
    this.resamplePhase = 0.0;

    // Antialiasing biquad lowpass filter for downsampling when sampleRate > 16kHz (cutoff ~7.5kHz)
    const sourceRate = sampleRate;
    if (sourceRate > 16000) {
      const cutoff = 7500;
      const w0 = (2 * Math.PI * cutoff) / sourceRate;
      const alpha = Math.sin(w0) / (2 * 0.7071);
      const cosw0 = Math.cos(w0);
      const a0 = 1 + alpha;
      this.filter = {
        b0: (1 - cosw0) / (2 * a0),
        b1: (1 - cosw0) / a0,
        b2: (1 - cosw0) / (2 * a0),
        a1: (-2 * cosw0) / a0,
        a2: (1 - alpha) / a0,
        x1: 0,
        x2: 0,
        y1: 0,
        y2: 0,
      };
    } else {
      this.filter = null;
    }

    // Listen on port to keep worklet alive and respond to main thread watchdog pings
    this.port.onmessage = () => {
      // Keep worker alive
    };
  }

  process(inputs, outputs, parameters) {
    // Keep output faintly non-zero (1e-6) so WebKit/Safari does not mark this node as dead/silent
    const output = outputs[0];
    if (output && output[0]) {
      output[0].fill(1e-6);
    }

    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }

    const ch0 = input[0];
    if (!ch0 || ch0.length === 0) {
      return true;
    }

    const numChannels = input.length;
    const hasStereo = numChannels >= 2 && input[1] && input[1].length > 0;
    const ch1 = hasStereo ? input[1] : null;
    const inputLen = ch0.length;

    // 1. Stereo downmixing & optional antialiasing filtering into a mono buffer
    const mono = new Float32Array(inputLen);
    const filt = this.filter;

    for (let i = 0; i < inputLen; i++) {
      let x = hasStereo ? (ch0[i] + ch1[i]) * 0.5 : ch0[i];
      if (filt) {
        const y = filt.b0 * x + filt.b1 * filt.x1 + filt.b2 * filt.x2 - filt.a1 * filt.y1 - filt.a2 * filt.y2;
        filt.x2 = filt.x1;
        filt.x1 = x;
        filt.y2 = filt.y1;
        filt.y1 = y;
        mono[i] = y;
      } else {
        mono[i] = x;
      }
    }

    const sourceRate = sampleRate; // Global AudioWorklet sampleRate
    const ratio = sourceRate / this.targetRate;

    if (Math.abs(ratio - 1.0) < 0.01) {
      // Direct copy (already 16kHz)
      for (let i = 0; i < inputLen; i++) {
        let s = Math.max(-1, Math.min(1, mono[i]));
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        if (this.bufferIndex >= this.bufferSize) {
          this.port.postMessage(this.buffer.buffer, [this.buffer.buffer]);
          this.buffer = new Int16Array(this.bufferSize);
          this.bufferIndex = 0;
        }
      }
    } else {
      // Linear interpolation resampler with antialiased mono audio
      let phase = this.resamplePhase;

      while (phase < inputLen) {
        const i0 = Math.floor(phase);
        const i1 = Math.min(i0 + 1, inputLen - 1);
        const frac = phase - i0;
        const s0 = mono[i0];
        const s1 = mono[i1];
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
