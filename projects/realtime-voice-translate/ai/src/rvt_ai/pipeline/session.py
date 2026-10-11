import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine, MtEngine, VadEngine
from rvt_ai.pipeline.lid_policy import pick_language, update_side_prior
from rvt_ai.pipeline.mt_validator import mt_validator
from rvt_ai.pipeline.scheduler import AsrScheduler
from rvt_ai.pipeline.segmenter import Segmenter, SegmenterConfig
from rvt_contracts.messages import (
    AsrFinal,
    AsrPartial,
    ErrorEvent,
    Lang,
    MtDelta,
    MtFinal,
    ServerEvent,
    SessionStart,
    Side,
    SidesUpdate,
    Vad,
)


class RVTSession:
    def __init__(
        self,
        session_id: str,
        vad: VadEngine,
        asr: AsrEngine,
        mt: MtEngine,
        send_event_cb: Callable[[ServerEvent], Awaitable[None]],
        segmenter_config: SegmenterConfig | None = None,
    ):
        self.session_id = session_id
        self.vad = vad
        self.vad_state = self.vad.create_state()
        self.asr = asr
        self.mt = mt
        self.send_event = send_event_cb
        self.scheduler = AsrScheduler(self.asr.transcribe)

        self.segmenter = Segmenter(segmenter_config or SegmenterConfig())
        self.current_side: Side | None = None
        self.sides_config: dict[Side, str] = {"A": "auto", "B": "auto"}
        self.sides_prior: dict[Side, dict[Lang, float]] = {
            "A": {"vi": 0.33, "en": 0.33, "ja": 0.33},
            "B": {"vi": 0.33, "en": 0.33, "ja": 0.33},
        }
        self.utterance_id_counter = 0

        # In-memory recent utterances audio buffer (LRU max 10) for utterance.override_lang
        self.recent_audio: OrderedDict[int, bytes] = OrderedDict()
        self.max_cached_utterances = 10

        # Track running MT tasks for graceful cancellation
        self.active_tasks: list[asyncio.Task] = []
        self.last_activity_time = time.time()

    async def handle_session_start(self, event: SessionStart) -> bool:
        self.last_activity_time = time.time()
        if event.protocol != 1:
            await self.send_event(
                ErrorEvent(
                    code="unsupported_protocol",
                    message=f"Unsupported protocol version: {event.protocol}",
                    retryable=False,
                )
            )
            return False

        if event.audio.rate != 16000 or event.audio.format not in ("pcm_s16le", "pcm16"):
            await self.send_event(
                ErrorEvent(
                    code="unsupported_audio_format",
                    message=f"Expected 16kHz pcm_s16le, got {event.audio.rate}Hz {event.audio.format}",
                    retryable=False,
                )
            )
            return False

        if "A" in event.sides and "B" in event.sides:
            self.sides_config["A"] = event.sides["A"].lang
            self.sides_config["B"] = event.sides["B"].lang
        return True

    async def handle_sides_update(self, event: SidesUpdate) -> None:
        self.last_activity_time = time.time()
        for side, cfg in event.sides.items():
            self.sides_config[side] = cfg.lang
        logger.info(f"[{self.session_id}] Sides updated: {self.sides_config}")

    async def handle_turn_start(self, side: Side) -> None:
        self.last_activity_time = time.time()
        logger.info(f"[{self.session_id}] 🎙️ Turn START on Side {side}")
        if self.current_side != side:
            await self._flush_segmenter()
        self.current_side = side
        self.vad_state.reset()

    async def handle_turn_stop(self) -> None:
        self.last_activity_time = time.time()
        logger.info(f"[{self.session_id}] ⏹️ Turn STOP on Side {self.current_side}")
        await self._flush_segmenter()
        self.current_side = None

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        self.last_activity_time = time.time()
        if not self.current_side:
            return

        was_speaking = self.segmenter.is_speaking
        has_speech = self.vad.process(chunk, self.vad_state)
        await self.send_event(Vad(side=self.current_side, speaking=has_speech))

        if has_speech and not was_speaking:
            logger.info(f"[{self.session_id}] 🗣️ VAD: Speech DETECTED on Side {self.current_side}")

        should_partial, should_final, buffer = self.segmenter.add_chunk(chunk, has_speech)

        if should_partial and len(buffer) > 0:
            uid = self.utterance_id_counter
            side = self.current_side
            asyncio.create_task(self._process_partial_audio(buffer, side, uid))

        if should_final and len(buffer) > 0:
            duration_ms = len(buffer) * 1000 // 32000
            logger.info(f"[{self.session_id}] ⏱️ Segmenter: Speech ended, final audio ({duration_ms}ms)")
            await self._process_final_audio(buffer, self.current_side)

    async def handle_override_lang(self, utterance_id: int, new_lang: Lang) -> None:
        self.last_activity_time = time.time()
        if utterance_id not in self.recent_audio:
            await self.send_event(
                ErrorEvent(
                    code="utterance_not_found",
                    message=f"Utterance {utterance_id} audio is no longer available in memory",
                    utterance_id=utterance_id,
                    retryable=False,
                )
            )
            return

        audio = self.recent_audio[utterance_id]
        logger.info(f"[{self.session_id}] Re-transcribing utterance {utterance_id} with forced lang={new_lang}")

        text, _, asr_probs = await self.scheduler.execute_transcribe(audio, force_lang=new_lang, is_final=True)

        await self.send_event(
            AsrFinal(
                utterance_id=utterance_id,
                side=self.current_side or "A",
                text=text,
                lang=new_lang,
                lang_probs=asr_probs,
                uncertain=False,
                audio_ms=len(audio) * 1000 // 32000,
            )
        )

        # Re-translate to the other two targets
        targets = [tgt for tgt in ["ja", "en", "vi"] if tgt != new_lang]
        for tgt in targets:
            task = asyncio.create_task(self._run_mt(utterance_id, text, new_lang, tgt))
            self.active_tasks.append(task)

    async def _flush_segmenter(self) -> None:
        if self.current_side and self.segmenter.is_speaking:
            buf = self.segmenter.force_final()
            if len(buf) > 0:
                await self._process_final_audio(buf, self.current_side)

    async def _process_partial_audio(self, audio: bytes, side: Side, uid: int) -> None:
        try:
            force_lang = self.sides_config[side] if self.sides_config[side] != "auto" else None
            text, lang, _ = await self.scheduler.execute_transcribe(audio, force_lang=force_lang, is_final=False)
            if text and self.current_side == side:
                await self.send_event(AsrPartial(utterance_id=uid, side=side, text=text, lang=lang))
        except Exception as e:
            logger.debug(f"Partial ASR error: {e}")

    async def _process_final_audio(self, audio: bytes, side: Side) -> None:
        uid = self.utterance_id_counter
        self.utterance_id_counter += 1

        # Cache in LRU buffer
        self.recent_audio[uid] = audio
        if len(self.recent_audio) > self.max_cached_utterances:
            self.recent_audio.popitem(last=False)

        # 1. ASR + LID
        force_lang = None
        if self.sides_config[side] != "auto":
            force_lang = self.sides_config[side]

        text, detected_lang, asr_probs = await self.scheduler.execute_transcribe(
            audio, force_lang=force_lang, is_final=True
        )

        # 2. LID Policy
        if force_lang:
            final_lang = force_lang  # type: ignore
            uncertain = False
        else:
            decision = pick_language(asr_probs, self.sides_prior[side])
            final_lang = decision.lang
            uncertain = decision.uncertain

            # If chosen language differs from initial detected language and not uncertain, re-decode
            if final_lang != detected_lang and not uncertain and text:
                text, _, _ = await self.scheduler.execute_transcribe(audio, force_lang=final_lang, is_final=True)

        # Update prior if confident
        if not uncertain:
            self.sides_prior[side] = update_side_prior(self.sides_prior[side], final_lang)

        # 3. Emit ASR Final
        logger.info(f"[{self.session_id}] 📝 ASR Final: '{text}' [lang={final_lang}, probs={asr_probs}]")
        await self.send_event(
            AsrFinal(
                utterance_id=uid,
                side=side,
                text=text,
                lang=final_lang,
                lang_probs=asr_probs,
                uncertain=uncertain,
                audio_ms=len(audio) * 1000 // 32000,
            )
        )

        # 4. Trigger MT for the other two languages
        targets = [tgt for tgt in ["ja", "en", "vi"] if tgt != final_lang]
        mt_tasks = []
        for tgt in targets:
            task = asyncio.create_task(self._run_mt(uid, text, final_lang, tgt))
            self.active_tasks.append(task)
            mt_tasks.append(task)

    async def _run_mt(self, uid: int, text: str, source: Lang, target: Lang) -> None:

        # Check exact cache first
        cached = mt_validator.get_cached(source, target, text)
        if cached:
            await self.send_event(MtFinal(utterance_id=uid, target=target, text=cached))
            return

        full_text = ""
        try:
            async for delta in self.mt.translate_stream(text, source, target):
                full_text += delta
                await self.send_event(MtDelta(utterance_id=uid, target=target, delta=delta))

            # Validate output
            v_res = mt_validator.validate(text, source, target, full_text)
            if not v_res.is_valid:
                logger.warning(f"MT output validation failed: {v_res.error_reason}")
                # Emit ErrorEvent
                await self.send_event(
                    ErrorEvent(
                        code="mt_validation_failed",
                        message=f"Translation failed validation ({v_res.error_reason})",
                        utterance_id=uid,
                        retryable=False,
                    )
                )
                await self.send_event(MtFinal(utterance_id=uid, target=target, text=f"[Lỗi dịch {target}]"))
            else:
                logger.info(f"[{self.session_id}] 🌐 MT Final ({source}->{target}): '{v_res.cleaned_text}'")
                mt_validator.cache_translation(source, target, text, v_res.cleaned_text)
                await self.send_event(MtFinal(utterance_id=uid, target=target, text=v_res.cleaned_text))
        except Exception as e:
            logger.error(f"MT failed for {target}: {e}")
            await self.send_event(
                ErrorEvent(code="mt_failed", message=f"MT failed for {target}: {e}", utterance_id=uid, retryable=True)
            )
            await self.send_event(MtFinal(utterance_id=uid, target=target, text=f"[Lỗi dịch {target}]"))

    async def close(self) -> None:
        logger.info(f"Closing session {self.session_id}...")
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        self.active_tasks.clear()
        self.recent_audio.clear()
