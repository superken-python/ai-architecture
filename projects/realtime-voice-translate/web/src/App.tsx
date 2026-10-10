import React, { useEffect, useState } from 'react';
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
    clearError
  } = useStore();

  const [fontSizeA, setFontSizeA] = useState<number>(22);
  const [fontSizeB, setFontSizeB] = useState<number>(22);
  const [showThirdLang, setShowThirdLang] = useState<boolean>(true);
  const [overrideModal, setOverrideModal] = useState<{ uid: number; current: string } | null>(null);

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

  // Latest utterance
  const utteranceList = Object.values(utterances);
  const currentU: Utterance | undefined = utteranceList[utteranceList.length - 1];

  // Render content for a side according to Section 7.2 display rules
  const renderHalfContent = (side: Side, fontSize: number) => {
    if (!currentU) {
      return (
        <div style={{ color: '#555', fontStyle: 'italic', margin: 'auto' }}>
          Chạm mic để bắt đầu nói...
        </div>
      );
    }

    const primaryLang = side === "A" ? primaryLangA : primaryLangB;
    const otherSide: Side = side === "A" ? "B" : "A";
    const speakerSide = currentU.side;
    const spokenLang = currentU.originalLang || (speakerSide === "A" ? primaryLangA : primaryLangB);

    let mainText = "";
    let subText = "";
    let isOriginal = false;
    let badgeText = "";

    if (spokenLang === primaryLang) {
      // Spoken language matches this half's primary language
      if (speakerSide === side) {
        // This half spoke: show original text in main
        mainText = currentU.originalText;
        isOriginal = true;
        const conf = currentU.langProbs?.[spokenLang]
          ? ` ${Math.round(currentU.langProbs[spokenLang] * 100)}%`
          : "";
        badgeText = (spokenLang.toUpperCase() + conf).trim();
        if (currentU.uncertain) badgeText += " ❓";

        // Show third language as subText
        if (showThirdLang && currentU.translations[thirdLangA]) {
          subText = `${LANG_LABELS[thirdLangA]}: ${currentU.translations[thirdLangA]}`;
        }
      } else {
        // Other half spoke in our language
        mainText = currentU.translations[primaryLang] || currentU.originalText;
      }
    } else {
      // Spoken language differs from this half's primary language: show translation
      mainText = currentU.translations[primaryLang] || (currentU.isFinal ? "..." : "");
      if (showThirdLang && currentU.translations[thirdLangA] && thirdLangA !== primaryLang) {
        subText = `${LANG_LABELS[thirdLangA]}: ${currentU.translations[thirdLangA]}`;
      }
    }

    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ fontSize: `${fontSize}px`, fontWeight: 500, lineHeight: 1.4, wordBreak: 'break-word' }}>
          {mainText || (currentU.isSpeaking ? "… đang nghe" : "…")}
          {isOriginal && badgeText && (
            <span
              onClick={() => setOverrideModal({ uid: currentU.id, current: spokenLang })}
              style={{
                marginLeft: '8px',
                fontSize: '12px',
                backgroundColor: currentU.uncertain ? '#E65100' : '#1976D2',
                padding: '3px 8px',
                borderRadius: '12px',
                cursor: 'pointer',
                verticalAlign: 'middle',
                display: 'inline-block'
              }}
            >
              {badgeText}
            </span>
          )}
        </div>
        {subText && (
          <div style={{ fontSize: `${Math.max(13, fontSize - 8)}px`, color: '#888', marginTop: '8px' }}>
            {subText}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', backgroundColor: '#121212', color: '#fff', fontFamily: 'sans-serif', userSelect: 'none' }}>
      
      {/* Error banner */}
      {errorMessage && (
        <div style={{ backgroundColor: '#D32F2F', color: '#fff', padding: '8px 16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>⚠️ {errorMessage}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      {/* Side B - Top half (Rotated 180° for opposite person) */}
      <div style={{ flex: 1, transform: 'rotate(180deg)', borderBottom: '2px solid #2A2A2A', padding: '16px', display: 'flex', flexDirection: 'column' }}>
        {/* Controls Side B */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={() => toggleMic("B")}
            style={{
              padding: '10px 20px',
              borderRadius: '24px',
              background: activeSide === "B" ? (vadSpeaking.B ? '#FF5252' : '#D32F2F') : '#263238',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              boxShadow: activeSide === "B" && vadSpeaking.B ? '0 0 16px #FF5252' : 'none',
              transition: 'all 0.2s'
            }}
          >
            {activeSide === "B" ? (vadSpeaking.B ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC B') : 'MIC B'}
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
            <button onClick={() => setFontSizeB((s) => Math.min(36, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px' }}>A+</button>
            <button onClick={() => setFontSizeB((s) => Math.max(16, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px' }}>A-</button>
          </div>
        </div>

        {/* Content Side B */}
        {renderHalfContent("B", fontSizeB)}
      </div>

      {/* Middle Divider & Status Indicator */}
      <div style={{ height: '28px', backgroundColor: '#1A1A1A', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#777' }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: connected ? '#00E676' : '#FF1744' }} />
        <span>{connected ? "WSS Sẵn sàng" : "Đang kết nối..."}</span>
      </div>

      {/* Side A - Bottom half (Facing user A) */}
      <div style={{ flex: 1, padding: '16px', display: 'flex', flexDirection: 'column' }}>
        {/* Content Side A */}
        {renderHalfContent("A", fontSizeA)}

        {/* Controls Side A */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto' }}>
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
            <button onClick={() => setFontSizeA((s) => Math.min(36, s + 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px' }}>A+</button>
            <button onClick={() => setFontSizeA((s) => Math.max(16, s - 2))} style={{ backgroundColor: '#333', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 8px' }}>A-</button>
          </div>

          <button
            onClick={() => toggleMic("A")}
            style={{
              padding: '10px 20px',
              borderRadius: '24px',
              background: activeSide === "A" ? (vadSpeaking.A ? '#FF5252' : '#D32F2F') : '#007AFF',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              boxShadow: activeSide === "A" && vadSpeaking.A ? '0 0 16px #FF5252' : 'none',
              transition: 'all 0.2s'
            }}
          >
            {activeSide === "A" ? (vadSpeaking.A ? '🎙 ĐANG NÓI...' : '⏹ DỪNG MIC A') : 'MIC A'}
          </button>
        </div>
      </div>

      {/* Language Override Modal */}
      {overrideModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#222', padding: '20px', borderRadius: '12px', minWidth: '260px', textAlign: 'center' }}>
            <h3 style={{ marginTop: 0, fontSize: '16px' }}>Sửa ngôn ngữ câu</h3>
            <p style={{ color: '#aaa', fontSize: '13px' }}>Nhận dạng lại và dịch lại sang 2 tiếng còn lại:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <button onClick={() => handleOverride("vi")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none' }}>Tiếng Việt (VI)</button>
              <button onClick={() => handleOverride("ja")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none' }}>日本語 (JA)</button>
              <button onClick={() => handleOverride("en")} style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#333', color: '#fff', border: 'none' }}>English (EN)</button>
            </div>
            <button onClick={() => setOverrideModal(null)} style={{ marginTop: '16px', background: 'none', color: '#888', border: 'none', cursor: 'pointer' }}>Hủy</button>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;
