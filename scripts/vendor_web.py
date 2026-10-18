#!/usr/bin/env python3
"""Tải thư viện JavaScript bên thứ ba cho trình xem tài liệu của trang web vào web/assets/vendor/.

    uv run python scripts/vendor_web.py

Trang web tự chứa thư viện (không gọi CDN) để sơ đồ mermaid và công thức luôn hiện được, kể cả khi CDN bị chặn.
Mỗi gói được ghim phiên bản và kiểm tra mã băm sha512 của gói npm (trường `integrity` của registry) trước khi giải nén.
Đổi phiên bản: sửa PACKAGES (version + integrity lấy ở https://registry.npmjs.org/<tên>/<phiên bản>) rồi chạy lại.
"""

from __future__ import annotations

import base64
import hashlib
import io
import shutil
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "web" / "assets" / "vendor"
PACKAGES = [
    {
        "name": "mermaid",
        "version": "11.17.2",
        "integrity": "sha512-V6K3C8EBdEsPFZXSKMJe6ppQOENxuHARr9GvHX4hh47lAbhMRD9qf4oEK7LoaRQxULMa80/qt5gHO73aCleBBg==",
        "files": {"dist/mermaid.min.js": "mermaid/mermaid.min.js", "LICENSE": "mermaid/LICENSE"},
    },
    {
        "name": "katex",
        "version": "0.16.47",
        "integrity": "sha512-Eeo8Ys1doU1z+x8AZsPpQu+p/QcZBI5PeOo7QGQdy2x2m0MU/hYagBbGOmXwr5KVbEfVuWv9LpnQWeehogurjg==",
        "files": {
            "dist/katex.min.js": "katex/katex.min.js",
            "dist/katex.min.css": "katex/katex.min.css",
            "LICENSE": "katex/LICENSE",
        },
        "dirs": {"dist/fonts/": ("katex/fonts/", ".woff2")},  # trình duyệt hiện đại chỉ cần woff2
    },
]


def fetch(pkg: dict) -> bytes:
    url = f"https://registry.npmjs.org/{pkg['name']}/-/{pkg['name']}-{pkg['version']}.tgz"
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    algo, _, expected = pkg["integrity"].partition("-")
    actual = base64.b64encode(hashlib.new(algo, data).digest()).decode()
    if actual != expected:
        raise SystemExit(f"{pkg['name']}@{pkg['version']}: mã băm không khớp — không giải nén")
    return data


def main() -> int:
    for pkg in PACKAGES:
        data = fetch(pkg)
        target_root = VENDOR / pkg["name"]
        if target_root.exists():
            shutil.rmtree(target_root)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member in tar.getmembers():
                name = member.name.removeprefix("package/")
                dest = pkg["files"].get(name)
                for prefix, (folder, ext) in pkg.get("dirs", {}).items():
                    if name.startswith(prefix) and name.endswith(ext) and "/" not in name[len(prefix) :]:
                        dest = folder + name[len(prefix) :]
                if dest is None or not member.isfile():
                    continue
                out = VENDOR / dest
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(tar.extractfile(member).read())
        size = sum(p.stat().st_size for p in target_root.rglob("*") if p.is_file())
        print(f"✓ {pkg['name']}@{pkg['version']} → {target_root.relative_to(ROOT)} ({size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
