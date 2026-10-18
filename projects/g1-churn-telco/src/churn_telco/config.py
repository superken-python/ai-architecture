"""Hằng số dùng chung: đường dẫn, mốc thời gian, giả định nghiệp vụ. Sửa một chỗ, mọi bước dùng theo.

Giả định nghiệp vụ (A1 — framing) do phòng CSKH và tài chính cung cấp; A8 phân tích độ nhạy của kết luận theo chúng.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # thư mục projects/g1-churn-telco
DATA = Path(os.getenv("CHURN_DATA", ROOT / "data"))
RAW = DATA / "raw"  # bảng thô như export từ hệ thống nguồn — không sửa
INTERIM = DATA / "interim"  # bảng đã làm sạch
PROCESSED = DATA / "processed"  # bảng feature + nhãn để học
MODELS = Path(os.getenv("CHURN_MODELS", ROOT / "models"))
EVAL_DIR = Path(os.getenv("CHURN_EVAL_DIR", ROOT / "eval"))  # manifest của bộ đánh giá đã đóng băng (có commit)
REPORTS = Path(os.getenv("CHURN_REPORTS", ROOT / "reports"))
# Biến môi trường CHURN_* cho phép test và lab chạy trên dữ liệu nhỏ ở thư mục tạm mà không đụng dữ liệu thật.

# ---------------------------------------------------------------- mốc thời gian
HISTORY_START = pd.Timestamp("2024-01-01")  # dữ liệu nguồn có từ ngày này
HISTORY_END = pd.Timestamp("2025-12-31")
EXPORT_DATE = pd.Timestamp("2026-01-05")  # ngày export CRM: cột "trạng thái hiện tại" phản ánh ngày này
HORIZON_DAYS = 30  # nhãn: khách gửi yêu cầu hủy trong 30 ngày sau ngày chấm điểm

# Ngày chấm điểm (snapshot) = ngày 1 mỗi tháng. Cần >= 6 tháng lịch sử để tính feature.
SNAPSHOTS = list(pd.date_range("2024-07-01", "2025-12-01", freq="MS"))
TRAIN_END = pd.Timestamp("2025-06-01")  # train: 2024-07 .. 2025-06
VALID_END = pd.Timestamp("2025-09-01")  # valid: 2025-07 .. 2025-09 (chọn model, ngưỡng)
# test (bộ đánh giá đóng băng): 2025-10 .. 2025-12 — chỉ dùng để báo cáo, không dùng để chọn gì

# ---------------------------------------------------------------- giả định nghiệp vụ
CALL_CAPACITY = 500  # đội giữ chân khách gọi được 500 khách mỗi tháng
CALL_COST = 25_000  # VND mỗi cuộc gọi (thời gian nhân viên + hạ tầng)
SAVE_RATE = 0.30  # gọi đúng khách sắp rời: 30% đồng ý ở lại (kết quả chiến dịch thử năm 2024)
OFFER_COST = 150_000  # VND ưu đãi tặng khách đồng ý ở lại
VALUE_MONTHS = 12  # một khách giữ được ở lại thêm trung bình 12 tháng
MARGIN = 0.45  # biên lợi nhuận gộp trên cước
SEED = 42
