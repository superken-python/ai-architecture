from pydantic import BaseModel


class SegmenterConfig(BaseModel):
    sample_rate: int = 16000
    min_speech_ms: int = 250
    min_silence_ms: int = 500
    speech_pad_ms: int = 200
    preroll_ms: int = 300
    max_ms: int = 15000
    hard_max_ms: int = 20000
    partial_interval_ms: int = 800


class Segmenter:
    """Quản lý buffer âm thanh cho một phiên, cắt câu dựa trên VAD và thời gian."""

    def __init__(self, config: SegmenterConfig | None = None):
        self.config = config or SegmenterConfig()
        self.buffer = bytearray()
        self.is_speaking = False
        self.speech_start_ms: int | None = None
        self.last_speech_ms: int | None = None
        self.current_time_ms: int = 0
        self.last_partial_ms: int = 0

    def add_chunk(self, chunk: bytes, has_speech: bool) -> tuple[bool, bool, bytes]:
        """
        Nạp chunk mới.
        Trả về (should_partial, should_final, buffer_so_far)
        """
        # PCM16 mono = 2 bytes per sample
        chunk_ms = len(chunk) * 1000 // (self.config.sample_rate * 2)
        self.current_time_ms += chunk_ms

        if not self.is_speaking:
            # Maintain a ring buffer for preroll
            self.buffer.extend(chunk)
            max_bytes = (self.config.preroll_ms * self.config.sample_rate * 2) // 1000
            if len(self.buffer) > max_bytes:
                self.buffer = self.buffer[-max_bytes:]
        else:
            self.buffer.extend(chunk)

        if has_speech:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_start_ms = max(0, self.current_time_ms - chunk_ms)
            self.last_speech_ms = self.current_time_ms

        should_partial = False
        should_final = False

        if self.is_speaking:
            # Check for partial interval
            if self.current_time_ms - self.last_partial_ms >= self.config.partial_interval_ms:
                should_partial = True
                self.last_partial_ms = self.current_time_ms

            # Check for silence to trigger final
            if (
                self.last_speech_ms is not None
                and self.speech_start_ms is not None
                and (self.current_time_ms - self.last_speech_ms) >= self.config.min_silence_ms
            ):
                if (self.last_speech_ms - self.speech_start_ms) >= self.config.min_speech_ms:
                    should_final = True
                else:
                    # Speech too short (e.g. noise/cough), drop it
                    self.reset()

            # Check for hard max (20s) or soft max (15s)
            if self.speech_start_ms is not None:
                duration_ms = self.current_time_ms - self.speech_start_ms
                if duration_ms >= self.config.hard_max_ms or (
                    duration_ms >= self.config.max_ms
                    and self.last_speech_ms is not None
                    and (self.current_time_ms - self.last_speech_ms) >= 200
                ):
                    should_final = True

        buffer_out = bytes(self.buffer)
        if should_final:
            self.reset()

        return should_partial, should_final, buffer_out

    def reset(self) -> None:
        self.buffer = bytearray()
        self.is_speaking = False
        self.speech_start_ms = None
        self.last_speech_ms = None
        self.last_partial_ms = self.current_time_ms

    def force_final(self) -> bytes:
        if (
            self.speech_start_ms is not None
            and self.last_speech_ms is not None
            and (self.last_speech_ms - self.speech_start_ms) >= self.config.min_speech_ms
        ):
            out = bytes(self.buffer)
        else:
            out = b""
        self.reset()
        return out
