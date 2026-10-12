import { describe, it, expect } from 'vitest';
import {
  CaptureSnapshot,
  REPLACED_CLOSE_CODE,
  captureMessage,
  detectCaptureProblem,
  needsNewCapture,
  newClientId,
  wsUrlWithClientId,
} from '../src/net/capture_health';

const NOW = 100_000;

function snap(over: Partial<CaptureSnapshot> = {}): CaptureSnapshot {
  return {
    source: 'mic',
    trackState: 'live',
    trackMuted: false,
    contextState: 'running',
    now: NOW,
    lastChunkAt: NOW - 40,
    zeroSince: 0,
    contextBadSince: 0,
    ...over,
  };
}

describe('detectCaptureProblem (docs 08 §4.1)', () => {
  it('reports nothing while audio flows', () => {
    expect(detectCaptureProblem(snap())).toBeNull();
  });

  it('reports a muted mic, e.g. another tab or a call took it', () => {
    expect(detectCaptureProblem(snap({ trackMuted: true }))).toBe('muted');
  });

  it('reports an ended or missing track', () => {
    expect(detectCaptureProblem(snap({ trackState: 'ended' }))).toBe('ended');
    expect(detectCaptureProblem(snap({ trackState: 'none' }))).toBe('ended');
  });

  it('waits a grace period before reporting a suspended AudioContext', () => {
    expect(detectCaptureProblem(snap({ contextState: 'interrupted', contextBadSince: NOW - 500 }))).toBeNull();
    expect(detectCaptureProblem(snap({ contextState: 'interrupted', contextBadSince: NOW - 1600 }))).toBe('suspended');
  });

  it('reports stalled chunks after 2 s', () => {
    expect(detectCaptureProblem(snap({ lastChunkAt: NOW - 1500 }))).toBeNull();
    expect(detectCaptureProblem(snap({ lastChunkAt: NOW - 2500 }))).toBe('stalled');
  });

  it('reports 2 s of digital zeros from a mic, but not from a tab (paused video is silent)', () => {
    expect(detectCaptureProblem(snap({ zeroSince: NOW - 1000 }))).toBeNull();
    expect(detectCaptureProblem(snap({ zeroSince: NOW - 2000 }))).toBe('zeros');
    expect(detectCaptureProblem(snap({ source: 'tab', zeroSince: NOW - 5000 }))).toBeNull();
  });

  it('keeps reporting while the problem lasts, so the warning can come back after a tap', () => {
    // 873d676 chỉ cảnh báo đúng lúc bộ đếm bằng 50 khung; sau một lần chạm, cảnh báo không bao giờ hiện lại
    for (const t of [2000, 3000, 10_000]) {
      expect(detectCaptureProblem(snap({ zeroSince: NOW - t }))).toBe('zeros');
    }
  });
});

describe('needsNewCapture', () => {
  it('re-acquires the mic for muted, ended, zeros and stalled, but only resumes a suspended context', () => {
    expect(needsNewCapture('muted')).toBe(true);
    expect(needsNewCapture('ended')).toBe(true);
    expect(needsNewCapture('zeros')).toBe(true);
    expect(needsNewCapture('stalled')).toBe(true);
    expect(needsNewCapture('suspended')).toBe(false);
    expect(needsNewCapture(null)).toBe(false);
  });
});

describe('captureMessage', () => {
  it('names the tab, not the microphone, when capturing a tab', () => {
    expect(captureMessage('stalled', 'tab')).toContain('tab');
    expect(captureMessage('stalled', 'tab')).not.toContain('icro');
    expect(captureMessage('muted', 'mic')).toContain('icro');
  });
});

describe('client_id (docs 08 §4.3)', () => {
  it('is different for every page instance, so two tabs never evict each other', () => {
    const ids = new Set(Array.from({ length: 50 }, () => newClientId()));
    expect(ids.size).toBe(50);
  });

  it('is sent on the WebSocket URL so the server can replace a stale connection before its session limit', () => {
    expect(wsUrlWithClientId('wss://host:8443/ws', 'page-1')).toBe('wss://host:8443/ws?client_id=page-1');
    expect(wsUrlWithClientId('ws://h/ws?x=1', 'a b')).toBe('ws://h/ws?x=1&client_id=a%20b');
  });

  it('uses the replaced-connection close code the server sends', () => {
    expect(REPLACED_CLOSE_CODE).toBe(4409);
  });
});
