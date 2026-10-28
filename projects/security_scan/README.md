# security_scan — knowledge base IPA + NVD để Semgrep, ZAP, Trivy tra cứu

**Trạng thái:** nghiên cứu + thiết kế dữ liệu (tài liệu, template CSV, bản export KB; job cập nhật đã viết và chạy thử, chưa triển khai) · **Ngày:** 2026-10-28 (cập nhật lần 5: KB tối giản còn 6 + 3 cột, tài liệu ý nghĩa từng cột, dữ liệu IPA từ checklist bản 7)

## Bài toán

[Semgrep](https://semgrep.dev/) (SAST), [ZAP](https://www.zaproxy.org/) (DAST) và [Trivy](https://trivy.dev/) (thư viện, container, cấu hình, secret) cho ra kết quả có mã **CWE** và/hoặc **CVE**. **IPA** (tài liệu "安全なウェブサイトの作り方", cơ sở dữ liệu JVN iPedia) và **NVD** là tài liệu tham chiếu để các công cụ đó tra vào. Cần export dữ liệu tổng hợp IPA + NVD thành knowledge base (KB) không phụ thuộc công cụ, có template CSV để import, và có cách cập nhật liên tục.

## Kết quả chính

- **KB gồm hai file tối giản**: [`kb/kb_cwe.csv`](kb/kb_cwe.csv) (6 cột: CWE → mục IPA, tên mục tiếng Nhật, kiểu khớp, trạng thái duyệt; đầy đủ 1.375 CWE và mã giả) và `kb_cve.csv` (3 cột: CVE → CWE được chọn và nguồn của nó). Mỗi dữ kiện lưu một chỗ; trước đây là 23 và 35 cột, kết quả map vẫn y hệt. Ý nghĩa từng cột: [tài liệu 06 (tiếng Anh)](docs/06-kb-field-reference.md). Bản mẫu 23 CVE thật: [`kb/kb_cve.sample.csv`](kb/kb_cve.sample.csv); bản đầy đủ sinh bằng script mỗi ngày.
- **Công cụ chỉ đưa ra khóa để tra**: Semgrep và ZAP tra `kb_cwe` theo CWE; Trivy tra `kb_cve` theo CVE để lấy CWE rồi tra tiếp `kb_cwe`, khi KB không có CVE mới dùng CWE của Trivy.
- **CWE của một CVE khác nhau tùy nguồn và tùy thời điểm** (ví dụ Log4Shell: JVN = 20, CNA = 20/400/502, NVD = 917; jquery `CVE-2019-11358`: NVD năm 2021 ghi CWE-79, nay ghi CWE-1321), nên bộ build đọc CWE từng nguồn rồi chọn theo chính sách (mặc định NVD → CNA/ADP → JVN); KB lưu CWE được chọn và nguồn của nó. Năm 2025 chỉ 0,55% CVE có chênh lệch CWE làm đổi mục IPA ([tài liệu 04](docs/04-thuat-ngu-so-sanh-va-cach-map.md)).
- **Đo trên NVD thật năm 2025**: 58,8% CVE (không tính Rejected) rơi vào 11 mục IPA; chỉ 12,5% CVE có CWE do chính NVD gắn, còn lại đến từ CNA/ADP. Trên rule của Semgrep/ZAP, độ phủ chỉ khoảng 25%.
- **Dữ liệu IPA chính thức**: 11 mục và 47 đối sách (32 根本的解決, 15 保険的対策) đã nhập từ checklist Excel 安全なウェブサイトの作り方 改訂第7版 của IPA (người dùng cung cấp). Checklist không có mã CWE, nên bảng IPA↔CWE vẫn là seed.
- **Runbook tiếng Anh** ([tài liệu 05](docs/05-kb-build-runbook.md)): các bước đã làm để dựng KB (CVE + CWE) từ IPA và NVD, và cách tự dựng lại, cập nhật hằng ngày. Kèm script đồng bộ NVD/JVN có kiểm tra sha256, client NVD API, nhập checklist của IPA, kiểm tra trước khi phát hành. Dựng thử trên toàn bộ lịch sử NVD (415.469 CVE, mirror ngày 2026-10-28): 73 giây, RAM đỉnh 2,6 GB, `kb_cve.csv` 12 MB; 46,8% CVE (không tính Rejected) rơi vào một mục IPA.
- **Trivy và ZAP đều là mã nguồn mở** (Apache-2.0; `trivy-checks` MIT). ZAP gắn `cweid` cho mỗi alert; Trivy chỉ gắn `CweIDs` cho lỗ hổng thư viện.
- **Đính chính**: bản trước có `exports/ipa_map_all_tools.csv` lấy rule của công cụ đổ vào template, tức đi ngược chiều. File này đã được gỡ; dữ liệu phía công cụ chuyển sang `tool_side/`.

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| [`docs/03-kb-ipa-nvd-cho-cong-cu.md`](docs/03-kb-ipa-nvd-cho-cong-cu.md) | **Tài liệu chính:** nguồn NVD và JVN iPedia, thiết kế KB, template CSV, chính sách chọn CWE, cách công cụ tra cứu, số đo trên NVD thật, code dựng KB, cập nhật liên tục |
| [`docs/04-thuat-ngu-so-sanh-va-cach-map.md`](docs/04-thuat-ngu-so-sanh-va-cach-map.md) | Thuật ngữ (NVD, IPA, JVN, CVE, CWE, CAPEC, CPE, CVSS, KEV, GHSA, OSV, Semgrep, ZAP, Trivy…), bảng so sánh, Trivy tra KB thế nào, các cách map khi mã không khớp, cách so sánh nguồn, 6 sơ đồ Mermaid |
| [`docs/05-kb-build-runbook.md`](docs/05-kb-build-runbook.md) | **Tiếng Anh.** Các bước đã làm để dựng KB từ IPA và NVD; cách tự dựng lại từng bước và cập nhật hằng ngày; script đồng bộ, nhập checklist IPA, kiểm tra, nạp SQLite (đã chạy thử); số liệu tham chiếu; xử lý sự cố |
| [`docs/06-kb-field-reference.md`](docs/06-kb-field-reference.md) | **Tiếng Anh.** Ý nghĩa từng cột của `kb_cwe.csv` (6 cột) và `kb_cve.csv` (3 cột), các trạng thái tính lúc tra, cột đã bỏ và chỗ lấy lại, bảng IPA phía sau |
| [`kb/`](kb/) | Bản export KB IPA + NVD: `kb_cwe.csv` (đầy đủ, 6 cột), `kb_cve.sample.csv` (mẫu, 3 cột) |
| [`templates/`](templates/) | Bảng nguồn để dựng KB: 11 mục IPA và 47 đối sách (từ checklist bản 7 của IPA), mapping IPA↔CWE (seed), CWE, phiên bản nguồn |
| [`docs/01-nghien-cuu-ipa-cwe-semgrep.md`](docs/01-nghien-cuu-ipa-cwe-semgrep.md) | Nghiên cứu ban đầu: IPA, CWE, Semgrep |
| [`docs/02-mapping-semgrep-ipa-va-cap-nhat.md`](docs/02-mapping-semgrep-ipa-va-cap-nhat.md) | Phía công cụ: CWE trong output Semgrep/ZAP/Trivy, chuẩn hóa, đo độ phủ theo rule, sửa CWE sai của rule |
| [`tool_side/`](tool_side/) | Catalog rule Semgrep/ZAP và override CWE: phía công cụ, **không** thuộc KB |

## Giới hạn quan trọng (đọc trước khi dùng)

- Môi trường nghiên cứu **chặn** `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp`, `cwe.mitre.org`, `semgrep.dev`. Dữ liệu NVD lấy qua mirror [`fkie-cad/nvd-json-data-feeds`](https://github.com/fkie-cad/nvd-json-data-feeds) (snapshot 2026-10-27 và 2026-10-28, sha256 đã đối chiếu). Dữ liệu JVN iPedia lấy từ fixture thật trong repo `vuls-data-update` (snapshot 2023-11-02, 13 bản ghi).
- 11 mục IPA và 47 đối sách **đã đối chiếu với checklist Excel bản 7 của IPA**. Mapping IPA↔CWE vẫn là **seed theo trí nhớ, chưa xác minh** (mọi dòng `seed_unverified`, vì checklist không có mã CWE). Không dùng mapping này cho báo cáo chính thức trước khi đối chiếu.
- Dữ liệu CWE là bản **4.14** (2024-02-29), không phải bản mới nhất.
- Code trong tài liệu 02, 03 và 05 **đã chạy thật**; phần chỉ chạy được với server cục bộ (feed chính thức của NVD/JVN, NVD API) được ghi rõ trong tài liệu 05. **Trivy và ZAP chưa được chạy scan thật**; schema đọc từ mã nguồn và dữ liệu mẫu của dự án. ZAP active scan chỉ dùng cho hệ thống bạn sở hữu hoặc được cấp phép.
- Giấy phép/điều khoản cần đọc trước khi phân phối lại: dữ liệu NVD và mirror, JVN iPedia, IPA, CWE, Semgrep Rules License v1.0.
