from pydantic import BaseModel


class SegmenterConfig(BaseModel):
    sample_rate: int = 16000
    threshold: float = 0.5  # p >= threshold: bắt đầu câu
    neg_threshold: float = 0.35  # đang nói thì chỉ coi là im lặng khi p < neg_threshold (Silero: threshold - 0.15)
    min_speech_ms: int = 200
    min_silence_ms: int = 500
    speech_pad_ms: int = 200
    preroll_ms: int = 400
    max_ms: int = 4000  # 4s max cho video nói liền/anime
    hard_max_ms: int = 6000  # 6s cắt cứng
    partial_interval_ms: int = 800


class SegmentStats(BaseModel):
    """Thống kê VAD của câu vừa chốt, để log theo câu."""

    speech_ms: int
    prob_mean: float
    prob_max: float


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
        self.last_stats: SegmentStats | None = None
        self.frame_probs: list[float] = []
        self._prob_sum = 0.0
        self._prob_count = 0
        self._prob_max = 0.0

    def add_chunk(self, chunk: bytes, speech_prob: float) -> tuple[bool, bool, bytes]:
        """
        Nạp chunk mới kèm xác suất có tiếng nói của VAD.
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

        # Hysteresis: bắt đầu câu khi p >= threshold, nhưng đang nói thì p >= neg_threshold vẫn tính là tiếng nói.
        threshold = self.config.neg_threshold if self.is_speaking else self.config.threshold
        has_speech = speech_prob >= threshold

        if has_speech:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_start_ms = max(0, self.current_time_ms - chunk_ms)
                self.frame_probs = []
                self._prob_sum = 0.0
                self._prob_count = 0
                self._prob_max = 0.0
            self.last_speech_ms = self.current_time_ms
            self._prob_sum += speech_prob
            self._prob_count += 1
            self._prob_max = max(self._prob_max, speech_prob)

        if self.is_speaking:
            self.frame_probs.append(speech_prob)

        should_partial = False
        should_final = False

        if self.is_speaking and self.speech_start_ms is not None:
            duration_ms = self.current_time_ms - self.speech_start_ms

            # Chỉ nhận dạng tạm khi đã có ít nhất min(interval, 1000)ms audio và đủ chu kỳ
            min_partial_duration = min(self.config.partial_interval_ms, 1000)
            if duration_ms >= min_partial_duration and (
                self.current_time_ms - self.last_partial_ms >= self.config.partial_interval_ms
            ):
                should_partial = True
                self.last_partial_ms = self.current_time_ms

            # Check for silence to trigger final
            if self.last_speech_ms is not None:
                silence_ms = self.current_time_ms - self.last_speech_ms
                required_silence_ms = self.config.min_silence_ms
                if duration_ms > 4000:
                    required_silence_ms = min(required_silence_ms, 250)

                if silence_ms >= required_silence_ms:
                    if (self.last_speech_ms - self.speech_start_ms) >= self.config.min_speech_ms:
                        should_final = True
                    else:
                        # Speech too short (e.g. noise/cough), drop it
                        self.reset()

            # Check for max_ms và cắt ở chỗ lặng nhất (Mục 5.1 docs 06)
            if not should_final and duration_ms >= self.config.max_ms:
                chunk_bytes = (self.config.sample_rate * 2 * chunk_ms) // 1000
                preroll_bytes = min(
                    len(self.buffer),
                    (self.config.preroll_ms * self.config.sample_rate * 2) // 1000,
                )
                n = len(self.frame_probs)
                window_frames = max(1, 1500 // chunk_ms)
                tail_frames = max(1, 200 // chunk_ms)
                start_idx = max(0, n - window_frames)
                end_idx = max(start_idx + 1, n - tail_frames)

                k = min(range(start_idx, end_idx), key=self.frame_probs.__getitem__)
                if self.frame_probs[k] < self.config.neg_threshold or duration_ms >= self.config.hard_max_ms:
                    cut = preroll_bytes + (k + 1) * chunk_bytes
                    cut = min(cut, len(self.buffer))
                    final_audio = bytes(self.buffer[:cut])
                    self.buffer = self.buffer[cut:]
                    self.frame_probs = self.frame_probs[k + 1 :]
                    self.speech_start_ms = self.current_time_ms - len(self.frame_probs) * chunk_ms
                    self.last_speech_ms = self.current_time_ms
                    self.last_partial_ms = self.current_time_ms
                    stats = self._stats()
                    self.last_stats = stats
                    return should_partial, True, final_audio

        buffer_out = bytes(self.buffer)
        if should_final:
            stats = self._stats()
            self.reset()
            self.last_stats = stats

        return should_partial, should_final, buffer_out

    def _stats(self) -> SegmentStats:
        speech_ms = 0
        if self.speech_start_ms is not None and self.last_speech_ms is not None:
            speech_ms = self.last_speech_ms - self.speech_start_ms
        prob_mean = self._prob_sum / self._prob_count if self._prob_count else 0.0
        return SegmentStats(speech_ms=speech_ms, prob_mean=prob_mean, prob_max=self._prob_max)

    def reset(self) -> None:
        self.buffer = bytearray()
        self.is_speaking = False
        self.speech_start_ms = None
        self.last_speech_ms = None
        self.last_partial_ms = self.current_time_ms
        self.last_stats = None
        self.frame_probs = []
        self._prob_sum = 0.0
        self._prob_count = 0
        self._prob_max = 0.0

    def force_final(self) -> bytes:
        if self.speech_start_ms is None:
            self.reset()
            return b""
        min_bytes = (self.config.sample_rate * 2 * self.config.min_speech_ms) // 1000
        out = bytes(self.buffer) if len(self.buffer) >= min_bytes else b""
        stats = self._stats()
        self.reset()
        if out:
            self.last_stats = stats
        return out
