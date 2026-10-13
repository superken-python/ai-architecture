"""Cấu hình logging tối giản cho POC."""

import logging


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx log mỗi request ở INFO — quá ồn khi agent gọi API liên tục
    logging.getLogger("httpx").setLevel(logging.WARNING)
