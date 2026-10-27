"""Đo chất lượng bản dịch Nhật → Việt trên bản dịch tham chiếu của một bộ golden (docs 09 §5.1).

Bộ dịch nhận đúng câu tiếng Nhật đã sửa (`<golden>/translation/ja-vi.jsonl`), dịch lần lượt với cùng prompt, ngữ cảnh 2
câu trước kèm bản dịch, glossary, bảng tra câu ngắn và khâu làm sạch như app, rồi chấm chrF so với bản tham chiếu. Đây
là mức trần của bộ dịch: chữ nghe được không sai. Phép đo cả chuỗi (nghe sai và cắt câu) chạy bằng
`golden_session.py --mt-url`.

Trên server (container rvt_ai, bộ dịch llama.cpp ở http://mt:8080/v1):

    docker exec -it rvt_ai uv run python eval/mt_eval.py --golden eval/golden_1 --api-url http://mt:8080/v1 \\
        --glossary default,naruto --out /tmp/mt_golden_1.json

So các cách: thêm `--no-context` (bỏ câu trước), `--glossary ""` (bỏ glossary), `--pivot-en` (dịch Nhật → Anh → Việt).
"""

import argparse
import asyncio
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

from rvt_ai.engines.mt_llama import LlamaCppMtEngine
from rvt_ai.engines.ports import MtHints
from rvt_ai.packs.glossary import Glossary, fix_leftovers, load_glossary, load_phrasebook
from rvt_ai.pipeline.mt_validator import JA_REGEX, mt_validator

PACKS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs"))
_SPACE = re.compile(r"\s+")


# ---------------------------------------------------------------- chrF (Popović 2015), như sacrebleu: n ≤ 6, β = 2
def chrf_stats(hyp: str, ref: str, order: int = 6) -> list[tuple[int, int, int]]:
    """(số n-gram khớp, số n-gram của bản dịch, số n-gram của tham chiếu) cho n = 1..order, bỏ khoảng trắng."""
    hyp, ref = _SPACE.sub("", hyp), _SPACE.sub("", ref)
    out = []
    for n in range(1, order + 1):
        h = Counter(hyp[i : i + n] for i in range(len(hyp) - n + 1))
        r = Counter(ref[i : i + n] for i in range(len(ref) - n + 1))
        out.append((sum((h & r).values()), sum(h.values()), sum(r.values())))
    return out


def chrf_score(stats: list[tuple[int, int, int]], beta: float = 2.0) -> float:
    precisions, recalls = [], []
    for match, hyp_n, ref_n in stats:
        if hyp_n and ref_n:
            precisions.append(match / hyp_n)
            recalls.append(match / ref_n)
    if not precisions:
        return 0.0
    p, r = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    if p + r == 0:
        return 0.0
    return 100 * (1 + beta**2) * p * r / (beta**2 * p + r)


def corpus_chrf(hyps: list[str], refs: list[str]) -> float:
    total = [(0, 0, 0)] * 6
    for h, r in zip(hyps, refs, strict=True):
        total = [tuple(a + b for a, b in zip(t, s, strict=True)) for t, s in zip(total, chrf_stats(h, r), strict=True)]
    return chrf_score(total)


# ---------------------------------------------------------------- dịch như app
class AppLikeTranslator:
    """Dịch từng câu như RVTSession._run_mt: bảng tra, glossary, 2 câu trước kèm bản dịch, sửa chữ Nhật còn sót, kiểm,
    dịch lại một lần nếu hỏng."""

    def __init__(self, engine, glossary: Glossary, use_context: bool = True, pivot_en: bool = False):
        self.engine = engine
        self.glossary = glossary
        self.use_context = use_context
        self.pivot_en = pivot_en
        self.phrasebook = load_phrasebook("ja", packs_dir=PACKS)
        self.history: list[tuple[str, str]] = []
        self.retries = 0

    async def _one(self, text: str, source: str, target: str, history: list[tuple[str, str | None]]) -> str:
        hints = MtHints(
            history=history,
            glossary=self.glossary.match(text, source, target),
            addressing=list(self.glossary.addressing.get(target, [])),
        )
        for attempt in range(2):
            raw = "".join([d async for d in self.engine.translate_stream(text, source, target, hints=hints)])
            v = mt_validator.validate(text, source, target, fix_leftovers(raw, source, target, self.glossary))
            if v.is_valid or attempt:
                return v.cleaned_text
            self.retries += 1
            hints = MtHints(history=hints.history, glossary=hints.glossary, addressing=hints.addressing, strict=True)
        return ""

    async def translate(self, ja: str) -> str:
        phrase = self.phrasebook.lookup(ja, "vi")
        if phrase:
            out = phrase
        elif self.pivot_en:
            en = await self._one(ja, "ja", "en", [])
            out = await self._one(en, "en", "vi", self.history[-2:] if self.use_context else [])
        else:
            out = await self._one(ja, "ja", "vi", self.history[-2:] if self.use_context else [])
        self.history.append((ja, out))
        return out


