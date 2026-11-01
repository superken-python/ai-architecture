import { create } from 'zustand';
import { ServerEvent } from '../contracts/ServerEvent';
import { cleanTranslationText } from '../utils/cleanText';

export type Side = "A" | "B";
export type SupportedLang = "auto" | "vi" | "en" | "ja";
// Đơn vị dịch ở chế độ Video & Họp: gom câu thành đoạn rồi dịch cả đoạn, hoặc dịch từng câu (docs 10 §13.9)
export type MtUnit = "paragraph" | "segment";

export interface Utterance {
  id: number;
  side: Side;
  originalText: string;
  originalLang: string;
  langProbs?: Record<string, number>;
  uncertain?: boolean;
  translations: Record<string, string>; // "en" -> "Hello", "ja" -> "..."
  isFinal: boolean;
  isSpeaking: boolean;
  // Dịch theo đoạn: số đoạn chứa câu này. Bản dịch của đoạn nằm ở câu đầu đoạn (id = paragraphId)
  paragraphId?: number;
  // Lần dịch mới hơn đang đến; màn hình giữ bản đã xong (translations) tới khi lần mới xong
  pendingTranslations?: Record<string, string>;
  mtRevision?: Record<string, number>; // lần dịch mới nhất đã nhận chữ
  doneRevision?: Record<string, number>; // lần dịch của bản đang hiện
}

interface AppState {
  connected: boolean;
  sessionReady: boolean;
  sessionId: string | null;
  // Server chạy profile chỉ nghe (models.mt = "none"): không có bản dịch, hiện chữ gốc (docs 10 §10.3)
  listenOnly: boolean;
  activeSide: Side | null;
  isMicActive: boolean;
  vadSpeaking: Record<Side, boolean>;
  sideALang: SupportedLang;
  sideBLang: SupportedLang;
  detectedSideLang: Record<Side, string>;
  utterances: Record<number, Utterance>;
  errorMessage: string | null;
  captureWarning: string | null;
  wakeLockHeld: boolean;
  audioSource: 'mic' | 'tab';
  meetingMode: boolean;
  mtUnit: MtUnit;

  setConnected: (status: boolean) => void;
  setActiveSide: (side: Side | null) => void;
  setMicActive: (active: boolean) => void;
  setSideConfig: (side: Side, lang: SupportedLang) => void;
  setAudioSource: (source: 'mic' | 'tab') => void;
  setMeetingMode: (active: boolean) => void;
  setMtUnit: (unit: MtUnit) => void;
  setError: (msg: string | null) => void;
  setCaptureWarning: (msg: string | null) => void;
  setWakeLockHeld: (held: boolean) => void;
  clearError: () => void;
  clearHistory: () => void;
  handleServerEvent: (event: ServerEvent) => void;
}

