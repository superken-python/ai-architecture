let wakeLockSentinel: any = null;

export async function requestWakeLock(): Promise<boolean> {
  if ('wakeLock' in navigator) {
    try {
      wakeLockSentinel = await (navigator as any).wakeLock.request('screen');
      wakeLockSentinel.addEventListener('release', () => {
        wakeLockSentinel = null;
      });
      return true;
    } catch (err) {
      console.warn('Screen Wake Lock request failed:', err);
      return false;
    }
  }
  return false;
}

// Màn hình còn được giữ sáng không: trình duyệt tự nhả wake lock khi trang bị ẩn, hoặc từ chối (pin yếu, không có thao
// tác người dùng, Safari < 16.4). ws_client.ts đọc giá trị này để hiện nhắc nhở khi đang nghe (docs 08 §4.5).
export function isWakeLockHeld(): boolean {
  return wakeLockSentinel !== null && wakeLockSentinel.released !== true;
}

export function releaseWakeLock(): void {
  if (wakeLockSentinel) {
    wakeLockSentinel.release().catch(() => {});
    wakeLockSentinel = null;
  }
}

export function setupWakeLockAutoRefresh(): () => void {
  const handleVisibilityChange = async () => {
    if (document.visibilityState === 'visible') {
      await requestWakeLock();
    }
  };

  document.addEventListener('visibilitychange', handleVisibilityChange);
  requestWakeLock();

  return () => {
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    releaseWakeLock();
  };
}
