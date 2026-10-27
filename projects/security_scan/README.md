# security_scan — knowledge base IPA + NVD để Semgrep, ZAP, Trivy tra cứu

**Trạng thái:** nghiên cứu + thiết kế dữ liệu (tài liệu, template CSV, bản export KB; chưa có job vận hành) · **Ngày:** 2026-10-27 (cập nhật lần 3: KB IPA + NVD)

## Bài toán

[Semgrep](https://semgrep.dev/) (SAST), [ZAP](https://www.zaproxy.org/) (DAST) và [Trivy](https://trivy.dev/) (thư viện, container, cấu hình, secret) cho ra kết quả có mã **CWE** và/hoặc **CVE**. **IPA** (tài liệu "安全なウェブサイトの作り方", cơ sở dữ liệu JVN iPedia) và **NVD** là tài liệu tham chiếu để các công cụ đó tra vào. Cần export dữ liệu tổng hợp IPA + NVD thành knowledge base (KB) không phụ thuộc công cụ, có template CSV để import, và có cách cập nhật liên tục.

## Kết quả chính

- **KB gồm hai file**: [`kb/kb_cwe.csv`](kb/kb_cwe.csv) (khóa CWE: tên EN/JA, CWE mà NVD dùng, mục IPA, đối sách; đầy đủ 1.375 CWE và mã giả) và `kb_cve.csv` (khóa CVE: CWE theo từng nguồn NVD/CNA/JVN, CWE được chọn, mục IPA, CVSS, KEV, mã JVNDB). Bản mẫu 23 CVE thật: [`kb/kb_cve.sample.csv`](kb/kb_cve.sample.csv); bản đầy đủ sinh bằng script mỗi ngày.
- **Công cụ chỉ đưa ra khóa để tra**: Semgrep và ZAP tra theo CWE; Trivy tra theo CVE trước, khi KB không có CVE mới dùng CWE của Trivy.
- **CWE của một CVE khác nhau tùy nguồn và tùy thời điểm** (ví dụ Log4Shell: JVN = 20, CNA = 20/400/502, NVD = 917; jquery `CVE-2019-11358`: NVD năm 2021 ghi CWE-79, nay ghi CWE-1321), nên KB lưu CWE từng nguồn và có chính sách chọn. Mặc định NVD → CNA/ADP → JVN. Năm 2025 chỉ 0,55% CVE có chênh lệch CWE làm đổi mục IPA ([tài liệu 04](docs/04-thuat-ngu-so-sanh-va-cach-map.md)).
- **Đo trên NVD thật năm 2025**: 58,8% CVE (không tính Rejected) rơi vào 11 mục IPA; chỉ 12,5% CVE có CWE do chính NVD gắn, còn lại đến từ CNA/ADP. Trên rule của Semgrep/ZAP, độ phủ chỉ khoảng 25%.
- **Trivy và ZAP đều là mã nguồn mở** (Apache-2.0; `trivy-checks` MIT). ZAP gắn `cweid` cho mỗi alert; Trivy chỉ gắn `CweIDs` cho lỗ hổng thư viện.
- **Đính chính**: bản trước có `exports/ipa_map_all_tools.csv` lấy rule của công cụ đổ vào template, tức đi ngược chiều. File này đã được gỡ; dữ liệu phía công cụ chuyển sang `tool_side/`.

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| [`docs/03-kb-ipa-nvd-cho-cong-cu.md`](docs/03-kb-ipa-nvd-cho-cong-cu.md) | **Tài liệu chính:** nguồn NVD và JVN iPedia, thiết kế KB, template CSV, chính sách chọn CWE, cách công cụ tra cứu, số đo trên NVD thật, code dựng KB, cập nhật liên tục |
| [`docs/04-thuat-ngu-so-sanh-va-cach-map.md`](docs/04-thuat-ngu-so-sanh-va-cach-map.md) | Thuật ngữ (NVD, IPA, JVN, CVE, CWE, CAPEC, CPE, CVSS, KEV, GHSA, OSV, Semgrep, ZAP, Trivy…), bảng so sánh, Trivy tra KB thế nào, các cách map khi mã không khớp, cách so sánh nguồn, 6 sơ đồ Mermaid |
| [`kb/`](kb/) | Bản export KB IPA + NVD: `kb_cwe.csv` (đầy đủ), `kb_cve.sample.csv` (mẫu) |
| [`templates/`](templates/) | Bảng nguồn để dựng KB: mục IPA, đối sách, mapping IPA↔CWE, CWE, phiên bản nguồn |
| [`docs/01-nghien-cuu-ipa-cwe-semgrep.md`](docs/01-nghien-cuu-ipa-cwe-semgrep.md) | Nghiên cứu ban đầu: IPA, CWE, Semgrep |
| [`docs/02-mapping-semgrep-ipa-va-cap-nhat.md`](docs/02-mapping-semgrep-ipa-va-cap-nhat.md) | Phía công cụ: CWE trong output Semgrep/ZAP/Trivy, chuẩn hóa, đo độ phủ theo rule, sửa CWE sai của rule |
| [`tool_side/`](tool_side/) | Catalog rule Semgrep/ZAP và override CWE: phía công cụ, **không** thuộc KB |

## Giới hạn quan trọng (đọc trước khi dùng)

- Môi trường nghiên cứu **chặn** `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp`, `cwe.mitre.org`, `semgrep.dev`. Dữ liệu NVD lấy qua mirror [`fkie-cad/nvd-json-data-feeds`](https://github.com/fkie-cad/nvd-json-data-feeds) (snapshot 2026-10-27, sha256 đã đối chiếu). Dữ liệu JVN iPedia lấy từ fixture thật trong repo `vuls-data-update` (snapshot 2023-11-02, 13 bản ghi).
- Mapping IPA↔CWE và nội dung 11 mục IPA là **seed theo trí nhớ, chưa xác minh** (mọi dòng `seed_unverified`). Không dùng cho báo cáo chính thức trước khi đối chiếu với tài liệu gốc của IPA.
- Dữ liệu CWE là bản **4.14** (2024-02-29), không phải bản mới nhất.
- Code trong tài liệu 02 và 03 **đã chạy thật**. **Trivy và ZAP chưa được chạy scan thật**; schema đọc từ mã nguồn và dữ liệu mẫu của dự án. ZAP active scan chỉ dùng cho hệ thống bạn sở hữu hoặc được cấp phép.
- Giấy phép/điều khoản cần đọc trước khi phân phối lại: dữ liệu NVD và mirror, JVN iPedia, IPA, CWE, Semgrep Rules License v1.0.
