import functools
import inspect
import time
from collections.abc import Callable
from typing import Any

from excel_agent.core.logging import app_logger


def measure_execution_time(action_name: str = "Tác vụ"):
    """
    Decorator đo thời gian thực thi của hàm và ghi log có cấu trúc.
    Hỗ trợ cả synchronous và asynchronous functions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            app_logger.bind(action=action_name).info(f"Bắt đầu thực thi: {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                app_logger.bind(action=action_name, duration_ms=round(duration_ms, 2)).info(
                    f"Hoàn thành {func.__name__} trong {duration_ms:.2f}ms"
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000
                app_logger.bind(action=action_name, duration_ms=round(duration_ms, 2)).error(
                    f"Thất bại {func.__name__} sau {duration_ms:.2f}ms: {exc!s}"
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            app_logger.bind(action=action_name).info(f"Bắt đầu thực thi: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                app_logger.bind(action=action_name, duration_ms=round(duration_ms, 2)).info(
                    f"Hoàn thành {func.__name__} trong {duration_ms:.2f}ms"
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000
                app_logger.bind(action=action_name, duration_ms=round(duration_ms, 2)).error(
                    f"Thất bại {func.__name__} sau {duration_ms:.2f}ms: {exc!s}"
                )
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
