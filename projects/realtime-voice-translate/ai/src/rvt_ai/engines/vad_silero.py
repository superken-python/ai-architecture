import hashlib
import os
import urllib.request

import numpy as np
import onnxruntime as ort

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import VadEngine

# Ghim đúng một bản model: file trên nhánh master của silero-vad đổi theo thời gian (v5.1 → v6.0 → v6.2) và mỗi bản
# phản ứng khác nhau khi gọi sai cách. Đổi bản thì cập nhật cả config/models.yaml và scripts/download_models.sh.
SILERO_VAD_VERSION = "v6.2.1"
SILERO_VAD_URL = (
    f"https://raw.githubusercontent.com/snakers4/silero-vad/{SILERO_VAD_VERSION}/src/silero_vad/data/silero_vad.onnx"
)
SILERO_VAD_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
SILERO_VAD_FALLBACK_URL = "https://huggingface.co/onnx-community/silero-vad/resolve/main/onnx/model.onnx"

# Model v5 trở lên ở 16 kHz cần 64 mẫu cuối của cửa sổ trước ghép vào đầu mỗi cửa sổ 512 mẫu (như OnnxWrapper của
# silero-vad). Thiếu phần này, bản v6.2 trả xác suất ≈ 0 cho mọi tiếng nói — xem docs/04-cai-thien-thu-am-tu-xa.md.
CONTEXT_SAMPLES = 64


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class SileroVadState:
    def __init__(self, is_v5: bool = True):
        self.is_v5 = is_v5
        self.reset()

    def reset(self) -> None:
        if self.is_v5:
            self.state = np.zeros((2, 1, 128), dtype=np.float32)
            self.context = np.zeros(CONTEXT_SAMPLES, dtype=np.float32)
        else:
            self.h = np.zeros((2, 1, 64), dtype=np.float32)
            self.c = np.zeros((2, 1, 64), dtype=np.float32)
        self.audio_remainder = np.empty(0, dtype=np.float32)


class SileroVadEngine(VadEngine):
    def __init__(self, model_dir: str = "models"):
        model_path = os.path.join(model_dir, "silero_vad.onnx")

        if not os.path.exists(model_path):
            fallback_path = "/tmp/silero_vad.onnx"
            if os.path.exists(fallback_path):
                model_path = fallback_path
            else:
                target_dest = model_path
                try:
                    os.makedirs(model_dir, exist_ok=True)
                except OSError:
                    target_dest = fallback_path

                downloaded = False
                for url, expected_sha256 in ((SILERO_VAD_URL, SILERO_VAD_SHA256), (SILERO_VAD_FALLBACK_URL, None)):
                    try:
                        logger.info(f"Downloading Silero VAD model from {url}...")
                        urllib.request.urlretrieve(url, target_dest)
                    except Exception as err:
                        logger.warning(f"Download failed from {url}: {err}")
                        continue
                    if expected_sha256 and _sha256(target_dest) != expected_sha256:
                        logger.warning(f"Checksum mismatch for {url}, discarding the file")
                        os.remove(target_dest)
                        continue
                    model_path = target_dest
                    downloaded = True
                    break

                if not downloaded:
                    raise FileNotFoundError(f"Could not download Silero VAD model to {target_dest}")

        model_sha256 = _sha256(model_path)
        if model_sha256 != SILERO_VAD_SHA256:
            logger.warning(
                f"Silero VAD model {model_path} (sha256 {model_sha256[:12]}) is not the pinned {SILERO_VAD_VERSION}; "
                "delete it and run scripts/download_models.sh to get the pinned version"
            )

        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_names = [x.name for x in self.session.get_inputs()]
        self.is_v5 = "state" in self.input_names
        logger.info(
            f"Loaded Silero VAD ({'v5+' if self.is_v5 else 'v4'}, sha256 {model_sha256[:12]}) from {model_path}"
        )
        self.window_size = 512  # 32ms at 16kHz

    def create_state(self) -> SileroVadState:
        return SileroVadState(is_v5=self.is_v5)

    def process(self, chunk: bytes, state: SileroVadState) -> float:
        """Xác suất có tiếng nói lớn nhất trong chunk. Việc quyết định (có hysteresis) do Segmenter làm."""
        # Convert 16bit PCM to float32 normalized [-1, 1]
        audio = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0

        # Prepend leftover from previous chunk
        if len(state.audio_remainder) > 0:
            audio = np.concatenate([state.audio_remainder, audio])

        max_prob = 0.0
        idx = 0
        while idx + self.window_size <= len(audio):
            window = audio[idx : idx + self.window_size]
            idx += self.window_size

            if self.is_v5:
                x = np.concatenate([state.context, window])[np.newaxis, :]  # [1, 64 + 512]
                ort_inputs = {"input": x, "state": state.state, "sr": np.array(16000, dtype=np.int64)}
                out, state.state = self.session.run(None, ort_inputs)
                state.context = x[0, -CONTEXT_SAMPLES:]
            else:
                ort_inputs = {
                    "input": window[np.newaxis, :],
                    "sr": np.array([16000], dtype=np.int64),
                    "h": state.h,
                    "c": state.c,
                }
                out, state.h, state.c = self.session.run(None, ort_inputs)

            max_prob = max(max_prob, float(out[0][0]))

        state.audio_remainder = audio[idx:]
        return max_prob
