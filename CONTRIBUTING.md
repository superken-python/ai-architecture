# Đóng góp và mở rộng dự án

## Quy ước chung

- **Ngôn ngữ:** nội dung tiếng Việt có dấu; **tên file/thư mục** dùng chữ thường không dấu, nối bằng `-`
  (ví dụ `03-tiet-kiem-token-chinh-xac.md`) để tránh lỗi đường dẫn trên mọi hệ điều hành.
- **Mã kỹ năng** (`PY-01`, `LLM-03`...), **mã nhóm** (`G1`–`G8`) và **mã tổ hợp** (`CMB-01`...) là định danh ổn
  định — không đổi, không tái sử dụng sau khi đã công bố; tài liệu, lab và dự án đều tham chiếu theo mã.
- **Một nguồn dữ liệu duy nhất:** mọi thông tin về nhóm/kỹ năng/tổ hợp nằm trong `catalog/*.yaml`. Không sửa tay
  các file trong `docs/02-skill-map/generated/` — chúng được sinh lại và CI sẽ báo lỗi nếu lệch.
- **Theo dõi công việc:** việc sắp làm ở [CHECKLIST.md](CHECKLIST.md), việc đã làm ở [HISTORY.md](HISTORY.md) — cập nhật cả hai trong cùng PR.
- **Nhánh & PR:** không commit thẳng vào `main`; mỗi thay đổi đi qua PR, điền mẫu PR, `make check` phải xanh.

## Các tác vụ thường gặp

### Thêm hoặc sửa một kỹ năng

1. Chép mẫu [templates/skill.yaml](templates/skill.yaml) vào `catalog/skills.yaml`, đặt cạnh các kỹ năng cùng mảng.
2. Viết `levels` bằng **động từ, kiểm chứng được** ("đo được Recall@K của tầng truy xuất"), không dùng "hiểu về...".
3. Khai báo `used_by` trung thực: **core** chỉ khi thiếu kỹ năng này thì không làm được nhóm đó ở mức trung cấp.
4. `make catalog && make check`.

### Thêm một nhóm bài toán mới (ví dụ Nhóm 9)

1. Thêm nhóm vào `catalog/problems.yaml` (id `G9`, `slug`, đủ các trường như nhóm khác) và xếp vào một **họ**
   trong `families` (hoặc tạo họ mới).
2. Khai báo `skill_areas` (ma trận mức cần theo mảng) cho nhóm mới.
3. Cập nhật `used_by` của các kỹ năng liên quan; thêm kỹ năng chuyên biệt nếu cần.
4. `make catalog` — bộ kiểm tra sẽ báo **thiếu độ phủ** nếu một mảng Cốt lõi của nhóm mới chưa có kỹ năng Cốt lõi.
   Tầng của mọi kỹ năng (nền tảng/cầu nối/...) được tính lại tự động.

### Thêm một mảng kỹ năng mới

Thêm vào `domains` trong `catalog/skills.yaml` (mã viết hoa, ngắn). Id kỹ năng của mảng phải bắt đầu bằng mã đó.

### Thêm tổ hợp, lab, dự án

- Tổ hợp: [docs/02-skill-map/02-ky-nang-ket-hop.md](docs/02-skill-map/02-ky-nang-ket-hop.md#thêm-một-tổ-hợp-mới).
- Lab: [labs/README.md](labs/README.md). Dự án: [projects/README.md](projects/README.md).

### Thêm thư viện Python

`uv add --group <nhóm> <gói>` — commit cả `pyproject.toml` và `uv.lock`. Gói nặng/đặc thù phần cứng thì để trong
môi trường riêng của lab/dự án, không đưa vào lockfile chung.

### Thêm một giai đoạn tài liệu mới

Tạo `docs/0N-<ten-giai-doan>/README.md`, rồi thêm một dòng vào bảng giai đoạn trong [README.md](README.md).

## Kiểm tra trước khi mở PR

```bash
make format   # tự sửa style
make check    # lint + test + catalog-check + kiểm tra link tài liệu
```
