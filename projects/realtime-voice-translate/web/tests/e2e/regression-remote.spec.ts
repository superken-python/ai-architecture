import { test, expect } from '@playwright/test';

test.describe('Realtime Voice Translate - Remote Regression Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Grant microphone permissions
    await page.context().grantPermissions(['microphone']);
  });

  test('loads application cleanly without blank screen and connects to live WebSocket', async ({ page }) => {
    await page.goto('/');

    // 1. Ensure the root DOM is mounted and visible (no black screen / blank page)
    const root = page.locator('#root');
    await expect(root).toBeVisible();
    await expect(page.locator('body')).not.toBeEmpty();

    // 2. Verify both user viewports are rendered
    const micA = page.getByRole('button', { name: /BẬT MIC A|DỪNG A/i });
    const micB = page.getByRole('button', { name: /BẬT MIC B|DỪNG B/i });
    await expect(micA).toBeVisible({ timeout: 10000 });
    await expect(micB).toBeVisible({ timeout: 10000 });

    // 3. Verify WebSocket status indicator transitions to "WSS Sẵn sàng"
    const statusIndicator = page.locator('text=WSS Sẵn sàng');
    await expect(statusIndicator).toBeVisible({ timeout: 15000 });
  });

  test('verifies language selectors and font scale controls', async ({ page }) => {
    await page.goto('/');

    // Verify language selects exist for both Side A and Side B
    const selects = page.locator('select');
    await expect(selects).toHaveCount(2);

    // Switch language on Side A to English
    const selectA = selects.nth(1);
    await selectA.selectOption('en');
    await expect(selectA).toHaveValue('en');

    // Switch language on Side B to Japanese
    const selectB = selects.nth(0);
    await selectB.selectOption('ja');
    await expect(selectB).toHaveValue('ja');

    // Test Font scaling buttons
    const aPlusButtons = page.getByRole('button', { name: 'A+' });
    await expect(aPlusButtons).toHaveCount(2);
    await aPlusButtons.nth(1).click();

    const aMinusButtons = page.getByRole('button', { name: 'A-' });
    await expect(aMinusButtons).toHaveCount(2);
    await aMinusButtons.nth(1).click();
  });

  test('tests microphone toggle lifecycle (start listening -> stop listening -> button resets)', async ({ page }) => {
    page.on('console', msg => console.log('BROWSER LOG:', msg.type(), msg.text()));
    await page.goto('/');

    // Wait for connection ready
    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 15000 });

    // 1. Initial state: Button says "BẬT MIC A"
    const micA = page.getByRole('button', { name: /BẬT MIC A/i });
    await expect(micA).toBeVisible();

    // 2. Click to start listening
    await micA.click();

    // 3. Button should switch to stop mode: "⏹ DỪNG MIC A" or "🎙 ĐANG NÓI..."
    const stopA = page.getByRole('button', { name: /DỪNG.*A|ĐANG NÓI/i });
    await expect(stopA).toBeVisible({ timeout: 5000 });

    // 4. Click to stop listening
    await stopA.click();

    // 5. Button MUST return to "BẬT MIC A" (not get stuck in active/red state)
    await expect(page.getByRole('button', { name: /BẬT MIC A/i })).toBeVisible({ timeout: 5000 });
  });

  test('validates speech recognition and translation UI rendering without errors or hallucinations', async ({ page }) => {
    await page.goto('/');

    // Wait for connection ready
    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible({ timeout: 15000 });

    // Inject realistic speech and translation events into client state
    await page.evaluate(() => {
      const store = (window as any).__store;
      if (!store) return;

      // 1. Simulate spoken Vietnamese utterance on Side A
      store.getState().handleServerEvent({
        type: 'asr.final',
        utterance_id: 101,
        side: 'A',
        text: 'Xin chào bạn, tôi cần hỗ trợ dịch thuật trực tiếp.',
        lang: 'vi',
        lang_probs: { vi: 0.99, en: 0.01, ja: 0.0 },
        uncertain: false,
        audio_ms: 2500,
      });

      // 2. Stream Japanese translation delta + final
      store.getState().handleServerEvent({
        type: 'mt.delta',
        utterance_id: 101,
        target: 'ja',
        delta: 'こんにちは、',
      });
      store.getState().handleServerEvent({
        type: 'mt.delta',
        utterance_id: 101,
        target: 'ja',
        delta: 'リアルタイム通訳のサポートが必要です。',
      });
      store.getState().handleServerEvent({
        type: 'mt.final',
        utterance_id: 101,
        target: 'ja',
        text: 'こんにちは、リアルタイム通訳のサポートが必要です。',
      });

      // 3. English translation
      store.getState().handleServerEvent({
        type: 'mt.final',
        utterance_id: 101,
        target: 'en',
        text: 'Hello, I need direct interpretation support.',
      });
    });

    // Verify transcript appears on Side A (Bottom)
    await expect(page.locator('text=Xin chào bạn, tôi cần hỗ trợ dịch thuật trực tiếp.').first()).toBeVisible();

    // Verify translation appears on Side B (Top)
    await expect(page.locator('text=こんにちは、リアルタイム通訳のサポートが必要です。').first()).toBeVisible();

    // Verify NO unwanted YouTube subtitle credit hallucinations
    await expect(page.locator('text=ghiền mì gõ')).not.toBeVisible();
    await expect(page.locator('text=subscribe')).not.toBeVisible();
    await expect(page.locator('text=đăng ký kênh')).not.toBeVisible();
  });

  test('verifies responsive layout on mobile viewport (iPhone 15)', async ({ page }) => {
    // Set viewport to mobile standard 393 x 852
    await page.setViewportSize({ width: 393, height: 852 });
    await page.goto('/');

    const root = page.locator('#root');
    await expect(root).toBeVisible();

    // Verify both top and bottom mic buttons are visible and not clipped
    await expect(page.getByRole('button', { name: /BẬT MIC B/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /BẬT MIC A/i })).toBeVisible();

    // Verify middle divider
    await expect(page.locator('text=WSS Sẵn sàng').or(page.locator('text=Đang kết nối...'))).toBeVisible();
  });
});
