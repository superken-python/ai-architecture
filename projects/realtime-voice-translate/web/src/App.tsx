import React, { useEffect, useRef, useState } from 'react';
import { useStore, Side, SupportedLang, Utterance } from './state/useStore';
import { rvtClient } from './net/ws_client';

const LANG_LABELS: Record<string, string> = {
  auto: "Tự động",
  vi: "Tiếng Việt",
  ja: "日本語",
  en: "English"
};

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
    setSideConfig,
    clearError,
    clearHistory
  } = useStore();

  const [fontSizeA, setFontSizeA] = useState<number>(20);
  const [fontSizeB, setFontSizeB] = useState<number>(20);
  const [showThirdLang, setShowThirdLang] = useState<boolean>(true);
  const [overrideModal, setOverrideModal] = useState<{ uid: number; current: string } | null>(null);

  const scrollRefA = useRef<HTMLDivElement>(null);
  const scrollRefB = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    rvtClient.connect(wsUrl);

    // Keep screen awake on mobile during conversation
    import('./audio/wake-lock').then(({ setupWakeLockAutoRefresh }) => {
      const cleanupWakeLock = setupWakeLockAutoRefresh();
      return cleanupWakeLock;
    });
  }, []);

  const utteranceList = Object.values(utterances);

  // Auto-scroll to latest message in both panels
  useEffect(() => {
    if (scrollRefA.current) {
      scrollRefA.current.scrollTop = scrollRefA.current.scrollHeight;
    }
    if (scrollRefB.current) {
      scrollRefB.current.scrollTop = scrollRefB.current.scrollHeight;
    }
  }, [utteranceList.length, isMicActive, vadSpeaking]);

  const toggleMic = (side: Side) => {
    if (activeSide === side && isMicActive) {
      rvtClient.stopAudio();
    } else {
      rvtClient.startAudio(side);
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
            <div style={{ color: '#4ade80', fontStyle: 'italic', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '28px' }}>🎙️</span>
              <span style={{ fontWeight: 600 }}>Đang lắng nghe...</span>
              <span style={{ fontSize: '13px', color: '#86efac' }}>Nói tự nhiên, hệ thống sẽ tự ngắt câu và dịch liên tục. Nhấn DỪNG MIC khi nói xong.</span>
            </div>
          ) : isMicActive && activeSide !== side ? (
            <div style={{ color: '#60a5fa', fontStyle: 'italic' }}>
              <span>🎙️ Bên đối diện đang nói... Bản dịch sẽ hiển thị tại đây.</span>
            </div>
          ) : (
            <div style={{ color: '#666', fontStyle: 'italic', fontSize: '15px' }}>
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
          gap: '12px',
          padding: '8px 4px',
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
            mainText = u.translations[primaryLang] || (u.isFinal ? u.originalText : "… đang dịch");
          }

          return (
            <div
              key={u.id}
              style={{
                backgroundColor: isSpeaker ? '#1e293b' : '#18181b',
                borderLeft: isSpeaker ? '4px solid #3b82f6' : '4px solid #10b981',
                borderRadius: '8px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.2)'
              }}
            >
              {/* Header row: Speaker and badges */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: '#94a3b8' }}>
                <span style={{ fontWeight: 600, color: isSpeaker ? '#60a5fa' : '#34d399' }}>
                  {isSpeaker ? `Bạn (Bên ${side})` : `Đối phương (Bên ${u.side})`}
                </span>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  {isOriginal && badgeText && (
                    <span
                      onClick={() => setOverrideModal({ uid: u.id, current: spokenLang })}
                      title="Chạm để đổi ngôn ngữ câu"
                      style={{
                        fontSize: '11px',
                        backgroundColor: u.uncertain ? '#ea580c' : '#2563eb',
                        color: '#fff',
                        padding: '2px 6px',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        userSelect: 'none'
                      }}
                    >
                      {badgeText}
                    </span>
                  )}
                  {!u.isFinal && (
                    <span style={{ color: '#f59e0b', fontSize: '11px', fontStyle: 'italic' }}>
                      ● đang xử lý...
                    </span>
                  )}
                </div>
              </div>

              {/* Main Text */}
              <div style={{ fontSize: `${fontSize}px`, fontWeight: 500, lineHeight: 1.4, wordBreak: 'break-word', color: '#f8fafc', marginTop: '2px' }}>
                {mainText || (u.isSpeaking ? "… đang nghe" : "…")}
              </div>

              {/* Translations for speaker, or original text for listener */}
              {isSpeaker ? (
                <div style={{ marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {u.translations[otherLang] && (
                    <div style={{ fontSize: `${Math.max(13, fontSize - 4)}px`, color: '#60a5fa', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, backgroundColor: 'rgba(59,130,246,0.2)', padding: '2px 6px', borderRadius: '4px', color: '#93c5fd' }}>
                        {LANG_LABELS[otherLang]}
                      </span>
                      <span>{u.translations[otherLang]}</span>
                    </div>
                  )}
                  {showThirdLang && u.translations[thirdLangA] && thirdLangA !== otherLang && (
                    <div style={{ fontSize: `${Math.max(12, fontSize - 6)}px`, color: '#94a3b8', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, backgroundColor: 'rgba(148,163,184,0.15)', padding: '2px 6px', borderRadius: '4px', color: '#cbd5e1' }}>
                        {LANG_LABELS[thirdLangA]}
                      </span>
                      <span>{u.translations[thirdLangA]}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ marginTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '6px', fontSize: `${Math.max(12, fontSize - 6)}px`, color: '#94a3b8', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, backgroundColor: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px', color: '#e2e8f0' }}>
                    {LANG_LABELS[spokenLang] || spokenLang.toUpperCase()}
                  </span>
                  <span>{u.originalText}</span>
                </div>
              )}
            </div>
          );
        })}

        {/* Live listening status indicator at bottom of stream */}
        {isMicActive && activeSide === side && (
          <div style={{ color: '#4ade80', fontSize: '13px', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 8px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: vadSpeaking[side] ? '#ef4444' : '#22c55e' }} />
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
      
      {/* Error banner */}
      {errorMessage && (
        <div style={{ backgroundColor: '#D32F2F', color: '#fff', padding: '8px 16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>⚠️ {errorMessage}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      {/* Side B - Top half (Rotated 180° for opposite person) */}
      <div style={{ flex: 1, transform: 'rotate(180deg)', borderBottom: '2px solid #2A2A2A', padding: '12px 16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Controls Side B */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <button
            onClick={() => toggleMic("B")}
            style={{
              padding: '10px 20px',
              borderRadius: '24px',
              background: isSideBActive ? (vadSpeaking.B ? '#FF5252' : '#D32F2F') : '#263238',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              boxShadow: isSideBActive ? '0 0 16px rgba(239,68,68,0.6)' : 'none',
              transition: 'all 0.2s',
              cursor: 'pointer'
            }}
          >
            {isSideBActive ? (vadSpeaking.B ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC B') : '🎙 BẬT MIC B'}
          </button>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select
              value={sideBLang}
              onChange={(e) => handleLangChange("B", e.target.value as SupportedLang)}
              style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '8px', padding: '4px 8px' }}
            >
              <option value="auto">Tự động (ja)</option>
              <option value="ja">日本語</option>
              <option value="en">English</option>
              <option value="vi">Tiếng Việt</option>
            </select>
            <button onClick={() => setFontSizeB((s) => Math.min(32, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}>A+</button>
            <button onClick={() => setFontSizeB((s) => Math.max(14, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}>A-</button>
          </div>
        </div>

        {/* Conversation Stream Side B */}
        {renderHalfContent("B", fontSizeB, scrollRefB)}
      </div>

      {/* Middle Divider & Status Indicator */}
      <div style={{ height: '32px', backgroundColor: '#1A1A1A', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 16px', fontSize: '12px', color: '#888', borderTop: '1px solid #222', borderBottom: '1px solid #222' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: connected ? '#00E676' : '#FF1744' }} />
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
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span>🗑️</span> Xóa hội thoại
          </button>
        )}

        <div style={{ fontSize: '11px', color: '#666' }}>
          {isMicActive ? `Đang nghe Bên ${activeSide}` : "Sẵn sàng (Chạm mic để nói)"}
        </div>
      </div>

      {/* Side A - Bottom half (Facing user A) */}
      <div style={{ flex: 1, padding: '12px 16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Conversation Stream Side A */}
        {renderHalfContent("A", fontSizeA, scrollRefA)}

        {/* Controls Side A */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select
              value={sideALang}
              onChange={(e) => handleLangChange("A", e.target.value as SupportedLang)}
              style={{ backgroundColor: '#1E1E1E', color: '#fff', border: '1px solid #444', borderRadius: '8px', padding: '4px 8px' }}
            >
              <option value="auto">Tự động (vi)</option>
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
            </select>
            <button onClick={() => setFontSizeA((s) => Math.min(32, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}>A+</button>
            <button onClick={() => setFontSizeA((s) => Math.max(14, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}>A-</button>
          </div>

          <button
            onClick={() => toggleMic("A")}
            style={{
              padding: '10px 20px',
              borderRadius: '24px',
              background: isSideAActive ? (vadSpeaking.A ? '#FF5252' : '#D32F2F') : '#007AFF',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              boxShadow: isSideAActive ? '0 0 16px rgba(239,68,68,0.6)' : 'none',
              transition: 'all 0.2s',
              cursor: 'pointer'
            }}
          >
            {isSideAActive ? (vadSpeaking.A ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC A') : '🎙 BẬT MIC A'}
          </button>
        </div>
      </div>

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

    </div>
  );
};

export default App;
