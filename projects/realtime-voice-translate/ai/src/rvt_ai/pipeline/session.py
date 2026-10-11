import asyncio
import re
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable

import numpy as np

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine, MtEngine, VadEngine
from rvt_ai.pipeline.lid_policy import pick_language, update_side_prior
from rvt_ai.pipeline.mt_validator import mt_validator
from rvt_ai.pipeline.scheduler import AsrScheduler
from rvt_ai.pipeline.segmenter import Segmenter, SegmenterConfig, SegmentStats
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

SENTENCE_END_RE = re.compile(r"[。！？!?]")


def find_stable_prefix(prev: str, curr: str, committed: int) -> int:
    """
    Vị trí hết câu hoàn chỉnh cuối cùng mà hai lần nhận dạng tạm liên tiếp cùng có,
    không lùi so với committed (LocalAgreement - Mục 5.2 docs 06).
    """
    common = 0
    limit = min(len(prev), len(curr))
    while common < limit and prev[common] == curr[common]:
        common += 1

    matches = [m.end() for m in SENTENCE_END_RE.finditer(curr[:common])]
    valid = [end for end in matches if end > committed]
    return max(valid) if valid else committed


def _audio_summary(audio: bytes, stats: SegmentStats | None) -> str:
    """Mức âm và thống kê VAD của một câu — đọc log để biết câu bị rơi vì nhỏ hay vì VAD (docs/04 §7.2)."""
    samples = np.frombuffer(audio, np.int16).astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(samples**2))) if len(samples) else 0.0
    summary = f"audio={len(audio) * 1000 // 32000}ms level={20 * np.log10(max(rms, 1e-9)):.1f}dBFS"
    if stats:
        summary += f" speech={stats.speech_ms}ms vad_mean={stats.prob_mean:.2f} vad_max={stats.prob_max:.2f}"
    return summary


