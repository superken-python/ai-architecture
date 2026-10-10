# RVT Docker Architecture & Deployment Guide

Thư mục `docker/` quản lý toàn bộ cấu hình container hoá, networking và kịch bản triển khai một chạm (one-click deploy) cho dự án Realtime Voice Translate.

---

## 1. Cấu Trúc Thư Mục `docker/`

```text
docker/
├── docker-compose.yml          # [MASTER] File Compose thống nhất gộp cả 3 service (mt + ai + web)
├── docker-compose.ai.yml       # [AI ONLY] Chạy riêng cụm backend AI (llama.cpp MT + FastAPI AI)
├── docker-compose.web.yml      # [WEB ONLY] Chạy riêng frontend PWA + Nginx reverse proxy
├── docker-compose.cpu.yml      # [CPU/DEV] Chế độ chạy CPU/Fake mode (không cần NVIDIA GPU/CUDA)
├── nginx/
│   └── nginx.conf.template     # Cấu hình Nginx reverse proxy (WSS /ws, HTTPS, caching)
├── start.sh                    # Kịch bản khởi động thông minh (tự gen TLS, detect GPU/CPU, chờ healthcheck)
└── stop.sh                     # Dừng toàn bộ các container và dọn dẹp network
```

---

## 2. Cách Khởi Động Với 1 File Duy Nhất

### Cách 1: Sử dụng script `start.sh` (Khuyên Dùng)

Từ thư mục gốc dự án:
```bash
# Tự động detect phần cứng (GPU nếu có NVIDIA runtime, ngược lại CPU/fake mode)
./start.sh

# Hoặc chỉ định rõ chế độ:
./start.sh --cpu       # Dành cho macOS / laptop dev / máy không có GPU
./start.sh --gpu       # Dành cho GPU server (NVIDIA 8GB VRAM)
./start.sh --build     # Rebuild lại images trước khi chạy
./start.sh --status    # Xem trạng thái container
./start.sh --logs      # Xem logs trực tiếp
./start.sh --down      # Tắt toàn bộ hệ thống
```

### Cách 2: Sử dụng Docker Compose Trực Tiếp

File `docker-compose.yml` tại thư mục gốc đã được liên kết với `docker/docker-compose.yml`:

```bash
# Khởi động toàn bộ cụm dịch vụ:
docker compose up -d

# Xem log:
docker compose logs -f

# Dừng hệ thống:
docker compose down
```

### Cách 3: Sử dụng Makefile

```bash
make up         # Tương đương ./start.sh
make up-cpu     # Khởi động chế độ CPU/dev
make up-gpu     # Khởi động chế độ GPU production
make down       # Tương đương ./docker/stop.sh
make status     # Kiểm tra trạng thái
```

---

## 3. Kiến Trúc Mạng & Bảo Mật Container

```text
+-----------------------------------------------------------------+
|                         HOST MACHINE                            |
|    Port 8443 (HTTPS)                        Port 8080 (HTTP)    |
+---------+------------------------------------------+------------+
          |                                          |
          v                                          v
+-----------------------------------------------------------------+
|                       rvt_web (Nginx)                           |
|   - Serves React PWA bundle                                     |
|   - SSL Termination (/etc/nginx/tls/cert.pem)                   |
|   - Proxy /ws & /v1/stream -> rvt_ai:8000                       |
|   - Proxy /api/* -> rvt_ai:8000/api/*                           |
+-------------------------------+---------------------------------+
                                | rvt_web_net (bridge)
                                v
+-----------------------------------------------------------------+
|                        rvt_ai (FastAPI)                         |
|   - VAD (Silero ONNX), ASR (Faster-Whisper), LID Policy         |
|   - Port 8000 CHỈ mở trong nội bộ container                     |
+-------------------------------+---------------------------------+
                                | rvt_backend_net (internal)
                                v
+-----------------------------------------------------------------+
|                      rvt_mt (llama.cpp)                         |
|   - Hy-MT2 GGUF Translation Engine                              |
|   - Port 8080 CHỈ mở trong internal network                     |
+-----------------------------------------------------------------+
```

- **Zero Outside Leakage:** Cả `rvt_ai` và `rvt_mt` đều **không** bind port ra bên ngoài Host. Tất cả request bắt buộc phải đi qua Nginx reverse proxy với TLS mã hoá và HMAC session authentication.
- **Tự Động Sinh Chứng Chỉ TLS:** Khi chạy `./start.sh`, nếu chưa có chứng chỉ tại `config/tls/`, script sẽ tự động tạo chứng chỉ self-signed bằng OpenSSL/mkcert để Nginx khởi động trơn tru không lỗi.
