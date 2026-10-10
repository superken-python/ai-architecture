import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../src/state/useStore';

describe('useStore', () => {
  beforeEach(() => {
    useStore.setState({
      connected: false,
      sessionReady: false,
      activeSide: null,
      isMicActive: false,
      vadSpeaking: { A: false, B: false },
      sideALang: 'auto',
      sideBLang: 'auto',
      detectedSideLang: { A: 'vi', B: 'ja' },
      utterances: {},
      errorMessage: null,
    });
  });

  it('updates connection and session state', () => {
    useStore.getState().setConnected(true);
    expect(useStore.getState().connected).toBe(true);

    useStore.getState().handleServerEvent({
      type: 'session.ready',
      session_id: 'test-session-123',
      profile: 'balanced',
      pack_revision: 'rev-1',
      models: { asr: 'whisper', mt: 'llama' },
    });
    expect(useStore.getState().sessionReady).toBe(true);
    expect(useStore.getState().sessionId).toBe('test-session-123');
  });

  it('handles VAD events', () => {
    useStore.getState().handleServerEvent({
      type: 'vad',
      side: 'A',
      speaking: true,
    });
    expect(useStore.getState().vadSpeaking.A).toBe(true);
    expect(useStore.getState().vadSpeaking.B).toBe(false);
  });

  it('handles ASR and MT events correctly', () => {
    // 1. ASR partial
    useStore.getState().handleServerEvent({
      type: 'asr.partial',
      utterance_id: 1,
      side: 'A',
      text: 'Xin chào',
    });
    let u = useStore.getState().utterances[1];
    expect(u).toBeDefined();
    expect(u.originalText).toBe('Xin chào');
    expect(u.isFinal).toBe(false);

    // 2. ASR final
    useStore.getState().handleServerEvent({
      type: 'asr.final',
      utterance_id: 1,
      side: 'A',
      text: 'Xin chào các bạn',
      lang: 'vi',
      lang_probs: { vi: 0.95, en: 0.03, ja: 0.02 },
      uncertain: false,
      audio_ms: 1200,
    } as any);
    u = useStore.getState().utterances[1];
    expect(u.originalText).toBe('Xin chào các bạn');
    expect(u.originalLang).toBe('vi');
    expect(u.isFinal).toBe(true);

    // 3. MT delta and final
    useStore.getState().handleServerEvent({
      type: 'mt.delta',
      utterance_id: 1,
      target: 'ja',
      delta: '皆',
    });
    useStore.getState().handleServerEvent({
      type: 'mt.final',
      utterance_id: 1,
      target: 'ja',
      text: '皆さん、こんにちは',
    });
    u = useStore.getState().utterances[1];
    expect(u.translations['ja']).toBe('皆さん、こんにちは');
  });
});
