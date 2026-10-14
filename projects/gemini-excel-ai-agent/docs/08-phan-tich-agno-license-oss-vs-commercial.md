# 08 · Phân tích bản quyền Agno: Open Source vs Commercial (Enterprise)

Tài liệu này cung cấp phân tích chi tiết và khách quan về mô hình cấp phép bản quyền của **Agno (tiền thân là Phidata)**, so sánh tính năng giữa phiên bản mã nguồn mở (Open Source) và bản thương mại (Commercial / Enterprise Cloud), trả lời câu hỏi liệu doanh nghiệp triển khai môi trường Production có bắt buộc phải mua bản quyền hay không.

---

## 1. Tổng quan về Agno & Giấy phép mã nguồn mở (OSS License)

- **Tên dự án:** Agno (trước đây là Phidata).
- **Mã nguồn:** Thư viện Python `agno` (ví dụ: `pip install agno`).
- **Giấy phép bản quyền mã nguồn mở (OSS License):** **Apache License 2.0**.
- **Ý nghĩa pháp lý của Apache 2.0 đối với Doanh nghiệp:**
  - Cho phép sử dụng miễn phí cho mục đích thương mại (Commercial use permitted).
  - Cho phép sửa đổi (Modification), phân phối nội bộ (Private use) và triển khai trên hạ tầng máy chủ của doanh nghiệp (On-premise / Private Cloud) mà **KHÔNG phải trả phí bản quyền (Royalty-free)**.
  - Không có điều khoản "Copyleft" nghiêm ngặt như GPL (tức doanh nghiệp không bị ép buộc phải công khai mã nguồn phần mềm riêng của mình khi tích hợp với thư viện Agno).

---

## 2. Doanh nghiệp chạy Production có BẮT BUỘC phải mua bản quyền Agno không?

> [!IMPORTANT]
> **CÂU TRẢ LỜI NGẮN GỌN: KHÔNG BẮT BUỘC.**
> 
> Nếu doanh nghiệp tự host mã nguồn (`self-hosted`) trên hạ tầng máy chủ riêng (AWS, Azure, GCP, hoặc On-Premise Kubernetes / Docker / VM), doanh nghiệp có thể sử dụng **100% miễn phí** phiên bản mã nguồn mở của Agno trong môi trường Production mà hoàn toàn hợp pháp.

### Khi nào doanh nghiệp KHÔNG CẦN mua bản quyền:
1. Doanh nghiệp muốn tự kiểm soát dữ liệu 100%, không gửi dữ liệu ra cloud của bên thứ ba (Data Sovereignty).
2. Hệ thống AI Agent phục vụ nội bộ công ty (như plugin Excel Copilot này).
3. Doanh nghiệp đã có hạ tầng Observability riêng (ví dụ: tự host **Langfuse** hoặc **OpenTelemetry** để ghi log LLM, token và độ trễ).
4. Đội ngũ kỹ thuật nội bộ có khả năng tự vận hành container, PostgreSQL database và FastAPI gateway.

---

## 3. Bảng so sánh chi tiết: Agno Open Source vs Agno Commercial (Cloud / Enterprise)

