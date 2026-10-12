// Phép kiểm "đang nghe" (docs 08 §4.1) và mã kết nối theo trang (docs 08 §4.3): logic thuần, không đụng tới DOM, để
// kiểm bằng vitest. ws_client.ts gom trạng thái track/AudioContext/khung audio rồi gọi các hàm ở đây.

export type CaptureSource = 'mic' | 'tab';

export type CaptureProblem =
  | 'ended' // track đã kết thúc: mất hẳn, phải xin lại
  | 'muted' // trang/app khác lấy mic (cuộc gọi, Siri, tab khác), hoặc hệ thống tạm tắt
  | 'suspended' // AudioContext bị dừng: khoá màn hình, chuyển app
  | 'stalled' // không còn khung audio nào tới
  | 'zeros'; // khung tới đều nhưng toàn số 0: mic bị hệ thống tắt tiếng

export interface CaptureSnapshot {
  source: CaptureSource;
  trackState: 'live' | 'ended' | 'none';
  trackMuted: boolean;
  contextState: string; // AudioContext.state: running, suspended, interrupted (iOS), closed, none
  now: number; // ms
  lastChunkAt: number; // ms: khung audio cuối cùng, hoặc lúc bắt đầu thu
  zeroSince: number; // ms: đầu chuỗi khung toàn số 0 đang diễn ra; 0 nếu khung gần nhất có tiếng
  contextBadSince: number; // ms: lúc AudioContext bắt đầu không "running"; 0 nếu đang chạy
}

export const STALL_MS = 2000;
export const ZERO_MS = 2000;
// AudioContext thường tự chạy lại sau vài trăm ms (watchdog gọi resume): chờ chút rồi mới báo
export const CONTEXT_GRACE_MS = 1500;

export function detectCaptureProblem(s: CaptureSnapshot): CaptureProblem | null {
  if (s.trackState !== 'live') return 'ended';
  if (s.trackMuted) return 'muted';
  if (s.contextState !== 'running' && s.contextBadSince > 0 && s.now - s.contextBadSince >= CONTEXT_GRACE_MS) {
    return 'suspended';
  }
  if (s.now - s.lastChunkAt > STALL_MS) return 'stalled';
  // Thu âm tab: video tạm dừng thì luồng âm thanh là im lặng số, không phải lỗi
  if (s.source === 'mic' && s.zeroSince > 0 && s.now - s.zeroSince >= ZERO_MS) return 'zeros';
  return null;
}

// AudioContext bị dừng thì resume() trong lần chạm là đủ. Các lỗi còn lại phải dừng luồng cũ và xin lại mic/tab ngay
// trong lần chạm: trên Safari, gọi lại getUserMedia là cách lấy lại mic từ trang hoặc app khác.
export function needsNewCapture(problem: CaptureProblem | null): boolean {
  return problem === 'ended' || problem === 'muted' || problem === 'zeros' || problem === 'stalled';
}

export function captureMessage(problem: CaptureProblem, source: CaptureSource): string {
  if (source === 'tab') {
    switch (problem) {
      case 'ended':
        return 'Đã dừng chia sẻ âm thanh tab. Chạm để chọn lại tab.';
      case 'muted':
        return 'Âm thanh tab đang bị tắt. Chạm để thu lại.';
      case 'suspended':
        return 'Trình duyệt đã tạm dừng thu âm. Chạm để tiếp tục nghe.';
      default:
        return 'Không còn nhận được âm thanh tab. Chạm để thu lại.';
    }
  }
  switch (problem) {
    case 'ended':
      return 'Micro đã bị tắt. Chạm để bật lại.';
    case 'muted':
      return 'Micro đang bị ứng dụng hoặc tab khác dùng (cuộc gọi, Siri, ghi âm…). Chạm để lấy lại micro.';
    case 'suspended':
      return 'Trình duyệt đã tạm dừng thu âm (khoá màn hình hoặc chuyển ứng dụng). Chạm để tiếp tục nghe.';
    case 'zeros':
      return 'Micro chỉ gửi im lặng tuyệt đối, có thể đang bị hệ thống tắt tiếng. Chạm để bật lại micro.';
    default:
      return 'Không còn nhận được âm thanh từ micro. Chạm để thu lại.';
  }
}

// Mỗi trang một mã, chỉ giữ trong bộ nhớ: tab khác (kể cả tab nhân bản) có mã khác nên không bao giờ đá nhau. Mã chỉ để
// chính trang này, khi nối lại, thay được kết nối "chết" của mình trên server.
export function newClientId(): string {
  const c = (globalThis as { crypto?: Crypto }).crypto;
  if (c && typeof c.randomUUID === 'function') return `page-${c.randomUUID()}`; // cần HTTPS hoặc localhost
  return `page-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

export function wsUrlWithClientId(url: string, clientId: string): string {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}client_id=${encodeURIComponent(clientId)}`;
}

// Server đóng bằng mã này khi kết nối bị thay bởi một kết nối mới cùng client_id: không tự nối lại
export const REPLACED_CLOSE_CODE = 4409;
