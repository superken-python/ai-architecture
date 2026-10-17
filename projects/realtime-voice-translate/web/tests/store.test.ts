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
    expect(useStore.getState().listenOnly).toBe(false);
  });

  it('marks listen-only sessions when the server has no translation model', () => {
    useStore.getState().handleServerEvent({
      type: 'session.ready',
      session_id: 'listen-1',
      profile: 'listen',
      pack_revision: 'rev-2',
      models: { vad: 'silero', asr: 'faster-whisper', mt: 'none' },
    });
    expect(useStore.getState().listenOnly).toBe(true);
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

  it('cleanTranslationText preserves genuine apologies and strips hallucinations', async () => {
    const { cleanTranslationText } = await import('../src/App');
    // Genuine apologies must be preserved
    expect(cleanTranslationText("I'm sorry.")).toBe("I'm sorry.");
    expect(cleanTranslationText("Xin lỗi bạn.")).toBe("Xin lỗi bạn.");
    expect(cleanTranslationText("申し訳ありません。")).toBe("申し訳ありません。");

    // Hallucinations and chatter should be stripped
    expect(cleanTranslationText("Thank you. I'm sorry, I'm not sure what you mean.")).toBe("Thank you.");
    expect(cleanTranslationText("Hello! Note: This is an explanation.")).toBe("Hello!");

    // Parenthetical English explanations (cultural terms, honorifics, etc.)
    expect(
      cleanTranslationText("Thưa thầy, em mang bài tập đến rồi. (Sensei means teacher in Japanese)")
    ).toBe("Thưa thầy, em mang bài tập đến rồi.");
    expect(
      cleanTranslationText("Thưa thầy, em mang bài tập đến rồi. (Sensei có nghĩa là thầy giáo)")
    ).toBe("Thưa thầy, em mang bài tập đến rồi.");
    expect(cleanTranslationText("Chào bạn! (Informal)")).toBe("Chào bạn!");
    expect(cleanTranslationText("Tôi hiểu rồi. (Used when expressing agreement)")).toBe("Tôi hiểu rồi.");

    // Trailing explanation sentences
    expect(
      cleanTranslationText("Thưa thầy, em mang bài tập đến rồi. Sensei means teacher in Japanese.")
    ).toBe("Thưa thầy, em mang bài tập đến rồi.");
    expect(
      cleanTranslationText("Thưa thầy, em mang bài tập đến rồi. This sentence is spoken politely.")
    ).toBe("Thưa thầy, em mang bài tập đến rồi.");

    // Multi-line and preambles
    expect(
      cleanTranslationText("Thưa thầy.\nNote: In Japanese culture, Sensei is an honorific title.")
    ).toBe("Thưa thầy.");
    expect(
      cleanTranslationText("Here is the translation into Vietnamese: Chào buổi sáng.")
    ).toBe("Chào buổi sáng.");
    expect(
      cleanTranslationText("Thưa thầy - Sensei refers to a teacher.")
    ).toBe("Thưa thầy");

    // Japanese target with Latin
    expect(
      cleanTranslationText("せんせい。(Sensei is teacher)", "", "ja")
    ).toBe("せんせい。");
  });

  it('removes ghost partial utterances when asr.final has empty text', () => {
    // 1. Partial arrives
    useStore.getState().handleServerEvent({
      type: 'asr.partial',
      utterance_id: 99,
      side: 'A',
      text: 'Âm thanh ngẫu nhiên',
    });
    expect(useStore.getState().utterances[99]).toBeDefined();

    // 2. Final arrives with empty text (silence/noise)
    useStore.getState().handleServerEvent({
      type: 'asr.final',
      utterance_id: 99,
      side: 'A',
      text: '',
    });

    // 3. Ghost partial must be removed completely
    expect(useStore.getState().utterances[99]).toBeUndefined();
  });
});

