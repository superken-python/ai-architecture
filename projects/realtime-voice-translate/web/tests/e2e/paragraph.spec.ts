import { test, expect } from '@playwright/test';

// Video & Họp, dịch theo đoạn (docs 10 §13.9): các câu của một đoạn hiện trong một thẻ, bản dịch của cả đoạn thay
// bản cũ khi lần dịch mới xong. Sự kiện server được đưa thẳng vào store, không cần backend.
test.use({ viewport: { width: 390, height: 844 } });

test('meeting mode groups sentences into one paragraph card with one translation', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Video & Họp/ }).click();
  await page.locator('select').nth(1).selectOption('vi'); // Dịch sang: Tiếng Việt
  await expect(page.locator('select').nth(2)).toHaveValue('paragraph'); // "Dịch theo: Đoạn" mặc định

  await page.evaluate(() => {
    const store = (window as any).__store;
    const send = (e: any) => store.getState().handleServerEvent(e);
    const final = (id: number, text: string, pid: number) =>
      send({ type: 'asr.final', utterance_id: id, side: 'A', text, lang: 'ja', lang_probs: { ja: 0.98 }, uncertain: false, audio_ms: 4000, paragraph_id: pid });
    send({ type: 'session.ready', session_id: 's', profile: 'api-mt', pack_revision: 'r', models: { asr: 'faster-whisper', mt: 'api' } });
    store.getState().setConnected(true);

    final(1, 'AIモデルはフリーで使えるみたいですので、あと、あの、3。', 1);
    send({ type: 'mt.final', utterance_id: 1, target: 'vi', text: 'Vì có vẻ như mô hình AI có thể dùng miễn phí, và thêm nữa, ờ, 3.', revision: 1 });

    final(2, 'あと、これ、あ、AIを入れておくと、あの、人の、え、なんか就労の作業が', 2);
    send({ type: 'mt.final', utterance_id: 2, target: 'vi', text: 'Và nữa, nếu để AI vào trước thì công việc của người lao động', revision: 1 });
    final(3, 'なんか減らすんじゃないかなということです。', 2);
    send({ type: 'mt.delta', utterance_id: 2, target: 'vi', delta: 'Và nữa, nếu ', revision: 2 });
  });

  const cards = page.locator('text=JA 98%');
  await expect(cards).toHaveCount(2);
  // Câu bị VAD cắt đôi nằm chung một thẻ; bản dịch cũ vẫn hiện trong lúc dịch lại cả đoạn
  await expect(page.locator('text=人の、え、なんか就労の作業がなんか減らすんじゃないかなということです。')).toBeVisible();
  await expect(page.locator('text=↻ đang dịch lại cả đoạn')).toBeVisible();
  await expect(page.locator('text=Và nữa, nếu để AI vào trước thì công việc của người lao động')).toBeVisible();

  await page.evaluate(() => {
    (window as any).__store.getState().handleServerEvent({
      type: 'mt.final', utterance_id: 2, target: 'vi', revision: 2,
      text: 'Và nữa, nếu để AI vào trước thì có lẽ sẽ giảm bớt được công việc của người lao động.',
    });
    (window as any).__store.getState().handleServerEvent({
      type: 'asr.partial', utterance_id: 4, side: 'A', text: '例えば、えっと、AIで意味合いが', lang: 'ja', paragraph_id: 2,
    });
  });
  await expect(page.locator('text=có lẽ sẽ giảm bớt được công việc của người lao động.')).toBeVisible();
  await expect(page.locator('text=↻ đang dịch lại cả đoạn')).toHaveCount(0);
  await expect(page.locator('text=ということです。例えば、えっと、AIで意味合いが')).toBeVisible();
  await expect(cards).toHaveCount(2);

  await page.screenshot({ path: 'test-results/paragraph-mode.png' });

  // Chuyển sang "Câu": mỗi câu một thẻ như trước
  await page.locator('select').nth(2).selectOption('segment');
  await expect(page.locator('text=JA 98%')).toHaveCount(3);
});
