# Tự làm video hoạt hình dạy học bằng Claude Code (cách A: dựng bằng code)

Hướng dẫn này đi lại đúng các bước đã làm ra [video chữ cái cùng Sách Vui](../README.md), để bạn tự làm video khác:
đổi nhân vật, đổi bài học, đổi giọng. Claude Code viết và chạy code giúp bạn. Bạn giữ ba việc: chọn nội dung, nhìn
khung hình, nghe duyệt lời đọc.

> [!NOTE]
> Claude (kể cả gói Max) **không có mô hình tạo video hay hình ảnh**. Cách A không cần: Claude Code viết code vẽ từng
> khung hình từ ảnh nhân vật của bạn, ghép giọng đọc và nhạc bằng ffmpeg. Kết quả là video hoạt hình ghép (nhân vật
> nhún, nghiêng, phóng to theo nhịp), không phải anime cử động tay chân. Muốn vậy xem [mục 8](#8--muốn-nhân-vật-cử-động-thật-cách-b).

| | |
|---|---|
| Thời gian | Lần đầu ~1 buổi (cài đặt + chỉnh kịch bản); các video sau ~10 phút sửa kịch bản + ~3 phút dựng |
| Chi phí | Gói Claude có Claude Code; giọng đọc, nhạc, dựng video chạy offline trên máy bạn, không tốn phí API |
| Máy | macOS, Linux hoặc Windows (WSL); CPU là đủ, không cần GPU; ~1 GB trống |

## 0 · Cần chuẩn bị

1. **Claude Code** — cài theo [hướng dẫn chính thức](https://code.claude.com/docs), đăng nhập bằng tài khoản Claude.
2. **uv** và **ffmpeg**: macOS `brew install uv ffmpeg`; Ubuntu `sudo apt install ffmpeg` rồi cài uv theo
   [docs/00-setup](../../../docs/00-setup/README.md).
3. **Ảnh nhân vật** — một ảnh PNG/JPG, nhân vật nằm trong một vùng tròn hoặc vuông rõ ràng. Ảnh tự tạo bằng công cụ
   tạo ảnh (Gemini, ChatGPT…) dùng được; tránh nhân vật có bản quyền (Doraemon, Pikachu…) nếu định đăng công khai.

Mở terminal ở thư mục dự án rồi chạy:

```bash
cd projects/g9-video-chu-cai
make setup     # môi trường Python đúng theo uv.lock
make assets    # tải font, hình, giọng đọc, model nghe lại (~150 MB, một lần)
make test      # 21 test phải xanh trước khi sửa gì
claude         # mở Claude Code ngay trong thư mục này
```

## 1 · Nhân vật: một ảnh dùng xuyên suốt

Video chỉ cần **một** ảnh nhân vật. Code cắt vùng tròn chứa nhân vật, làm mềm viền, phóng to và cho nhân vật nhún theo
phách nhạc, nghiêng nhẹ, to lên khi đang đọc. Vì dùng đúng một ảnh, nhân vật luôn giống nhau ở mọi cảnh. Đây là điểm
khó nhất nếu dùng công cụ tạo video.

1. Chép ảnh vào `assets/nhan-vat/`, sửa `character.image` trong kịch bản.
2. Đặt `character.crop` = tâm và bán kính vùng tròn (pixel của ảnh gốc). Không chắc thì nhờ Claude Code:

```text
Ảnh nhân vật mới ở assets/nhan-vat/meo-mun.png. Hãy tìm vùng tròn chứa trọn nhân vật (tâm x, y, bán kính),
cập nhật character.crop trong kich-ban/chu-cai.yaml, chạy `make preview` rồi xem out/khung-*.png:
nhân vật có bị cắt mất tai, viền có lộ nền cũ không. Chỉnh đến khi đẹp.
```

## 2 · Kịch bản: một file YAML là nguồn duy nhất

Mọi thứ trên hình và trong tai đều lấy từ [`kich-ban/chu-cai.yaml`](../kich-ban/chu-cai.yaml): tiêu đề, tên nhân vật,
nhịp nhạc, câu chào, và với mỗi chữ cái: cách đọc, từ ví dụ, từ chứa chữ cái, hình minh họa. Chữ trên hình được vẽ từ
file này bằng font thật, nên **không bao giờ sai dấu**. Ngược lại, công cụ tạo ảnh/video hay viết sai dấu tiếng Việt.

Nhờ Claude viết hoặc sửa kịch bản bằng lời thường:

```text
Đổi từ ví dụ cho các chữ cái để phù hợp bé mẫu giáo vùng biển: ưu tiên con vật, đồ vật quen thuộc,
mỗi từ có emoji Noto rõ nghĩa. Giữ nguyên cách đọc âm (bờ, cờ, ca, quy, i dài). Sau khi sửa, chạy
`make test` và `uv run python -m chu_cai_video voice` để chắc mọi câu vừa khúc nhạc.
```

Bộ kiểm tra kịch bản (`lesson.py`) báo lỗi ngay nếu từ ví dụ không chứa chữ cái (bỏ qua dấu thanh: "ếch" có chữ ê),
từ không nằm trong cụm từ, thiếu hình, hay chữ cái bị lặp.

## 3 · Dựng thử bằng khung hình, chưa cần video

Dựng cả video mất ~3 phút; xem vài khung hình chỉ mất vài giây. Hãy sửa bố cục bằng khung hình trước:

```bash
make preview                                              # mở đầu, chuyển cảnh, 3 chữ đầu, kết thúc
uv run python -m chu_cai_video frame --at 10.6 61.5 116   # hoặc chọn giây cần xem
```

Claude Code đọc được ảnh, nên có thể tự xem khung hình và sửa code vẽ:

```text
Xem out/khung-*.png. Phụ đề đang che bảng tên nhân vật ở cảnh mở đầu; thẻ chữ hơi sát mép phải.
Sửa bố cục trong render.py, vẽ lại khung hình và cho tôi xem trước/sau.
```

> [!TIP]
> Tiết kiệm token: để Claude xem **vài khung hình PNG** thay vì đọc log dài; giao việc theo từng lớp (bố cục → giọng
> → nhạc), mỗi lớp có một lệnh kiểm tra nhanh (`make preview`, `make qa`, `make test`).

## 4 · Nhạc nền: tự tổng hợp, không vướng bản quyền

[`music.py`](../src/chu_cai_video/music.py) tạo nhạc bằng numpy: trống nhẹ, bass nảy, đàn gảy phách lẻ, tiếng "ting"
khi sang chữ mới, và một câu đáp ngắn của mộc cầm sau mỗi lời đọc. Không dùng bản thu của ai nên đăng ở đâu cũng được.

- Nhịp: `music.bpm`. Mỗi chữ cái chiếm `letter_bars` ô nhịp (mặc định 2). Ở 132 nhịp/phút, cả video đúng 2 phút.
- Khi có lời, nhạc tự hạ 9 dB (ducking). Đo được: lời to hơn nhạc 14 dB lúc đang đọc.
- Muốn dùng nhạc có sẵn: chọn bản có giấy phép rõ ràng, rồi nhờ Claude thay `music.render` bằng hàm đọc file WAV và
  cắt cho đủ độ dài.

## 5 · Giọng đọc: đo rồi mới tin

Giọng đọc là phần dễ sai nhất, và bạn sẽ không nghe hết 31 câu sau mỗi lần sửa. Dự án làm như sau:

1. **Giọng máy offline:** Piper vi_VN vais1000 (chạy trên CPU qua sherpa-onnx). Tắt phần ngẫu nhiên để cùng câu luôn
   ra cùng giọng.
2. **Máy nghe lại:** `make qa` cho một mô hình nhận dạng giọng nói tiếng Việt chép lại từng câu (giọng riêng và khi có
   nhạc), rồi so với kịch bản → [`reports/kiem-tra-giong.md`](../reports/kiem-tra-giong.md).
3. **Sửa câu sai** theo thứ tự từ rẻ đến đắt:

| Cách | Khi nào | Ví dụ trong dự án |
|---|---|---|
| Đọc cả câu thay vì từ đứng riêng | Luôn luôn | "Bờ, con bò!" (máy nghe đúng 8/29) → "Đây là chữ bờ, như trong con bò." (18/29) |
| Đổi từ ví dụ | Giọng đọc sai một từ | N: "con nai" → "cây nấm"; V: "con vịt" → "cái váy" |
| Câu riêng `say` | Sai dấu thanh của âm | "Đây là chữ quy nhé, …" (không có "nhé" thì máy nghe thành "quỵ") |
| Thu âm thật | Giọng máy không đọc được | Âm "pờ": thu câu của chữ P, lưu `giong-thu-am/chu-20.wav` |

Thu âm bằng điện thoại cho nhanh, rồi đổi sang WAV 16 bit và đặt đúng tên file (id câu có trong bảng kiểm tra):

```bash
ffmpeg -i ghi-am-chu-p.m4a -ac 1 -ar 44100 -c:a pcm_s16le giong-thu-am/chu-20.wav
make video && make qa      # câu chu-20 giờ có nguồn "thu-am"
```

Muốn giọng hay hơn cho cả video: thu âm cả 31 câu (giáo viên đọc, mỗi câu một file), hoặc dùng dịch vụ đọc tiếng
Việt (FPT.AI, Vbee, Google, Azure, ElevenLabs) rồi lưu kết quả vào `giong-thu-am/`. Vẫn chạy `make qa` để kiểm tra.

> [!WARNING]
> Máy nghe lại cũng nghe nhầm, nhất là âm đọc đứng riêng và dấu thanh. ✓ không thay được tai người — **giáo viên vẫn
> phải nghe duyệt trước khi chiếu cho bé**.

## 6 · Dựng video và đưa lên trang web

```bash
make clip      # 15 giây đầu → out/thu.mp4, xem nhanh trước khi dựng hết
make video     # cả video → media/video-chu-cai.mp4 + poster.jpg + chuong.vtt + phu-de.vtt
```

Video là MP4 H.264 + AAC, phát được trên mọi trình duyệt, tua được ngay. Kèm theo là ảnh bìa, file chương (mỗi chữ cái
một chương) và phụ đề WebVTT. Trang web lộ trình hiện video ở trang **Nhóm 9** và trong README này. Xem thử ở repo gốc:
`make site-serve` → http://localhost:8000/#/nhom/G9. Commit cả `media/` để GitHub Pages phát được video.

## 7 · Người duyệt: kiểm tra trước khi dùng với bé

- [ ] Xem hết video một lượt, có tiếng: chữ, dấu, hình minh họa đúng và hợp lứa tuổi.
- [ ] Nghe kỹ các câu bảng kiểm tra đánh ✗ (và chữ P nếu chưa thu âm).
- [ ] Cách đọc âm khớp cách dạy ở lớp (bờ hay bê, quy hay cu).
- [ ] Nhân vật, nhạc, giọng đọc có quyền sử dụng; dòng ghi nguồn ở cuối video còn nguyên.
- [ ] Đăng lên YouTube: chọn "Dành cho trẻ em"; mô tả có ghi nguồn giọng đọc (CC BY 4.0).

## 8 · Muốn nhân vật cử động thật (cách B)

Cách A không làm được tay chân cử động, khẩu hình, đổi góc máy. Những việc đó cần một công cụ tạo video (Kling, Veo,
Seedance, Sora…) có tính năng giữ nhân vật theo ảnh tham chiếu. Cách ghép hợp lý:

- Dùng công cụ tạo video cho vài cảnh ngắn **không có chữ** (mở đầu, kết thúc), mỗi cảnh 5–10 giây, đưa ảnh nhân vật
  làm tham chiếu.
- Giữ phần dạy chữ bằng cách A, vì chữ và giọng phải đúng tuyệt đối. Chữ chèn bằng code, giọng từ `giong-thu-am/`.
- Nhờ Claude Code ghép các cảnh: đọc clip, cắt cho khớp nhịp, chèn trước/sau phần dạy chữ. ffmpeg làm được hết.

## 9 · Lỗi thường gặp

| Lỗi | Cách sửa |
|---|---|
| `Chưa có ffmpeg` | macOS `brew install ffmpeg`; Ubuntu `sudo apt install ffmpeg`; Windows dùng WSL |
| `libonnxruntime.so: cannot open shared object file` | Thiếu `sherpa-onnx-core` cùng phiên bản với `sherpa-onnx`; chạy lại `make setup` (uv.lock đã khai báo) |
| `Lời đọc dài hơn khúc nhạc` | Rút gọn câu, giảm `music.bpm` hoặc tăng `letter_bars` |
| `Không tải được …` | Mạng chặn GitHub hoặc Google Fonts: tải tay file trong `config.py` vào `.cache/` (mã băm được kiểm khi dùng) |
| Chữ hiện bằng font khác | Không tải được Baloo 2, đang dùng font dự phòng của máy — chạy lại `make assets` |
| Hình minh họa là vòng tròn có chữ cái | Không tải được emoji; dùng ảnh riêng: `image: ../assets/hinh/bo.png` |

## Prompt mẫu cho cả quy trình

```text
Tôi muốn làm video 2 phút dạy chữ cái tiếng Việt cho bé, dùng nhân vật trong assets/nhan-vat/<ảnh>.png xuyên suốt,
trên nền nhạc vui. Làm theo projects/g9-video-chu-cai: (1) cập nhật kịch bản kich-ban/chu-cai.yaml, (2) chạy
make preview và tự xem khung hình, sửa bố cục nếu chồng chéo, (3) chạy make video rồi make qa, (4) với câu bị đánh ✗,
thử đổi từ ví dụ hoặc thêm câu `say`, chạy lại make qa; câu nào vẫn sai thì liệt kê để tôi thu âm.
Mỗi bước báo kết quả bằng số (câu đúng / tổng), không dán log dài.
```
