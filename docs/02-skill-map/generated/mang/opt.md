<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# OPT · Tối ưu hóa (OR)

LP/MIP, định tuyến, lập lịch, quyết định dưới bất định, bandit.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [OPT-01](#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) | Dùng chung trong họ | Mô hình hóa quyết định có ràng buộc và để solver tìm phương án tốt nhất. |
| [OPT-02](#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch | Chuyên biệt | Giải VRP, xếp ca, lập lịch với ràng buộc thực tế. |
| [OPT-03](#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) | Dùng chung trong họ | Nối dự báo xác suất với tối ưu để quyết định chịu được rủi ro. |
| [OPT-04](#opt-04) Bandit và học tăng cường cơ bản | Dùng chung trong họ | Vừa khám phá vừa khai thác khi lựa chọn có phản hồi liên tục. |

<a id="opt-01"></a>

### OPT-01 · Quy hoạch tuyến tính và nguyên (LP/MIP)

> Mô hình hóa quyết định có ràng buộc và để solver tìm phương án tốt nhất.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 2 Thời gian

| Mức | Làm được |
|---|---|
| Cơ bản | Biến quyết định–ràng buộc–mục tiêu; giải LP với PuLP/OR-Tools (phân bổ ngân sách, pha trộn). |
| Trung cấp | MIP cho xếp ca, chọn địa điểm; kỹ thuật mô hình hóa (big-M, biến nhị phân); đọc gap và thời gian giải. |
| Nâng cao | Mô hình lớn (phân rã, warm start), so sánh solver (HiGHS, CBC, SCIP), phân tích độ nhạy (shadow price) để giải thích cho nghiệp vụ. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [OPT-02](../mang/opt.md#opt-02), [OPT-03](../mang/opt.md#opt-03)
- **Công cụ:** OR-Tools, PuLP, Pyomo, HiGHS
- **Đạt khi:** Mô hình phân bổ ngân sách cho kết quả tốt hơn cách làm hiện tại và giải thích được ràng buộc nào đang "chặn" lợi nhuận.

<a id="opt-02"></a>

### OPT-02 · Tối ưu tổ hợp — định tuyến và lập lịch

> Giải VRP, xếp ca, lập lịch với ràng buộc thực tế.

**Tầng:** Chuyên biệt · **Điểm đòn bẩy:** 2  
**Dùng cho:** ● Cốt lõi: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | TSP/VRP nhỏ với OR-Tools routing, ma trận khoảng cách. |
| Trung cấp | VRP có cửa sổ thời gian và tải trọng; xếp ca bằng CP-SAT với ràng buộc cứng/mềm. |
| Nâng cao | Heuristic/metaheuristic cho bài toán lớn, tối ưu lại theo thời gian thực, đo lợi ích so với cách làm hiện tại. |

- **Tiên quyết:** [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP)
- **Mở khóa:** —
- **Công cụ:** OR-Tools routing, CP-SAT
- **Đạt khi:** Tuyến giao hàng 1 kho × 20 điểm ngắn hơn tuyến hiện tại và tôn trọng mọi ràng buộc.

<a id="opt-03"></a>

### OPT-03 · Ra quyết định dưới bất định (dự báo rồi tối ưu)

> Nối dự báo xác suất với tối ưu để quyết định chịu được rủi ro.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 2 Thời gian

| Mức | Làm được |
|---|---|
| Cơ bản | Bài toán newsvendor, tồn kho an toàn từ quantile dự báo. |
| Trung cấp | Tối ưu theo kịch bản (stochastic), đưa dự báo quantile vào MIP, đánh giá quyết định bằng mô phỏng. |
| Nâng cao | Robust optimization, đánh giá theo chi phí quyết định (decision-focused) thay vì độ chính xác dự báo. |

- **Tiên quyết:** [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP), [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định
- **Mở khóa:** —
- **Công cụ:** OR-Tools, Pyomo, numpy
- **Đạt khi:** Mô phỏng cho thấy chính sách đặt hàng dựa trên quantile giảm tổng chi phí (thiếu + tồn) so với dùng dự báo điểm.

<a id="opt-04"></a>

### OPT-04 · Bandit và học tăng cường cơ bản

> Vừa khám phá vừa khai thác khi lựa chọn có phản hồi liên tục.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Explore vs exploit, epsilon-greedy, Thompson sampling. |
| Trung cấp | Contextual bandit, đánh giá off-policy. |
| Nâng cao | RL cho định giá/phân bổ khi có mô phỏng tốt; nhận biết khi RL là quá mức cần thiết. |

- **Tiên quyết:** [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test
- **Mở khóa:** —
- **Công cụ:** Vowpal Wabbit, numpy
- **Đạt khi:** Mô phỏng cho thấy Thompson sampling thu được nhiều lợi ích hơn A/B cố định trong cùng thời gian.
