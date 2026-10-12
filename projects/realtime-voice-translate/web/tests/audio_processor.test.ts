import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

// Chạy đúng file public/audio-processor.js như trong AudioWorkletGlobalScope: khối 128 mẫu, input[0] = [L, R]
// (docs 08 §4.4).
const SOURCE = readFileSync(new URL('../public/audio-processor.js', import.meta.url), 'utf8');

interface Processor {
  process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: object): boolean;
}

interface Worklet {
  processor: Processor;
  chunks: Int16Array[];
  float32Allocs: () => number;
}

function makeWorklet(sampleRate: number): Worklet {
  const chunks: Int16Array[] = [];
  let float32Allocs = 0;
  class AudioWorkletProcessor {
    port = {
      postMessage: (buf: ArrayBuffer) => chunks.push(Int16Array.from(new Int16Array(buf))),
      onmessage: null as unknown,
    };
  }
  // Đếm mọi lần tạo Float32Array trong worklet
  const CountingFloat32Array = new Proxy(Float32Array, {
    construct(target, args) {
      float32Allocs += 1;
      return new target(...(args as [number]));
    },
  });
  const registered: { cls?: new () => Processor } = {};
  vm.runInNewContext(SOURCE, {
    sampleRate,
    AudioWorkletProcessor,
    Float32Array: CountingFloat32Array,
    registerProcessor: (_name: string, cls: new () => Processor) => {
      registered.cls = cls;
    },
  });
  return { processor: new registered.cls!(), chunks, float32Allocs: () => float32Allocs };
}

// Đưa tín hiệu (một hoặc hai kênh) qua worklet theo từng khối 128 mẫu, trả về các mẫu 16 kHz đã gửi đi
function run(sampleRate: number, channels: Float32Array[], worklet = makeWorklet(sampleRate)): number[] {
  const out = [new Float32Array(128)];
  for (let b = 0; b + 128 <= channels[0].length; b += 128) {
    worklet.processor.process([channels.map((c) => c.subarray(b, b + 128))], [out], {});
  }
  return worklet.chunks.flatMap((c) => Array.from(c, (v) => (v < 0 ? v / 0x8000 : v / 0x7fff)));
}

function sine(freq: number, sampleRate: number, seconds: number, amp = 0.5): Float32Array {
  const n = Math.round(sampleRate * seconds);
  return Float32Array.from({ length: n }, (_, i) => amp * Math.sin((2 * Math.PI * freq * i) / sampleRate));
}

// Mức RMS (dB) so với sin biên độ 0,5, bỏ 10 ms đầu (quá độ của bộ lọc)
function levelDb(x: number[]): number {
  let s = 0;
  for (let i = 160; i < x.length; i++) s += x[i] * x[i];
  return 20 * Math.log10(Math.sqrt(s / (x.length - 160)) / (0.5 / Math.SQRT2));
}

describe('audio-processor.js (docs 08 §4.4)', () => {
  it('sends 40 ms chunks of 16 kHz PCM from 48 kHz', () => {
    const w = makeWorklet(48000);
    const samples = run(48000, [sine(1000, 48000, 1)], w);
    expect(w.chunks.every((c) => c.length === 640)).toBe(true);
    expect(samples.length).toBe(Math.floor(16000 / 640) * 640);
  });

  it('keeps speech-band tones at 48 kHz', () => {
    for (const f of [300, 1000, 3000, 5000]) {
      expect(Math.abs(levelDb(run(48000, [sine(f, 48000, 0.5)])))).toBeLessThan(0.2);
    }
  });

  it('blocks tones above 8 kHz that would fold into the speech band', () => {
    // 9 kHz gập về 7 kHz, 12 kHz về 4 kHz, 16 kHz về 0 Hz. Biquad bậc 2 cũ chỉ giảm 4–20 dB ở 8–16 kHz
    for (const f of [9000, 10000, 12000, 16000, 20000]) {
      expect(levelDb(run(48000, [sine(f, 48000, 0.5)]))).toBeLessThan(-55);
    }
  });

  it('mixes the two channels (L+R)/2 instead of taking only the left one', () => {
    const left = sine(1000, 48000, 0.5);
    const inverted = sine(1000, 48000, 0.5, -0.5);
    expect(levelDb(run(48000, [left, inverted]))).toBeLessThan(-60); // ngược pha: triệt tiêu
    expect(run(48000, [left, left])).toEqual(run(48000, [left]));
  });

  it('interpolates across block edges at 44.1 kHz', () => {
    // Tỉ lệ 2,75625 không nguyên. Bản cũ lấy luôn mẫu cuối của khối cho điểm nằm giữa hai khối
    const samples = run(44100, [sine(1000, 44100, 1)]);
    expect(samples.length).toBe(Math.floor((16000 * (Math.floor(44100 / 128) * 128)) / 44100 / 640) * 640);
    const delay = 31 / 44100; // trễ nhóm của FIR 63 tap
    let worst = 0;
    for (let i = 160; i < samples.length; i++) {
      const ideal = 0.5 * Math.sin(2 * Math.PI * 1000 * (i / 16000 - delay));
      worst = Math.max(worst, Math.abs(samples[i] - ideal));
    }
    expect(worst).toBeLessThan(0.005); // dưới −40 dB so với biên độ
  });

  it('passes 16 kHz through unchanged, and only interpolates when upsampling', () => {
    const x16 = sine(1000, 16000, 0.5);
    const out16 = run(16000, [x16]);
    expect(Math.max(...out16.map((v, i) => Math.abs(v - x16[i])))).toBeLessThan(1e-4);
    // 8 kHz: không lọc, nên mẫu gốc giữ nguyên ở các vị trí chẵn
    const x8 = sine(3000, 8000, 0.5);
    const out8 = run(8000, [x8]);
    expect(out8.length).toBe(Math.floor(7936 / 640) * 640);
    for (let k = 0; 2 * k < out8.length; k++) {
      expect(Math.abs(out8[2 * k] - x8[k])).toBeLessThan(1e-4);
    }
  });

  it('allocates its buffers once, not a Float32Array per 128-sample block', () => {
    const w = makeWorklet(48000);
    const before = w.float32Allocs();
    run(48000, [sine(1000, 48000, 1)], w);
    expect(w.float32Allocs() - before).toBe(0);
  });
});
