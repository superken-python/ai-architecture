/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Tuỳ chọn: RVT_AI_URL=http://localhost:8000 npm run dev — chuyển /ws và /api tới server AI chạy ở máy, như nginx làm
// khi triển khai. Không đặt biến này thì dev server giữ nguyên như cũ.
const aiUrl = process.env.RVT_AI_URL;

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: aiUrl
      ? {
          '/ws': { target: aiUrl.replace(/^http/, 'ws'), ws: true },
          '/api': { target: aiUrl },
        }
      : undefined,
  },
  test: {
    exclude: ['**/node_modules/**', '**/dist/**', 'tests/e2e/**'],
  },
});
