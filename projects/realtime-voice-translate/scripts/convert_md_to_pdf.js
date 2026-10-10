const fs = require('fs');
const path = require('path');
const { chromium } = require('../web/node_modules/@playwright/test');
const { marked } = require('/Users/duc.nguyen/.nvm/versions/node/v22.23.3/lib/node_modules/md-to-pdf/node_modules/marked');

async function convertMdToPdf() {
  const inputFile = path.resolve(__dirname, '../docs/03-technical-details-design.md');
  const outputFile = path.resolve(__dirname, '../docs/03-technical-details-design.pdf');

  console.log(`[1/5] Reading markdown file: ${inputFile}`);
  const mdContent = fs.readFileSync(inputFile, 'utf-8');

  // Extract all mermaid blocks and replace with placeholders
  const mermaidBlocks = [];
  const processedMd = mdContent.replace(/```mermaid\n([\s\S]*?)```/g, (match, code) => {
    const id = mermaidBlocks.length;
    mermaidBlocks.push(code.trim());
    return `<div class="mermaid-slot" id="slot-${id}" data-diagram-id="${id}"></div>`;
  });

  console.log(`[2/5] Extracted ${mermaidBlocks.length} Mermaid diagrams. Parsing markdown to HTML...`);
  marked.setOptions({
    gfm: true,
    breaks: false
  });

  const bodyHtml = marked.parse(processedMd);

  const fullHtml = `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>03 · Technical Details Design — Realtime Voice Translate</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-light.min.css">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
  <style>
    @page {
      size: A4;
      margin: 18mm 14mm 18mm 14mm;
    }
    
    * {
      box-sizing: border-box;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background-color: #ffffff;
      margin: 0;
      padding: 0;
    }
    
    .markdown-body {
      max-width: 100%;
      margin: 0 auto;
      padding: 0;
      font-size: 13px;
      color: #1e293b;
    }
    
    /* Document Title & Meta Header */
    h1 {
      border-bottom: 3px solid #2563eb;
      padding-bottom: 12px;
      color: #1e3a8a;
      font-size: 23px;
      font-weight: 700;
      margin-top: 5px;
      margin-bottom: 16px;
      page-break-after: avoid;
    }
    
    h2 {
      border-bottom: 1.5px solid #cbd5e1;
      padding-bottom: 8px;
      color: #0f172a;
      font-size: 17px;
      font-weight: 600;
      margin-top: 32px;
      margin-bottom: 14px;
      page-break-after: avoid;
    }
    
    h3 {
      color: #334155;
      font-size: 14.5px;
      font-weight: 600;
      margin-top: 20px;
      margin-bottom: 10px;
      page-break-after: avoid;
    }
    
    p {
      margin-top: 0;
      margin-bottom: 12px;
      line-height: 1.65;
    }
    
    ul, ol {
      padding-left: 24px;
      margin-bottom: 14px;
    }
    
    li {
      margin-bottom: 6px;
      line-height: 1.6;
    }
    
    /* Tables */
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      page-break-inside: avoid;
      font-size: 12px;
    }
    
    th {
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
      border: 1px solid #cbd5e1;
      padding: 8px 12px;
      text-align: left;
    }
    
    td {
      border: 1px solid #e2e8f0;
      padding: 8px 12px;
      vertical-align: top;
    }
    
    tr:nth-child(even) td {
      background-color: #f8fafc;
    }
    
    /* Code Blocks */
    pre {
      background-color: #0f172a !important;
      color: #f8fafc !important;
      border-radius: 8px;
      padding: 14px;
      font-size: 11.5px;
      line-height: 1.5;
      overflow-x: auto;
      margin: 16px 0;
      page-break-inside: avoid;
    }
    
    pre code {
      background-color: transparent !important;
      color: #f8fafc !important;
      font-family: "JetBrains Mono", "SFMono-Regular", Consolas, Menlo, monospace;
      padding: 0;
    }
    
    code:not(pre code) {
      background-color: #e2e8f0;
      color: #0f172a;
      font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
      font-size: 11.5px;
      padding: 2px 6px;
      border-radius: 4px;
    }
    
    /* Mermaid Diagram Container */
    .mermaid-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      margin: 22px 0;
      padding: 16px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      page-break-inside: avoid;
    }
    
    .mermaid-card svg {
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto;
    }
    
    .diagram-caption {
      margin-top: 10px;
      font-size: 11px;
      color: #64748b;
      font-style: italic;
      text-align: center;
    }
    
    /* Alerts and Blockquotes */
    blockquote {
      border-left: 4px solid #2563eb;
      background-color: #eff6ff;
      color: #1e40af;
      padding: 8px 16px;
      margin: 16px 0;
      border-radius: 0 6px 6px 0;
      page-break-inside: avoid;
    }
    
    hr {
      margin: 28px 0;
      border: 0;
      border-top: 1px solid #e2e8f0;
    }
    
    /* Explicit Section Page Break Control */
    .page-break-before {
      page-break-before: always;
    }
  </style>
</head>
<body class="markdown-body">
  ${bodyHtml}
  
  <script>
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      themeVariables: {
        primaryColor: '#e0f2fe',
        primaryTextColor: '#0369a1',
        primaryBorderColor: '#0284c7',
        lineColor: '#475569',
        secondaryColor: '#f1f5f9',
        tertiaryColor: '#f8fafc'
      }
    });
  </script>
</body>
</html>`;

  console.log(`[3/5] Launching Playwright Chromium...`);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.setContent(fullHtml, { waitUntil: 'networkidle' });

  console.log(`[4/5] Rendering all ${mermaidBlocks.length} Mermaid diagrams directly via SVG engine...`);
  const captions = [
    "Sơ đồ 1: Kiến trúc tổng thể hệ thống, phân vùng mạng và các khối container",
    "Sơ đồ 2: Trình tự xử lý âm thanh thời gian thực (Audio Streaming, VAD, ASR và Song ngữ MT)",
    "Sơ đồ 3: Máy trạng thái VAD & Bộ đệm Audio Segmenter (Preroll, Partial, Final)",
    "Sơ đồ 4: Cây quyết định nhận diện ngôn ngữ (LID) & Thuật toán cập nhật Prior EMA",
    "Sơ đồ 5: Trình tự bắt tay WebSocket, xác thực token và truyền tải khung nhị phân",
    "Sơ đồ 6: Bố cục giao diện Split-Screen đối xứng 180° trên thiết bị di động"
  ];

  for (let i = 0; i < mermaidBlocks.length; i++) {
    const code = mermaidBlocks[i];
    const caption = captions[i] || `Sơ đồ ${i + 1}`;

    const renderResult = await page.evaluate(async ({ id, code, caption }) => {
      try {
        const { svg } = await mermaid.render(`rendered-mermaid-${id}`, code);
        const slot = document.getElementById(`slot-${id}`);
        if (slot) {
          slot.innerHTML = `
            <div class="mermaid-card">
              ${svg}
              <div class="diagram-caption">${caption}</div>
            </div>
          `;
          return { success: true };
        }
        return { success: false, error: 'Slot not found' };
      } catch (err) {
        return { success: false, error: err.message || String(err) };
      }
    }, { id: i, code, caption });

    if (!renderResult.success) {
      console.error(`❌ Failed to render diagram ${i + 1}: ${renderResult.error}`);
    } else {
      console.log(`✓ Diagram ${i + 1} rendered successfully.`);
    }
  }

  // Ensure large diagrams have appropriate sizing and spacing
  await page.waitForTimeout(1000);

  console.log(`[5/5] Generating PDF document: ${outputFile}...`);
  await page.pdf({
    path: outputFile,
    format: 'A4',
    printBackground: true,
    margin: {
      top: '18mm',
      bottom: '18mm',
      left: '14mm',
      right: '14mm'
    },
    displayHeaderFooter: true,
    headerTemplate: `
      <div style="font-family: -apple-system, sans-serif; font-size: 8pt; color: #64748b; width: 100%; display: flex; justify-content: space-between; padding: 0 14mm;">
        <span>Realtime Voice Translate (JA ⇄ EN ⇄ VI) · Technical Details Design</span>
        <span>Motive IDP Architecture</span>
      </div>
    `,
    footerTemplate: `
      <div style="font-family: -apple-system, sans-serif; font-size: 8pt; color: #64748b; width: 100%; display: flex; justify-content: space-between; padding: 0 14mm;">
        <span>Phục vụ máy chủ GPU NVIDIA ≤ 8 GB VRAM</span>
        <span>Trang <span class="pageNumber"></span> / <span class="totalPages"></span></span>
      </div>
    `
  });

  await browser.close();

  const stats = fs.statSync(outputFile);
  console.log(`\n🎉 PDF GENERATION COMPLETE!`);
  console.log(`📍 Output file: ${outputFile}`);
  console.log(`📊 Size: ${(stats.size / 1024).toFixed(1)} KB`);
}

convertMdToPdf().catch(err => {
  console.error(`Error:`, err);
  process.exit(1);
});
