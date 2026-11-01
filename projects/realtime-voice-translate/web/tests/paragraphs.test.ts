import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../src/state/useStore';
import { paragraphCards } from '../src/state/paragraphs';

// Dịch theo đoạn ở chế độ Video & Họp (docs 10 §13.9)
const send = (event: any) => useStore.getState().handleServerEvent(event);
const final = (id: number, text: string, paragraph_id: number | null, lang = 'ja') =>
  send({ type: 'asr.final', utterance_id: id, side: 'A', text, lang, lang_probs: {}, uncertain: false, audio_ms: 3000, paragraph_id });
const cards = () => paragraphCards(Object.values(useStore.getState().utterances), 'vi');

describe('paragraph translation', () => {
  beforeEach(() => {
    useStore.setState({ utterances: {}, sideALang: 'ja', sideBLang: 'vi', meetingMode: true, mtUnit: 'paragraph' });
  });

  it('shows sentences of one paragraph in one card, Japanese joined without spaces', () => {
    final(10, '人の作業が', 10);
    final(11, '減らせると思います。', 10);
    final(12, '次の話です。', 12);
    const view = cards();
    expect(view.map((c) => c.card.id)).toEqual([10, 12]);
    expect(view[0].card.originalText).toBe('人の作業が減らせると思います。');
  });

  it('keeps the finished translation on screen while a newer revision streams, then replaces it', () => {
    final(10, '人の作業が', 10);
    send({ type: 'mt.delta', utterance_id: 10, target: 'vi', delta: 'Công việc ', revision: 1 });
    expect(cards()[0].card.translations.vi).toBe('Công việc');  // chưa có bản xong: hiện bản đang đến
    send({ type: 'mt.final', utterance_id: 10, target: 'vi', text: 'Công việc của mọi người', revision: 1 });

    final(11, '減らせると思います。', 10);
    send({ type: 'mt.delta', utterance_id: 10, target: 'vi', delta: 'Tôi nghĩ ', revision: 2 });
    let view = cards();
    expect(view[0].card.translations.vi).toBe('Công việc của mọi người');
    expect(view[0].retranslating).toBe(true);

    send({ type: 'mt.final', utterance_id: 10, target: 'vi', text: 'Tôi nghĩ công việc của mọi người sẽ giảm.', revision: 2 });
    view = cards();
    expect(view[0].card.translations.vi).toBe('Tôi nghĩ công việc của mọi người sẽ giảm.');
    expect(view[0].retranslating).toBe(false);
  });

  it('ignores text of an older revision that arrives late', () => {
    final(10, '人の作業が', 10);
    send({ type: 'mt.final', utterance_id: 10, target: 'vi', text: 'Bản mới', revision: 2 });
    send({ type: 'mt.delta', utterance_id: 10, target: 'vi', delta: 'cũ', revision: 1 });
    send({ type: 'mt.final', utterance_id: 10, target: 'vi', text: 'Bản cũ', revision: 1 });
    const u = useStore.getState().utterances[10];
    expect(u.translations.vi).toBe('Bản mới');
    expect(u.pendingTranslations?.vi).toBeUndefined();
  });

  it('puts the partial of a sentence that will join the paragraph into the same card', () => {
    final(10, '人の作業が', 10);
    send({ type: 'asr.partial', utterance_id: 11, side: 'A', text: '減らせる', lang: 'ja', paragraph_id: 10 });
    send({ type: 'asr.partial', utterance_id: 12, side: 'B', text: 'Xin chào', lang: 'vi', paragraph_id: null });
    const view = cards();
    expect(view.map((c) => c.card.id)).toEqual([10, 12]);
    expect(view[0].card.originalText).toBe('人の作業が減らせる');
    expect(view[0].card.isFinal).toBe(false);
  });

  it('segment mode events (no paragraph, no revision) keep the old behaviour', () => {
    final(1, 'Xin chào.', null, 'vi');
    final(2, 'Hẹn gặp lại.', null, 'vi');
    send({ type: 'mt.delta', utterance_id: 1, target: 'ja', delta: 'こんにちは' });
    send({ type: 'mt.final', utterance_id: 2, target: 'ja', text: 'またね。' });
    const u = useStore.getState().utterances;
    expect(u[1].translations.ja).toBe('こんにちは');
    expect(u[2].translations.ja).toBe('またね。');
    expect(paragraphCards(Object.values(u), 'ja').map((c) => c.card.id)).toEqual([1, 2]);
  });

  it('keeps the paragraph when a sentence is re-sent after a language override', () => {
    final(10, '人の作業が', 10);
    final(11, '減らせる', 10);
    send({ type: 'asr.final', utterance_id: 11, side: 'A', text: 'giảm được', lang: 'vi', lang_probs: {}, uncertain: false, audio_ms: 1000 });
    expect(useStore.getState().utterances[11].paragraphId).toBe(10);
  });
});