class RVTSession:
    def __init__(
        self,
        session_id: str,
        vad: VadEngine,
        asr: AsrEngine,
        mt: MtEngine,
        send_event_cb: Callable[[ServerEvent], Awaitable[None]],
        segmenter_config: SegmenterConfig | None = None,
        scheduler: AsrScheduler | None = None,
    ):
        self.session_id = session_id
        self.vad = vad
        self.vad_state = self.vad.create_state()
        self.asr = asr
        self.mt = mt
        self.send_event = send_event_cb
        self.scheduler = scheduler or AsrScheduler(self.asr.transcribe)
        self.recent_context: deque[str] = deque(maxlen=3)
        self.targets: list[Lang] | None = None

        self.segmenter = Segmenter(segmenter_config or SegmenterConfig())
        self.current_side: Side | None = None
        self.sides_config: dict[Side, str] = {"A": "auto", "B": "auto"}
        self.sides_prior: dict[Side, dict[Lang, float]] = {
            "A": {"vi": 0.33, "en": 0.33, "ja": 0.33},
            "B": {"vi": 0.33, "en": 0.33, "ja": 0.33},
        }
        self.utterance_id_counter = 0
        self.last_partial_uid: int | None = None
        self.last_partial_text: str = ""
        self.last_partial_lang: Lang = "vi"

        # Early commit tracking for fast continuous speech (LocalAgreement)
        self.prev_partial_text: str = ""
        self.committed_offset: int = 0
        self.committed_sentences: list[str] = []

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
        if event.targets is not None:
            self.targets = event.targets
        return True

    async def handle_sides_update(self, event: SidesUpdate) -> None:
        self.last_activity_time = time.time()
        for side, cfg in event.sides.items():
            self.sides_config[side] = cfg.lang
        if event.targets is not None:
            self.targets = event.targets
        logger.info(f"[{self.session_id}] Sides updated: {self.sides_config}, targets: {self.targets}")

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

        side = self.current_side
        was_speaking = self.segmenter.is_speaking
        speech_prob = self.vad.process(chunk, self.vad_state)
        should_partial, should_final, buffer = self.segmenter.add_chunk(chunk, speech_prob)

        # Chỉ gửi event vad khi trạng thái nói thay đổi (Mục 5.4 docs 06: giảm từ 25 event/s xuống vài event/phút)
        if self.segmenter.is_speaking != was_speaking:
            await self.send_event(Vad(side=side, speaking=self.segmenter.is_speaking))

        if self.segmenter.is_speaking and not was_speaking:
            logger.info(f"[{self.session_id}] 🗣️ VAD: Speech DETECTED on Side {side} (p={speech_prob:.2f})")
        elif was_speaking and not self.segmenter.is_speaking and not should_final:
            logger.debug(f"[{self.session_id}] VAD: segment shorter than min_speech_ms dropped on Side {side}")

        if should_final and len(buffer) > 0:
            duration_ms = len(buffer) * 1000 // 32000
            logger.info(f"[{self.session_id}] ⏱️ Segmenter: Speech ended, final audio ({duration_ms}ms)")
            task = asyncio.create_task(self._process_final_audio(buffer, side, self.segmenter.last_stats))
            self.active_tasks.append(task)
        elif should_partial and len(buffer) > 0:
            uid = self.utterance_id_counter
            asyncio.create_task(self._process_partial_audio(buffer, side, uid))

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
        if self.current_side:
            buf = self.segmenter.force_final()
            if len(buf) > 0:
                duration_ms = len(buf) * 1000 // 32000
                logger.info(f"[{self.session_id}] ⏱️ Flush on turn stop: processing final audio ({duration_ms}ms)")
                await self._process_final_audio(buf, self.current_side, self.segmenter.last_stats)

    async def _process_partial_audio(self, audio: bytes, side: Side, uid: int) -> None:
        try:
            force_lang = self.sides_config[side] if self.sides_config[side] != "auto" else None
            text, lang, _ = await self.scheduler.execute_transcribe(
                audio, force_lang=force_lang, is_final=False, session_id=self.session_id
            )
            if not text or self.current_side != side:
                return

            text = text.strip()

            # Early commit stable complete sentences (LocalAgreement - Mục 5.2 docs 06)
            if self.prev_partial_text and text:
                stable_end = find_stable_prefix(self.prev_partial_text, text, self.committed_offset)
                if stable_end > self.committed_offset:
                    stable_sentence = text[self.committed_offset : stable_end].strip()
                    if stable_sentence:
                        commit_uid = self.utterance_id_counter
                        self.utterance_id_counter += 1
                        logger.info(
                            f"[{self.session_id}] ⚡ Early-commit stable sentence: "
                            f"'{stable_sentence}' (uid={commit_uid})"
                        )
                        self.recent_context.append(stable_sentence)
                        self.committed_sentences.append(stable_sentence)
                        self.committed_offset = stable_end

                        # Emit asr.final for the early committed sentence
                        await self.send_event(
                            AsrFinal(
                                utterance_id=commit_uid,
                                side=side,
                                text=stable_sentence,
                                lang=lang,
                                lang_probs={},
                                uncertain=False,
                                audio_ms=0,
                            )
                        )

                        # Trigger MT immediately for the early committed sentence
                        if self.targets:
                            mt_targets = [tgt for tgt in self.targets if tgt != lang]
                        else:
                            mt_targets = [tgt for tgt in ["ja", "en", "vi"] if tgt != lang]
                        for tgt in mt_targets:
                            task = asyncio.create_task(self._run_mt(commit_uid, stable_sentence, lang, tgt))
                            self.active_tasks.append(task)

            self.prev_partial_text = text

            # Partials remaining for user view (the uncommitted portion)
            remaining_partial = text[self.committed_offset :].strip() if self.committed_offset < len(text) else ""
            active_partial_uid = self.utterance_id_counter

            if remaining_partial:
                self.last_partial_uid = active_partial_uid
                self.last_partial_text = remaining_partial
                self.last_partial_lang = lang
                await self.send_event(
                    AsrPartial(utterance_id=active_partial_uid, side=side, text=remaining_partial, lang=lang)
                )
            elif not self.committed_sentences:
                self.last_partial_uid = active_partial_uid
                self.last_partial_text = text
                self.last_partial_lang = lang
                await self.send_event(AsrPartial(utterance_id=active_partial_uid, side=side, text=text, lang=lang))
        except Exception as e:
            logger.debug(f"Partial ASR error: {e}")

    async def _process_final_audio(self, audio: bytes, side: Side, stats: SegmentStats | None = None) -> None:
        uid = self.utterance_id_counter
        self.utterance_id_counter += 1

        # Cancel any pending partial jobs for this session since final has arrived
        self.scheduler.cancel_session_partials(self.session_id)

        # Cache in LRU buffer
        self.recent_audio[uid] = audio
        if len(self.recent_audio) > self.max_cached_utterances:
            self.recent_audio.popitem(last=False)

        # 1. ASR + LID
        force_lang = None
        if self.sides_config[side] != "auto":
            force_lang = self.sides_config[side]

        try:
            text, detected_lang, asr_probs = await self.scheduler.execute_transcribe(
                audio, force_lang=force_lang, is_final=True, session_id=self.session_id
            )
        except Exception as e:
            logger.error(f"[{self.session_id}] Final transcribe error: {e}")
            text, detected_lang, asr_probs = "", "vi", {}

        # Remove already committed sentences from final text (Mục 5.2 docs 06)
        committed_to_clean = self.committed_sentences[:]
        self.committed_offset = 0
        self.committed_sentences = []
        self.prev_partial_text = ""
        # NOTE: Do NOT reset self.vad_state here! _process_final_audio runs asynchronously
        # while subsequent chunks are already streaming into handle_audio_chunk. Resetting VAD
        # state mid-stream causes Silero VAD v6.2 to lose recurrent context and miss subsequent speech.

        if committed_to_clean and text:
            clean_text = text.strip()
            for cs in committed_to_clean:
                cs_clean = cs.strip()
                if clean_text.startswith(cs_clean):
                    clean_text = clean_text[len(cs_clean) :].strip()
                elif clean_text.replace(" ", "").startswith(cs_clean.replace(" ", "")):
                    idx = 0
                    cs_no_space = cs_clean.replace(" ", "")
                    matched_chars = 0
                    while idx < len(clean_text) and matched_chars < len(cs_no_space):
                        if clean_text[idx] != " ":
                            matched_chars += 1
                        idx += 1
                    clean_text = clean_text[idx:].strip()
            text = clean_text

        # Rescue from partial if final Whisper returned empty but partial had valid recognized speech
        if (
            (not text or not text.strip())
            and not committed_to_clean
            and self.last_partial_uid == uid
            and self.last_partial_text
        ):
            logger.info(
                f"[{self.session_id}] Rescuing final text from previous partial for uid={uid}: "
                f"'{self.last_partial_text}'"
            )
            text = self.last_partial_text
            detected_lang = self.last_partial_lang

        if not text or not text.strip():
            if committed_to_clean:
                logger.info(f"[{self.session_id}] All speech in segment was already committed early, segment complete.")
                return

            logger.info(
                f"[{self.session_id}] 🔇 Audio transcribed to empty text (silence/noise), skipping "
                f"[side={side}, {_audio_summary(audio, stats)}]"
            )
            # If client received a partial card for this uid, tell client to finalize with empty text
            # so the client clears the ghost card instead of leaving it stuck
            if self.last_partial_uid == uid:
                await self.send_event(
                    AsrFinal(
                        utterance_id=uid,
                        side=side,
                        text="",
                        lang=force_lang or "vi",
                        lang_probs={},
                        uncertain=False,
                        audio_ms=len(audio) * 1000 // 32000,
                    )
                )
            return

        # Check for potential language mismatch (locked to one lang, but speech detected strongly as another)
        if force_lang and detected_lang != force_lang and asr_probs.get(detected_lang, 0.0) >= 0.8:
            logger.warning(
                f"[{self.session_id}] ⚠️ Potential language mismatch on side {side}: channel locked to '{force_lang}', "
                f"but speech strongly detected as '{detected_lang}' (p={asr_probs.get(detected_lang):.2f})."
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
                text, _, _ = await self.scheduler.execute_transcribe(
                    audio, force_lang=final_lang, is_final=True, session_id=self.session_id
                )

        # Update prior if confident
        if not uncertain:
            self.sides_prior[side] = update_side_prior(self.sides_prior[side], final_lang)

        # 3. Emit ASR Final
        logger.info(
            f"[{self.session_id}] 📝 ASR Final: '{text}' [lang={final_lang}, probs={asr_probs}, side={side}, "
            f"{_audio_summary(audio, stats)}]"
        )
        self.recent_context.append(text)
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

        # 4. Trigger MT for targets
        if self.targets:
            targets = [tgt for tgt in self.targets if tgt != final_lang]
        else:
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
        should_stream = True
        context = " ".join(self.recent_context)
        try:
            async for delta in self.mt.translate_stream(text, source, target, context=context):
                full_text += delta
                lower_full = full_text.lower()
                cutoff_markers = [
                    "**",
                    "【",
                    "—",
                    "note:",
                    "notes:",
                    "explanation:",
                    "\n\n",
                    "alright, let's",
                    "no notes",
                    "translate the following",
                    "i'm not sure what you mean",
                    "i’m not sure what you mean",
                    "i don't understand what you mean",
                    "i don’t understand what you mean",
                    "could you please clarify",
                    "could you please explain",
                    "can you please clarify",
                    "please clarify your question",
                    "what do you mean by",
                    "as an ai",
                    "how can i help you",
                    "this is the most important",
                    "they are very friendly",
                    "ご質問の意味が",
                ]
                if any(m in lower_full for m in cutoff_markers):
                    should_stream = False
                if target == "ja" and re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF].*[a-zA-Z]{4,}", full_text):
                    should_stream = False
                if should_stream:
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
