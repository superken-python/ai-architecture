import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Continuous Japanese Video Streaming Test', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().grantPermissions(['microphone']);
  });

  test('streams continuous Japanese video speech (> 3 sentences) and verifies translation flow without freeze', async ({ page }) => {
    // Increase test timeout for multi-sentence streaming
    test.setTimeout(60000);

    // Intercept WebSocket creation so we can stream raw PCM chunks directly through the page's active connection
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

    // 1. Wait for connection
    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 15000 });

    // 2. Switch to '📺 Video & Họp' continuous mode
    const meetingBtn = page.getByRole('button', { name: '📺 Video & Họp' });
    await expect(meetingBtn).toBeVisible();
    await meetingBtn.click();

    // 3. Select Japanese for input and Vietnamese for translation
    const selects = page.locator('select');
    await expect(selects).toHaveCount(2);

    const inputLangSelect = selects.nth(0);
    await inputLangSelect.selectOption('ja');
    await expect(inputLangSelect).toHaveValue('ja');

    const targetLangSelect = selects.nth(1);
    await targetLangSelect.selectOption('vi');
    await expect(targetLangSelect).toHaveValue('vi');

    // 4. Load real 16kHz mono PCM fixtures
    const fixturesDir = path.join(__dirname, '../fixtures/ja_video');
    const clipFiles = ['s1_stitch.pcm', 's2_owari.pcm', 's3_arigatou.pcm', 's4_tsugi.pcm'];
    const clipsBase64 = clipFiles.map((file) => {
      const buf = fs.readFileSync(path.join(fixturesDir, file));
      return buf.toString('base64');
    });

    // 5. Start listening turn on Side A and stream the clips sequentially
    await page.evaluate(async (clips) => {
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

      // Start turn on side A
      sendJson({ type: 'turn.start', side: 'A' });

      const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
      const chunkSize = 1280; // 40ms at 16kHz 16-bit mono
      const silenceChunk = new Uint8Array(chunkSize);

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
          await sleep(40);
        }

        // Send 1.2s silence between sentences so VAD chốt câu
        for (let s = 0; s < 30; s++) {
          sendAudio(silenceChunk.buffer);
          await sleep(40);
        }

        // Small pause between sentences
        await sleep(600);
      }
    }, clipsBase64);

    // 6. Assertions on the rendered cards
    // Verify Sentence 1 rendered
    await expect(page.locator('text=スティッチ').or(page.locator('text=スチッチ'))).toBeVisible({ timeout: 15000 });

    // Verify Sentence 2 rendered
    await expect(page.locator('text=おわり').or(page.locator('text=終わり'))).toBeVisible({ timeout: 15000 });

    // Verify Sentence 3 (ご視聴ありがとうございました) is present AND finalized (translated into Vietnamese)
    const s3 = page.locator('text=ご視聴ありがとうございました');
    await expect(s3).toBeVisible({ timeout: 15000 });

    // Sentence 3 MUST have Vietnamese translation and NOT be stuck in "... đang dịch"
    await expect(page.locator('text=Cảm ơn quý khán giả').or(page.locator('text=Cảm ơn các bạn'))).toBeVisible({ timeout: 20000 });

    // Verify Sentence 4 (次の動画でお会いしましょう) appears (proves it didn't stop at sentence 3!)
    await expect(page.locator('text=次の動画で')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('text=video tiếp theo').or(page.locator('text=video sau'))).toBeVisible({ timeout: 20000 });

    // Verify there are at least 4 utterance cards rendered
    const storeUtterancesCount = await page.evaluate(() => {
      const store = (window as any).__store;
      return Object.keys(store.getState().utterances).length;
    });
    expect(storeUtterancesCount).toBeGreaterThanOrEqual(4);

    // Verify NONE of the sentences are stuck in "● đang xử lý..."
    await expect(page.locator('text=● đang xử lý...')).not.toBeVisible({ timeout: 10000 });
  });
});
