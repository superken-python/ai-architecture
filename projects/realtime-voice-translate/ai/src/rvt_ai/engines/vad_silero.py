import os
import urllib.request

import numpy as np
import onnxruntime as ort

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import VadEngine


class SileroVadState:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.h = np.zeros((2, 1, 64), dtype=np.float32)
        self.c = np.zeros((2, 1, 64), dtype=np.float32)
        self.audio_remainder = np.empty(0, dtype=np.float32)


class SileroVadEngine(VadEngine):
    def __init__(self, model_dir: str = "models", threshold: float = 0.5):
        self.threshold = threshold
        model_path = os.path.join(model_dir, "silero_vad.onnx")

        if not os.path.exists(model_path):
            fallback_path = "/tmp/silero_vad.onnx"
            if os.path.exists(fallback_path):
                model_path = fallback_path
            else:
                urls = [
                    "https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx",
                    "https://huggingface.co/onnx-community/silero-vad/resolve/main/onnx/model.onnx",
                ]
                target_dest = model_path
                try:
                    os.makedirs(model_dir, exist_ok=True)
                except OSError:
                    target_dest = fallback_path

                downloaded = False
                for u in urls:
                    try:
                        logger.info(f"Downloading Silero VAD model from {u}...")
                        urllib.request.urlretrieve(u, target_dest)
                        model_path = target_dest
                        downloaded = True
                        break
                    except Exception as err:
                        logger.warning(f"Download failed from {u}: {err}")

                if not downloaded:
                    raise FileNotFoundError(f"Could not download Silero VAD model to {target_dest}")

        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.window_size = 512  # 32ms at 16kHz

    def create_state(self) -> SileroVadState:
        return SileroVadState()

    def process(self, chunk: bytes, state: SileroVadState) -> bool:
        # Convert 16bit PCM to float32 normalized [-1, 1]
        audio_int16 = np.frombuffer(chunk, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Prepend leftover from previous chunk
        if len(state.audio_remainder) > 0:
            audio = np.concatenate([state.audio_remainder, audio_float32])
        else:
            audio = audio_float32

        has_speech = False
        idx = 0
        while idx + self.window_size <= len(audio):
            window = audio[idx : idx + self.window_size]
            idx += self.window_size

            input_data = np.expand_dims(window, axis=0)  # [1, 512]
            ort_inputs = {"input": input_data, "sr": np.array([16000], dtype=np.int64), "h": state.h, "c": state.c}

            ort_outs = self.session.run(None, ort_inputs)
            out, state.h, state.c = ort_outs
            prob = float(out[0][0])
            if prob > self.threshold:
                has_speech = True

        state.audio_remainder = audio[idx:]
        return has_speech
