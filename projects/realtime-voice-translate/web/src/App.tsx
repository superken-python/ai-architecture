import React, { useEffect, useRef, useState } from 'react';
import { useStore, Side, SupportedLang, Utterance } from './state/useStore';
import { rvtClient } from './net/ws_client';
import { setupWakeLockAutoRefresh } from './audio/wake-lock';

const LANG_LABELS: Record<string, string> = {
  auto: "Tự động",
  vi: "Tiếng Việt",
  ja: "日本語",
  en: "English"
};

import { cleanTranslationText } from './utils/cleanText';
export { cleanTranslationText };

interface MeetingUtteranceCardProps {
  u: Utterance;
  targetLang: string;
  primaryLang: string;
  fontSize: number;
}

const MeetingUtteranceCard = React.memo<MeetingUtteranceCardProps>(({ u, targetLang, primaryLang, fontSize }) => {
  const rawTrans = u.translations[targetLang];
  const trans = rawTrans ? cleanTranslationText(rawTrans) : (u.isFinal ? "" : "… đang dịch");
  const spokenLang = u.originalLang || primaryLang;
  const conf = u.langProbs?.[spokenLang] ? ` ${Math.round(u.langProbs[spokenLang] * 100)}%` : "";

  return (
    <div
      key={u.id}
      style={{
        backgroundColor: '#18181b',
        borderLeft: '4px solid #3b82f6',
        borderRadius: '8px',
        padding: '8px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#94a3b8' }}>
        <span style={{ backgroundColor: '#2563eb', color: '#fff', padding: '1px 6px', borderRadius: '8px', fontWeight: 600 }}>
          {spokenLang.toUpperCase()}{conf}
        </span>
        {!u.isFinal && <span style={{ color: '#f59e0b', fontStyle: 'italic' }}>● đang xử lý...</span>}
      </div>

      <div style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>
        {u.originalText}
      </div>

      <div style={{ fontSize: `${fontSize + 2}px`, fontWeight: 600, color: '#f8fafc', lineHeight: 1.35 }}>
        {trans || (u.isFinal ? u.originalText : "… đang dịch")}
      </div>
    </div>
  );
});

