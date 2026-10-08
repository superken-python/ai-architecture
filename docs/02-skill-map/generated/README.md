<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Bản đồ kỹ năng — phần sinh tự động

Danh mục hiện có **65 kỹ năng** trong **10 mảng**, phủ **8 nhóm bài toán** và **9 tổ hợp** dự án thực tế.

| Tầng | Số kỹ năng | Ý nghĩa |
|---|---:|---|
| Nền tảng chung | 13 | Cốt lõi/Cần ở cả 8 nhóm — học một lần, dùng mọi nơi. |
| Cầu nối liên họ | 14 | Cốt lõi/Cần ở cả hai họ bài toán nhưng chưa đủ 8 nhóm — giúp chuyển qua lại giữa ML cổ điển và GenAI. |
| Dùng chung trong họ | 31 | Cốt lõi/Cần ở ≥ 2 nhóm của cùng một họ. |
| Chuyên biệt | 5 | Cốt lõi/Cần ở đúng 1 nhóm — học khi đi sâu nhóm đó. |
| Bổ trợ | 2 | Chỉ ở mức Ít — nâng hiệu quả làm việc, không chặn nhóm nào. |

## Hai họ bài toán

- **Họ dữ liệu có cấu trúc & quyết định:** Nhóm 1 Bảng, Nhóm 2 Thời gian, Nhóm 3 Bất thường, Nhóm 4 Gợi ý, Nhóm 8 Tối ưu
- **Họ dữ liệu phi cấu trúc & GenAI:** Nhóm 5 Ảnh/TL, Nhóm 6 LLM/RAG, Nhóm 7 Agent

## Kỹ năng theo tầng

