import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isRemoteRun = Boolean(process.env.TARGET_URL);

test.describe('Anime Fast Continuous Speech Simulation (Doc 06)', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().grantPermissions(['microphone']);
  });

  test('simulates continuous fast anime dialogue (<250ms pause) and verifies responsive translation', async ({ page }) => {
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

    // 1. Wait for connection or fallback to simulated session for local dev
    if (!isRemoteRun) {
      await page.evaluate(() => {
        const store = (window as any).__store;
        store?.getState().handleServerEvent({
          type: 'session.ready',
          session_id: 'sess-anime-local',
          profile: 'balanced',
          pack_revision: 'rev-anime',
          models: { asr: 'whisper', mt: 'llama' },
        });
        store?.getState().setConnected(true);
      });
    }

    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 15000 });

    // 2. Switch to '📺 Video & Họp' continuous mode
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

    // 4. Load anime fast speech PCM fixtures (16kHz 16-bit mono)
    const fixturesDir = path.join(__dirname, '../fixtures/anime_fast');
    const clipFiles = [
      'a1_kaizoku.pcm',   // 海賊王に俺はなる！ (~0.85s)
      'a2_ikuzo.pcm',     // 行くぞ野郎ども、次の島へ出発だ！ (~1.43s)
      'a3_zettai.pcm',    // 絶対に諦めるな、俺たちが勝つ！ (~1.33s)
      'a4_nakama.pcm',    // 仲間には指一本触れさせない！ (~1.18s)
      'a5_arigatou.pcm',  // みんな、本当にありがとう！ (~0.96s)
    ];

    const clipsBase64 = clipFiles.map((file) => {
      const buf = fs.readFileSync(path.join(fixturesDir, file));
      return buf.toString('base64');
    });

    // 5. Stream anime audio with rapid dialogue (<250ms pauses)
    await page.evaluate(
      async ({ clips, mockMode }) => {
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

        // Start turn on side A with target: ['vi']
        sendJson({ type: 'turn.start', side: 'A' });

        const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
        const chunkSize = 1280; // 40ms at 16kHz
        const silenceChunk = new Uint8Array(chunkSize);

        const mockResponses = [
          { text: '海賊王に俺はなる！', vi: 'Tôi sẽ trở thành vua hải tặc!' },
          { text: '行くぞ野郎ども、次の島へ出発だ！', vi: 'Đi thôi các anh em, xuất phát đến hòn đảo tiếp theo!' },
          { text: '絶対に諦めるな、俺たちが勝つ！', vi: 'Tuyệt đối không bỏ cuộc, chúng ta sẽ thắng!' },
          { text: '仲間には指一本触れさせない！', vi: 'Không ai được đụng đến đồng đội của ta!' },
          { text: 'みんな、本当にありがとう！', vi: 'Mọi người, thực sự cảm ơn rất nhiều!' },
        ];

        for (let clipIdx = 0; clipIdx < clips.length; clipIdx++) {
          const b64 = clips[clipIdx];
          const binaryStr = atob(b64);
          const bytes = new Uint8Array(binaryStr.length);
          for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
          }

          // Stream audio in 40ms chunks
          for (let offset = 0; offset < bytes.length; offset += chunkSize) {
            const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
            const sendBuf = new Uint8Array(chunkSize);
            sendBuf.set(chunk);
            sendAudio(sendBuf.buffer);
            await sleep(30);
          }

          // In local mock mode, simulate server segmenter/ASR/MT response
          if (mockMode) {
            const store = (window as any).__store;
            const res = mockResponses[clipIdx];
            store.getState().handleServerEvent({
              type: 'asr.final',
              utterance_id: clipIdx + 1,
              side: 'A',
              text: res.text,
              lang: 'ja',
              lang_probs: { ja: 0.99 },
              uncertain: false,
              audio_ms: 1000,
            });
            store.getState().handleServerEvent({
              type: 'mt.final',
              utterance_id: clipIdx + 1,
              target: 'vi',
              text: res.vi,
            });
          }

          // Anime dialogue has sub-250ms gap (~120ms = 3 chunks of 40ms)
          // With doc 06 optimizations (4s/6s lowest-silence cut & early-commit),
          // the system cuts cleanly and translates without hanging for 10s!
          for (let s = 0; s < 3; s++) {
            sendAudio(silenceChunk.buffer);
            await sleep(30);
          }
        }

        // Trailing silence at the end of the anime scene
        for (let s = 0; s < 10; s++) {
          sendAudio(silenceChunk.buffer);
          await sleep(30);
        }
      },
      { clips: clipsBase64, mockMode: !isRemoteRun }
    );

    // 6. Assertions:
    // With 4s/6s max limits and early-commit, dialogue is split into sentences and translated
    const storeUtterancesCount = await page.evaluate(async () => {
      const store = (window as any).__store;
      for (let i = 0; i < 30; i++) {
        const count = Object.keys(store.getState().utterances).length;
        if (count >= 2) break;
        await new Promise((r) => setTimeout(r, 500));
      }
      return Object.keys(store.getState().utterances).length;
    });

    expect(storeUtterancesCount).toBeGreaterThanOrEqual(2);

    // Check that Vietnamese translations appear in the feed
    await expect(page.locator('text=vua hải tặc').or(page.locator('text=hải tặc')).or(page.locator('text=hòn đảo')).first()).toBeVisible({ timeout: 15000 });

    // Verify UI has no lingering unprocessed state
    await expect(page.locator('text=● đang xử lý...')).not.toBeVisible({ timeout: 10000 });
  });

  test('stress tests UI performance with rapid anime subtitle updates (rendering memoization)', async ({ page }) => {
    await page.goto('/');

    // Switch to Meeting mode
    const meetingBtn = page.getByRole('button', { name: '📺 Video & Họp' });
    await expect(meetingBtn).toBeVisible();
    await meetingBtn.click();

    // Select Vietnamese as target language
    const selects = page.locator('select');
    await selects.nth(1).selectOption('vi');

    // Inject 50 rapid utterances to verify memoized MeetingUtteranceCard and DOM slice
    const renderStartTime = Date.now();
    await page.evaluate(() => {
      const store = (window as any).__store;
      store.getState().setSideConfig('B', 'vi');
      for (let i = 1; i <= 50; i++) {
        store.getState().handleServerEvent({
          type: 'asr.final',
          utterance_id: i,
          side: 'A',
          text: `アニメのセリフ #${i} 行くぞ！`,
          lang: 'ja',
          lang_probs: { ja: 0.99 },
          uncertain: false,
          audio_ms: 1200,
        });
        store.getState().handleServerEvent({
          type: 'mt.final',
          utterance_id: i,
          target: 'vi',
          text: `Lời thoại anime #${i} tiến lên nào!`,
        });
      }
    });

    // Verify last utterance rendered immediately without browser lag
    await expect(page.locator('text=Lời thoại anime #50').first()).toBeVisible({ timeout: 5000 });
    const durationMs = Date.now() - renderStartTime;
    console.log(`Rendered 50 anime subtitles in ${durationMs}ms`);
    expect(durationMs).toBeLessThan(3000);
  });
});
