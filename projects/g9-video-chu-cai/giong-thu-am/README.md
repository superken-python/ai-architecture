# giong-thu-am/ — câu thu âm thật thay cho giọng máy

Đặt ở đây file WAV của câu nào thì câu đó dùng giọng thật, các câu còn lại vẫn dùng giọng máy. Tên file là id câu:

| Id | Câu |
|---|---|
| `mo-dau` | Câu chào mở đầu |
| `chu-01` … `chu-29` | Câu của từng chữ cái theo thứ tự trong kịch bản (`chu-20` là chữ P) |
| `ket-thuc` | Câu kết |

Thu bằng điện thoại rồi đổi sang WAV 16 bit, một kênh:

```bash
ffmpeg -i ghi-am-chu-p.m4a -ac 1 -ar 44100 -c:a pcm_s16le chu-20.wav
```

Đọc đúng câu trong kịch bản (cột "Câu trong kịch bản" của [bảng kiểm tra](../reports/kiem-tra-giong.md)). Đọc chậm,
rõ, không để trống quá lâu ở đầu và cuối (code tự cắt khoảng lặng). Câu phải ngắn hơn khúc nhạc của nó (~3,4 giây với
chữ cái, ~6,8 giây với câu mở đầu và kết). Sau đó chạy `make video` và `make qa`.
