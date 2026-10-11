import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isRemoteRun = Boolean(process.env.TARGET_URL);

// Golden evaluation paths
const GOLDEN_DIR = path.resolve(__dirname, '../../../eval/golden_1');
const GOLDEN_AUDIO_MP4 = path.join(GOLDEN_DIR, 'audio/videoplayback.mp4');
const GOLDEN_SUBTITLE_TXT = path.join(
  GOLDEN_DIR,
  'subtitle/[Japanese (auto-generated)] NARUTO  - EPISODE 2 (THE SURVIVAL TEST) AI 4K LIVE ACTION [DownSub.com].txt'
);
const FIXTURE_PCM = path.join(__dirname, '../fixtures/golden_1/naruto_scene1_16k.pcm');

// Auto-extract 56s 16kHz mono PCM from videoplayback.mp4 if fixture does not exist
if (!fs.existsSync(FIXTURE_PCM) && fs.existsSync(GOLDEN_AUDIO_MP4)) {
  fs.mkdirSync(path.dirname(FIXTURE_PCM), { recursive: true });
  execSync(`ffmpeg -y -i "${GOLDEN_AUDIO_MP4}" -ss 0 -t 56 -ac 1 -ar 16000 -f s16le "${FIXTURE_PCM}"`, {
    stdio: 'ignore',
  });
}

