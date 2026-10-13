# gemini-excel-ai-agent · Trợ lý AI Agent nhúng Excel (Agno AgentOS SDK)

**Nhóm bài toán:** Nhóm 7 · AI Agent & Tự động hóa quy trình (Tổ hợp mở rộng: **CMB-10 · Enterprise Spreadsheet Copilot**)  
**Runtime & Model:** **Agno AgentOS SDK** kết hợp mô hình **Azure OpenAI (`gpt-5-mini`)**  
**Trạng thái:** **Đã hoàn thiện mã nguồn POC đầy đủ** (FastAPI backend + Agno SDK + Mock Enterprise DB + Office Add-in UI)  
**Người đề xuất / Nghiên cứu:** Motives AI Architecture Team  

---

## 1 · Tổng quan dự án

Dự án phát triển một giải pháp toàn diện bao gồm:
1. **Plugin Office Add-in (Taskpane UI):** Nhúng trực tiếp vào Microsoft Excel (Desktop Windows/Mac và Excel Online), hỗ trợ lệnh tắt `/search`, hội thoại tự nhiên và thẻ xác nhận thay đổi dữ liệu (Human-in-the-Loop Preview Diff).
2. **Backend AI Agent (Agno AgentOS):** Dịch vụ FastAPI chuẩn kiến trúc phân tầng (Layered Architecture), Pydantic v2, Strategy Pattern và Pipeline Step-Context.
3. **Mô hình AI:** Sử dụng **Azure OpenAI (`gpt-5-mini`)** cấu hình Zero-Hardcoding qua `.env`.
4. **Mock Enterprise Database:** Giả lập danh mục sản phẩm doanh nghiệp, cho phép tra cứu bằng `/search` và đẩy dữ liệu trực tiếp vào bảng tính Excel.

---

## 2 · Cấu trúc thư mục mã nguồn

```
projects/gemini-excel-ai-agent/
├── .env.example                         # File mẫu cấu hình Azure OpenAI gpt-5-mini & Agno
├── pyproject.toml                       # Cấu hình Poetry dependencies
├── Makefile                             # Lệnh dev, setup, lint, format
├── README.md                            # Tổng quan và hướng dẫn dự án
├── prompts/                             # Cô lập prompt theo chuẩn (.yml)
│   ├── excel_agent.yml                  # Prompt ReAct cho Excel Copilot
│   └── search_agent.yml                 # Prompt phân tích lệnh tìm kiếm
├── addin/                               # Mã nguồn Microsoft Office Web Add-in
│   ├── manifest.xml                     # File manifest sideload vào Excel
│   ├── index.html                       # Giao diện Fluent UI Taskpane & Web Simulator
│   ├── styles.css                       # CSS giao diện chuẩn Office
│   └── app.js                           # Kết nối Office.js, xử lý /search và API call
├── docs/                                # Hệ thống tài liệu nghiên cứu chuyên sâu
│   ├── 01-mo-ta-bai-toan.md             # Mô tả bài toán nghiệp vụ & định vị G7 / CMB-10
│   ├── 02-solution-approach-kien-truc.md# Kiến trúc Agno AgentOS 3 tầng & Pydantic schemas
│   ├── 03-danh-gia-tinh-kha-thi.md      # Báo cáo đánh giá khả thi kỹ thuật
│   ├── 04-danh-muc-tinh-nang-mo-rong.md # Danh mục 6 nhóm tính năng mở rộng
│   ├── 05-ke-hoach-poc.md               # Kế hoạch triển khai thử nghiệm POC
│   ├── 06-huong-dan-chay-excel-vi.md    # Hướng dẫn chi tiết chạy với Excel (Tiếng Việt)
│   ├── 07-running-with-excel-en.md      # Detailed running guide with Excel (English)
│   └── 08-phan-tich-agno-license-oss-vs-commercial.md # Phân tích bản quyền Agno OSS vs Commercial
└── src/excel_agent/                     # Mã nguồn Backend theo chuẩn kiến trúc
    ├── main.py                          # FastAPI entrypoint & static mount
    ├── core/                            # Config (BaseSettings), Logging (loguru), Decorators
    ├── models/                          # SQLModel entities (Product, AuditLog)
    ├── schemas/                         # Pydantic v2 DTOs (Search, Excel, Agent, Common)
    ├── strategies/                      # Strategy Pattern (AzureOpenAI, MockLLM, FuzzySearch)
    ├── builders/                        # YAML PromptBuilder loader
    ├── pipelines/                       # Step-Context Pipeline Pattern
    ├── services/                        # 100% Business Logic (DbService, ExcelService, AgentService)
    └── api/v1/                          # Routers (chat, search, excel)
```