| Hạng mục tính năng | Agno Open Source (Tự host) | Agno Commercial / Enterprise |
|---|:---:|:---:|
| **Chi phí bản quyền phần mềm** | **$0 (Miễn phí vĩnh viễn - Apache 2.0)** | Trả phí theo User / Thao tác / Gói tháng |
| **Agent Core & Reasoning Loop** | Đầy đủ (ReAct, Autonomous, Tool calling) | Đầy đủ |
| **Hỗ trợ Models (Azure OpenAI, Gemini, v.v.)** | Đầy đủ (Qua Python SDK) | Đầy đủ |
| **AgentOS (Local UI & FastAPI Server)** | Đầy đủ (Chạy qua `agno[os]`) | Được host sẵn trên Agno Cloud |
| **Lưu trữ State, Sessions & Memory** | Tự quản lý (PostgreSQL, SQLite, Redis) | Được quản lý tự động trên Cloud DB |
| **MCP (Model Context Protocol) Support** | Đầy đủ | Đầy đủ |
| **Knowledge Base & Vector DB** | Tự tích hợp (pgvector, Qdrant, LanceDB) | Tích hợp sẵn và đồng bộ tự động |
| **Bảng điều khiển Giám sát (Control Plane)** | Giao diện Local / AgentOS UI cơ bản | Web Console tập trung cho nhiều dự án |
| **Quản lý nhóm & Phân quyền (RBAC)** | Phải tự xây dựng logic phân quyền | Sẵn có: Admin, Developer, Viewer, Team |
| **Đăng nhập một lần (Enterprise SSO)** | Tự tích hợp qua FastAPI middleware | Sẵn có: Okta, SAML 2.0, Azure Entra ID |
| **Quản trị Prompt tập trung & Versioning** | Quản lý qua file code / YAML nội bộ | Quản lý trên UI Cloud, A/B test prompt |
| **Đánh giá tự động (Continuous Evals)** | Tự viết script test / Pytest | Dashboard chấm điểm LLM tự động |
| **Tuân thủ chuẩn bảo mật (SOC2, HIPAA)** | Doanh nghiệp tự chịu trách nhiệm hạ tầng | Agno cung cấp chứng chỉ SOC2 Type II |
| **Hỗ trợ kỹ thuật & Cam kết SLA** | Cộng đồng GitHub & Discord | Kênh hỗ trợ riêng, SLA phản hồi 1h-4h |

---

## 4. Tính năng mở rộng của bản Commercial (Khi nào nên mua?)

Bản thương mại (Agno Enterprise / Cloud) được thiết kế cho các tập đoàn lớn cần:
1. **Không muốn tốn công vận hành hạ tầng DevOps:** Agno Cloud lo toàn bộ việc scaling, database replication, backup phiên làm việc.
2. **Quản lý hàng trăm Agent và hàng ngàn nhân viên:** Cần dashboard tổng quát xem phòng ban nào đang gọi agent nào, tiêu tốn bao nhiêu token, ai có quyền sửa prompt của agent.
3. **Tuân thủ chính sách kiểm toán khắt khe:** Cần chứng nhận SOC2 có sẵn từ nhà cung cấp để trình ban giám đốc hoặc khách hàng quốc tế.
4. **Cần cam kết bảo hành và hỗ trợ 24/7 (SLA).**

---

## 5. Khuyến nghị chiến lược cho dự án `gemini-excel-ai-agent`

Đối với dự án **Plugin AI Chatbot nhúng Excel kết nối hệ thống nội bộ**:

| Giai đoạn | Lựa chọn đề xuất | Lý do & Tối ưu chi phí |
|---|---|---|
| **Giai đoạn 1: POC & Thử nghiệm** | **Agno Open Source (Self-hosted)** | Tiết kiệm 100% chi phí bản quyền, tự do tùy biến luồng ReAct trên `Office.js`, chạy trực tiếp trên máy dev hoặc server nội bộ. |
| **Giai đoạn 2: Pilot nội bộ (Vài chục user)** | **Agno Open Source + PostgreSQL + Langfuse** | Hoàn toàn đáp ứng tải, bảo mật dữ liệu nội bộ không lọt ra ngoài, tận dụng Langfuse để trace chi phí token và độ trễ. |
| **Giai đoạn 3: Scale toàn tập đoàn (> 1,000 user)** | **Xem xét Agno Enterprise HOẶC Tiếp tục Self-hosted** | Nếu IT nội bộ mạnh: Tiếp tục chạy Kubernetes Private Cluster. Nếu IT muốn giao việc vận hành cho vendor: Mua bản quyền Enterprise. |

> [!TIP]
> **Kết luận:** Dự án này được thiết kế và triển khai hoàn toàn trên nền tảng **Agno Open Source SDK kết hợp FastAPI**, đảm bảo doanh nghiệp có thể vận hành production ngay lập tức mà **không phát sinh bất kỳ chi phí bản quyền phần mềm nào** ngoài chi phí API Azure OpenAI theo mức sử dụng thực tế.
