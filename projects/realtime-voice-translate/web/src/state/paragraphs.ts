import type { Utterance } from './useStore';

export interface ParagraphCard {
  // Thẻ hiện cả đoạn: chữ gốc nối các câu, bản dịch của đoạn (lấy ở câu đầu đoạn)
  card: Utterance;
  // Đang dịch lại đoạn sau khi có thêm câu: màn hình vẫn giữ bản dịch cũ
  retranslating: boolean;
}

/**
 * Gom các câu theo đoạn (docs 10 §13.9). Câu không có số đoạn (dịch từng câu, hoặc chữ tạm sẽ mở đoạn mới) là một thẻ
 * riêng. Thứ tự thẻ theo câu đầu của mỗi đoạn.
 */
export function paragraphCards(utterances: Utterance[], target: string): ParagraphCard[] {
  const groups = new Map<number, Utterance[]>();
  for (const u of utterances) {
    const key = u.paragraphId ?? u.id;
    const items = groups.get(key);
    if (items) items.push(u);
    else groups.set(key, [u]);
  }
  return Array.from(groups, ([key, items]) => {
    const head = items.find((u) => u.id === key) ?? items[0];
    const lang = head.originalLang || items.find((u) => u.originalLang)?.originalLang || '';
    // Tiếng Nhật viết liền, không có khoảng trắng giữa các câu
    const text = items
      .map((u) => u.originalText.trim())
      .filter(Boolean)
      .join(lang === 'ja' ? '' : ' ');
    const done = head.translations[target];
    const pending = head.pendingTranslations?.[target];
    return {
      card: {
        ...head,
        id: key,
        originalText: text,
        originalLang: lang,
        translations: done || !pending ? head.translations : { ...head.translations, [target]: pending },
        isFinal: items.every((u) => u.isFinal),
        isSpeaking: items.some((u) => u.isSpeaking),
      },
      retranslating: Boolean(done && pending),
    };
  });
}
