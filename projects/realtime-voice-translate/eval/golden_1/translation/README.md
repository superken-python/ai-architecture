# Bản dịch tham chiếu golden_1 (Nhật → Việt)

Dùng cho `eval/mt_eval.py` và `eval/golden_session.py --mt-url` (docs 09 §5.1).

`ja-vi.jsonl` có mỗi dòng một câu:

```json
{"id": 1, "lines": [1, 2], "speaker": "Naruto", "ja": "先生どこだよ。…", "vi": "Thầy đâu rồi chứ? …"}
```

- `lines` là số dòng trong `subtitle/*.txt`. Phụ đề tự sinh hay cắt một câu ra hai dòng, nên một mục có thể gồm nhiều
  dòng. Mỗi mục là một câu nói trọn ý của một người.
- `speaker` là người nói, dùng để kiểm cách xưng hô. Ví dụ Naruto với Sakura xưng "tớ/cậu", học trò với Kakashi xưng
  "em/thầy". Quy ước này giống `packs/glossary/naruto.yaml`.
- `ja` là câu nguồn đã sửa lỗi nghe của phụ đề tự sinh: 上忍, 里の長, 手裏剣, 丸太, 正午, 千年殺し, 多重影分身…
  Bộ đo dịch phải nhận câu đúng thì mới đo riêng được bộ dịch.
- Không có tham chiếu cho dòng 12–25 và từ 180 trở đi. Đây là phần không phải lời thoại, giống `--skip-lines
  12-25,180-`. Cũng không có cho các dòng chỉ ghi tiếng động (`[音楽]`, `[ため息]`…) và dòng 151 (`受けた分に潜`), vì
  dòng này nghe hỏng tới mức không đoán được câu gốc.

**Nguồn gốc.** Bản dịch là bản nháp do model tạo, rồi được soát theo ngữ cảnh cả tập phim, glossary và quy ước xưng hô.
Chưa có người bản ngữ duyệt. Trước khi dùng điểm chrF để so model, nên có người đọc lại các câu bị điểm thấp nhất mà
`mt_eval.py` in ra. Sửa thẳng vào file này, giữ nguyên `id`.

chrF so ký tự nên chỉ dùng để so trước/sau trên cùng bộ câu. Một câu dịch đúng nghĩa nhưng chọn từ khác vẫn bị điểm
thấp. Điểm tuyệt đối không nói được bản dịch "tốt" hay "dở".