async def translate_all(texts: list[str], translator: AppLikeTranslator) -> tuple[list[str], list[float]]:
    outs, secs = [], []
    for t in texts:
        started = time.perf_counter()
        outs.append(await translator.translate(t))
        secs.append(time.perf_counter() - started)
    return outs, secs


def load_references(golden: str) -> list[dict]:
    path = Path(golden) / "translation" / "ja-vi.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", default="eval/golden_1")
    parser.add_argument("--api-url", default=os.environ.get("RVT_MT_API_URL", "http://localhost:8080/v1"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--glossary", default="default,naruto", help='tên glossary trong packs/glossary; "" để bỏ')
    parser.add_argument("--no-context", action="store_true", help="không đưa 2 câu trước vào prompt")
    parser.add_argument("--pivot-en", action="store_true", help="dịch Nhật → Anh → Việt")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--model",
        default=os.environ.get("RVT_MT_MODEL", ""),
        help="tên model khi gọi API trên cloud; URL deployment của Azure đã có tên deployment thì để trống",
    )
    parser.add_argument("--provider", default=os.environ.get("RVT_MT_PROVIDER", ""), help="azure | openai; trống: đoán")
    parser.add_argument(
        "--reasoning-effort",
        default=os.environ.get("RVT_MT_REASONING_EFFORT", "auto"),
        help='auto: thấp nhất theo tên model (gpt-5.4-mini: none, gpt-5-mini: minimal); "" để không gửi',
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RVT_MT_API_KEY", ""),
        help="khoá API (đọc từ RVT_MT_API_KEY để không lộ trên dòng lệnh); có khoá thì gọi API lưu trữ",
    )
    parser.add_argument("--label", default="", help="nhãn của lần chạy, ghi vào báo cáo để so sánh")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    refs = load_references(args.golden)
    if args.limit:
        refs = refs[: args.limit]
    glossary = load_glossary([n for n in args.glossary.split(",") if n.strip()], packs_dir=PACKS)
    engine = LlamaCppMtEngine(
        api_url=args.api_url,
        timeout_sec=args.timeout,
        api_key=args.api_key,
        model=args.model,
        provider=args.provider,
        reasoning_effort=args.reasoning_effort,
    )
    translator = AppLikeTranslator(engine, glossary, use_context=not args.no_context, pivot_en=args.pivot_en)
    outs, secs = asyncio.run(translate_all([r["ja"] for r in refs], translator))

    sentence = [chrf_score(chrf_stats(o, r["vi"])) for o, r in zip(outs, refs, strict=True)]
    secs_sorted = sorted(secs)
    summary = {
        "sentences": len(refs),
        "chrf_corpus": round(corpus_chrf(outs, [r["vi"] for r in refs]), 2),
        "chrf_sentence_mean": round(sum(sentence) / max(1, len(sentence)), 2),
        "with_japanese_left": sum(1 for o in outs if JA_REGEX.search(o)),
        "empty": sum(1 for o in outs if not o.strip()),
        "retries": translator.retries,
        "latency_p50_s": round(secs_sorted[len(secs) // 2], 3) if secs else None,
        "latency_p95_s": round(secs_sorted[int(len(secs) * 0.95) - 1], 3) if secs else None,
        "glossary": args.glossary,
        "context": not args.no_context,
        "pivot_en": args.pivot_en,
        "label": args.label or args.model or args.api_url,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    worst = sorted(zip(sentence, refs, outs, strict=True), key=lambda x: x[0])[:10]
    for score, ref, out in worst:
        print(f"  {score:5.1f} | {ref['ja']} | {out} | {ref['vi']}")
    if args.out:
        rows = [{**r, "mt": o, "chrf": round(s, 2)} for r, o, s in zip(refs, outs, sentence, strict=True)]
        Path(args.out).write_text(json.dumps({**summary, "rows": rows}, ensure_ascii=False, indent=1), "utf-8")
        print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
