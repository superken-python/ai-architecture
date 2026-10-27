# security_scan — nối kết quả Semgrep, ZAP, Trivy với tri thức IPA (Nhật Bản)

**Trạng thái:** nghiên cứu + thiết kế dữ liệu (chỉ tài liệu và CSV mẫu, chưa có code vận hành) · **Ngày:** 2026-10-27 (cập nhật lần 2: thêm Trivy và ZAP)

## Bài toán

Quét bằng [Semgrep](https://semgrep.dev/) (SAST, đọc mã nguồn), [ZAP](https://www.zaproxy.org/) (DAST, dò website đang chạy) và [Trivy](https://trivy.dev/) (thư viện, container, cấu hình, secret), rồi đọc kết quả theo cách phân loại của **IPA** ("安全なウェブサイトの作り方" và các tài liệu liên quan) thông qua mã **CWE**. Cần: (1) hiểu mối liên hệ output ↔ IPA, (2) cách đưa tri thức IPA vào dữ liệu có cấu trúc, (3) template CSV để import, (4) cách luôn cập nhật khi IPA/CWE/rule thay đổi.

## Kết quả chính

- Chuỗi mapping: `finding → CWE → mục IPA → đối sách IPA`.
- **Trivy và ZAP đều là mã nguồn mở** (Apache-2.0; `trivy-checks` MIT). Cả hai có CWE trong output nhưng **không đồng đều**: ZAP gắn `cweid` cho mỗi alert; Trivy chỉ gắn `CweIDs` cho lỗ hổng thư viện (CVE), còn misconfig/secret/license không có CWE.
- Bản seed 11 mục IPA phủ **khoảng 1/4** cặp rule–CWE: Semgrep 22,6% trực tiếp + 2,2% qua cây CWE, ZAP 19,5% + 2,7%. Phần còn lại (~75–78%) nằm ngoài → phải có trạng thái `OUT_OF_IPA_SCOPE`.
- ZAP bổ sung chỗ Semgrep yếu: 10/11 mục IPA có ít nhất một scan rule ZAP (header chống clickjacking, cờ cookie, token CSRF...).
- Tag CWE của Semgrep có chỗ sai (đã gặp 2 kiểu: `tainted-sql-string` bị gắn CWE-915/704; `filter-skipping` của Rails bị gắn CWE-1021 clickjacking) → cần bảng override có người duyệt.
- **Một file import duy nhất cho cả ba công cụ:** [`exports/ipa_map_all_tools.csv`](exports/ipa_map_all_tools.csv) (553 dòng) nối mục IPA ↔ CWE ↔ công cụ ↔ rule/check. File này sinh ra từ các bảng nguồn, không sửa tay.
- Đã chạy thật: scan một file Flask mẫu bằng Semgrep (20 finding) và chạy chung với 5 file output mẫu của Trivy + fixture ZAP → nạp 9 CSV mẫu vào SQLite → báo cáo theo mục IPA, kèm phần ngoài phạm vi và phần không có CWE.

## Đọc theo thứ tự

| File | Nội dung |
|---|---|
| [`docs/01-nghien-cuu-ipa-cwe-semgrep.md`](docs/01-nghien-cuu-ipa-cwe-semgrep.md) | IPA, CWE, Semgrep: là gì, output trông ra sao, những bẫy khi lấy CWE, số liệu bộ rule |
| [`docs/02-mapping-semgrep-ipa-va-cap-nhat.md`](docs/02-mapping-semgrep-ipa-va-cap-nhat.md) | **Tài liệu chính:** Trivy và ZAP, quy tắc mapping, đo độ phủ, ví dụ chạy thật, cách export IPA knowledge base, template CSV, code import, quy trình cập nhật liên tục |
| [`templates/`](templates/) | 9 file CSV mẫu (IPA, CWE, mapping, catalog rule Semgrep và ZAP, override, phiên bản nguồn) |
| [`exports/ipa_map_all_tools.csv`](exports/ipa_map_all_tools.csv) | **File import duy nhất** cho Semgrep + ZAP + Trivy, dẫn xuất từ các bảng nguồn; cột `review_flag` đánh dấu dòng chờ duyệt override |

## Giới hạn quan trọng (đọc trước khi dùng)

- Môi trường nghiên cứu **chặn** `www.ipa.go.jp`, `cwe.mitre.org`, `semgrep.dev` (403 từ proxy). Nội dung IPA **chưa được đọc trực tiếp**; mọi dữ liệu IPA trong `templates/` là seed theo trí nhớ, gắn `seed_unverified`. Cần người có quyền truy cập đối chiếu với tài liệu gốc.
- Dữ liệu CWE trong mẫu là bản **4.14** (2024-02-29) lấy từ gói PyPI `cwe2`, không phải bản mới nhất.
- Phần Semgrep (rule, scan, số liệu) và code mẫu trong tài liệu 02 **đã chạy thật**.
- **Trivy và ZAP chưa được chạy scan thật.** Schema và CWE của chúng đọc từ mã nguồn, dữ liệu mẫu của chính dự án và script trích CWE từ mã rule ZAP. Cần chạy thử trên mục tiêu hợp lệ để xác nhận (xem tài liệu 02, mục 11). ZAP active scan chỉ dùng cho hệ thống bạn sở hữu hoặc được cấp phép.
- `exports/ipa_map_all_tools.csv` dựa trên bảng seed IPA↔CWE **chưa xác minh** (mọi dòng `seed_unverified`); không dùng cho báo cáo chính thức trước khi đối chiếu IPA.
- Giấy phép cần đọc trước khi phân phối lại: Semgrep Rules License v1.0, điều khoản sử dụng CWE, điều khoản của IPA, điều khoản của các nguồn dữ liệu lỗ hổng mà Trivy tải về.
