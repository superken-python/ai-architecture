export const cleanTranslationText = (
  text: string,
  originalText: string = "",
  targetLang: string = ""
): string => {
  if (!text) return "";
  let cleaned = text.trim();

  // 1. Strip surrounding quotation marks or markdown code blocks
  if (cleaned.startsWith("```") && cleaned.endsWith("```")) {
    cleaned = cleaned.replace(/^```[a-z]*\n?/i, "").replace(/\n?```$/i, "").trim();
  }
  if ((cleaned.startsWith('"') && cleaned.endsWith('"')) || (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
    cleaned = cleaned.slice(1, -1).trim();
  }

  // 2. Take only the first non-empty line (speech translation never spans paragraphs)
  const lines = cleaned.split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length > 0) {
    cleaned = lines[0];
  }

  // 3. Strip common preambles
  const preambles = [
    /^Here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*/i,
    /^Here['’]s\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*/i,
    /^Sure,?\s*(?:here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*)?/i,
    /^Certainly,?\s*(?:here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*)?/i,
    /^The\s+translation(?:\s+into\s+[a-zA-Z]+)?\s+is:?\s*/i,
    /^Translation\s*(?:into\s+[a-zA-Z]+)?:?\s*/i,
    /^Translated\s+text:?\s*/i,
    /^Vietnamese:?\s*/i,
    /^Japanese:?\s*/i,
    /^English:?\s*/i,
    /^Bản\s+dịch:?\s*/i,
    /^Câu\s+dịch:?\s*/i,
    /^Dịch:?\s*/i,
    /^翻訳:?\s*/i,
    /^翻译(?:成|为)?(?:越南语|英语|日语)?:?\s*/i,
    /^意思是:?\s*/i,
    /^Input:\s*.*?\s*Translation:\s*/is,
  ];
  for (const p of preambles) {
    cleaned = cleaned.replace(p, "").trim();
  }

  // 4. Remove parenthetical explanations, cultural notes, and annotations
  const parenExplanationPattern = /\s*[\(\[（【]\s*(?:Note|Notes|Explanation|Meaning|Context|Literal|Literally|Sensei|Senpai|Honorific|Informal|Formal|Polite|Casual|Slang|Refers|Referring|This\s+means|Used\s+(?:when|to|as)|In\s+Japanese|In\s+Vietnamese|In\s+English|A\s+term\s+of|Commonly\s+used|Ghi\s+chú|Lưu\s+ý|Giải\s+thích|Ý\s+nghĩa|Nghĩa\s+là|[a-zA-Z\s,.'’"—-]{4,}).*?[\)\]）】]/gi;
  cleaned = cleaned.replace(parenExplanationPattern, "").trim();

  // If original text had no parentheses, and target is not English, strip any Latin parenthetical note
  const hasOrigParens = /[\(\[（【]/.test(originalText);
  if (!hasOrigParens && targetLang !== "en") {
    cleaned = cleaned.replace(/\s*[\(\[（【][a-zA-Z0-9\s,.'’"—\-:;!?]+[\)\]）】]/gi, "").trim();
  }

  // 5. Remove note / explanation / reasoning suffixes and conversational chatbot responses
  const markers = [
    /\bI['’]m sorry,\s*(?:I['’]m not sure|I don['’]t understand|could you|can you|what do you|as an AI|please clarify|but I).*/is,
    /\bI am sorry,\s*(?:I am not sure|I do not understand|could you|can you|what do you|as an AI|please clarify|but I).*/is,
    /\b(I['’]m not sure what you mean|I am not sure what you mean|I don['’]t understand what you mean|I do not understand what you mean|Could you please (?:clarify|explain|repeat)|Can you please (?:clarify|explain|repeat)|Would you please (?:clarify|explain|repeat)|Please clarify|Please explain|What do you mean by|As an AI|As a language model|This is the most important thing|They are very friendly|No notes|No note|Note:|Notes:|Explanation:|Meaning:|Literal\s+translation:|Ghi chú:|Lưu ý:|Giải thích:|Ý nghĩa:).*/is,
    /[—【].*/s,
    /\*\*.*/s,
    /(申し訳ありませんが、.*(?:分かりかねます|質問|理解)|ご質問の意味が|説明:|注意:|補足:|翻译[为成][:：]|意思[是为][:：]).*/is,
  ];
  for (const m of markers) {
    cleaned = cleaned.replace(m, "").trim();
  }

  // 6. Trailing explanation sentences appended after punctuation
  const trailingExpl = /([.!?。！？])\s*(?:(?:This|That|It)\s+(?:means|sentence|phrase|translates|is|implies|refers)|The\s+(?:speaker|word|phrase|meaning|translation|sentence|term)|Here\s+(?:is|,|we)|In\s+(?:English|Vietnamese|Japanese|this\s+context)|(?:Meaning|Note|Notes|Explanation|Literal|Literally|Context)\s*:?|(?:Sensei|Senpai)\s+(?:means|is|refers|can)|Used\s+(?:when|to|as)|An?\s+(?:expression|term)\s+of|I['’]m\s*sorry|I\s*am\s*sorry|Could\s*you|Can\s*you|Please|What\s*do\s*you|As\s*an\s*AI).*/is;
  cleaned = cleaned.replace(trailingExpl, "$1").trim();

  // Hyphen/dash explanations
  cleaned = cleaned.replace(/\s*[-–—:]\s*(?:Note|Explanation|Meaning|Context|Sensei|This\s+means|The\s+speaker).*/is, "").trim();

  // Strip appended chatbot apologies after end-of-sentence punctuation if not an apology source
  const isSourceApology = /(?:xin lỗi|xin loi|sorry|すみません|すいません|ごめん|申し訳)/i.test(originalText);
  if (!isSourceApology) {
    cleaned = cleaned.replace(/([.!?。！？])\s*I['’]m sorry.*/is, "$1").trim();
    cleaned = cleaned.replace(/([.!?。！？])\s*I am sorry.*/is, "$1").trim();
    cleaned = cleaned.replace(/([.!?。！？])\s*申し訳ありません.*/is, "$1").trim();
  }

  // 7. For Japanese target: if Latin text appears after Japanese script, cut off Latin babble
  const jaMatch = cleaned.match(/([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF][\s\.\?!。！？]*)([a-zA-Z]{3,}.*)/);
  if (jaMatch) {
    cleaned = cleaned.substring(0, cleaned.length - jaMatch[2].length).trim();
  }

  // 8. For Vietnamese target: if pure ASCII English sentence appears after punctuation, strip it
  if (targetLang === "vi" || !targetLang) {
    const viMatch = cleaned.match(/([.!?])\s+([A-Za-z\s,.'’"—\-:;]+)$/);
    if (viMatch) {
      const trail = viMatch[2].toLowerCase();
      const enKeywords = [
        "means", "meaning", "teacher", "speaker", "refers", "referring",
        "informal", "formal", "polite", "casual", "slang", "translation",
        "translates", "sentence", "phrase", "note", "notes", "explanation",
        "context", "literally", "literal", "japanese", "vietnamese", "english",
        "honorific", "respect", "cultural", "culture", "implies", "indicating",
        "indicates", "used", "term", "addressing", "respectful"
      ];
      if (enKeywords.some(w => trail.includes(w)) || /^(?:this |the |it |in |note |sensei )/.test(trail)) {
        cleaned = cleaned.substring(0, cleaned.length - viMatch[2].length).trim();
      }
    }
  }

  return cleaned;
};
