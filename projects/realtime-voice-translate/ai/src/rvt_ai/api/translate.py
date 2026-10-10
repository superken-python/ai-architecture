from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from rvt_ai.pipeline.mt_validator import JA_REGEX
from rvt_contracts.messages import (
    Lang,
    SpeechTranslateResponse,
    TranscribeResponse,
    TranslateRequest,
    TranslateResponse,
)

router = APIRouter(prefix="/v1", tags=["translate"])


def detect_text_lang(text: str) -> Lang:
    # Rule from doc 6.7: kana/kanji -> ja; vietnamese distinctive -> vi; else -> en
    if JA_REGEX.search(text):
        return "ja"
    vi_chars = set("ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
    if any(c in vi_chars for c in text):
        return "vi"
    return "en"


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest, request: Request) -> TranslateResponse:
    mt_engine = request.app.state.mt_engine
    source_lang = req.source or detect_text_lang(req.text)
    targets: list[Lang] = [tgt for tgt in ["ja", "en", "vi"] if tgt != source_lang]

    translations: dict[Lang, str] = {}
    for tgt in targets:
        full_text = ""
        async for delta in mt_engine.translate_stream(req.text, source_lang, tgt):
            full_text += delta
        translations[tgt] = full_text.strip()

    return TranslateResponse(source=source_lang, translations=translations)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: Request, file: UploadFile = File(...)) -> TranscribeResponse:
    asr_engine = request.app.state.asr_engine
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    text, lang, probs = asr_engine.transcribe(audio_bytes)
    return TranscribeResponse(text=text, lang=lang, lang_probs=probs)


@router.post("/speech-translate", response_model=SpeechTranslateResponse)
async def speech_translate(request: Request, file: UploadFile = File(...)) -> SpeechTranslateResponse:
    asr_engine = request.app.state.asr_engine
    mt_engine = request.app.state.mt_engine
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    text, lang, probs = asr_engine.transcribe(audio_bytes)
    targets: list[Lang] = [tgt for tgt in ["ja", "en", "vi"] if tgt != lang]

    translations: dict[Lang, str] = {}
    for tgt in targets:
        full_text = ""
        async for delta in mt_engine.translate_stream(text, lang, tgt):
            full_text += delta
        translations[tgt] = full_text.strip()

    return SpeechTranslateResponse(text=text, source_lang=lang, lang_probs=probs, translations=translations)
