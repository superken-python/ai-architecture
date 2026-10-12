import { test, expect } from '@playwright/test';

test.describe('Realtime Voice Translate UI', () => {
  test('renders split screen layout with controls for both users', async ({ page }) => {
    await page.goto('/');

    // 1. Verify buttons for both sides
    const micA = page.getByRole('button', { name: /MIC A/i });
    const micB = page.getByRole('button', { name: /MIC B/i });

    await expect(micA).toBeVisible();
    await expect(micB).toBeVisible();

    // 2. Verify language selectors for both sides
    const selects = page.locator('select');
    await expect(selects).toHaveCount(2);

    // 3. Verify middle divider status indicator
    await expect(page.locator('text=Đang kết nối...').or(page.locator('text=WSS Sẵn sàng'))).toBeVisible();

    // 4. Test changing language on Side A
    const selectA = selects.nth(1);
    await selectA.selectOption('en');
    await expect(selectA).toHaveValue('en');

    // 5. Test font size scaling buttons
    const aPlusButtons = page.getByRole('button', { name: 'A+' });
    await expect(aPlusButtons).toHaveCount(2);
    await aPlusButtons.nth(1).click();

    // 6. Verify initial guide text
    await expect(page.locator('text=BẬT MIC').first()).toBeVisible();
  });

  test('handles live speech translation flow via state events', async ({ page }) => {
    await page.goto('/');

    // 1. Simulate session.ready event
    await page.evaluate(() => {
      const store = (window as any).__store;
      store.getState().handleServerEvent({
        type: 'session.ready',
        session_id: 'sess-test-playwright',
        profile: 'balanced',
        pack_revision: 'rev-test',
        models: { asr: 'whisper', mt: 'llama' },
      });
      store.getState().setConnected(true);
    });

    // Verify status indicator turns to "WSS Sẵn sàng"
    await expect(page.locator('text=WSS Sẵn sàng')).toBeVisible();

    // 2. Simulate ASR final on side A
    await page.evaluate(() => {
      const store = (window as any).__store;
      store.getState().handleServerEvent({
        type: 'asr.final',
        utterance_id: 42,
        side: 'A',
        text: 'Xin chào, hôm nay thế nào?',
        lang: 'vi',
        lang_probs: { vi: 0.98, en: 0.01, ja: 0.01 },
        uncertain: false,
        audio_ms: 2000,
      });
      store.getState().handleServerEvent({
        type: 'mt.final',
        utterance_id: 42,
        target: 'ja',
        text: 'こんにちは、今日はいかがですか？',
      });
      store.getState().handleServerEvent({
        type: 'mt.final',
        utterance_id: 42,
        target: 'en',
        text: 'Hello, how are you today?',
      });
    });

    // 3. Verify transcript on Side A (bottom)
    await expect(page.locator('text=Xin chào, hôm nay thế nào?').first()).toBeVisible();
    await expect(page.locator('text=VI 98%').first()).toBeVisible();

    // 4. Verify English translation on Side B (top)
    await expect(page.locator('text=Hello, how are you today?').first()).toBeVisible();

    // 5. Click on language badge to open override modal
    await page.locator('text=VI 98%').first().click();
    await expect(page.locator('text=Sửa ngôn ngữ câu')).toBeVisible();

    // 6. Cancel modal
    await page.getByRole('button', { name: 'Hủy' }).click();
    await expect(page.locator('text=Sửa ngôn ngữ câu')).not.toBeVisible();
  });

  test('switches to Video & Meeting continuous mode and toggles audio sources', async ({ page }) => {
    await page.goto('/');

    // 1. Switch to Video & Họp mode
    const meetingBtn = page.getByRole('button', { name: '📺 Video & Họp' });
    await expect(meetingBtn).toBeVisible();
    await meetingBtn.click();

    // 2. Verify continuous mode layout elements
    await expect(page.locator('text=Nói:').first()).toBeVisible();
    await expect(page.locator('text=Dịch sang:').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /BẬT DỊCH LIÊN TỤC/i })).toBeVisible();

    // 3. Test Audio Source toggle
    const tabSourceBtn = page.getByRole('button', { name: '💻 Tab/Video' });
    await expect(tabSourceBtn).toBeVisible();
    await tabSourceBtn.click();
    await expect(page.locator('text=Thu âm Tab/Video:')).toBeVisible();

    const micSourceBtn = page.getByRole('button', { name: '🎙️ Mic' });
    await micSourceBtn.click();
    await expect(page.locator('text=Trên iPhone/iPad (Safari), giữ trình duyệt mở và màn hình sáng')).toBeVisible();
  });
});

