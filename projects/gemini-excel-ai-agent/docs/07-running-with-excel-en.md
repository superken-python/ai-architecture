# 07 · Comprehensive Installation & User Guide for Excel Web & Desktop Apps (macOS & Windows)

This document is the complete, step-by-step master guide for configuring, installing (sideloading), and operating the **Excel Enterprise AI Agent Copilot** across **Excel on the Web** and **Excel Desktop Apps on both macOS and Windows**.

---

## TABLE OF CONTENTS
1. [Part I: Environment Setup & Service Launch](#part-1)
2. [Part II: Sideloading & Installation Guide](#part-2)
   - [Section A: Excel on the Web (Microsoft 365 Browser)](#sec-a-web)
   - [Section B: Excel Desktop App on macOS](#sec-b-macos)
   - [Section C: Excel Desktop App on Windows](#sec-c-windows)
   - [Section D: Centralized Deployment for Enterprise (M365 Admin)](#sec-d-admin)
3. [Part III: Detailed Feature User Guide](#part-3)
   - [3.1. Opening & Pinning the AI Copilot Taskpane](#user-31)
   - [3.2. Fast Catalog Query with `/search` Slash Command](#user-32)
   - [3.3. Browsing Catalog & 1-Click Insert via "DB Search" Tab](#user-33)
   - [3.4. Human-in-the-Loop Safety Protocol: Preview Diff Modal](#user-34)
   - [3.5. Natural Language ReAct Commands](#user-35)
   - [3.6. Dynamic Formula Recalculation](#user-36)
4. [Part IV: Troubleshooting & FAQ](#part-4)

---

<a id="part-1"></a>
## PART I: ENVIRONMENT SETUP & SERVICE LAUNCH

### Step 1.1: Launch the Backend Service
Open your Terminal and run:
```bash
cd projects/gemini-excel-ai-agent

# Install dependencies using Poetry
poetry install

# Create environment configuration
cp .env.example .env

# Start the FastAPI + Agno AgentOS server
poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000
```
*(Or use the shortcut: `make dev`)*

> [!NOTE]
> The system has a built-in **Smart Mock Fallback Strategy**. Even if no Azure OpenAI API key is supplied in `.env`, you can immediately test 100% of the `/search` catalog queries, Preview Diff cards, and live Excel cell updates!

### Step 1.2: Install HTTPS SSL Certificate for Localhost (Mandatory for Desktop Apps)
Unlike Excel on the Web, **Excel Desktop Apps on Mac and Windows run inside strict WebView sandboxes (Apple WebKit / Edge WebView2) and strictly require trusted HTTPS endpoints**.

Install Microsoft's official local development certificate:
```bash
npx office-addin-dev-certs install
```
When prompted by your OS, choose **Yes / Allow** to trust the certificate.

### Step 1.3: Verification Check
Visit the following endpoints in your browser:
- Backend Health: [http://localhost:8000/health](http://localhost:8000/health) → `"status": "healthy"`.
- Taskpane Web UI: [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html).

---

<a id="part-2"></a>
## PART II: SIDELOADING & INSTALLATION GUIDE

The manifest configuration file is located at:
`projects/gemini-excel-ai-agent/addin/manifest.xml`

---

<a id="sec-a-web"></a>
### SECTION A: Excel on the Web (Office 365 Browser)
*The fastest method — works on any operating system without installing software.*

1. Open your browser, navigate to [https://excel.new](https://excel.new) (or [https://office.com](https://office.com)) and sign in.
2. Open a **Blank workbook**.
3. In the top ribbon, select the **Insert** tab.
4. Click **Add-ins** (or **Office Add-ins**).
5. In the dialog, select the top tab: **Upload My Add-in**.
6. Click **Browse...** and select:
   `projects/gemini-excel-ai-agent/addin/manifest.xml`.
7. Click **Upload**.
8. **Result:** The **Excel AI Copilot** taskpane immediately docks on the right side of your sheet!

---

<a id="sec-b-macos"></a>
### SECTION B: Excel Desktop App on macOS
*For native Microsoft Excel installations on Mac.*

Excel for Mac automatically discovers local add-ins from a system directory called **`wef` (Web Extension Framework)**.

#### Step 1: Copy the manifest into macOS `wef` Directory
Open Terminal on your Mac and run:
```bash
# 1. Create the wef directory if it doesn't exist
mkdir -p ~/Library/Containers/com.microsoft.Excel/Data/Documents/wef

# 2. Copy the manifest file into wef
cp /Users/duc.nguyen/data/projects/success/motives/motivesidp-ai-learning/ai-architecture/projects/gemini-excel-ai-agent/addin/manifest.xml ~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/
```

*(Alternatively, in **Finder**, press `Cmd + Shift + G`, paste `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/`, and drag `manifest.xml` there).*

#### Step 2: Open the Add-in in Excel for Mac
1. Launch **Microsoft Excel** on your Mac.
2. Open any workbook.
3. In the ribbon, click the **Insert** tab.
4. Next to the **My Add-ins** button, click the small **downward arrow (drop-down menu)**.
5. Under **Developer Add-ins**, you will see **AI Agent Copilot**.
6. Click **AI Agent Copilot**:
   - The Taskpane will open on the right edge.
   - It is ready for action!

*(Tip: If it does not appear right away, quit Excel completely with `Cmd + Q` and restart).*

---

<a id="sec-c-windows"></a>
### SECTION C: Excel Desktop App on Windows
*For Microsoft Excel on Windows 10/11.*

#### Method C.1: Shared Folder Catalog (Official Microsoft Standard)
1. Create a folder on your drive: `C:\OfficeManifests`.
2. Copy `addin/manifest.xml` into `C:\OfficeManifests`.
3. Right-click `C:\OfficeManifests` > **Properties** > **Sharing** tab.
4. Click **Share...** > select your Windows account > click **Share** > **Done**.
5. Copy the generated network UNC path, e.g., `\\localhost\OfficeManifests`.
6. Open **Excel Desktop** on Windows:
   - Go to **File** > **Options** (bottom-left).
   - Select **Trust Center** > click **Trust Center Settings...**.
   - On the left, choose **Trusted Add-in Catalogs**.
   - In **Catalog Url**, paste: `\\localhost\OfficeManifests`.
   - Click **Add catalog**.
   - **Check the box "Show in Menu"** next to the path.
   - Click **OK** > **OK**.
7. Restart Excel. Go to **Insert** > **My Add-ins** > click the **Shared Folder** tab at the top > select **AI Agent Copilot** > click **Add**.

#### Method C.2: Automatic CLI Command (Developer Shortcut)
In your Windows terminal, run:
```bash
npx office-addin-debugging start addin/manifest.xml desktop --app excel
```
This automatically registers the manifest in your Windows registry and opens Excel with the plugin pre-attached to the ribbon.

---

<a id="sec-d-admin"></a>
### SECTION D: Centralized Deployment for Enterprise (Microsoft 365 Admin Center)
*For IT Administrators with Microsoft 365 Business / Enterprise subscriptions.*

This method requires **zero manual configuration on end-user machines**:
1. Sign in to the admin portal: [https://admin.microsoft.com](https://admin.microsoft.com).
2. Go to **Settings** > **Integrated apps**.
3. Click **Upload custom apps** > select **Office Add-in**.
4. Choose **Upload manifest file (.xml)** and select `addin/manifest.xml`.
5. Select target users: *Entire organization* or specific departments (Accounting, Procurement, Sales).
6. Click **Deploy**.
7. **Result:** Within hours, the **AI Copilot** button appears automatically on the Ribbon of every employee's Excel app (both Windows and Mac)!

---

<a id="part-3"></a>
## PART III: DETAILED FEATURE USER GUIDE

<a id="user-31"></a>
### 3.1. Opening & Pinning the AI Copilot Taskpane
- Click the **Motives AI** ribbon button: **"Mở AI Copilot"** to open the sidebar.
- A green status light in the header indicates **Online** connectivity.

---

<a id="user-32"></a>
### 3.2. Fast Catalog Query with `/search` Slash Command
Query the simulated enterprise database directly from chat:
1. In the input box at the bottom, type:
   ```
   /search <keyword>
   ```
   *Examples:*
   - `/search Áo thun`
   - `/search SP-002`
   - `/search Vải`
   - `/search Carton`
2. Press **Enter**.
3. The chatbot returns product cards with SKU, name, unit price (formatted in VND), and stock level.
4. Click **`+ Chèn vào Excel`** below any item to start row insertion.

---

<a id="user-33"></a>
### 3.3. Browsing Catalog & 1-Click Insert via "DB Search" Tab
If you prefer a visual search interface:
1. Click the **🔍 Tra cứu DB** tab in the taskpane navigation.
2. Enter any search term or leave blank to browse all items.
3. Click **➕ Chèn vào Excel** on any product card.

---

<a id="user-34"></a>
### 3.4. Human-in-the-Loop Safety Protocol: Preview Diff Modal
To ensure AI never accidentally overwrites critical spreadsheet data:
1. Whenever a row insertion is triggered, a **⚡ Preview Diff Modal** pops up:
   - Displays the target Row number and target Sheet name.
   - Shows a table mapping each Column header to its proposed new value.
2. Review the data:
   - Click **Xác nhận ghi (Apply)**: `Office.js` immediately inserts the row and highlights it in pale green for 2 seconds.
   - Click **Hủy bỏ (Cancel)**: Discards the action safely without modifying the worksheet.

---

<a id="user-35"></a>
### 3.5. Natural Language ReAct Commands
You can also chat in natural Vietnamese or English:
- *"Tìm mã SP-003 rồi thêm vào bảng giúp tôi"*
- *"Thêm sản phẩm vải kháng khuẩn vào dòng tiếp theo"*
- *"Find item SP-001 in stock and add it to my sheet"*

The Agent uses ReAct tool calling to search the database and construct the row insertion proposal automatically.

---

<a id="user-36"></a>
### 3.6. Dynamic Formula Recalculation
When the AI inserts a row:
- The **Thành tiền** (Total Amount) column receives a dynamic Excel formula: `=D<row>*E<row>` (Quantity × Unit Price).
- If you edit the Quantity in Column D on the sheet, Excel will automatically recalculate the Total Amount using native calculation engine.

---

<a id="part-4"></a>
## PART IV: TROUBLESHOOTING & FAQ

### Issue 1: Blank Taskpane on Excel Desktop
- **Cause:** Missing local HTTPS SSL certificate. Desktop WebView blocks insecure HTTP connections.
- **Fix:**
  1. In terminal, run: `npx office-addin-dev-certs install`.
  2. Accept the certificate prompt.
  3. Restart Excel.

### Issue 2: Copilot Button Missing on Mac
- **Fix:**
  1. Verify the file is named exactly `manifest.xml` in `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/`.
  2. Fully quit Excel (`Cmd + Q`), then reopen.
  3. Check the drop-down menu next to the **My Add-ins** button on the **Insert** tab.

### Issue 3: "Cannot connect to server" Message
- **Fix:** Verify the backend is running (`poetry run uvicorn excel_agent.main:app` on port 8000) and that [http://localhost:8000/health](http://localhost:8000/health) returns healthy.

### Issue 4: How to Inspect / Debug Console Logs on Desktop
- **On macOS:** Enable Web Inspector by running:
  ```bash
  defaults write com.microsoft.Excel OfficeWebAddinDeveloperExtras -bool true
  ```
  Then right-click inside the taskpane and select **Inspect Element**.
- **On Windows:** Use the free **Microsoft Edge DevTools Preview** from the Microsoft Store to attach to the WebView2 runtime.
