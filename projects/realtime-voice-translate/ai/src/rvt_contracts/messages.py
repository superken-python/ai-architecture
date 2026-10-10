from typing import Annotated, Literal

from pydantic import BaseModel, Field

Lang = Literal["ja", "en", "vi"]
Side = Literal["A", "B"]


class AudioConfig(BaseModel):
    rate: int = 16000
    format: str = "pcm_s16le"


class SideConfig(BaseModel):
    lang: str = "auto"  # "auto" or Lang


# Client -> Server


class SessionStart(BaseModel):
    type: Literal["session.start"] = "session.start"
    protocol: int = 1
    audio: AudioConfig = Field(default_factory=AudioConfig)
    sides: dict[Side, SideConfig] = Field(default_factory=lambda: {"A": SideConfig(), "B": SideConfig()})


class TurnStart(BaseModel):
    type: Literal["turn.start"] = "turn.start"
    side: Side


class TurnStop(BaseModel):
    type: Literal["turn.stop"] = "turn.stop"


class UtteranceOverrideLang(BaseModel):
    type: Literal["utterance.override_lang"] = "utterance.override_lang"
    utterance_id: int
    lang: Lang


class SidesUpdate(BaseModel):
    type: Literal["sides.update"] = "sides.update"
    sides: dict[Side, SideConfig]


class Ping(BaseModel):
    type: Literal["ping"] = "ping"
    t: int


# Server -> Client


class SessionReady(BaseModel):
    type: Literal["session.ready"] = "session.ready"
    session_id: str
    profile: str
    pack_revision: str
    models: dict


class Vad(BaseModel):
    type: Literal["vad"] = "vad"
    side: Side
    speaking: bool


class AsrPartial(BaseModel):
    type: Literal["asr.partial"] = "asr.partial"
    utterance_id: int
    side: Side
    text: str
    lang: Lang | None = None


class AsrFinal(BaseModel):
    type: Literal["asr.final"] = "asr.final"
    utterance_id: int
    side: Side
    text: str
    lang: Lang
    lang_probs: dict[Lang, float]
    uncertain: bool
    audio_ms: int


class MtDelta(BaseModel):
    type: Literal["mt.delta"] = "mt.delta"
    utterance_id: int
    target: Lang
    delta: str


class MtFinal(BaseModel):
    type: Literal["mt.final"] = "mt.final"
    utterance_id: int
    target: Lang
    text: str


class UtteranceMetrics(BaseModel):
    type: Literal["utterance.metrics"] = "utterance.metrics"
    utterance_id: int
    asr_ms: int
    mt_ms: dict[Lang, int]
    e2e_ms: int


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    utterance_id: int | None = None
    retryable: bool


class Pong(BaseModel):
    type: Literal["pong"] = "pong"
    t: int
    server_t: int


# REST Models (Universal Response Rule: Always return Pydantic v2 models)


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    ready: bool
    profile: str
    pack_revision: str
    models: dict[str, str]


class SessionTokenRequest(BaseModel):
    access_code: str | None = None


class SessionTokenResponse(BaseModel):
    token: str
    expires_in: int


class TranslateRequest(BaseModel):
    text: str
    source: Lang | None = None


class TranslateResponse(BaseModel):
    source: Lang
    translations: dict[Lang, str]


class TranscribeResponse(BaseModel):
    text: str
    lang: Lang
    lang_probs: dict[Lang, float]


class SpeechTranslateResponse(BaseModel):
    text: str
    source_lang: Lang
    lang_probs: dict[Lang, float]
    translations: dict[Lang, str]


class MetricsResponse(BaseModel):
    active_sessions: int
    max_sessions: int
    profile: str
    pack_revision: str


ClientEvent = Annotated[
    SessionStart | TurnStart | TurnStop | UtteranceOverrideLang | SidesUpdate | Ping, Field(discriminator="type")
]

ServerEvent = Annotated[
    SessionReady | Vad | AsrPartial | AsrFinal | MtDelta | MtFinal | UtteranceMetrics | ErrorEvent | Pong,
    Field(discriminator="type"),
]
