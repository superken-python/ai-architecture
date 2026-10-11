import { defineConfig, devices } from '@playwright/test';

const targetUrl = process.env.TARGET_URL;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  webServer: targetUrl
    ? undefined
    : {
        command: 'npm run dev',
        port: 3000,
        reuseExistingServer: true,
      },
  use: {
    baseURL: targetUrl || 'http://localhost:3000',
    ignoreHTTPSErrors: true,
    permissions: ['microphone'],
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: [
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
          ],
        },
      },
    },
  ],
});
