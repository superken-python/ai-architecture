import { test, expect, Page } from '@playwright/test';

// Kết nối và thu âm với server AI thật (docs 08 §4.1, §4.3). Cần server chạy riêng, ví dụ engine giả:
//   cd ai && RVT_USE_FAKE=1 PYTHONPATH=src uv run uvicorn rvt_ai.main:app --port 8000
//   cd web && RVT_AI_URL=http://localhost:8000 npx playwright test tests/e2e/connection.spec.ts
const aiUrl = process.env.RVT_AI_URL;
test.skip(!aiUrl, 'cần RVT_AI_URL trỏ tới server AI đang chạy');

async function waitConnected(page: Page) {
  await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 10_000 });
}

test('two tabs of the same browser keep their own connection', async ({ context }) => {
  // 873d676 lưu client_id trong localStorage: hai tab dùng chung mã nên server đá tab cũ mỗi lần tab kia nối lại
  const a = await context.newPage();
  const b = await context.newPage();
  await a.goto('/');
  await b.goto('/');
  await waitConnected(a);
  await waitConnected(b);

  const idA = await a.evaluate(() => (window as any).__rvtClient.clientId);
  const idB = await b.evaluate(() => (window as any).__rvtClient.clientId);
  expect(idA).not.toBe(idB);

  // Ghi lại mọi lần mất kết nối trong 8 s (bản cũ: cứ 2 s một lần)
  for (const p of [a, b]) {
    await p.evaluate(() => {
      (window as any).__drops = 0;
      (window as any).__store.subscribe((s: any, prev: any) => {
        if (prev.connected && !s.connected) (window as any).__drops += 1;
      });
    });
  }
  await a.waitForTimeout(8000);
  expect(await a.evaluate(() => (window as any).__drops)).toBe(0);
  expect(await b.evaluate(() => (window as any).__drops)).toBe(0);
});

test('a connection replaced by the same page id stops reconnecting and says why', async ({ page }) => {
  await page.goto('/');
  await waitConnected(page);
  const clientId = await page.evaluate(() => (window as any).__rvtClient.clientId);

  // Một kết nối khác cùng client_id: server đóng kết nối của trang bằng 4409
  const wsUrl = aiUrl!.replace(/^http/, 'ws') + `/ws?client_id=${encodeURIComponent(clientId)}`;
  const intruder = new WebSocket(wsUrl, 'rvt.v1');
  await new Promise((resolve, reject) => {
    intruder.onopen = resolve;
    intruder.onerror = reject;
  });

  await expect(page.locator('text=Phiên này đã được mở lại ở một kết nối khác')).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(4000); // bản cũ nối lại sau 2 s
  await expect(page.locator('text=Đang kết nối...')).toBeVisible();
  intruder.close();
});

test('a dead microphone track shows the warning, and one tap captures again', async ({ page }) => {
  await page.goto('/');
  await waitConnected(page);
  await page.getByRole('button', { name: /BẬT MIC A/ }).click();
  await expect.poll(() => page.evaluate(() => (window as any).__rvtClient.getDebugStats().chunksSent)).toBeGreaterThan(5);
  await expect(page.locator('text=Chạm để tiếp tục nghe')).toHaveCount(0);

  // Track mic chết (stop() không phát sự kiện "ended"): phép kiểm mỗi giây phải tự phát hiện
  await page.evaluate(() => (window as any).__rvtClient.mediaStream.getAudioTracks()[0].stop());
  await expect(page.locator('text=Micro đã bị tắt. Chạm để bật lại.')).toBeVisible({ timeout: 3000 });

  const before = await page.evaluate(() => (window as any).__rvtClient.getDebugStats().chunksSent);
  await page.getByRole('button', { name: 'Chạm để tiếp tục nghe' }).click();
  await expect(page.locator('text=Micro đã bị tắt. Chạm để bật lại.')).toHaveCount(0, { timeout: 3000 });
  await expect
    .poll(() => page.evaluate(() => (window as any).__rvtClient.getDebugStats().chunksSent))
    .toBeGreaterThan(before + 5);
  expect(await page.evaluate(() => (window as any).__rvtClient.getDebugStats().trackReadyState)).toBe('live');
});
