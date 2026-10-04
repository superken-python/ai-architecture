# 4 · GPU và tài nguyên tính toán

## Nhóm nào cần GPU?

| Nhóm bài toán | Cần GPU? | Ghi chú |
|---|---|---|
| 1 · Bảng, 2 · Thời gian, 3 · Bất thường, 8 · Tối ưu | Không | CPU laptop là đủ; LightGBM/OR-Tools chạy tốt trên CPU |
| 4 · Gợi ý | Hiếm khi | ALS/LightGBM chạy CPU; two-tower/sequential cần GPU khi dữ liệu lớn |
| 6 · LLM/RAG, 7 · Agent | Không (khi dùng API) | Cần GPU chỉ khi tự host model hoặc fine-tune (LLM-07) |
| 5 · Ảnh/TL, embedding, fine-tune | **Có** | Huấn luyện YOLO, fine-tune PhoBERT/ViT, chạy ASR nhanh |

Nguyên tắc: học được ~80% lộ trình mà không cần GPU riêng. Khi cần, dùng GPU đám mây miễn phí trước.

## Lựa chọn

| Lựa chọn | Phù hợp | Lưu ý |
|---|---|---|
| **Google Colab** | Thử nhanh, notebook | GPU miễn phí có giới hạn thời gian và không bảo đảm loại GPU; phiên bị ngắt khi rảnh |
| **Kaggle Notebooks** | Huấn luyện vài giờ, dữ liệu Kaggle có sẵn | Có hạn mức GPU miễn phí theo tuần; tải dữ liệu Kaggle không cần API key |
| **GPU máy nhà (NVIDIA)** | Học lâu dài, dữ liệu nhạy cảm | ≥ 8 GB VRAM cho fine-tune nhỏ; cần driver NVIDIA |
| **Apple Silicon (M1+)** | Laptop Mac | PyTorch dùng backend `mps`; một số thư viện CUDA không chạy được |
| **GPU thuê theo giờ** | Fine-tune LLM, vLLM | Tắt máy khi xong; theo dõi chi phí như theo dõi token |

Hạn mức miễn phí của Colab/Kaggle thay đổi theo thời gian — kiểm tra trang của dịch vụ trước khi lên kế hoạch.

## Cài PyTorch có GPU

`make setup-vision` cài PyTorch từ PyPI:

- **Linux / WSL2 (x86_64):** bản PyPI đã kèm thư viện CUDA — chỉ cần driver NVIDIA (trên WSL2: driver cài ở
  Windows). Driver phải đủ mới cho phiên bản CUDA mà PyTorch được build: so `CUDA Version` ở góc phải
  `nvidia-smi` với kết quả `torch.version.cuda` (bản trong `uv.lock` lúc viết tài liệu là CUDA 13.0) — driver
  thấp hơn thì cập nhật driver.
- **macOS Apple Silicon:** dùng `mps`, không cần cài thêm.
- **Windows thuần:** bản PyPI là CPU-only — dùng WSL2, hoặc cài theo hướng dẫn trên pytorch.org trong môi
  trường riêng.

Kiểm tra:

```bash
uv run python -c "import torch; print('cuda:', torch.cuda.is_available(), '| mps:', torch.backends.mps.is_available())"
nvidia-smi    # Linux/WSL2: xem GPU, driver và phiên bản CUDA mà driver hỗ trợ
```

## Code chạy được ở mọi nơi

```python
import torch

device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
```

Đặt dữ liệu và checkpoint ngoài Git (`data/`, `outputs/` đã bị bỏ qua). Trên Colab/Kaggle, notebook chạy
bằng Python có sẵn của dịch vụ (đã có PyTorch), nên **không** dùng `uv sync` — chỉ cài thêm đúng gói cần
dùng bằng `%pip install ultralytics` (ghi phiên bản giống `uv.lock` nếu cần tái lập), và lưu kết quả quan
trọng ra Drive/Kaggle Dataset trước khi phiên kết thúc.

Tiếp theo: [5 · Dữ liệu luyện tập](05-du-lieu-luyen-tap.md).