- **Nền tảng chung:** [PY-01](mang/py.md#py-01), [PY-02](mang/py.md#py-02), [PY-03](mang/py.md#py-03), [DATA-05](mang/data.md#data-05), [STAT-01](mang/stat.md#stat-01), [STAT-02](mang/stat.md#stat-02), [OPS-01](mang/ops.md#ops-01), [OPS-02](mang/ops.md#ops-02), [BIZ-01](mang/biz.md#biz-01), [BIZ-02](mang/biz.md#biz-02), [BIZ-03](mang/biz.md#biz-03), [BIZ-04](mang/biz.md#biz-04), [BIZ-05](mang/biz.md#biz-05)
- **Cầu nối liên họ:** [PY-04](mang/py.md#py-04), [DATA-01](mang/data.md#data-01), [STAT-03](mang/stat.md#stat-03), [STAT-05](mang/stat.md#stat-05), [ML-01](mang/ml.md#ml-01), [ML-03](mang/ml.md#ml-03), [ML-04](mang/ml.md#ml-04), [ML-07](mang/ml.md#ml-07), [DL-01](mang/dl.md#dl-01), [DL-03](mang/dl.md#dl-03), [OPS-03](mang/ops.md#ops-03), [OPS-04](mang/ops.md#ops-04), [OPS-05](mang/ops.md#ops-05), [OPS-08](mang/ops.md#ops-08)
- **Dùng chung trong họ:** [DATA-02](mang/data.md#data-02), [DATA-03](mang/data.md#data-03), [DATA-04](mang/data.md#data-04), [DATA-06](mang/data.md#data-06), [STAT-04](mang/stat.md#stat-04), [STAT-06](mang/stat.md#stat-06), [ML-02](mang/ml.md#ml-02), [ML-05](mang/ml.md#ml-05), [ML-06](mang/ml.md#ml-06), [DL-02](mang/dl.md#dl-02), [DL-05](mang/dl.md#dl-05), [LLM-01](mang/llm.md#llm-01), [LLM-02](mang/llm.md#llm-02), [LLM-03](mang/llm.md#llm-03), [LLM-04](mang/llm.md#llm-04), [LLM-05](mang/llm.md#llm-05), [LLM-06](mang/llm.md#llm-06), [LLM-07](mang/llm.md#llm-07), [LLM-08](mang/llm.md#llm-08), [OPT-01](mang/opt.md#opt-01), [OPT-03](mang/opt.md#opt-03), [OPT-04](mang/opt.md#opt-04), [OPS-06](mang/ops.md#ops-06), [OPS-07](mang/ops.md#ops-07), [EFF-01](mang/eff.md#eff-01), [EFF-02](mang/eff.md#eff-02), [EFF-03](mang/eff.md#eff-03), [EFF-04](mang/eff.md#eff-04), [EFF-05](mang/eff.md#eff-05), [EFF-06](mang/eff.md#eff-06), [EFF-07](mang/eff.md#eff-07)
- **Chuyên biệt:** [DATA-07](mang/data.md#data-07), [ML-08](mang/ml.md#ml-08), [DL-04](mang/dl.md#dl-04), [DL-06](mang/dl.md#dl-06), [OPT-02](mang/opt.md#opt-02)
- **Bổ trợ:** [BIZ-06](mang/biz.md#biz-06), [EFF-08](mang/eff.md#eff-08)

## Các trang

- [Ma trận kỹ năng × nhóm bài toán](ma-tran-ky-nang.md) — kỹ năng nào dùng cho nhóm nào, mức chia sẻ giữa các nhóm, đối chiếu với giai đoạn 1.
- [Lộ trình theo bước](lo-trinh.md) — 4 giai đoạn, từng tuần học kỹ năng nào đến mức nào, nộp gì.
- [Thứ tự học & kỹ năng đòn bẩy](thu-tu-hoc.md) — học gì trước, kỹ năng nào dùng được nhiều nhất.
- [Tổ hợp kỹ năng](to-hop-ky-nang.md) — dự án ghép nhiều nhóm và kỹ năng "keo" ở điểm nối.
- [Bảng tự đánh giá](tu-danh-gia.md) — đánh dấu từng mức của từng kỹ năng.

### Thẻ kỹ năng theo mảng

- [PY · Lập trình nền tảng](mang/py.md) — 4 kỹ năng
- [DATA · SQL & dữ liệu](mang/data.md) — 7 kỹ năng
- [STAT · Thống kê & thực nghiệm](mang/stat.md) — 6 kỹ năng
- [ML · ML cổ điển](mang/ml.md) — 8 kỹ năng
- [DL · Deep learning](mang/dl.md) — 6 kỹ năng
- [LLM · LLM, RAG & Agent](mang/llm.md) — 8 kỹ năng
- [OPT · Tối ưu hóa (OR)](mang/opt.md) — 4 kỹ năng
- [OPS · Triển khai & MLOps](mang/ops.md) — 8 kỹ năng
- [BIZ · Nghiệp vụ & phương pháp](mang/biz.md) — 6 kỹ năng
- [EFF · Tiết kiệm token & độ tin cậy](mang/eff.md) — 8 kỹ năng

### Lộ trình theo nhóm bài toán

- [Nhóm 1 · Dự đoán trên dữ liệu bảng](nhom/g1-du-lieu-bang.md)
- [Nhóm 2 · Dự báo chuỗi thời gian](nhom/g2-chuoi-thoi-gian.md)
- [Nhóm 3 · Phát hiện bất thường](nhom/g3-bat-thuong.md)
- [Nhóm 4 · Gợi ý và xếp hạng](nhom/g4-goi-y-xep-hang.md)
- [Nhóm 5 · Thị giác máy tính và Document AI](nhom/g5-anh-tai-lieu.md)
- [Nhóm 6 · Ngôn ngữ, LLM và RAG](nhom/g6-llm-rag.md)
- [Nhóm 7 · AI Agent và tự động hóa quy trình](nhom/g7-agent-tu-dong-hoa.md)
- [Nhóm 8 · Tối ưu hóa và suy luận nhân quả](nhom/g8-toi-uu-nhan-qua.md)