const App: React.FC = () => {
  const {
    connected,
    activeSide,
    isMicActive,
    vadSpeaking,
    sideALang,
    sideBLang,
    detectedSideLang,
    utterances,
    errorMessage,
    captureWarning,
    wakeLockHeld,
    audioSource,
    meetingMode,
    setAudioSource,
    setMeetingMode,
    setSideConfig,
    clearError,
    clearHistory
  } = useStore();

  const handleMeetingModeChange = (mode: boolean) => {
    setMeetingMode(mode);
    const targets = mode && sideBLang !== 'auto'
      ? [sideBLang]
      : ['ja', 'en', 'vi'];
    rvtClient.send({
      type: "sides.update",
      sides: {
        A: { lang: sideALang },
        B: { lang: sideBLang }
      },
      targets
    });
  };

  const [fontSizeA, setFontSizeA] = useState<number>(13);
  const [fontSizeB, setFontSizeB] = useState<number>(13);
  const [showThirdLang, setShowThirdLang] = useState<boolean>(true);
  const [overrideModal, setOverrideModal] = useState<{ uid: number; current: string } | null>(null);

  const scrollRefA = useRef<HTMLDivElement>(null);
  const scrollRefB = useRef<HTMLDivElement>(null);
  const scrollRefMeeting = useRef<HTMLDivElement>(null);

  const [debugStats, setDebugStats] = useState<any>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    rvtClient.connect(wsUrl);

    // Keep screen awake on mobile during conversation (xin lại khi bật mic: ws_client.startAudio)
    const cleanupWakeLock = setupWakeLockAutoRefresh();

    let debugTimer: ReturnType<typeof setInterval> | null = null;
    if (typeof window !== 'undefined' && window.location.search.includes('debug=1')) {
      debugTimer = setInterval(() => {
        setDebugStats(rvtClient.getDebugStats());
      }, 2000);
    }
    return () => {
      cleanupWakeLock();
      if (debugTimer) clearInterval(debugTimer);
    };
  }, []);

  const utteranceList = Object.values(utterances);

  // Auto-scroll to latest message in all panels
  useEffect(() => {
    if (scrollRefA.current) {
      scrollRefA.current.scrollTop = scrollRefA.current.scrollHeight;
    }
    if (scrollRefB.current) {
      scrollRefB.current.scrollTop = scrollRefB.current.scrollHeight;
    }
    if (scrollRefMeeting.current) {
      scrollRefMeeting.current.scrollTop = scrollRefMeeting.current.scrollHeight;
    }
  }, [utteranceList.length, isMicActive, vadSpeaking]);

  const toggleMic = (side: Side) => {
    if (activeSide === side && isMicActive) {
      rvtClient.stopAudio();
    } else {
      rvtClient.startAudio(side, audioSource);
    }
  };

  const handleLangChange = (side: Side, lang: SupportedLang) => {
    setSideConfig(side, lang);
    const newA = side === "A" ? lang : sideALang;
    const newB = side === "B" ? lang : sideBLang;
    rvtClient.updateSides(newA, newB);
  };

  const handleOverride = (targetLang: "ja" | "en" | "vi") => {
    if (overrideModal) {
      rvtClient.overrideLang(overrideModal.uid, targetLang);
      setOverrideModal(null);
    }
  };

  // Get effective primary language for a side
  const getPrimaryLang = (side: Side): string => {
    const locked = side === "A" ? sideALang : sideBLang;
    if (locked !== "auto") return locked;
    return detectedSideLang[side] || (side === "A" ? "vi" : "ja");
  };

  const primaryLangA = getPrimaryLang("A");
  const primaryLangB = getPrimaryLang("B");

  // Determine the third language
  const allLangs = ["ja", "en", "vi"];
  const thirdLangA = allLangs.find((l) => l !== primaryLangA && l !== primaryLangB) || "en";
  const thirdLangB = thirdLangA;

  // Render conversation content for one side
  const renderHalfContent = (side: Side, fontSize: number, scrollRef: React.RefObject<HTMLDivElement | null>) => {
    const primaryLang = side === "A" ? primaryLangA : primaryLangB;
    const otherLang = side === "A" ? primaryLangB : primaryLangA;

    if (utteranceList.length === 0) {
      return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '20px' }}>
          {isMicActive && activeSide === side ? (
            <div style={{ color: '#4ade80', fontStyle: 'italic', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '24px' }}>🎙️</span>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Đang lắng nghe...</span>
              <span style={{ fontSize: '11px', color: '#86efac' }}>Nói tự nhiên, hệ thống sẽ tự ngắt câu và dịch liên tục. Nhấn DỪNG MIC khi nói xong.</span>
            </div>
          ) : isMicActive && activeSide !== side ? (
            <div style={{ color: '#60a5fa', fontStyle: 'italic', fontSize: '12px' }}>
              <span>🎙️ Bên đối diện đang nói... Bản dịch sẽ hiển thị tại đây.</span>
            </div>
          ) : (
            <div style={{ color: '#666', fontStyle: 'italic', fontSize: '12px' }}>
              Chạm vào nút <strong>BẬT MIC {side}</strong> bên dưới để bắt đầu nói...
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          padding: '4px 2px',
          WebkitOverflowScrolling: 'touch'
        }}
      >
        {utteranceList.map((u: Utterance) => {
          const isSpeaker = u.side === side;
          const spokenLang = u.originalLang || (u.side === "A" ? primaryLangA : primaryLangB);

          let mainText = "";
          let isOriginal = false;
          let badgeText = "";

          if (isSpeaker) {
            // This side spoke: main text is original spoken text
            mainText = u.originalText;
            isOriginal = true;
            const conf = u.langProbs?.[spokenLang]
              ? ` ${Math.round(u.langProbs[spokenLang] * 100)}%`
              : "";
            badgeText = (spokenLang.toUpperCase() + conf).trim();
            if (u.uncertain) badgeText += " ❓";
          } else {
            // Other side spoke: main text is translation into this side's language
            const rawTrans = u.translations[primaryLang];
            mainText = rawTrans ? cleanTranslationText(rawTrans) : (u.isFinal ? u.originalText : "… đang dịch");
          }

          const hasBadge = (isOriginal && !!badgeText) || !u.isFinal;

          return (
            <div
              key={u.id}
              style={{
                backgroundColor: isSpeaker ? '#1e293b' : '#18181b',
                borderLeft: isSpeaker ? '3px solid #3b82f6' : '3px solid #10b981',
                borderRadius: '8px',
                padding: '6px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
              }}
            >
              {/* Badges row: Right aligned, no redundant speaker labels */}
              {hasBadge && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '6px', fontSize: '10px' }}>
                  {isOriginal && badgeText && (
                    <span
                      onClick={() => setOverrideModal({ uid: u.id, current: spokenLang })}
                      title="Chạm để đổi ngôn ngữ câu"
                      style={{
                        fontSize: '9px',
                        backgroundColor: u.uncertain ? '#ea580c' : '#2563eb',
                        color: '#fff',
                        padding: '1px 5px',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        userSelect: 'none'
                      }}
                    >
                      {badgeText}
                    </span>
                  )}
                  {!u.isFinal && (
                    <span style={{ color: '#f59e0b', fontSize: '10px', fontStyle: 'italic' }}>
                      ● đang xử lý...
                    </span>
                  )}
                </div>
              )}

              {/* Main Text */}
              <div style={{ fontSize: `${fontSize}px`, fontWeight: 500, lineHeight: 1.35, wordBreak: 'break-word', color: '#f8fafc' }}>
                {mainText || (u.isSpeaking ? "… đang nghe" : "…")}
              </div>
            </div>
          );
        })}

        {/* Live listening status indicator at bottom of stream */}
        {isMicActive && activeSide === side && (
          <div style={{ color: '#4ade80', fontSize: '11px', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px' }}>
            <span style={{ display: 'inline-block', width: '7px', height: '7px', borderRadius: '50%', backgroundColor: vadSpeaking[side] ? '#ef4444' : '#22c55e' }} />
            <span>{vadSpeaking[side] ? '🎙️ Đang ghi nhận giọng nói...' : '🎙️ Đang nghe... Hãy nói tiếp hoặc nhấn DỪNG MIC khi xong.'}</span>
          </div>
        )}
      </div>
    );
  };

  const isSideAActive = isMicActive && activeSide === "A";
  const isSideBActive = isMicActive && activeSide === "B";

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', backgroundColor: '#121212', color: '#fff', fontFamily: 'sans-serif', userSelect: 'none', overflow: 'hidden' }}>
      
      {/* Top Application Bar: Mode switch & Audio source toggle */}
      <div style={{ height: '38px', backgroundColor: '#18181b', borderBottom: '1px solid #27272a', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 12px', fontSize: '11px', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <button
            onClick={() => handleMeetingModeChange(false)}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: !meetingMode ? '#2563eb' : '#27272a',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: !meetingMode ? 600 : 400,
              fontSize: '11px'
            }}
          >
            👥 2 Chiều
          </button>
          <button
            onClick={() => handleMeetingModeChange(true)}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: meetingMode ? '#2563eb' : '#27272a',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: meetingMode ? 600 : 400,
              fontSize: '11px'
            }}
          >
            📺 Video & Họp
          </button>
        </div>

        {/* Audio Source Selector */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <span style={{ color: '#71717a', fontSize: '10px' }}>Nguồn:</span>
          <button
            onClick={() => setAudioSource('mic')}
            title="Thu từ microphone thiết bị"
            style={{
              padding: '3px 8px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: audioSource === 'mic' ? '#3f3f46' : '#27272a',
              color: audioSource === 'mic' ? '#38bdf8' : '#a1a1aa',
              cursor: 'pointer',
              fontSize: '10px',
              fontWeight: audioSource === 'mic' ? 600 : 400
            }}
          >
            🎙️ Mic
          </button>
          <button
            onClick={() => setAudioSource('tab')}
            title="Thu âm thanh số trực tiếp từ Tab YouTube / Video / Màn hình (không bị bộ khử vọng xóa)"
            style={{
              padding: '3px 8px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: audioSource === 'tab' ? '#3f3f46' : '#27272a',
              color: audioSource === 'tab' ? '#38bdf8' : '#a1a1aa',
              cursor: 'pointer',
              fontSize: '10px',
              fontWeight: audioSource === 'tab' ? 600 : 400
            }}
          >
            💻 Tab/Video
          </button>
        </div>
      </div>

      {/* Error banner */}
      {errorMessage && (
        <div style={{ backgroundColor: '#D32F2F', color: '#fff', padding: '8px 16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>⚠️ {errorMessage}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      {/* Capture Warning / Tap to resume overlay banner (Safari & iOS handling - Mục 9.4 docs 07) */}
      {captureWarning && (
        <div
          onClick={() => rvtClient.resumeCapture()}
          style={{
            backgroundColor: '#ea580c',
            color: '#fff',
            padding: '10px 16px',
            fontSize: '13px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            zIndex: 100
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>⚠️</span>
            <span>{captureWarning}</span>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              rvtClient.resumeCapture();
            }}
            style={{
              backgroundColor: '#fff',
              color: '#ea580c',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              fontWeight: 700,
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Chạm để tiếp tục nghe
          </button>
        </div>
      )}

      {/* Không giữ được màn hình sáng khi đang nghe: màn hình tự khoá sẽ làm ngừng thu âm (docs 08 §4.5) */}
      {isMicActive && !wakeLockHeld && !captureWarning && (
        <div style={{ backgroundColor: '#1e293b', color: '#fbbf24', padding: '6px 16px', fontSize: '12px', borderBottom: '1px solid #334155' }}>
          🔆 Màn hình có thể tự khoá và làm ngừng thu âm. Tắt Tự động khoá hoặc cắm sạc trong lúc dùng.
        </div>
      )}

      {/* Mode View: Continuous Meeting / Video vs Split Screen */}
      {meetingMode ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '10px 14px' }}>
          {/* Controls Bar for Meeting Mode */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Nói:</span>
              <select
                value={sideALang}
                onChange={(e) => handleLangChange("A", e.target.value as SupportedLang)}
                style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '6px', padding: '3px 6px', fontSize: '12px' }}
              >
                <option value="auto">🌐 Tự động (LID)</option>
                <option value="ja">🇯🇵 日本語</option>
                <option value="en">🇬🇧 English</option>
                <option value="vi">🇻🇳 Tiếng Việt</option>
              </select>

              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Dịch sang:</span>
              <select
                value={sideBLang}
                onChange={(e) => handleLangChange("B", e.target.value as SupportedLang)}
                style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '6px', padding: '3px 6px', fontSize: '12px' }}
              >
                <option value="vi">🇻🇳 Tiếng Việt</option>
                <option value="en">🇬🇧 English</option>
                <option value="ja">🇯🇵 日本語</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <button onClick={() => setFontSizeA((s) => Math.min(24, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A+</button>
              <button onClick={() => setFontSizeA((s) => Math.max(10, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A-</button>
              {utteranceList.length > 0 && (
                <button onClick={clearHistory} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '11px' }}>🗑️ Xóa</button>
              )}
            </div>
          </div>

          {/* Audio capture reminder */}
          {audioSource === 'mic' ? (
            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px', fontSize: '11px', color: '#93c5fd', marginBottom: '8px' }}>
              💡 <strong>Lưu ý:</strong> Trên iPhone/iPad (Safari), giữ trình duyệt mở và màn hình sáng; phát video trên thiết bị khác (TV/máy tính). Nếu xem video trên chính máy này, hãy chọn nguồn <strong>💻 Tab/Video</strong> ở góc trên!
            </div>
          ) : (
            <div style={{ backgroundColor: '#064e3b', border: '1px solid #047857', borderRadius: '6px', padding: '6px 10px', fontSize: '11px', color: '#a7f3d0', marginBottom: '8px' }}>
              💻 <strong>Thu âm Tab/Video:</strong> Tín hiệu số trực tiếp từ tab video/họp (độ chính xác cao, không tiếng ồn phòng).
            </div>
          )}

          {/* Subtitle feed */}
          <div ref={scrollRefMeeting} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', padding: '4px 2px', WebkitOverflowScrolling: 'touch' }}>
            {utteranceList.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                <span style={{ fontSize: '32px', marginBottom: '8px' }}>📺</span>
                <span>Bật <strong>DỊCH LIÊN TỤC</strong> bên dưới và phát video hoặc bắt đầu cuộc họp.</span>
                <span style={{ fontSize: '11px', color: '#475569', marginTop: '4px' }}>Hệ thống sẽ tự động ngắt câu linh hoạt và dịch phụ đề liên tục theo thời gian thực.</span>
              </div>
            ) : (
              utteranceList.slice(-150).map((u) => {
                const targetLang = sideBLang === "auto" ? "vi" : sideBLang;
                const primaryLang = u.side === "A" ? primaryLangA : primaryLangB;
                return (
                  <MeetingUtteranceCard
                    key={u.id}
                    u={u}
                    targetLang={targetLang}
                    primaryLang={primaryLang}
                    fontSize={fontSizeA}
                  />
                );
              })
            )}
          </div>

          {/* Action button */}
          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            <button
              onClick={() => toggleMic("A")}
              style={{
                width: '100%',
                maxWidth: '400px',
                padding: '12px 24px',
                borderRadius: '28px',
                background: isSideAActive ? (vadSpeaking.A ? '#FF5252' : '#D32F2F') : '#007AFF',
                color: 'white',
                border: 'none',
                fontWeight: 700,
                fontSize: '14px',
                boxShadow: isSideAActive ? '0 0 20px rgba(239,68,68,0.7)' : '0 4px 12px rgba(0,122,255,0.4)',
                transition: 'all 0.2s',
                cursor: 'pointer'
              }}
            >
              {isSideAActive ? (vadSpeaking.A ? '🎙 ĐANG NHẬN DIỆN TIẾNG NÓI...' : '⏹ DỪNG DỊCH LIÊN TỤC') : '▶️ BẬT DỊCH LIÊN TỤC (MIC A)'}
            </button>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              {isSideAActive ? '🟢 Đang chạy liên tục. Nhấn nút trên khi muốn dừng.' : 'Hệ thống tự động cắt câu và dịch theo luồng.'}
            </span>
          </div>
        </div>
      ) : (
        /* Split Screen (Face-to-Face Dual Mode) */
        <>
          {/* Side B - Top half (Rotated 180° for opposite person) */}
          <div style={{ flex: 1, transform: 'rotate(180deg)', borderBottom: '2px solid #2A2A2A', padding: '10px 14px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Controls Side B */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <button
                onClick={() => toggleMic("B")}
                style={{
                  padding: '8px 16px',
                  borderRadius: '24px',
                  background: isSideBActive ? (vadSpeaking.B ? '#FF5252' : '#D32F2F') : '#263238',
                  color: 'white',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '12px',
                  boxShadow: isSideBActive ? '0 0 16px rgba(239,68,68,0.6)' : 'none',
                  transition: 'all 0.2s',
                  cursor: 'pointer'
                }}
              >
                {isSideBActive ? (vadSpeaking.B ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC B') : '🎙 BẬT MIC B'}
              </button>
              
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <select
                  value={sideBLang}
                  onChange={(e) => handleLangChange("B", e.target.value as SupportedLang)}
                  style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '8px', padding: '3px 6px', fontSize: '12px' }}
                >
                  <option value="auto">🌐 Tự động (LID)</option>
                  <option value="en">English</option>
                  <option value="vi">Tiếng Việt</option>
                  <option value="ja">日本語</option>
                </select>
                <button onClick={() => setFontSizeB((s) => Math.min(22, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A+</button>
                <button onClick={() => setFontSizeB((s) => Math.max(10, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A-</button>
              </div>
            </div>

            {/* Conversation Stream Side B */}
            {renderHalfContent("B", fontSizeB, scrollRefB)}
          </div>

          {/* Middle Divider & Status Indicator */}
          <div style={{ height: '30px', backgroundColor: '#1A1A1A', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 14px', fontSize: '11px', color: '#888', borderTop: '1px solid #222', borderBottom: '1px solid #222' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: connected ? '#00E676' : '#FF1744' }} />
              <span>{connected ? "WSS Sẵn sàng" : "Đang kết nối..."}</span>
            </div>

            {utteranceList.length > 0 && (
              <button
                onClick={clearHistory}
                title="Xóa toàn bộ hội thoại hiện tại"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <span>🗑️</span> Xóa hội thoại
              </button>
            )}

            <div style={{ fontSize: '10px', color: '#666' }}>
              {isMicActive ? `Đang nghe Bên ${activeSide}` : "Sẵn sàng (Chạm mic để nói)"}
            </div>
          </div>

          {/* Side A - Bottom half (Facing user A) */}
          <div style={{ flex: 1, padding: '10px 14px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Conversation Stream Side A */}
            {renderHalfContent("A", fontSizeA, scrollRefA)}

            {/* Controls Side A */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <select
                  value={sideALang}
                  onChange={(e) => handleLangChange("A", e.target.value as SupportedLang)}
                  style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '8px', padding: '3px 6px', fontSize: '12px' }}
                >
                  <option value="auto">🌐 Tự động (LID)</option>
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                </select>
                <button onClick={() => setFontSizeA((s) => Math.min(22, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A+</button>
                <button onClick={() => setFontSizeA((s) => Math.max(10, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '3px 6px', cursor: 'pointer', fontSize: '11px' }}>A-</button>
              </div>

              <button
                onClick={() => toggleMic("A")}
                style={{
                  padding: '8px 16px',
                  borderRadius: '24px',
                  background: isSideAActive ? (vadSpeaking.A ? '#FF5252' : '#D32F2F') : '#007AFF',
                  color: 'white',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '12px',
                  boxShadow: isSideAActive ? '0 0 16px rgba(239,68,68,0.6)' : 'none',
                  transition: 'all 0.2s',
                  cursor: 'pointer'
                }}
              >
                {isSideAActive ? (vadSpeaking.A ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC A') : '🎙 BẬT MIC A'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Language Override Modal */}
      {overrideModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#222', padding: '20px', borderRadius: '12px', minWidth: '260px', textAlign: 'center', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
            <h3 style={{ marginTop: 0, fontSize: '16px' }}>Sửa ngôn ngữ câu</h3>
            <p style={{ color: '#aaa', fontSize: '13px' }}>Nhận dạng lại và dịch lại sang 2 tiếng còn lại:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <button onClick={() => handleOverride("vi")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none', cursor: 'pointer' }}>Tiếng Việt (VI)</button>
              <button onClick={() => handleOverride("ja")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none', cursor: 'pointer' }}>日本語 (JA)</button>
              <button onClick={() => handleOverride("en")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none', cursor: 'pointer' }}>English (EN)</button>
            </div>
            <button onClick={() => setOverrideModal(null)} style={{ marginTop: '16px', background: 'none', color: '#888', border: 'none', cursor: 'pointer' }}>Hủy</button>
          </div>
        </div>
      )}

      {/* Debug status bar (Mục 9.3 docs 07) */}
      {debugStats && (
        <div style={{ backgroundColor: '#09090b', borderTop: '1px solid #27272a', padding: '4px 12px', fontSize: '10px', color: '#a1a1aa', display: 'flex', gap: '12px', flexWrap: 'wrap', fontFamily: 'monospace', flexShrink: 0 }}>
          <span>Ctx: <b style={{ color: debugStats.audioContextState === 'running' ? '#4ade80' : '#f87171' }}>{debugStats.audioContextState}</b></span>
          <span>Track: {debugStats.trackReadyState} {debugStats.trackMuted ? '(MUTED)' : ''}</span>
          <span>RMS: {debugStats.rmsDbfs !== null ? `${debugStats.rmsDbfs}dBFS` : '—'}</span>
          <span>Chunks: {debugStats.chunksSent}</span>
          <span>WS: <b style={{ color: debugStats.wsState === 'OPEN' ? '#4ade80' : '#f87171' }}>{debugStats.wsState}</b></span>
          <span>Last msg: {debugStats.lastServerMsgSecAgo}s ago</span>
          <span>Vis: {debugStats.docVisible}</span>
        </div>
      )}

    </div>
  );
};

export default App;
