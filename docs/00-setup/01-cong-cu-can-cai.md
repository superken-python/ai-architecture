# 1 · Công cụ cần cài

Cần: **Git**, **uv** (quản lý Python và thư viện), **VS Code**, **make**. Tùy chọn: **Docker** (từ khi học
đóng gói model — kỹ năng OPS-01).

## Windows: dùng WSL2 (khuyên dùng)

Phần lớn công cụ AI (CUDA, vLLM, Docker, shell script) chạy mượt nhất trên Linux. Trên Windows, cài
**WSL2 + Ubuntu** rồi làm mọi thứ bên trong Ubuntu:

```powershell
# PowerShell chạy với quyền Administrator, rồi khởi động lại máy
wsl --install -d Ubuntu
```

Sau đó mở "Ubuntu" từ Start menu và làm theo phần **Linux / WSL2** bên dưới. Lưu ý:

- Để mã nguồn **trong** hệ thống file của Linux (`~/code/...`), không để ở `/mnt/c/...` — nhanh hơn nhiều lần.
- VS Code: cài extension **WSL**, rồi trong Ubuntu gõ `code .` để mở thư mục.
- GPU NVIDIA: chỉ cần cài driver NVIDIA **trên Windows**; WSL2 tự dùng được (xem [04-gpu-va-tinh-toan.md](04-gpu-va-tinh-toan.md)).

Nếu không dùng được WSL2: vẫn học được Nhóm 1–4, 6–8 trên Windows thuần — cài uv bằng PowerShell
(bên dưới) và chạy trực tiếp các lệnh trong Makefile.

## Linux / WSL2 (Ubuntu)

```bash
sudo apt update && sudo apt install -y git make curl build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL            # nạp lại PATH để nhận lệnh uv
```

## macOS

```bash
xcode-select --install                     # Git + công cụ biên dịch
curl -LsSf https://astral.sh/uv/install.sh | sh
# hoặc nếu dùng Homebrew:  brew install git uv
```

## Windows thuần (PowerShell, không WSL)

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Cấu hình Git (mọi hệ điều hành)

```bash
git config --global user.name "Họ Tên"
git config --global user.email "email@congty.vn"
git config --global init.defaultBranch main
git config --global core.autocrlf input    # tránh lỗi xuống dòng giữa Windows và Linux
```

Xác thực với GitHub: dùng [GitHub CLI](https://cli.github.com/) (`gh auth login`) hoặc SSH key. Không dán
token vào URL remote.

## VS Code

Cài [VS Code](https://code.visualstudio.com/). Khi mở repo, VS Code sẽ gợi ý các extension trong
[.vscode/extensions.json](../../.vscode/extensions.json): Python, Jupyter, Ruff, EditorConfig, YAML,
Markdown Mermaid. Chọn interpreter: `Ctrl/Cmd+Shift+P` → *Python: Select Interpreter* → `.venv`.

## Docker (tùy chọn, cần từ kỹ năng OPS-01)

- Windows/macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (bật tích hợp WSL2 trên Windows).
- Linux: [Docker Engine](https://docs.docker.com/engine/install/ubuntu/), rồi `sudo usermod -aG docker $USER`.

Kiểm tra: `docker run --rm hello-world`.

## Kiểm tra

```bash
git --version && uv --version && make --version | head -1
```

Tiếp theo: [2 · Môi trường Python](02-moi-truong-python.md).