export const useStore = create<AppState>((set, get) => ({
  connected: false,
  sessionReady: false,
  sessionId: null,
  listenOnly: false,
  activeSide: null,
  isMicActive: false,
  vadSpeaking: { A: false, B: false },
  sideALang: "vi",
  sideBLang: "en",
  detectedSideLang: { A: "vi", B: "en" },
  utterances: {},
  errorMessage: null,
  captureWarning: null,
  wakeLockHeld: true,
  audioSource: 'mic',
  meetingMode: false,
  mtUnit: "paragraph",

  setConnected: (status) => set({ connected: status }),
  setActiveSide: (side) => set({ activeSide: side }),
  setMicActive: (active) => set({ isMicActive: active }),
  setCaptureWarning: (msg) => set({ captureWarning: msg }),
  setWakeLockHeld: (held) => set({ wakeLockHeld: held }),
  setAudioSource: (source) => set({ audioSource: source }),
  setMeetingMode: (active) => set({ meetingMode: active }),
  setMtUnit: (unit) => set({ mtUnit: unit }),
  
  setSideConfig: (side, lang) => {
    set((state) => {
      const updated = side === "A" ? { sideALang: lang } : { sideBLang: lang };
      return updated;
    });
  },

  setError: (msg) => set({ errorMessage: msg }),
  clearError: () => set({ errorMessage: null }),
  clearHistory: () => set({ utterances: {} }),

  handleServerEvent: (event) => {
    set((state) => {
      const newUtterances = { ...state.utterances };

      switch (event.type) {
        case "session.ready":
          return {
            sessionReady: true,
            sessionId: event.session_id,
            listenOnly: event.models?.mt === "none",
            errorMessage: null
          };

        case "vad":
          return {
            vadSpeaking: {
              ...state.vadSpeaking,
              [event.side as Side]: event.speaking
            }
          };

        case "asr.partial":
          if (!newUtterances[event.utterance_id]) {
            newUtterances[event.utterance_id] = {
              id: event.utterance_id,
              side: event.side as Side,
              originalText: event.text,
              originalLang: (event.lang as string) || "",
              translations: {},
              isFinal: false,
              isSpeaking: true,
              paragraphId: event.paragraph_id ?? undefined
            };
          } else {
            newUtterances[event.utterance_id] = {
              ...newUtterances[event.utterance_id],
              originalText: event.text,
              paragraphId: event.paragraph_id ?? undefined
            };
          }
          break;

        case "asr.final":
          {
            if (!event.text || !event.text.trim()) {
              // Final audio was silence or noise; remove ghost partial utterance if it existed
              delete newUtterances[event.utterance_id];
              return { utterances: newUtterances };
            }

            const existing = newUtterances[event.utterance_id] || {
              id: event.utterance_id,
              side: event.side as Side,
              translations: {}
            };
            newUtterances[event.utterance_id] = {
              ...existing,
              originalText: event.text,
              originalLang: event.lang as string,
              langProbs: (event as any).lang_probs || {},
              uncertain: (event as any).uncertain || false,
              isFinal: true,
              isSpeaking: false,
              // Bản gửi lại khi đổi ngôn ngữ không kèm số đoạn: giữ đoạn cũ
              paragraphId: event.paragraph_id ?? existing.paragraphId
            };

            // Update detected language for this side if confidence is high
            const updatedDetected = { ...state.detectedSideLang };
            if (event.side && event.lang) {
              updatedDetected[event.side as Side] = event.lang as string;
            }
            return {
              utterances: newUtterances,
              detectedSideLang: updatedDetected
            };
          }

        case "mt.delta":
          if (newUtterances[event.utterance_id] && event.revision != null) {
            // Dịch theo đoạn: chữ của lần dịch mới gom riêng, không chen vào bản đang hiện; lần cũ đến muộn thì bỏ
            const u = newUtterances[event.utterance_id];
            const tgt = event.target as string;
            const seen = u.mtRevision?.[tgt] ?? 0;
            if (event.revision < seen) break;
            const before = event.revision > seen ? "" : (u.pendingTranslations?.[tgt] ?? "");
            newUtterances[event.utterance_id] = {
              ...u,
              pendingTranslations: {
                ...u.pendingTranslations,
                [tgt]: cleanTranslationText(before + (event.delta as string), u.originalText || "", tgt)
              },
              mtRevision: { ...u.mtRevision, [tgt]: event.revision }
            };
          } else if (newUtterances[event.utterance_id]) {
            const current = newUtterances[event.utterance_id].translations[event.target as string] || "";
            const orig = newUtterances[event.utterance_id].originalText || "";
            const tgt = event.target as string;
            const updated = current + (event.delta as string);
            newUtterances[event.utterance_id] = {
              ...newUtterances[event.utterance_id],
              translations: {
                ...newUtterances[event.utterance_id].translations,
                [tgt]: cleanTranslationText(updated, orig, tgt)
              }
            };
          }
          break;

        case "mt.final":
          if (newUtterances[event.utterance_id] && event.revision != null) {
            const u = newUtterances[event.utterance_id];
            const tgt = event.target as string;
            if (event.revision < (u.doneRevision?.[tgt] ?? 0)) break;
            const seen = u.mtRevision?.[tgt] ?? 0;
            const pending = { ...u.pendingTranslations };
            if (event.revision >= seen) delete pending[tgt];
            newUtterances[event.utterance_id] = {
              ...u,
              translations: { ...u.translations, [tgt]: cleanTranslationText(event.text as string, u.originalText || "", tgt) },
              pendingTranslations: pending,
              mtRevision: { ...u.mtRevision, [tgt]: Math.max(seen, event.revision) },
              doneRevision: { ...u.doneRevision, [tgt]: event.revision }
            };
          } else if (newUtterances[event.utterance_id]) {
            const raw = event.text as string;
            const orig = newUtterances[event.utterance_id].originalText || "";
            const tgt = event.target as string;
            newUtterances[event.utterance_id] = {
              ...newUtterances[event.utterance_id],
              translations: {
                ...newUtterances[event.utterance_id].translations,
                [tgt]: cleanTranslationText(raw, orig, tgt)
              }
            };
          }
          break;

        case "error":
          if (event.code === "mt_validation_failed" || event.code === "mt_failed") {
            console.warn("MT warning:", event.code, event.message);
            return {};
          }
          return {
            errorMessage: `${event.code}: ${event.message}`
          };
      }

      return { utterances: newUtterances };
    });
  }
}));