---

## 3 · Bắt đầu nhanh (Quick Start)

### 3.1. Cài đặt và cấu hình
```bash
cd projects/gemini-excel-ai-agent

# Cài đặt thư viện bằng Poetry
poetry install

# Tạo file cấu hình môi trường
cp .env.example .env
# (Điền AZURE_OPENAI_API_KEY nếu có, hoặc để trống để chạy chế độ Fallback Simulator)
```

### 3.2. Khởi chạy Server
```bash
poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000
# Hoặc chạy lệnh make:
make dev
```

### 3.3. Trải nghiệm
- **Kiểm thử trên trình duyệt:** Mở [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html). Thử gõ `/search Áo thun` hoặc bấm các nút quick action.
- **Sideload vào Microsoft Excel:** Xem chi tiết hướng dẫn tại [06-huong-dan-chay-excel-vi.md](docs/06-huong-dan-chay-excel-vi.md) hoặc [07-running-with-excel-en.md](docs/07-running-with-excel-en.md).

---

## 4 · Danh mục tài liệu chi tiết trong `docs/`

| # | Tài liệu | Nội dung chính |
|---|---|---|
| 1 | [01 · Mô tả bài toán](docs/01-mo-ta-bai-toan.md) | Bối cảnh doanh nghiệp, pain points & định vị trong bản đồ bài toán (Nhóm 7 / CMB-10). |
| 2 | [02 · Kiến trúc giải pháp](docs/02-solution-approach-kien-truc.md) | Kiến trúc 3 tầng với **Agno AgentOS**, Client-Side Tool Calling và Pydantic schemas. |
| 3 | [03 · Đánh giá tính khả thi](docs/03-danh-gia-tinh-kha-thi.md) | Khảo sát năng lực Office.js API, ma trận tương thích Win/Mac/Web, hiệu năng và rủi ro. |
| 4 | [04 · Danh mục tính năng mở rộng](docs/04-danh-muc-tinh-nang-mo-rong.md) | Đề xuất các tính năng mở rộng: Smart VLOOKUP, 2-Way ERP Sync, Formula Copilot, VLM Doc Ingestion. |
| 5 | [05 · Kế hoạch thử nghiệm POC](docs/05-ke-hoach-poc.md) | Lộ trình triển khai POC 3 giai đoạn (POC-1, POC-2, POC-3). |
| 6 | [06 · Hướng dẫn chạy với Excel (Tiếng Việt)](docs/06-huong-dan-chay-excel-vi.md) | **Hướng dẫn chi tiết từng bước chạy và nạp vào Excel Desktop / Excel Web (Tiếng Việt).** |
| 7 | [07 · Running Guide with Excel (English)](docs/07-running-with-excel-en.md) | **Step-by-step setup and sideloading instructions into Microsoft Excel (English).** |
| 8 | [08 · Phân tích bản quyền Agno (OSS vs Commercial)](docs/08-phan-tich-agno-license-oss-vs-commercial.md) | **Phân tích bản quyền Apache 2.0, chi phí prod, so sánh tính năng mã nguồn mở vs bản trả phí.** |

---

## 5 · Kết luận phân tích bản quyền Agno cho Doanh nghiệp

- **Agno Open Source SDK (Apache 2.0):** Miễn phí thương mại vĩnh viễn, được phép tự host trên máy chủ doanh nghiệp (on-premise / private cloud) chạy production mà **không cần mua license**.
- **Bản Commercial (Agno Enterprise Cloud):** Chỉ cần thiết khi doanh nghiệp muốn ủy thác toàn bộ việc quản lý hạ tầng cho vendor, cần dashboard quản lý nhiều team tập trung và chứng chỉ SOC2 Type II.
