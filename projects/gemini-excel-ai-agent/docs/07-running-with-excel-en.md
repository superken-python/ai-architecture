# 07 · End-to-End Implementation & Excel Execution Guide (English)

This document provides a comprehensive, step-by-step technical guide to running the **Excel Enterprise AI Agent Copilot** (powered by Agno SDK & Azure OpenAI `gpt-5-mini`) and sideloading the Office Web Add-in into Microsoft Excel (Windows, macOS, and Excel Online).

---

## 1. Prerequisites

- **Python:** Version 3.11 or 3.12 (managed via `poetry`).
- **Microsoft Excel:** Any of the following:
  - Excel on the Web (Microsoft 365 in Chrome/Edge - free or business account).
  - Excel Desktop for Windows (Microsoft 365, Office 2019/2021).
  - Excel Desktop for macOS (Microsoft 365).
- **Web Browser:** Google Chrome or Microsoft Edge.

---

## 2. Step 1: Install Backend Dependencies

Navigate to the project root directory:

```bash
cd projects/gemini-excel-ai-agent

# Install dependencies using Poetry
poetry install
```

---

## 3. Step 2: Environment Configuration (.env)

Create your local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Configure your Azure OpenAI credentials in `.env` (or leave as default to test with the smart fallback simulator):

```dotenv
AZURE_OPENAI_API_KEY=your-actual-azure-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_MODEL=gpt-5-mini

HOST=0.0.0.0
PORT=8000
DEBUG=true
```

> [!NOTE]
> **Built-in Fallback Strategy:** If no valid Azure API key is configured yet, the backend automatically engages its intelligent Mock Strategy, allowing you to test 100% of the UI, `/search` command, Diff previews, and Excel row insertions immediately!

---

## 4. Step 3: Launch the Backend Service & Add-in Server

Start the FastAPI application:

```bash
poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000
```
*(Or simply run: `make dev`)*

Verify service endpoints:
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Taskpane UI:** [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html)

---

## 5. Step 4: Standalone Browser Testing (Simulator Mode)

You can verify the entire workflow in your browser before opening Excel:
1. Open [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html) in your browser.
2. Click any suggestion pill (e.g. `🔍 /search Áo thun`) or type `/search Vải` into the chat input.
3. The chatbot returns relevant catalog items from the Mock Database.
4. Click `+ Chèn vào Excel` (Insert into Excel).
5. The **Preview Diff Modal** opens, showing the exact columns to be updated.
6. Click `Xác nhận ghi (Apply)`: the row is instantly inserted into the simulated worksheet on the **"Bảng tính mẫu"** (Sample Sheet) tab.

---

## 6. Step 5: Sideloading into Microsoft Excel

### Method A: Excel on the Web (Fastest & Recommended)
1. Go to [https://excel.new](https://excel.new) or [https://office.com](https://office.com) and open a new blank workbook.
2. In the top ribbon, select the **Insert** tab.
3. Click **Office Add-ins** (or **Add-ins**).
4. Select the **Upload My Add-in** tab in the popup dialog.
5. Click **Browse** and select the manifest file:
   `projects/gemini-excel-ai-agent/addin/manifest.xml`.
6. Click **Upload**.
7. The **"Excel AI Copilot"** taskpane will immediately appear on the right side of your active worksheet!

### Method B: Excel Desktop for Windows
1. Open Excel on your PC.
2. Create a local shared folder (e.g., `C:\OfficeManifests`) and copy `addin/manifest.xml` into it.
3. In Excel, go to **File** > **Options** > **Trust Center** > **Trust Center Settings** > **Trusted Add-in Catalogs**.
4. Enter `C:\OfficeManifests`, click **Add catalog**, check **Show in Menu**, and click **OK**.
5. Restart Excel. Go to **Insert** > **My Add-ins** > select **Shared Folder** tab and launch **Excel AI Copilot**.

### Method C: Excel Desktop for macOS
1. Open Finder on Mac, press `Cmd + Shift + G` and navigate to:
   `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/`
   *(Create the `wef` directory if it does not exist)*.
2. Copy `addin/manifest.xml` into this `wef/` folder.
3. Launch Excel for Mac. Go to **Insert** > click the small arrow next to **My Add-ins** > select **AI Agent Copilot**.

---

## 7. Verification Test Scenarios

### Scenario 1: Slash Command `/search`
- Type: `/search Áo thun`
- Result: Returns matching product items (`SP-001`) with price `250,000 đ`. Click the insert button to populate the sheet.

### Scenario 2: Natural Language Interaction
- Type: *"Find item SP-002 in stock and insert it as a new row in my table"*
- Result: Agent detects intent, queries the Mock DB, calculates total price formulas, and presents a Preview Diff card for your confirmation.

### Scenario 3: Dedicated Search Catalog Tab
- Click the **🔍 Tra cứu DB** tab.
- Search for `Nguyên phụ liệu` or `Vải`.
- Click `➕ Chèn vào Excel` to write directly to your workbook via `Office.js`!
