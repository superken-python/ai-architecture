"""Hệ thống nguồn GIẢ LẬP của nhà mạng Sóng Xanh (tên hư cấu): sinh các bảng thô như khi export từ CRM, billing,
helpdesk và kho dữ liệu đo mạng.

Vì sao mô phỏng thay vì dùng bộ Telco công khai: bộ công khai là MỘT bảng đã phẳng hoá tại một thời điểm, không có
dấu thời gian — không học được cách dựng bảng học từ dữ liệu vận hành, feature as-of và rò rỉ dữ liệu (A4). Ở đây
ta có đủ bảng thô với lỗi thường gặp, và biết cơ chế sinh churn để đối chiếu với điều model học được (A6).

Cơ chế churn (ẩn với "người làm dự án" — chỉ mở ra ở A6): mỗi tháng, khách đang hoạt động có xác suất nảy ý định
rời mạng theo một hàm logistic của: loại hợp đồng, hợp đồng sắp hết hạn, khách mới, tăng giá, sự cố mạng, ticket
mạng, ticket chưa xử lý, đánh giá CSAT thấp, trả cước trễ, tự động trừ tiền, gói kèm TV/di động, khuyến mãi của đối
thủ theo tỉnh (dữ liệu marketing — không có trong bảng nguồn ban đầu) và một yếu tố cá nhân không quan sát được.
Khách có ý định thì tháng đó dùng ít data hẳn (dấu hiệu sớm), tháng sau gửi yêu cầu hủy. Thêm churn ngẫu nhiên
(chuyển nhà) và churn do nợ cước (2 hoá đơn liên tiếp không trả).

    uv run python -m churn_telco.simulate      # sinh vào data/raw/ (+ data/marketing/), cố định theo seed
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from churn_telco import config

PLANS = pd.DataFrame(
    {
        "plan_code": ["SX50", "SX150", "SX300", "SX150TV", "SX300TV", "COMBO"],
        "plan_name": [
            "Sóng Xanh 50",
            "Sóng Xanh 150",
            "Sóng Xanh 300",
            "Sóng Xanh 150 + TV",
            "Sóng Xanh 300 + TV",
            "Combo 300 + TV + di động",
        ],
        "speed_mbps": [50, 150, 300, 150, 300, 300],
        "has_tv": [False, False, False, True, True, True],
        "has_mobile": [False, False, False, False, False, True],
    }
)
LIST_PRICE = np.array([180_000, 245_000, 320_000, 290_000, 365_000, 450_000])
MEAN_GB = np.array([110.0, 220.0, 340.0, 230.0, 350.0, 360.0])
PRICE_HIKE_DATE = np.datetime64("2025-04-01")
PRICE_HIKE = {0: 198_000, 1: 269_000}  # SX50, SX150 tăng 10% từ 2025-04-01

PROVINCES = [
    "TP. Hồ Chí Minh",
    "Hà Nội",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Bình Dương",
    "Đồng Nai",
    "Khánh Hòa",
    "Thừa Thiên Huế",
    "Nghệ An",
]
PROVINCE_WEIGHTS = np.array([0.30, 0.27, 0.07, 0.06, 0.05, 0.07, 0.05, 0.04, 0.04, 0.05])
PROVINCE_VARIANTS = {  # cách nhân viên các chi nhánh gõ tên tỉnh trong CRM
    "TP. Hồ Chí Minh": ["TP.HCM", "Hồ Chí Minh", "TP HCM", "Ho Chi Minh"],
    "Hà Nội": ["Ha Noi", "HN", "TP. Hà Nội"],
    "Đà Nẵng": ["Da Nang", "TP. Đà Nẵng"],
    "Hải Phòng": ["Hai Phong"],
    "Cần Thơ": ["Can Tho"],
    "Bình Dương": ["Binh Duong"],
    "Đồng Nai": ["Dong Nai"],
    "Khánh Hòa": ["Khánh Hoà", "Khanh Hoa"],
    "Thừa Thiên Huế": ["Huế", "Thua Thien Hue"],
    "Nghệ An": ["Nghe An"],
}
BASE_OUTAGE = np.array([35, 30, 40, 35, 50, 45, 45, 55, 55, 60], dtype=float)  # phút mất mạng / tháng
STORM_PROVINCES = [2, 7, 8, 9]  # mùa bão tháng 10–11: Đà Nẵng, Khánh Hòa, Huế, Nghệ An
COMPETITOR_PROMOS = [  # lịch khuyến mãi của đối thủ — phòng marketing có, bảng nguồn ban đầu không có
    ("Hà Nội", "2024-10-01", "2024-11-30", "NetNhanh", "Giảm 50% cước 6 tháng cho khách chuyển mạng"),
    ("TP. Hồ Chí Minh", "2025-06-15", "2025-09-30", "NetNhanh", "Miễn phí lắp đặt + 3 tháng cước"),
    ("Bình Dương", "2025-06-15", "2025-09-30", "NetNhanh", "Miễn phí lắp đặt + 3 tháng cước"),
]
CHANNELS = np.array(["Cửa hàng", "Online", "Đại lý"])
PAYMENTS = np.array(["Tiền mặt tại điểm", "Chuyển khoản", "Ví điện tử", "Tự động trừ thẻ"])
TICKET_VARIANTS = {  # helpdesk cho gõ tay loại ticket ở vài chi nhánh
    "Mất kết nối": ["Mất kết nối", "mất kết nối", "MẤT KẾT NỐI", "Mất kết nối "],
    "Mạng chậm": ["Mạng chậm", "mạng chậm", "Mang cham"],
    "Cước phí": ["Cước phí", "cước phí", "Cuoc phi"],
    "Chuyển địa điểm": ["Chuyển địa điểm"],
    "Yêu cầu hủy": ["Yêu cầu hủy", "Yêu cầu huỷ", "yêu cầu hủy"],
    "Khác": ["Khác", "khác"],
}
FAMILY = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô"]
MIDDLE = ["Văn", "Thị", "Đức", "Minh", "Ngọc", "Thanh", "Hữu", "Quốc", "Thu", "Hoàng"]
GIVEN = ["An", "Bình", "Châu", "Dũng", "Hà", "Hải", "Hạnh", "Hiếu", "Hoa", "Hùng", "Hương", "Khánh", "Lan", "Linh"]
GIVEN += ["Long", "Mai", "Nam", "Nga", "Phong", "Phương", "Quang", "Sơn", "Tâm", "Thảo", "Trang", "Trung", "Tuấn"]


@dataclass(frozen=True)
class SimConfig:
    n_initial: int = 18_000  # khách đang hoạt động ngày 2024-01-01
    new_per_month: int = 480  # khách mới mỗi tháng
    months: int = 24  # 2024-01 .. 2025-12
    seed: int = config.SEED
    intercept: float = -5.3  # chỉnh để churn tháng khoảng 2%


def _months(cfg: SimConfig) -> np.ndarray:
    return np.array(pd.date_range(config.HISTORY_START, periods=cfg.months, freq="MS"), dtype="datetime64[D]")


def _promo_active(province: np.ndarray, month: np.datetime64) -> np.ndarray:
    active = np.zeros(len(province), dtype=bool)
    mid = month + np.timedelta64(14, "D")
    for name, start, end, *_ in COMPETITOR_PROMOS:
        if np.datetime64(start) <= mid <= np.datetime64(end):
            active |= province == PROVINCES.index(name)
    return active


class _Book:
    """Gom bản ghi của từng tháng rồi nối lại một lần (nhanh hơn nối DataFrame trong vòng lặp)."""

    def __init__(self) -> None:
        self.parts: dict[str, list[dict[str, np.ndarray]]] = {}

    def add(self, table: str, **cols: np.ndarray) -> None:
        self.parts.setdefault(table, []).append(cols)

    def frame(self, table: str) -> pd.DataFrame:
        parts = self.parts.get(table, [])
        if not parts:
            return pd.DataFrame()
        return pd.DataFrame({k: np.concatenate([p[k] for p in parts]) for k in parts[0]})


def simulate(cfg: SimConfig | None = None) -> dict[str, pd.DataFrame]:
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(cfg.seed)
    months = _months(cfg)
    n = cfg.n_initial + cfg.new_per_month * cfg.months
    book = _Book()

    # ------------------------------------------------------------ thuộc tính khách (cố định)
    signup = np.empty(n, dtype="datetime64[D]")
    first = months[0]
    days_before = (rng.beta(1.3, 2.2, cfg.n_initial) * 6 * 365).astype(int) + 1  # khách cũ: vào mạng 1 ngày–6 năm trước
    signup[: cfg.n_initial] = first - days_before.astype("timedelta64[D]")
    for m, month in enumerate(months):
        lo = cfg.n_initial + m * cfg.new_per_month
        signup[lo : lo + cfg.new_per_month] = month + rng.integers(0, 28, cfg.new_per_month).astype("timedelta64[D]")
    province = rng.choice(len(PROVINCES), n, p=PROVINCE_WEIGHTS)
    sme = rng.random(n) < 0.10
    channel = rng.choice(3, n, p=[0.45, 0.25, 0.30])
    birth_year = np.clip(rng.normal(1983, 11, n).round(), 1950, 2004).astype(int)
    plan = np.where(
        sme,
        rng.choice(6, n, p=[0.05, 0.15, 0.35, 0.05, 0.15, 0.25]),
        rng.choice(6, n, p=[0.22, 0.30, 0.13, 0.15, 0.10, 0.10]),
    )
    contract = np.where(
        sme, rng.choice([0, 12, 24], n, p=[0.2, 0.3, 0.5]), rng.choice([0, 12, 24], n, p=[0.48, 0.34, 0.18])
    )
    payment = rng.choice(4, n, p=[0.20, 0.30, 0.25, 0.25])
    autopay = payment == 3
    fin_stress = rng.beta(2, 8, n)  # khó khăn tài chính → trả cước trễ
    usage_factor = rng.lognormal(0, 0.4, n)
    bad_line = rng.random(n) < 0.05  # đường dây kém → mất mạng nhiều hơn hẳn
    hetero = rng.normal(0, 0.45, n)  # yếu tố cá nhân không quan sát được

    # hợp đồng hiện tại: ngày bắt đầu, ngày hết hạn
    start = signup.copy()
    end = np.full(n, np.datetime64("NaT", "D"), dtype="datetime64[D]")
    has_c = contract > 0
    end[has_c] = signup[has_c] + (contract[has_c] * 30).astype("timedelta64[D]")
    # khách cũ có hợp đồng đã gia hạn nhiều lần: kỳ hiện tại kết thúc rải đều trong vài tháng tới
    old = np.arange(n) < cfg.n_initial
    renew_old = old & has_c & (end < first)
    left = rng.integers(1, (contract[renew_old] * 30) + 1)
    end[renew_old] = first + left.astype("timedelta64[D]")
    start[renew_old] = end[renew_old] - (contract[renew_old] * 30).astype("timedelta64[D]")
    sub_id = np.zeros(n, dtype=int)  # số thứ tự kỳ thuê bao của từng khách

    def open_sub(idx: np.ndarray, when: np.ndarray) -> None:
        sub_id[idx] += 1
        book.add(
            "subscriptions",
            subscription_id=np.array([f"SUB{i:06d}-{s}" for i, s in zip(idx, sub_id[idx], strict=True)]),
            customer_id=idx.copy(),
            plan=plan[idx].copy(),
            contract_months=contract[idx].copy(),
            start_date=when.copy(),
            payment=payment[idx].copy(),
        )

    exists = np.zeros(n, dtype=bool)
    active = np.zeros(n, dtype=bool)
    intent = np.zeros(n, dtype=bool)  # có ý định rời mạng (gửi yêu cầu hủy tháng sau)
    reason_code = np.zeros(n, dtype=int)
    unpaid_streak = np.zeros(n, dtype=int)
    late_hist = np.zeros((n, 3), dtype=int)  # trả trễ 3 tháng gần nhất
    net_tickets_hist = np.zeros((n, 2), dtype=int)
    low_csat_hist = np.zeros((n, 3), dtype=bool)
    open_ticket_until = np.full(n, np.datetime64("1970-01-01"), dtype="datetime64[D]")
    sub_closed: list[tuple[np.ndarray, np.ndarray]] = []
    cancel_effective = np.full(n, np.datetime64("NaT", "D"), dtype="datetime64[D]")

    for m, month in enumerate(months):
        next_month = month + np.timedelta64(32, "D")
        next_month = next_month.astype("datetime64[M]").astype("datetime64[D]")
        days_in = int((next_month - month).astype(int))

        # khách mới vào mạng trong tháng
        joining = (~exists) & (signup < next_month)
        exists |= joining
        active |= joining
        new_idx = np.flatnonzero(joining)
        if m == 0:
            open_sub(new_idx, start[new_idx])
        else:
            open_sub(new_idx, signup[new_idx])

        # yêu cầu hủy (ý định từ tháng trước) → ghi nhận trong tháng này
        req = np.flatnonzero(intent & active)
        if len(req):
            req_day = month + rng.integers(0, days_in - 2, len(req)).astype("timedelta64[D]")
            effective = req_day + rng.integers(3, 15, len(req)).astype("timedelta64[D]")
            revoked = (rng.random(len(req)) < 0.04) & (reason_code[req] != 5)  # khách đổi ý trong 7 ngày
            book.add(
                "cancellations",
                customer_id=req,
                request_date=req_day,
                effective_date=np.where(revoked, np.datetime64("NaT", "D"), effective),
                reason=reason_code[req].copy(),
                revoked=revoked,
            )
            # 70% khách gọi tổng đài hỏi thủ tục hủy 0–5 ngày trước khi gửi yêu cầu chính thức
            asks = rng.random(len(req)) < 0.70
            ask_idx = req[asks]
            ask_at = req_day[asks] - rng.integers(0, 6, asks.sum()).astype("timedelta64[D]")
            book.add(
                "tickets",
                customer_id=ask_idx,
                created_at=ask_at,
                category=np.full(len(ask_idx), "Yêu cầu hủy", dtype=object),
                resolved_days=np.zeros(len(ask_idx)),
                csat=np.full(len(ask_idx), np.nan),
            )
            gone = req[~revoked]
            cancel_effective[gone] = effective[~revoked]
            active[gone] = False
            sub_closed.append((gone, effective[~revoked]))
            intent[req] = False
        act = np.flatnonzero(active)

        # ---------------------------------------------------- giá, hợp đồng
        fee = LIST_PRICE[plan[act]].astype(float)
        if month >= PRICE_HIKE_DATE:
            for p, new_price in PRICE_HIKE.items():
                fee[plan[act] == p] = new_price
        hike_recent = (month >= PRICE_HIKE_DATE) & (
            month < PRICE_HIKE_DATE + np.timedelta64(61, "D")
        )  # sốc giá 2 tháng
        price_hike = np.isin(plan[act], list(PRICE_HIKE)) & hike_recent
        c_end = end[act]
        ends_next = (contract[act] > 0) & (c_end >= next_month) & (c_end < next_month + np.timedelta64(31, "D"))
        ended = (contract[act] > 0) & (c_end < next_month)
        if ended.any():  # hết hạn trong tháng: 50% gia hạn cùng kỳ, còn lại chuyển sang không kỳ hạn
            idx = act[ended]
            renew = rng.random(len(idx)) < 0.5
            contract[idx[~renew]] = 0
            new_start = end[idx]
            end[idx[renew]] = new_start[renew] + (contract[idx[renew]] * 30).astype("timedelta64[D]")
            end[idx[~renew]] = np.datetime64("NaT", "D")
            sub_closed.append((idx, new_start))
            open_sub(idx, new_start)
        upgrade = (rng.random(len(act)) < 0.006) & (plan[act] < 5) & ~ended  # không đổi gói đúng tháng gia hạn
        if upgrade.any():
            idx = act[upgrade]
            when = month + rng.integers(1, days_in - 1, len(idx)).astype("timedelta64[D]")
            plan[idx] = np.minimum(plan[idx] + 1, 5)
            sub_closed.append((idx, when))
            open_sub(idx, when)

        # ---------------------------------------------------- mạng: sự cố theo tỉnh + đường dây từng khách
        prov_out = BASE_OUTAGE.copy()
        if month.astype(object).month in (10, 11):
            prov_out[STORM_PROVINCES] += 180
        incident = rng.random(len(PROVINCES)) < 0.08
        prov_out[incident] += 120
        outage = prov_out[province[act]] * rng.gamma(1.2, 1 / 1.2, len(act)) * np.where(bad_line[act], 3.0, 1.0)

        # ---------------------------------------------------- ticket
        lam_net = 0.02 + 0.0025 * outage
        n_net = np.minimum(rng.poisson(lam_net), 4)
        n_bill = rng.poisson(0.02 + 0.10 * price_hike)
        n_move = rng.poisson(0.008, len(act))
        n_other = rng.poisson(0.015, len(act))
        for counts, cats in [
            (n_net, ["Mất kết nối", "Mạng chậm"]),
            (n_bill, ["Cước phí"]),
            (n_move, ["Chuyển địa điểm"]),
            (n_other, ["Khác"]),
        ]:
            who = np.repeat(act, counts)
            if not len(who):
                continue
            created = month + rng.integers(0, days_in, len(who)).astype("timedelta64[D]")
            resolved_days = rng.exponential(1.5, len(who))
            never = rng.random(len(who)) < 0.06
            resolved_days[never] = np.nan
            bad = np.repeat(outage, counts) > 150
            score = 4.3 - 1.4 * (never | (resolved_days > 3)) - 0.8 * bad + rng.normal(0, 0.6, len(who))
            csat = np.where(rng.random(len(who)) < 0.55, np.clip(score.round(), 1, 5), np.nan)
            book.add(
                "tickets",
                customer_id=who,
                created_at=created,
                category=rng.choice(np.array(cats, dtype=object), len(who)),
                resolved_days=resolved_days,
                csat=csat,
            )
            if cats[0] == "Mất kết nối":
                np.add.at(net_tickets_hist[:, 0], who, 1)
            unresolved = np.where(np.isnan(resolved_days), 10_000, resolved_days).astype(int)
            until = created + np.minimum(unresolved, 10_000).astype("timedelta64[D]")
            np.maximum.at(open_ticket_until, who, until)
            low = np.zeros(n, dtype=bool)
            low[who[csat <= 2]] = True
            low_csat_hist[:, 0] |= low

        # ---------------------------------------------------- hoá đơn
        due = month + np.timedelta64(14, "D")
        late_p = 0.04 + 0.55 * fin_stress[act]
        unpaid_p = 0.004 + 0.10 * fin_stress[act] ** 2
        u = rng.random(len(act))
        unpaid = (u < unpaid_p) & ~autopay[act]
        late = (~unpaid) & (u < unpaid_p + late_p) & ~autopay[act]
        paid = np.where(
            autopay[act],
            month + rng.integers(0, 3, len(act)).astype("timedelta64[D]"),
            np.where(
                late,
                due + rng.integers(1, 26, len(act)).astype("timedelta64[D]"),
                month + rng.integers(1, 15, len(act)).astype("timedelta64[D]"),
            ),
        )
        paid = np.where(unpaid, np.datetime64("NaT", "D"), paid)
        book.add("invoices", customer_id=act, billing_month=np.full(len(act), month), amount=fee, paid_date=paid)
        late_now = np.zeros(n, dtype=int)
        late_now[act[late | unpaid]] = 1
        unpaid_streak[act] = np.where(unpaid, unpaid_streak[act] + 1, 0)

        # ---------------------------------------------------- sử dụng (data) — giảm hẳn khi khách đã có ý định rời
        tenure_days = (month - signup[act]).astype(int)
        logit = (
            cfg.intercept
            + 1.05 * (contract[act] == 0)
            - 0.45 * (contract[act] == 24)
            + 2.20 * ends_next  # hết hợp đồng: thời điểm khách tự do quyết định ở lại hay đi
            + 0.55 * (tenure_days < 120)
            - 0.35 * (tenure_days > 3 * 365)
            + 0.75 * price_hike
            + np.minimum(1.1, 0.006 * np.maximum(0, outage - 60))
            + 0.40 * np.minimum(3, net_tickets_hist[act].sum(axis=1))
            + 0.55 * (open_ticket_until[act] >= next_month)
            + 0.60 * ((outage > 150) & (open_ticket_until[act] >= next_month))  # sự cố lớn mà chưa xử lý xong
            + 0.45 * low_csat_hist[act].any(axis=1)
            + 0.30 * np.minimum(3, late_hist[act].sum(axis=1) + late_now[act])
            - 0.45 * autopay[act]
            - 0.30 * PLANS["has_tv"].to_numpy()[plan[act]]
            - 0.45 * PLANS["has_mobile"].to_numpy()[plan[act]]
            + 0.65 * _promo_active(province[act], month)
            - 0.20 * sme[act]
            + hetero[act]
        )
        p_leave = 1 / (1 + np.exp(-logit))
        leave = rng.random(len(act)) < p_leave
        move_away = rng.random(len(act)) < 0.0035  # chuyển nhà/đi xa: không có dấu hiệu trước
        debt = unpaid_streak[act] >= 2  # nợ 2 kỳ liên tiếp → cắt dịch vụ
        new_intent = (leave | move_away | debt) & (signup[act] < month)
        reasons = np.select(
            [
                debt,
                move_away,
                _promo_active(province[act], month),
                ends_next,
                price_hike,
                outage > 150,
                net_tickets_hist[act].sum(axis=1) > 0,
            ],
            [5, 4, 3, 2, 1, 0, 0],
            default=6,
        )
        reason_code[act[new_intent]] = reasons[new_intent]
        intent[act[new_intent]] = True

        gb = MEAN_GB[plan[act]] * usage_factor[act] * rng.lognormal(0, 0.15, len(act))
        away = rng.random(len(act)) < 0.04  # đi công tác/về quê cả tháng: dùng ít hẳn nhưng không định rời mạng
        gb[away] *= rng.uniform(0.3, 0.8, away.sum())
        # khách bị khuyến mãi của đối thủ lôi kéo thường chuyển mạng ngay, ít khi dùng ít đi trước
        p_drop = np.where(reasons == 3, 0.15, 0.50)
        drop = new_intent & ~move_away & ~debt & (rng.random(len(act)) < p_drop)
        gb[drop] *= rng.uniform(0.3, 0.75, drop.sum())
        tv = np.where(
            PLANS["has_tv"].to_numpy()[plan[act]], 55 * usage_factor[act] * rng.lognormal(0, 0.3, len(act)), np.nan
        )
        keep = rng.random(len(act)) >= 0.015  # 1,5% tháng mất số liệu đo (thiết bị đo lỗi)
        book.add(
            "usage",
            customer_id=act[keep],
            month=np.full(keep.sum(), month),
            data_gb=gb[keep].round(1),
            tv_hours=tv[keep].round(1),
            outage_minutes=outage[keep].round(0),
        )

        # dịch lịch sử sang tháng sau
        late_hist = np.roll(late_hist, 1, axis=1)
        late_hist[:, 0] = late_now
        net_tickets_hist = np.roll(net_tickets_hist, 1, axis=1)
        net_tickets_hist[:, 0] = 0
        low_csat_hist = np.roll(low_csat_hist, 1, axis=1)
        low_csat_hist[:, 0] = False

    return _assemble(rng, cfg, signup, province, sme, channel, birth_year, payment, cancel_effective, book, sub_closed)


def _assemble(rng, cfg, signup, province, sme, channel, birth_year, payment, cancel_effective, book, sub_closed):
    n = len(signup)
    ids = np.array([f"KH{i:06d}" for i in range(n)])
    exists = signup <= np.datetime64(config.HISTORY_END)

    # ----------------------------------------------------- CRM: khách hàng (có PII, trùng dòng, tên tỉnh lộn xộn)
    names = [f"{rng.choice(FAMILY)} {rng.choice(MIDDLE)} {rng.choice(GIVEN)}" for _ in range(n)]
    dob = pd.to_datetime(
        pd.Series(birth_year).astype(str) + "-" + pd.Series(rng.integers(1, 13, n)).astype(str) + "-15"
    )
    dob[rng.random(n) < 0.01] = pd.Timestamp("1900-01-01")  # giá trị mặc định khi nhân viên bỏ trống
    status = np.where(
        pd.isna(cancel_effective) | (cancel_effective > np.datetime64(config.EXPORT_DATE)), "Đang hoạt động", "Đã hủy"
    )
    customers = pd.DataFrame(
        {
            "customer_id": ids,
            "full_name": names,
            "phone": ["09" + "".join(map(str, rng.integers(0, 10, 8))) for _ in range(n)],
            "email": [f"kh{i:06d}@mail.example" for i in range(n)],
            "date_of_birth": dob,
            "province": [PROVINCES[p] for p in province],
            "segment": np.where(sme, "Doanh nghiệp nhỏ", "Hộ gia đình"),
            "channel": CHANNELS[channel],
            "signup_date": pd.to_datetime(signup),
            "status": status,  # trạng thái TẠI NGÀY EXPORT — không phải tại ngày chấm điểm
            "cancel_date": pd.to_datetime(cancel_effective),
            "updated_at": pd.Timestamp(config.EXPORT_DATE) - pd.to_timedelta(rng.integers(0, 400, n), unit="D"),
        }
    )[exists]
    customers.loc[customers.sample(frac=0.03, random_state=1).index, "channel"] = None
    variant = customers.sample(frac=0.12, random_state=2).index
    customers.loc[variant, "province"] = [
        rng.choice(PROVINCE_VARIANTS[p]) if PROVINCE_VARIANTS[p] else p for p in customers.loc[variant, "province"]
    ]
    nfd = customers.sample(frac=0.02, random_state=3).index  # chuỗi Unicode tổ hợp (NFD): trông giống nhưng khác byte
    customers.loc[nfd, "province"] = [unicodedata.normalize("NFD", p) for p in customers.loc[nfd, "province"]]
    dup = customers.sample(frac=0.015, random_state=4).copy()  # export trùng: bản cũ hơn, tỉnh gõ khác
    dup["updated_at"] = dup["updated_at"] - pd.to_timedelta(rng.integers(30, 300, len(dup)), unit="D")
    dup["province"] = [rng.choice(PROVINCE_VARIANTS.get(p, [p]) or [p]) for p in dup["province"]]
    customers = pd.concat([customers, dup]).sample(frac=1, random_state=5).reset_index(drop=True)

    # ----------------------------------------------------- billing: kỳ thuê bao (đóng kỳ cũ khi đổi gói/gia hạn/hủy)
    subs = book.frame("subscriptions").sort_values(["customer_id", "start_date"], kind="stable")
    closes = pd.DataFrame(
        {"customer_id": np.concatenate([c for c, _ in sub_closed]), "close": np.concatenate([d for _, d in sub_closed])}
    )
    subs["seq"] = subs.groupby("customer_id").cumcount()
    closes = closes.sort_values(["customer_id", "close"], kind="stable")
    closes["seq"] = closes.groupby("customer_id").cumcount()
    subs = subs.merge(closes, on=["customer_id", "seq"], how="left")
    subscriptions = pd.DataFrame(
        {
            "subscription_id": subs["subscription_id"],
            "customer_id": ids[subs["customer_id"]],
            "plan_code": PLANS["plan_code"].to_numpy()[subs["plan"]],
            "contract_months": subs["contract_months"],
            "start_date": pd.to_datetime(subs["start_date"]),
            "end_date": pd.to_datetime(subs["close"]),
            "payment_method": PAYMENTS[subs["payment"]],
        }
    )

    prices = pd.DataFrame(
        {
            "plan_code": list(PLANS["plan_code"]) + ["SX50", "SX150"],
            "effective_from": [pd.Timestamp("2023-01-01")] * 6 + [pd.Timestamp("2025-04-01")] * 2,
            "monthly_fee": list(LIST_PRICE) + [PRICE_HIKE[0], PRICE_HIKE[1]],
        }
    )

    inv = book.frame("invoices")
    invoices = pd.DataFrame(
        {
            "invoice_id": [f"HD{i:07d}" for i in range(len(inv))],
            "customer_id": ids[inv["customer_id"]],
            "billing_month": pd.to_datetime(inv["billing_month"]),
            "amount": inv["amount"].round(0),
            "issued_date": pd.to_datetime(inv["billing_month"]),
            "due_date": pd.to_datetime(inv["billing_month"]) + pd.Timedelta(days=14),
            "paid_date": pd.to_datetime(inv["paid_date"]),
        }
    )
    adj = invoices.sample(frac=0.01, random_state=6).copy()  # dòng điều chỉnh giảm cước (hoàn tiền khi mất mạng)
    adj["invoice_id"] = adj["invoice_id"] + "-ADJ"
    adj["amount"] = -(adj["amount"] * rng.uniform(0.1, 0.5, len(adj))).round(-3)
    redo = invoices.sample(frac=0.005, random_state=7)  # export lại: trùng nguyên dòng
    invoices = pd.concat([invoices, adj, redo]).sort_values(["customer_id", "billing_month"]).reset_index(drop=True)

    use = book.frame("usage")
    usage = pd.DataFrame(
        {
            "customer_id": ids[use["customer_id"]],
            "month": pd.to_datetime(use["month"]),
            "data_gb": use["data_gb"],
            "tv_hours": use["tv_hours"],
            "outage_minutes": use["outage_minutes"],
        }
    )

    tk = book.frame("tickets")
    created = pd.to_datetime(tk["created_at"]) + pd.to_timedelta(rng.integers(7 * 60, 21 * 60, len(tk)), unit="m")
    lag_days = np.select(
        [rng.random(len(tk)) < 0.80, rng.random(len(tk)) < 0.75],
        [0, rng.integers(1, 4, len(tk))],
        rng.integers(4, 11, len(tk)),
    )
    logged = created + pd.to_timedelta(lag_days, unit="D") + pd.to_timedelta(rng.integers(5, 240, len(tk)), unit="m")
    resolved = created + pd.to_timedelta(tk["resolved_days"].astype(float), unit="D")
    messy = rng.random(len(tk)) < 0.15  # 15% ticket gõ tay sai kiểu (hoa/thường, không dấu, thừa khoảng trắng)
    category = [rng.choice(TICKET_VARIANTS[c]) if bad else c for c, bad in zip(tk["category"], messy, strict=True)]
    tickets = (
        pd.DataFrame(
            {
                "customer_id": ids[tk["customer_id"]],
                "created_at": created,
                "logged_at": logged,  # thời điểm ticket vào hệ thống — có khi trễ vài ngày
                "category": category,
                "resolved_at": resolved,
                "csat": tk["csat"].astype("Int64"),
            }
        )
        .sort_values("created_at")
        .reset_index(drop=True)
    )
    tickets.insert(0, "ticket_id", [f"TK{i:07d}" for i in range(len(tickets))])
    tickets = tickets[tickets["logged_at"] < pd.Timestamp(config.EXPORT_DATE)]  # export chỉ có ticket đã vào hệ thống

    cn = book.frame("cancellations")
    reasons = np.array(
        ["Chất lượng mạng", "Giá cao", "Hết hợp đồng", "Đối thủ khuyến mãi", "Chuyển nhà/đi xa", "Nợ cước", "Khác"]
    )
    cancellations = pd.DataFrame(
        {
            "request_id": [f"YC{i:06d}" for i in range(len(cn))],
            "customer_id": ids[cn["customer_id"]],
            "request_date": pd.to_datetime(cn["request_date"]),
            "effective_date": pd.to_datetime(cn["effective_date"]),
            "reason": reasons[cn["reason"]],
            "status": np.where(cn["revoked"], "Đã hoàn tác", "Hoàn tất"),
        }
    )
    promotions = pd.DataFrame(COMPETITOR_PROMOS, columns=["province", "start_date", "end_date", "competitor", "offer"])
    promotions[["start_date", "end_date"]] = promotions[["start_date", "end_date"]].apply(pd.to_datetime)
    return {
        "customers": customers,
        "subscriptions": subscriptions,
        "plans": PLANS,
        "plan_prices": prices,
        "invoices": invoices,
        "usage": usage,
        "tickets": tickets,
        "cancellations": cancellations,
        "competitor_promotions": promotions,
    }


CSV_TABLES = ["customers", "subscriptions", "plans", "plan_prices", "tickets", "cancellations"]  # export từ CRM/billing
PARQUET_TABLES = ["invoices", "usage"]  # kho dữ liệu
MARKETING_TABLES = ["competitor_promotions"]  # chỉ có từ A6, khi hỏi phòng marketing


def write_raw(tables: dict[str, pd.DataFrame], out: Path = config.RAW) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in CSV_TABLES:
        tables[name].to_csv(out / f"{name}.csv", index=False)
    for name in PARQUET_TABLES:
        tables[name].to_parquet(out / f"{name}.parquet", index=False)
    marketing = out.parent / "marketing"
    marketing.mkdir(parents=True, exist_ok=True)
    for name in MARKETING_TABLES:
        tables[name].to_csv(marketing / f"{name}.csv", index=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    tables = simulate()
    write_raw(tables)
    for name, df in tables.items():
        logging.getLogger("churn_telco.simulate").info("%-22s %8d dòng", name, len(df))
