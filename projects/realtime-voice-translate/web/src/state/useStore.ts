import { create } from 'zustand';
import { ServerEvent } from '../contracts/ServerEvent';
import { cleanTranslationText } from '../utils/cleanText';

export type Side = "A" | "B";
export type SupportedLang = "auto" | "vi" | "en" | "ja";

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
}

interface AppState {
  connected: boolean;
  sessionReady: boolean;
  sessionId: string | null;
  activeSide: Side | null;
  isMicActive: boolean;
  vadSpeaking: Record<Side, boolean>;
  sideALang: SupportedLang;
  sideBLang: SupportedLang;
  detectedSideLang: Record<Side, string>;
  utterances: Record<number, Utterance>;
  errorMessage: string | null;
  captureWarning: string | null;
  audioSource: 'mic' | 'tab';
  meetingMode: boolean;

  setConnected: (status: boolean) => void;
  setActiveSide: (side: Side | null) => void;
  setMicActive: (active: boolean) => void;
  setSideConfig: (side: Side, lang: SupportedLang) => void;
  setAudioSource: (source: 'mic' | 'tab') => void;
  setMeetingMode: (active: boolean) => void;
  setError: (msg: string | null) => void;
  setCaptureWarning: (msg: string | null) => void;
  clearError: () => void;
  clearHistory: () => void;
  handleServerEvent: (event: ServerEvent) => void;
}

export const useStore = create<AppState>((set, get) => ({
  connected: false,
  sessionReady: false,
  sessionId: null,
  activeSide: null,
  isMicActive: false,
  vadSpeaking: { A: false, B: false },
  sideALang: "vi",
  sideBLang: "en",
  detectedSideLang: { A: "vi", B: "en" },
  utterances: {},
  errorMessage: null,
  captureWarning: null,
  audioSource: 'mic',
  meetingMode: false,

  setConnected: (status) => set({ connected: status }),
  setActiveSide: (side) => set({ activeSide: side }),
  setMicActive: (active) => set({ isMicActive: active }),
  setCaptureWarning: (msg) => set({ captureWarning: msg }),
  setAudioSource: (source) => set({ audioSource: source }),
  setMeetingMode: (active) => set({ meetingMode: active }),
  
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
              isSpeaking: true
            };
          } else {
            newUtterances[event.utterance_id] = {
              ...newUtterances[event.utterance_id],
              originalText: event.text
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
              isSpeaking: false
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
          if (newUtterances[event.utterance_id]) {
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
          if (newUtterances[event.utterance_id]) {
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
