# Kiểm tra lời đọc bằng máy nghe lại

<!-- FILE SINH TỰ ĐỘNG bằng `make qa` — không sửa tay. -->

Mô hình nhận dạng giọng nói tiếng Việt (zipformer, sherpa-onnx) chép lại từng câu của video, rồi so với kịch bản. Phụ âm đầu đọc giống nhau ở giọng Bắc (d/gi/r, s/x, ch/tr, c/k/q) tính là khớp. Mỗi câu chấm hai lần: **giọng riêng** và **trong bản trộn có nhạc**.

| Chỉ số | Kết quả |
|---|---|
| Từ ví dụ nghe đúng (giọng riêng) | **28/29** |
| Từ ví dụ nghe đúng (có nhạc nền) | **28/29** |
| Âm đọc chữ cái nghe đúng (giọng riêng) | 28/29 |
| Câu mở đầu: tỷ lệ lỗi theo tiếng (giọng riêng → có nhạc) | 3% → 7% |
| Câu kết: tỷ lệ lỗi theo tiếng (giọng riêng → có nhạc) | 0% → 0% |

ASR hay nghe nhầm âm đọc đứng riêng ("bờ", "ca") và dấu thanh, nên ✗ nghĩa là **cần người nghe lại**, chưa chắc giọng đọc sai. Câu sai thật thì thu âm lại và đặt file vào `giong-thu-am/<id>.wav` (xem README).

| Id | Câu trong kịch bản | Nguồn | Máy nghe được (giọng riêng) | Âm | Từ | Có nhạc |
|---|---|---|---|:-:|:-:|:-:|
| `mo-dau` | Xin chào các bạn nhỏ! Sách Vui đây, còn đây là bạn Thỏ Bông của mình. Hôm nay, cùng chúng mình học hai mươi chín chữ cái tiếng Việt nhé! | piper | xin chào các bạn nhỏ sách vui đầy còn đây là bạn thỏ bông của mình hôm nay cùng chúng mình học hai mươi chín chữ cái tiếng việt nhé | — | — | 7% lỗi |
| `chu-01` | Đây là chữ a, như trong cái áo. | piper | đây là chữ a nghĩ trong cái áo | ✓ | ✓ | ✓ |
| `chu-02` | Đây là chữ á nhé, như trong khăn quàng. | piper | đây là chữ á nhé trong khăn quàng | ✓ | ✓ | ✓ |
| `chu-03` | Đây là chữ ớ, như trong con gấu. | piper | đây là chữ ớ như trong con gấu | ✓ | ✓ | ✓ |
| `chu-04` | Đây là chữ bờ, như trong con bò. | piper | đây là chữ bờ như trong con bò | ✓ | ✓ | ✓ |
| `chu-05` | Đây là chữ cờ, như trong con cá. | piper | đây là chữ cờ như trong con cá | ✓ | ✓ | ✓ |
| `chu-06` | Đây là chữ dờ, như trong dưa hấu. | piper | đây là chữ giờ như trong dưa hấu | ✓ | ✓ | ✓ |
| `chu-07` | Đây là chữ đờ, như trong đồng hồ. | piper | đây là chữ đờ ghi trong đồng hồ | ✓ | ✓ | ✓ |
| `chu-08` | Đây là chữ e, như trong em bé. | piper | đây là chữ e trong em bé | ✓ | ✓ | ✓ |
| `chu-09` | Đây là chữ ê, ê, như trong cái lều. | piper | đây là chữ ê như trong cái lều | ✓ | ✓ | ✓ |
| `chu-10` | Đây là chữ gờ, như trong con gà. | piper | đây là chữ g như trong con gà | ✓ | ✓ | ✓ |
| `chu-11` | Đây là chữ hờ, như trong bông hoa. | piper | đây là chữ hờ như trong bông hoa | ✓ | ✓ | ✓ |
| `chu-12` | Đây là chữ i, như trong bút chì. | piper | đây là chữ y như trong bút chì | ✓ | ✓ | ✓ |
| `chu-13` | Đây là chữ ca nhé, như trong cái kéo. | piper | đây là chữ ca nhé trong cái kéo | ✓ | ✓ | ✓ |
| `chu-14` | Đây là chữ lờ, như trong chiếc lá. | piper | đây là chữ l trong chiếc lá | ✓ | ✓ | ✓ |
| `chu-15` | Đây là chữ mờ, như trong con mèo. | piper | đây là chữ mờ như trong con mèo | ✓ | ✓ | ✓ |
| `chu-16` | Đây là chữ nờ, như trong cây nấm. | piper | đây là chữ n trong cây nấm | ✓ | ✓ | ✓ |
| `chu-17` | Đây là chữ o, như trong quả bóng. | piper | đây là chữ o như cho quả bóng | ✓ | ✓ | ✓ |
| `chu-18` | Đây là chữ ô, như trong ô tô. | piper | đây là chữ ô ghi trong ô tô | ✓ | ✓ | ✓ |
| `chu-19` | Đây là chữ ơ, như trong quả ớt. | piper | đây là chữ ơ như trong quả ớt | ✓ | ✓ | ✓ |
| `chu-20` | Đây là chữ pờ, như trong cục pin. | piper | đây là chữ thờ như trong cục hình | ✗ | ✗ | ✗ |
| `chu-21` | Đây là chữ quy nhé, như trong quả chuối. | piper | đây là chữ quy nhé như trong quả chuối | ✓ | ✓ | ✓ |
| `chu-22` | Đây là chữ rờ, như trong con rùa. | piper | đây là chữ giờ như trong con rùa | ✓ | ✓ | ✓ |
| `chu-23` | Đây là chữ sờ, như trong ngôi sao. | piper | đây là chữ sờ như trong ngôi sao | ✓ | ✓ | ✓ |
| `chu-24` | Đây là chữ tờ, như trong quả táo. | piper | đây là chữ tờ như trong quả táo | ✓ | ✓ | ✓ |
| `chu-25` | Đây là chữ u, như trong củ cà rốt. | piper | đây là chữ u như trong củ cà rốt | ✓ | ✓ | ✓ |
| `chu-26` | Đây là chữ ư, như trong sư tử. | piper | đây là chữ ư ghi trong sư tử | ✓ | ✓ | ✓ |
| `chu-27` | Đây là chữ vờ, như trong cái váy. | piper | đây là chữ vờ trong cái váy | ✓ | ✓ | ✓ |
| `chu-28` | Đây là chữ xờ, như trong quả xoài. | piper | đây là chữ sờ như trong quả xoài | ✓ | ✓ | ✓ |
| `chu-29` | Đây là chữ i dài, như trong yêu thương. | piper | đây là chữ y dài nghi trong yêu thương | ✓ | ✓ | ✓ |
| `ket-thuc` | Giỏi quá! Các bạn đã học xong hai mươi chín chữ cái rồi. Hẹn gặp lại nhé! | piper | giỏi quá các bạn đã học xong hai mươi chín chữ cái rồi hẹn gặp lại nhé | — | — | 0% lỗi |
