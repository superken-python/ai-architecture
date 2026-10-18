"""Lý do cho từng khách (A6 · ML-04): SHAP → nhóm feature → câu tiếng Việt CSKH đọc hiểu + gợi ý hành động.

SHAP (TreeSHAP) chia log-odds của model cho từng feature: bias + Σ shap_j = log-odds của khách. LightGBM tính sẵn
TreeSHAP (`pred_contrib=True`) — đúng bằng thư viện shap (có test), nên API không phải cài shap/numba. Ba bước:
1. Gộp feature cùng ý nghĩa thành NHÓM LÝ DO (data_gb_m1, usage_ratio... → "dùng ít đi"): CSKH cần một lý do, không cần
   năm con số tương quan với nhau.
2. Chỉ lấy nhóm làm TĂNG rủi ro (tổng SHAP > 0) và bỏ nhóm "hồ sơ" (tỉnh, tuổi, kênh): đúng về thống kê nhưng không
   phải lý do để gọi và dễ thành phân biệt đối xử.
3. Diễn đạt bằng GIÁ TRỊ THẬT của khách ("mất mạng 420 phút tháng trước"), kèm việc nên làm.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from churn_telco.train import Bundle

Row = pd.Series


def _usage(r: Row) -> str:
    if r.usage_missing_m1:
        return "Không có số liệu dùng data tháng trước (thiết bị không gửi số liệu hoặc ngừng dùng)"
    return f"Tháng trước dùng {r.data_gb_m1:.0f} GB, bằng {r.usage_ratio:.0%} mức trung bình 3 tháng trước đó"


def _contract(r: Row) -> str:
    if r.contract_months == 0:
        return "Không có hợp đồng kỳ hạn — có thể rời mạng bất cứ lúc nào"
    when = "hôm nay" if r.days_to_contract_end == 0 else f"sau {r.days_to_contract_end:.0f} ngày"
    return f"Hợp đồng {r.contract_months:.0f} tháng hết hạn {when}"


def _network(r: Row) -> str:
    parts = [f"mất mạng {r.outage_m1:.0f} phút tháng trước"] if pd.notna(r.outage_m1) else []
    if r.network_tickets_60d:
        parts.append(f"{r.network_tickets_60d:.0f} lần báo lỗi mạng trong 60 ngày")
    return ("Chất lượng mạng: " + ", ".join(parts)) if parts else "Chất lượng mạng khu vực kém"


def _support(r: Row) -> str:
    parts = []
    if r.open_tickets:
        parts.append(f"còn {r.open_tickets:.0f} yêu cầu hỗ trợ chưa xử lý xong")
    if pd.notna(r.min_csat_90d) and r.min_csat_90d <= 3:
        parts.append(f"chấm hài lòng {r.min_csat_90d:.0f}/5")
    if r.tickets_30d:
        parts.append(f"{r.tickets_30d:.0f} lần liên hệ tổng đài trong 30 ngày")
    return ("Hỗ trợ: " + ", ".join(parts)) if parts else "Lâu không liên hệ tổng đài"


def _billing(r: Row) -> str:
    if r.unpaid_at_t:
        return f"Đang nợ {r.unpaid_at_t:.0f} hoá đơn quá hạn"
    if r.late_or_unpaid_90d:
        return f"Trả cước trễ {r.late_or_unpaid_90d:.0f} kỳ trong 90 ngày (trễ nhất {r.max_days_late_90d:.0f} ngày)"
    return "Thanh toán thủ công, không tự động trừ tiền"


def _vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " đ"


def _price(r: Row) -> str:
    if r.fee_change_90d > 0:
        return f"Cước tăng {r.fee_change_90d:.0%} trong 90 ngày, hiện {_vnd(r.monthly_fee)}/tháng"
    return f"Gói {r.plan_code}, cước {_vnd(r.monthly_fee)}/tháng"


def _tenure(r: Row) -> str:
    return f"Khách mới — vào mạng {r.tenure_days:.0f} ngày" if r.tenure_days < 365 else "Thời gian dùng dịch vụ"


def _bundle(r: Row) -> str:
    if not (r.has_tv or r.has_mobile):
        return "Chỉ dùng internet, không có gói kèm TV/di động"
    return "Cấu hình gói dịch vụ"


def _promo(r: Row) -> str:
    return f"Đối thủ đang khuyến mãi mạnh tại {r.province}"


@dataclass(frozen=True)
class Group:
    label: str  # tên nhóm lý do cho người đọc
    features: list[str]
    phrase: Callable[[Row], str] | None  # câu lý do từ giá trị thật của khách; None = không bao giờ là lý do
    action: str  # việc CSKH nên làm


GROUPS = {
    "usage": Group(
        "Dùng ít đi",
        ["data_gb_m1", "data_gb_m2_m4", "usage_ratio", "usage_missing_m1", "tv_hours_m1"],
        _usage,
        "Hỏi nhu cầu thực tế, tư vấn gói phù hợp hơn",
    ),
    "contract": Group(
        "Hợp đồng", ["contract_months", "days_to_contract_end"], _contract, "Mời gia hạn/ký hợp đồng kỳ hạn kèm ưu đãi"
    ),
    "network": Group(
        "Chất lượng mạng",
        ["outage_m1", "outage_avg_3m", "network_tickets_60d"],
        _network,
        "Kỹ thuật kiểm tra đường truyền trước khi gọi; xin lỗi và bù cước",
    ),
    "support": Group(
        "Hỗ trợ khách hàng",
        ["open_tickets", "min_csat_90d", "tickets_30d", "days_since_last_ticket", "billing_tickets_90d"],
        _support,
        "Ưu tiên đóng yêu cầu đang mở, gọi lại xác nhận",
    ),
    "billing": Group(
        "Thanh toán",
        ["late_or_unpaid_90d", "unpaid_at_t", "max_days_late_90d", "refunds_90d", "autopay", "payment_method"],
        _billing,
        "Nhắc lịch thanh toán, mời đăng ký tự động trừ tiền",
    ),
    "price": Group(
        "Giá cước", ["monthly_fee", "fee_change_90d", "plan_code", "speed_mbps"], _price, "Tư vấn gói tiết kiệm hơn"
    ),
    "tenure": Group("Khách mới", ["tenure_days"], _tenure, "Gọi chăm sóc khách mới, hướng dẫn sử dụng"),
    "bundle": Group("Gói dịch vụ", ["has_tv", "has_mobile"], _bundle, "Giới thiệu gói kèm TV/di động"),
    "promo": Group("Đối thủ khuyến mãi", ["competitor_promo_30d"], _promo, "Đưa ưu đãi giữ chân cạnh tranh"),
    "profile": Group("Hồ sơ khách", ["segment", "channel", "province", "age"], None, ""),  # không bao giờ là lý do
}


def shap_values(bundle: Bundle, df: pd.DataFrame) -> pd.DataFrame:
    """SHAP theo log-odds, một cột mỗi feature (TreeSHAP chính xác, không xấp xỉ); cột cuối của pred_contrib là bias."""
    contrib = bundle.booster.predict(
        df[bundle.features], num_iteration=bundle.meta["best_iteration"], pred_contrib=True
    )
    return pd.DataFrame(contrib[:, :-1], index=df.index, columns=bundle.features)


def group_shap(values: pd.DataFrame) -> pd.DataFrame:
    """Tổng SHAP theo nhóm lý do (chỉ nhóm có feature trong model)."""
    out = {}
    for name, group in GROUPS.items():
        present = [c for c in group.features if c in values.columns]
        if present:
            out[name] = values[present].sum(axis=1)
    return pd.DataFrame(out)


def reasons(bundle: Bundle, df: pd.DataFrame, top: int = 3, min_shap: float = 0.05) -> pd.DataFrame:
    """Mỗi khách: tối đa `top` lý do làm tăng rủi ro (SHAP nhóm ≥ min_shap), mạnh nhất trước, kèm việc nên làm."""
    grouped = group_shap(shap_values(bundle, df)).drop(columns="profile", errors="ignore")
    rows = []
    for idx, contrib in grouped.iterrows():
        record = df.loc[idx]
        best = contrib[contrib >= min_shap].sort_values(ascending=False).head(top)
        row: dict = {}
        for i, (name, value) in enumerate(best.items(), start=1):
            group = GROUPS[name]
            row |= {
                f"reason_{i}": group.phrase(record),
                f"action_{i}": group.action,
                f"shap_{i}": round(float(value), 3),
            }
        rows.append(row)
    return pd.DataFrame(rows, index=df.index)
