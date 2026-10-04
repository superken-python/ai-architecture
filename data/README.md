# data/

Thư mục chứa dữ liệu luyện tập **trên máy bạn**. Mọi thứ ở đây (trừ file này) đều bị `.gitignore` bỏ qua —
dữ liệu không bao giờ vào Git.

Quy ước:

```
data/
├── raw/<tên-bộ-dữ-liệu>/        # dữ liệu gốc tải về, không sửa
├── interim/<tên-bộ-dữ-liệu>/    # dữ liệu trung gian
└── processed/<tên-bộ-dữ-liệu>/  # dữ liệu sạch dùng để huấn luyện/đánh giá
```

Danh sách bộ dữ liệu và cách tải: [docs/00-setup/05-du-lieu-luyen-tap.md](../docs/00-setup/05-du-lieu-luyen-tap.md).
Dữ liệu thật của công ty: chỉ dùng khi được phép, ẩn danh hóa trước, và không bao giờ đưa lên dịch vụ ngoài
khi chưa có chấp thuận (xem kỹ năng OPS-08).
