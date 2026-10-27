# security_scan — nối kết quả Semgrep với tri thức IPA (Nhật Bản)

**Trạng thái:** nghiên cứu + thiết kế dữ liệu (chỉ tài liệu và CSV mẫu, chưa có code vận hành) · **Ngày:** 2026-10-27

## Bài toán

Quét mã nguồn bằng [Semgrep](https://semgrep.dev/), rồi đọc kết quả theo cách phân loại của **IPA** ("安全なウェブサイトの作り方" và các tài liệu liên quan) thông qua mã **CWE**. Cần: (1) hiểu mối liên hệ output Semgrep ↔ IPA, (2) cách đưa tri thức IPA vào dữ liệu có cấu trúc, (3) template CSV để import, (4) cách luôn cập nhật khi IPA/CWE/rule thay đổi.

## Kết quả chính

- Chuỗi mapping: `finding → rule → CWE → mục IPA → đối sách IPA`.
- Bản seed 11 mục IPA phủ **khoảng 1/4** cặp rule–CWE của Semgrep (22,6% trực tiếp + 2,2% qua cây CWE); **75,2% nằm ngoài** → phải có trạng thái `OUT_OF_IPA_SCOPE`.
- Tag CWE của Semgrep có chỗ sai → cần bảng override có người duyệt.
- Đã chạy thật: scan một file Flask mẫu (20 finding) → nạp 8 CSV mẫu vào SQLite → báo cáo gộp 4 dòng theo mục IPA + 9 dòng ngoài phạm vi.

## Đọc theo thứ tự

| File | Nội dung |
|---|---|
| [`docs/01-nghien-cuu-ipa-cwe-semgrep.md`](docs/01-nghien-cuu-ipa-cwe-semgrep.md) | IPA, CWE, Semgrep: là gì, output trông ra sao, những bẫy khi lấy CWE, số liệu bộ rule |
| [`docs/02-mapping-semgrep-ipa-va-cap-nhat.md`](docs/02-mapping-semgrep-ipa-va-cap-nhat.md) | **Tài liệu chính:** quy tắc mapping, đo độ phủ, ví dụ chạy thật, cách export IPA knowledge base, template CSV, code import, quy trình cập nhật liên tục |
| [`templates/`](templates/) | 8 file CSV mẫu (IPA, CWE, mapping, catalog rule Semgrep, override, phiên bản nguồn) |

## Giới hạn quan trọng (đọc trước khi dùng)

- Môi trường nghiên cứu **chặn** `www.ipa.go.jp`, `cwe.mitre.org`, `semgrep.dev` (403 từ proxy). Nội dung IPA **chưa được đọc trực tiếp**; mọi dữ liệu IPA trong `templates/` là seed theo trí nhớ, gắn `seed_unverified`. Cần người có quyền truy cập đối chiếu với tài liệu gốc.
- Dữ liệu CWE trong mẫu là bản **4.14** (2024-02-29) lấy từ gói PyPI `cwe2`, không phải bản mới nhất.
- Phần Semgrep (rule, scan, số liệu) và code mẫu trong tài liệu 02 **đã chạy thật**.
- Giấy phép cần đọc trước khi phân phối lại: Semgrep Rules License v1.0, điều khoản sử dụng CWE, điều khoản của IPA.
