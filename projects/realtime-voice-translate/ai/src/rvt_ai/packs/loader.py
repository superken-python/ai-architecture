import hashlib
import os

import yaml
from pydantic import BaseModel

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger


class VadConfig(BaseModel):
    engine: str = "fake"
    threshold: float = 0.5
    min_speech_ms: int = 250
    min_silence_ms: int = 500
    speech_pad_ms: int = 200
    preroll_ms: int = 300
    max_ms: int = 15000
    hard_max_ms: int = 20000
    partial_interval_ms: int = 800


class AsrConfig(BaseModel):
    engine: str = "fake"
    model: str = "fake"
    device: str = "cpu"
    compute_type: str = "float32"


class MtConfig(BaseModel):
    engine: str = "fake"
    model: str = "fake"
    temperature: float = 0.1
    top_p: float = 0.95
    max_tokens: int = 256


class ProfileConfig(BaseModel):
    name: str
    description: str
    vad: VadConfig
    asr: AsrConfig
    mt: MtConfig


class PackRegistry:
    def __init__(self, packs_dir: str):
        self.packs_dir = packs_dir
        self.profiles: dict[str, ProfileConfig] = {}
        self.revision: str = "1"
        self._load()

    def _load(self):
        profiles_dir = os.path.join(self.packs_dir, "profiles")
        hasher = hashlib.sha256()

        if os.path.exists(profiles_dir):
            for fname in sorted(os.listdir(profiles_dir)):
                if fname.endswith((".yaml", ".yml")):
                    path = os.path.join(profiles_dir, fname)
                    with open(path, "rb") as f:
                        content = f.read()
                        hasher.update(content)
                        data = yaml.safe_load(content.decode("utf-8"))
                        prof = ProfileConfig.model_validate(data)
                        self.profiles[prof.name] = prof

        self.revision = hasher.hexdigest()[:12]
        logger.info(f"Loaded {len(self.profiles)} profiles. Pack revision: {self.revision}")

    def get_profile(self, name: str) -> ProfileConfig:
        if name in self.profiles:
            return self.profiles[name]
        if "fake" in self.profiles:
            return self.profiles["fake"]
        # Fallback default
        return ProfileConfig(name=name, description="Fallback profile", vad=VadConfig(), asr=AsrConfig(), mt=MtConfig())


# Global pack registry initialized from settings
def get_pack_registry() -> PackRegistry:
    packs_path = os.path.abspath(settings.PACKS_DIR)
    if not os.path.exists(packs_path):
        # Fallback relative to project root
        packs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packs"))
    return PackRegistry(packs_path)