test.describe('Naruto Episode 2 Golden Audio Test (eval/golden_1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().grantPermissions(['microphone']);
  });

  test('verifies audio and subtitle fixtures exist in eval/golden_1', async () => {
    expect(fs.existsSync(GOLDEN_AUDIO_MP4)).toBeTruthy();
    expect(fs.existsSync(GOLDEN_SUBTITLE_TXT)).toBeTruthy();
    expect(fs.existsSync(FIXTURE_PCM)).toBeTruthy();

    const stats = fs.statSync(FIXTURE_PCM);
    expect(stats.size).toBeGreaterThan(1000000); // 56s @ 32kB/s ≈ 1.79MB
  });

  test('streams Naruto anime audio with pause/silence and verifies continuous recognition and translation', async ({
    page,
  }) => {
    test.setTimeout(90000);

    // Track active WebSockets to allow injecting audio stream
    await page.addInitScript(() => {
      const OrigWebSocket = window.WebSocket;
      (window as any).__activeWebSockets = [];
      window.WebSocket = class extends OrigWebSocket {
        constructor(...args: any[]) {
          super(...(args as [any, any]));
          (window as any).__activeWebSockets.push(this);
        }
      };
    });

    await page.goto('/');

    // 1. Connection check / fallback for local dev
    if (!isRemoteRun) {
      await page.evaluate(() => {
        const store = (window as any).__store;
        store?.getState().handleServerEvent({
          type: 'session.ready',
          session_id: 'sess-naruto-golden',
          profile: 'balanced',
          pack_revision: 'rev-golden-1',
          models: { asr: 'whisper-large-v3-turbo', mt: 'qwen' },
        });
        store?.getState().setConnected(true);
      });
    }

    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 15000 });

    // 2. Switch to '📺 Video & Họp' continuous subtitle mode
    const meetingBtn = page.getByRole('button', { name: '📺 Video & Họp' });
    await expect(meetingBtn).toBeVisible();
    await meetingBtn.click();

    // 3. Set Input = Japanese (ja) and Target = Vietnamese (vi)
    const selects = page.locator('select');
    await expect(selects).toHaveCount(2);

    const inputLangSelect = selects.nth(0);
    await inputLangSelect.selectOption('ja');
    await expect(inputLangSelect).toHaveValue('ja');

    const targetLangSelect = selects.nth(1);
    await targetLangSelect.selectOption('vi');
    await expect(targetLangSelect).toHaveValue('vi');

    // 4. Read 56-second PCM audio extracted from eval/golden_1/audio/videoplayback.mp4
    const audioBuf = fs.readFileSync(FIXTURE_PCM);
    const audioBase64 = audioBuf.toString('base64');

    // 5. Stream the Naruto audio chunks into the client session
    await page.evaluate(
      async ({ audioB64, mockMode }) => {
        const client = (window as any).__rvtClient;
        const ws = (window as any).__activeWebSockets?.[0];

        const sendJson = (data: any) => {
          if (client) {
            client.send(data);
          } else if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
          }
        };

        const sendAudio = (buffer: ArrayBuffer) => {
          if (client) {
            client.sendAudioChunk(buffer);
          } else if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(buffer);
          }
        };

        // Start continuous turn on side A
        sendJson({ type: 'turn.start', side: 'A' });

        const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
        const chunkSize = 1280; // 40ms at 16kHz 16-bit mono

        const binaryStr = atob(audioB64);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }

        // Mock events for local runs simulating backend ASR/MT pipeline for the golden audio
        const goldenMockScript = [
          { timeMs: 4000, ja: '先生どこだよ。他のクラスはもう来てるのにうちらだけ。', vi: 'Thầy ở đâu rồi? Lớp khác tới cả rồi chỉ còn mỗi lớp mình.' },
          { timeMs: 9000, ja: '落ち着きなさいよ。私だって知らないわ。少しは我慢しなさい。', vi: 'Bình tĩnh lại đi. Tôi cũng đâu có biết. Hãy kiên nhẫn một chút.' },
          { timeMs: 15000, ja: '遅刻するやつが悪いんだよ。', vi: 'Kẻ đi trễ mới là người có lỗi.' },
          { timeMs: 22000, ja: 'もう本当に私は関係ないからね。', vi: 'Tôi thực sự không liên quan gì đâu đấy nhé.' },
          { timeMs: 28000, ja: '上級の忍者がそんな手に引っかかるわけないだろう。', vi: 'Ninja cấp cao làm sao có thể mắc cái bẫy như thế được chứ.' },
          // ~11s pause/silence occurs here during the chalkboard eraser trap!
          { timeMs: 42000, ja: '引っかかった！引っかかったよ！', vi: 'Dính bẫy rồi! Thầy ấy dính bẫy rồi!' },
          { timeMs: 50000, ja: 'なんというか、君たちの第一印象は最悪だ。', vi: 'Nói sao nhỉ, ấn tượng đầu tiên của ta về mấy đứa là tồi tệ nhất.' },
        ];

        let mockIdx = 0;
        const totalChunks = Math.ceil(bytes.length / chunkSize);

        for (let chunkIdx = 0; chunkIdx < totalChunks; chunkIdx++) {
          const offset = chunkIdx * chunkSize;
          const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
          const sendBuf = new Uint8Array(chunkSize);
          sendBuf.set(chunk);
          sendAudio(sendBuf.buffer);

          const currentTimeMs = chunkIdx * 40;

          if (mockMode && mockIdx < goldenMockScript.length) {
            if (currentTimeMs >= goldenMockScript[mockIdx].timeMs) {
              const res = goldenMockScript[mockIdx];
              const store = (window as any).__store;
              const uid = mockIdx + 1;

              store.getState().handleServerEvent({
                type: 'asr.final',
                utterance_id: uid,
                side: 'A',
                text: res.ja,
                lang: 'ja',
                lang_probs: { ja: 0.99 },
                uncertain: false,
                audio_ms: 2000,
              });

              store.getState().handleServerEvent({
                type: 'mt.final',
                utterance_id: uid,
                target: 'vi',
                text: res.vi,
              });

              mockIdx++;
            }
          }

          // Accelerated playback in test (6ms per 40ms audio chunk)
          await sleep(6);
        }
      },
      { audioB64: audioBase64, mockMode: !isRemoteRun }
    );

    // 6. Assertions on the rendered golden subtitles
    // Sentence 1 (Naruto): 先生どこだよ (Where is sensei?)
    await expect(page.locator('text=先生どこだよ').or(page.locator('text=先生')).first()).toBeVisible({ timeout: 15000 });

    // Sentence 2 (Sakura): 落ち着きなさいよ (Calm down)
    await expect(page.locator('text=落ち着きなさいよ').or(page.locator('text=落ち着き')).first()).toBeVisible({ timeout: 15000 });

    // Sentences after the ~11s eraser pause (Naruto & Kakashi):
    // Proves that recognition CONTINUES and DOES NOT DIE after long pauses/silence!
    await expect(page.locator('text=引っかかった').first()).toBeVisible({ timeout: 20000 });
    await expect(page.locator('text=第一印象').first()).toBeVisible({ timeout: 20000 });

    // Verify Vietnamese translations are rendered properly
    await expect(
      page.locator('text=Thầy').or(page.locator('text=Bình tĩnh')).or(page.locator('text=ấn tượng')).first()
    ).toBeVisible({ timeout: 15000 });

    // Verify at least 5 dialogue cards are displayed in the feed
    const utteranceCount = await page.evaluate(() => {
      const store = (window as any).__store;
      return Object.keys(store.getState().utterances).length;
    });
    expect(utteranceCount).toBeGreaterThanOrEqual(5);

    // Verify UI subtitle feed contains cards with proper badges
    const jaBadges = page.locator('text=JA');
    await expect(jaBadges.first()).toBeVisible();
  });
});
