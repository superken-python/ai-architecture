import asyncio
import re
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable

import numpy as np

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine, MtEngine, VadEngine
from rvt_ai.pipeline.lid_policy import pick_language, update_side_prior
from rvt_ai.pipeline.mt_validator import LATIN_REGEX, ValidationResult, mt_validator
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
PUNCT_REGEX = re.compile(r"[.。!?！？\s,，、・~～—\-_]")
LANG_NAMES: dict[str, str] = {"vi": "Vietnamese", "ja": "Japanese", "en": "English"}

# Prompt ngữ cảnh cho Whisper (07 §5): chữ của tối đa 2 đoạn trước, tối đa 60 ký tự, bỏ đoạn đã kết thúc quá 5 s audio
PROMPT_MAX_CHARS = 60
PROMPT_MAX_GAP_MS = 5000
# Đoạn có VAD trung bình thấp (nhạc, tiếng động, hơi thở) không nhận prompt: ở đoạn không có lời, Whisper hay chép lại
# prompt (07 §5). Cùng ngưỡng với bộ lọc câu bịa tiếng Nhật (asr_whisper.py).
PROMPT_MIN_VAD_MEAN = 0.35


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def strip_committed_prefix(full: str, committed: str) -> str:
    """Bỏ câu đã chốt sớm khỏi đầu chữ chốt của cả đoạn.

    Chịu được lệch dấu câu và khoảng trắng, thừa/thiếu/sai vài ký tự ("あ、" ở đầu, rơi ký tự đầu, おく/置く,
    ズレ/ずれ): sau khi bỏ dấu câu, so câu đã chốt (n ký tự) với từng đoạn đầu dài n − 3 … n + 3 ký tự của chữ chốt
    bằng khoảng cách sửa, chọn đoạn gần nhất và chỉ cắt khi khác không quá 1/4 số ký tự. Không giống thì giữ nguyên
    (docs 08 §3.6).
    """
    full = full.strip()
    norm_c = PUNCT_REGEX.sub("", committed)
    if not norm_c or not full:
        return full
    pos = [i for i, ch in enumerate(full) if not PUNCT_REGEX.match(ch)]  # vị trí các ký tự không phải dấu câu
    norm_full = "".join(full[i] for i in pos)
    n = len(norm_c)
    best: tuple[int, int, int] | None = None  # (khoảng cách, |j - n|, j)
    for j in range(max(1, n - 3), min(len(norm_full), n + 3) + 1):
        cand = (_edit_distance(norm_c, norm_full[:j]), abs(j - n), j)
        if best is None or cand < best:
            best = cand
    if best is None or best[0] > max(1, n // 4):
        return full  # thà hiện trùng còn hơn mất chữ
    idx = pos[best[2] - 1] + 1
    while idx < len(full) and PUNCT_REGEX.match(full[idx]):
        idx += 1
    return full[idx:].strip()


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
        # Lịch sử cho prompt ngữ cảnh: (lúc đoạn kết thúc, ms theo thời gian audio; chữ của cả đoạn, gồm câu chốt sớm)
        self.recent_asr_history: deque[tuple[int, str]] = deque(maxlen=5)

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
        self.targets = event.targets
        return True

    async def handle_sides_update(self, event: SidesUpdate) -> None:
        self.last_activity_time = time.time()
        for side, cfg in event.sides.items():
            self.sides_config[side] = cfg.lang
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
            task = asyncio.create_task(
                self._process_final_audio(buffer, side, self.segmenter.last_stats, self._audio_end_ms())
            )
            self.active_tasks.append(task)
        elif should_partial and len(buffer) > 0:
            uid = self.utterance_id_counter
            # Chữ tạm cũng mang VAD trung bình (cùng cách tính với chữ chốt), để bộ lọc câu bịa áp cho cả chữ tạm:
            # nếu không, "ご視聴…" vẫn nháy lên và có thể quay lại qua nhánh "cứu chữ từ chữ tạm" (docs 08 §3.3)
            probs = self.segmenter.frame_probs
            vad_mean = sum(probs) / len(probs) if probs else None
            asyncio.create_task(self._process_partial_audio(buffer, side, uid, vad_mean))

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

    def _audio_end_ms(self) -> int:
        """Thời điểm (ms, theo thời gian audio) kết thúc đoạn vừa được segmenter chốt: phần còn lại trong buffer là
        của đoạn sau (khi cắt ở max_ms)."""
        pending_ms = len(self.segmenter.buffer) * 1000 // (self.segmenter.config.sample_rate * 2)
        return self.segmenter.current_time_ms - pending_ms

    def _context_prompt(self, start_ms: int) -> str | None:
        """Prompt ngữ cảnh cho đoạn bắt đầu ở start_ms: chữ của tối đa 2 đoạn trước, nối bằng "。".

        Bỏ đoạn đã kết thúc quá 5 s audio trước start_ms, tức sau khoảng lặng dài hoặc đoạn nhạc. Tính theo thời gian
        audio chứ không theo giờ hệ thống: một đoạn nói liền 5–6 s vẫn có prompt (docs 08 §3.8).
        """
        parts = []
        for end_ms, text in list(self.recent_asr_history)[-2:]:
            part = text.strip().rstrip("。！？.!?")
            if part and start_ms - end_ms <= PROMPT_MAX_GAP_MS:
                parts.append(part)
        if not parts:
            return None
        return ("。".join(parts) + "。")[-PROMPT_MAX_CHARS:]

    async def _flush_segmenter(self) -> None:
        if self.current_side:
            buf = self.segmenter.force_final()
            if len(buf) > 0:
                duration_ms = len(buf) * 1000 // 32000
                logger.info(f"[{self.session_id}] ⏱️ Flush on turn stop: processing final audio ({duration_ms}ms)")
                await self._process_final_audio(buf, self.current_side, self.segmenter.last_stats, self._audio_end_ms())

    async def _process_partial_audio(self, audio: bytes, side: Side, uid: int, vad_mean: float | None = None) -> None:
        try:
            force_lang = self.sides_config[side] if self.sides_config[side] != "auto" else None
            text, lang, _ = await self.scheduler.execute_transcribe(
                audio, force_lang=force_lang, is_final=False, session_id=self.session_id, vad_mean=vad_mean
            )
            # Đoạn đã chốt (hoặc vừa chốt sớm) trong lúc chờ nhận dạng: chữ tạm này đã cũ. Nếu vẫn gửi đi, nó mang uid
            # của đoạn sau, hiện thành thẻ trùng và có thể treo luôn trên màn hình (docs 08 §3.7).
            if uid != self.utterance_id_counter:
                return
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
                        approx_ms = int((len(audio) * 1000 // 32000) * (stable_end / max(1, len(text))))
                        await self.send_event(
                            AsrFinal(
                                utterance_id=commit_uid,
                                side=side,
                                text=stable_sentence,
                                lang=lang,
                                lang_probs={lang: 1.0},
                                uncertain=False,
                                audio_ms=approx_ms,
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

    async def _process_final_audio(
        self, audio: bytes, side: Side, stats: SegmentStats | None = None, end_ms: int | None = None
    ) -> None:
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

        # Prompt ngữ cảnh (07 §5) do scheduler dựng ngay trước khi nhận dạng, để có cả chữ của đoạn trước nếu đoạn đó
        # còn đang chờ GPU lúc đoạn này được chốt (docs 08 §3.8)
        if end_ms is None:
            end_ms = self.segmenter.current_time_ms
        start_ms = end_ms - len(audio) * 1000 // 32000
        vad_mean = stats.prob_mean if stats else None
        use_prompt = vad_mean is None or vad_mean >= PROMPT_MIN_VAD_MEAN

        try:
            text, detected_lang, asr_probs = await self.scheduler.execute_transcribe(
                audio,
                force_lang=force_lang,
                is_final=True,
                session_id=self.session_id,
                vad_mean=vad_mean,
                initial_prompt=(lambda: self._context_prompt(start_ms)) if use_prompt else None,
            )
        except Exception as e:
            logger.error(f"[{self.session_id}] Final transcribe error: {e}")
            text, detected_lang, asr_probs = "", "vi", {}

        # Remove already committed sentences from final text (Mục 5.2 docs 06 & Mục 7 docs 07)
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
                clean_text = strip_committed_prefix(clean_text, cs)
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

        # Ghi cả câu chốt sớm vào lịch sử prompt, không chỉ phần còn lại (docs 08 §3.8). Ghi trước mọi lệnh await, để
        # đoạn kế tiếp, nếu đã xếp hàng, dựng prompt có chữ của đoạn này.
        segment_text = "".join(committed_to_clean) + (text.strip() if text else "")
        if segment_text:
            self.recent_asr_history.append((end_ms, segment_text))

        if not text or not text.strip():
            # If client received a partial card for this uid, tell client to finalize with empty text
            # so the client clears the ghost card instead of leaving it stuck (Mục 10 docs 07).
            # Chỉ xoá thẻ chữ tạm của CHÍNH đoạn này: last_partial_uid không được đặt lại sau mỗi câu chốt, nên có thể
            # còn trỏ vào thẻ đã chốt của câu trước hoặc câu vừa chốt sớm — web sẽ xoá mất thẻ đó (docs 08 §3.2).
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
                self.last_partial_uid = None
                self.last_partial_text = ""

            if committed_to_clean:
                logger.info(f"[{self.session_id}] All speech in segment was already committed early, segment complete.")
                return

            logger.info(
                f"[{self.session_id}] 🔇 Audio transcribed to empty text (silence/noise), skipping "
                f"[side={side}, {_audio_summary(audio, stats)}]"
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

        # 3. Emit ASR Final & MT. Luôn chốt cả đoạn: việc giữ phần đuôi sau dấu kết câu để ghép vào đoạn sau
        # (07 §6.1) đã được bỏ — trên golden_1 nó chỉ được dùng 3 lần trong 14 phút, không lần nào ghép được, và có lần
        # chiếm mất thẻ chữ tạm của câu đang nói (docs 08 §3.4). Ngữ cảnh 2 câu trước gửi kèm bản dịch đã giữ mạch câu
        # qua các đoạn.
        logger.info(
            f"[{self.session_id}] 📝 ASR Final: '{text}' [lang={final_lang}, probs={asr_probs}, side={side}, "
            f"{_audio_summary(audio, stats)}]"
        )
        audio_ms = len(audio) * 1000 // 32000
        await self._emit_final_and_mt(uid, side, text, final_lang, asr_probs, uncertain, audio_ms)

    async def _emit_final_and_mt(
        self,
        uid: int,
        side: Side,
        text: str,
        lang: Lang,
        asr_probs: dict[Lang, float],
        uncertain: bool,
        audio_ms: int,
    ) -> None:
        self.recent_context.append(text)
        await self.send_event(
            AsrFinal(
                utterance_id=uid,
                side=side,
                text=text,
                lang=lang,
                lang_probs=asr_probs,
                uncertain=uncertain,
                audio_ms=audio_ms,
            )
        )

        # 4. Trigger MT for targets
        if self.targets:
            targets = [tgt for tgt in self.targets if tgt != lang]
        else:
            targets = [tgt for tgt in ["ja", "en", "vi"] if tgt != lang]
        for tgt in targets:
            task = asyncio.create_task(self._run_mt(uid, text, lang, tgt))
            self.active_tasks.append(task)

    def _validate_mt(self, text: str, source: Lang, target: Lang, raw: str) -> ValidationResult:
        """Bộ làm sạch bản dịch lỗi thì dùng dòng đầu của bản dịch thô, không đổi thành "[Lỗi dịch]" (docs 08 §3.1)."""
        try:
            return mt_validator.validate(text, source, target, raw)
        except Exception as e:
            logger.exception(
                f"[{self.session_id}] mt_validator failed ({source}->{target}), using raw translation: {e}"
            )
            first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
            return ValidationResult(
                is_valid=bool(first_line),
                cleaned_text=first_line,
                error_reason=None if first_line else "Empty translation",
            )

    async def _run_mt(self, uid: int, text: str, source: Lang, target: Lang) -> None:
        # Sanitize text: collapse excessive repeated characters (e.g. scream loop うおおおお... 500 times)
        text = re.sub(r"(.)\1{7,}", r"\1\1\1\1\1", text).strip()
        text = re.sub(r"(.{2,6}?)\1{5,}", r"\1\1\1", text).strip()
        if not text:
            return

        # Check exact cache first
        cached = mt_validator.get_cached(source, target, text)
        if cached:
            await self.send_event(MtFinal(utterance_id=uid, target=target, text=cached))
            return

        full_text = ""
        should_stream = True
        # Collect prior context without duplicating the current utterance text
        prev_history = [s for s in list(self.recent_context)[:-1] if s.strip() and s.strip() != text.strip()]
        context = " ".join(prev_history[-2:])
        try:
            async for delta in self.mt.translate_stream(text, source, target, context=context):
                full_text += delta
                lower_full = full_text.lower()
                # Không ngắt ở "—" hay "**": cleanText.ts đã dọn hai ký hiệu này trên từng mt.delta (docs 08 §3.5)
                cutoff_markers = [
                    "【",
                    "\n",
                    "\n\n",
                    "(note",
                    "(explanation",
                    "(meaning",
                    "(context",
                    "(literal",
                    "(informal",
                    "(formal",
                    "(polite",
                    "(sensei",
                    "(used",
                    "note:",
                    "notes:",
                    "explanation:",
                    "meaning:",
                    "literal translation:",
                    "alright, let's",
                    "no notes",
                    "translate the following",
                    "this means",
                    "this sentence means",
                    "the speaker is",
                    "the word ",
                    "sensei means",
                    "here is the translation",
                    "here's the translation",
                    "ghi chú:",
                    "lưu ý:",
                    "giải thích:",
                    "ý nghĩa:",
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
                if target in ("vi", "ja") and re.search(
                    r"([.!?。！？])\s*(?:this\s|the\s|sensei\s|it\s|in\s|meaning:|note:)", lower_full
                ):
                    should_stream = False
                if target == "ja" and re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF].*[a-zA-Z]{3,}", full_text):
                    should_stream = False
                if should_stream:
                    await self.send_event(MtDelta(utterance_id=uid, target=target, delta=delta))

            # Validate output
            v_res = self._validate_mt(text, source, target, full_text)
            if not v_res.is_valid:
                logger.warning(
                    f"MT output validation failed for {source}->{target}: {v_res.error_reason}. "
                    "Attempting quick retry..."
                )
                try:
                    retry_text = ""
                    target_name = LANG_NAMES.get(target, target)
                    async for delta in self.mt.translate_stream(
                        text, source, target, context=f"Strictly translate completely into {target_name}"
                    ):
                        retry_text += delta
                    v_retry = self._validate_mt(text, source, target, retry_text)
                    if v_retry.is_valid:
                        v_res = v_retry
                        logger.info(
                            f"[{self.session_id}] 🌐 MT Retry succeeded ({source}->{target}): '{v_res.cleaned_text}'"
                        )
                except Exception as e_retry:
                    logger.warning(f"MT retry failed: {e_retry}")

            if not v_res.is_valid:
                logger.warning(f"MT output validation failed permanently: {v_res.error_reason}")
                fallback_text = (
                    v_res.cleaned_text
                    if (target in ("vi", "en") and LATIN_REGEX.search(v_res.cleaned_text))
                    else f"[Chưa dịch được {target}]"
                )
                await self.send_event(MtFinal(utterance_id=uid, target=target, text=fallback_text))
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
