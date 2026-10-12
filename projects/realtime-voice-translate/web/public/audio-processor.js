// Lọc thông thấp FIR trước khi hạ mẫu xuống 16 kHz (docs 08 §4.4): 63 tap, cửa sổ Hamming, cắt 7 kHz. Ở 48 kHz: phẳng
// tới 5,8 kHz, giảm 31 dB ở 8 kHz (tần số Nyquist mới) và ít nhất 58 dB từ 9 kHz, nên âm 8–24 kHz của nhạc nền, tiếng
// động không gập vào dải lời nói. Đo trên golden_1: aliasing −58 dB so với lời (biquad bậc 2 trước đây: −33 dB). Trễ 31
// mẫu (0,65 ms ở 48 kHz).
const FIR_TAPS = 63;
const FIR_CUTOFF_HZ = 7000;

function designLowpass(taps, cutoffHz, rate) {
  const fc = cutoffHz / rate;
  const mid = (taps - 1) / 2;
  const h = new Float32Array(taps);
  let sum = 0;
  for (let i = 0; i < taps; i++) {
    const x = i - mid;
    const sinc = x === 0 ? 2 * fc : Math.sin(2 * Math.PI * fc * x) / (Math.PI * x);
    h[i] = sinc * (0.54 - 0.46 * Math.cos((2 * Math.PI * i) / (taps - 1)));
    sum += h[i];
  }
  for (let i = 0; i < taps; i++) {
    h[i] /= sum; // độ lợi 1 ở 0 Hz
  }
  return h;
}

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetRate = 16000;
    this.bufferSize = 640; // 40ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;

    const sourceRate = sampleRate; // Global AudioWorklet sampleRate
    this.ratio = sourceRate / this.targetRate;
    this.passthrough = Math.abs(this.ratio - 1.0) < 0.01; // đã là 16 kHz: không lọc, không đổi tần số mẫu
    this.resamplePhase = 0.0;
    this.prevSample = 0.0; // mẫu cuối của khối trước, để nội suy được qua ranh giới khối

    // Chỉ lọc khi hạ mẫu: nguồn dưới 16 kHz không có âm nào trên 8 kHz để gập vào dải lời nói
    this.fir = null;
    if (this.ratio > 1.01) {
      this.fir = designLowpass(FIR_TAPS, FIR_CUTOFF_HZ, sourceRate);
      // Lịch sử gấp đôi: hist[pos + k] luôn là mẫu cách đây k bước, không phải quấn vòng trong vòng lặp tích chập
      this.firHistory = new Float32Array(2 * FIR_TAPS);
      this.firPos = 0;
    }

    // Cấp phát một lần (trước đây mỗi khối 128 mẫu tạo một Float32Array mới, 375 lần/giây trên luồng audio)
    this.mono = new Float32Array(128);

    // Listen on port to keep worklet alive and respond to main thread watchdog pings
    this.port.onmessage = () => {
      // Keep worker alive
    };
  }

  push(sample) {
    const s = sample < -1 ? -1 : sample > 1 ? 1 : sample;
    this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7fff;
    if (this.bufferIndex >= this.bufferSize) {
      this.port.postMessage(this.buffer.buffer, [this.buffer.buffer]);
      this.buffer = new Int16Array(this.bufferSize);
      this.bufferIndex = 0;
    }
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

    const ch1 = input.length >= 2 && input[1] && input[1].length > 0 ? input[1] : null;
    const inputLen = ch0.length;
    if (this.mono.length < inputLen) {
      this.mono = new Float32Array(inputLen);
    }
    const mono = this.mono;

    // 1. Trộn hai kênh (L+R)/2, lọc FIR thông thấp nếu sắp hạ mẫu
    if (!this.fir) {
      for (let i = 0; i < inputLen; i++) {
        mono[i] = ch1 ? (ch0[i] + ch1[i]) * 0.5 : ch0[i];
      }
    } else {
      const h = this.fir;
      const hist = this.firHistory;
      const taps = h.length;
      let pos = this.firPos;
      for (let i = 0; i < inputLen; i++) {
        const x = ch1 ? (ch0[i] + ch1[i]) * 0.5 : ch0[i];
        pos = pos === 0 ? taps - 1 : pos - 1;
        hist[pos] = x;
        hist[pos + taps] = x;
        let y = 0;
        for (let k = 0; k < taps; k++) {
          y += h[k] * hist[pos + k];
        }
        mono[i] = y;
      }
      this.firPos = pos;
    }

    // 2. Đổi tần số mẫu về 16 kHz
    if (this.passthrough) {
      for (let i = 0; i < inputLen; i++) {
        this.push(mono[i]);
      }
    } else {
      // Nội suy tuyến tính. Vị trí -1 là mẫu cuối của khối trước, nên điểm nằm giữa hai khối vẫn được nội suy (bản cũ
      // lấy luôn mẫu cuối của khối, sai ở mỗi ranh giới khối khi tỉ lệ không nguyên, ví dụ 44,1 kHz)
      let phase = this.resamplePhase;
      while (phase < inputLen - 1) {
        const i0 = Math.floor(phase);
        const frac = phase - i0;
        const s0 = i0 < 0 ? this.prevSample : mono[i0];
        const s1 = mono[i0 + 1];
        this.push(s0 + frac * (s1 - s0));
        phase += this.ratio;
      }
      this.resamplePhase = phase - inputLen;
      this.prevSample = mono[inputLen - 1];
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
