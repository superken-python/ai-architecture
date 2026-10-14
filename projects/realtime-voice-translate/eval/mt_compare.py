"""So hai lần chạy mt_eval.py trên cùng bộ câu (ví dụ Qwen Q5 cục bộ và một model API), docs 09 §5.6.

    uv run python eval/mt_compare.py /tmp/mt_qwen.json /tmp/mt_gpt.json --out /tmp/mt_compare.md

In chrF của từng bên, số câu mỗi bên tốt hơn, rồi ghi bảng các câu chênh nhiều nhất (cả hai bản dịch và bản tham chiếu)
để người đọc tự đánh giá. chrF so bề mặt chữ với bản tham chiếu do model viết nháp, nên luôn đọc bảng này cùng điểm.
"""

import argparse
import json
from pathlib import Path


def load_rows(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"label": data.get("label") or Path(path).stem, "summary": data, "rows": data["rows"]}


def _cell(row: dict) -> str:
    return f"{row['mt']} ({row['chrf']:.0f})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--top", type=int, default=40, help="số câu chênh nhiều nhất đưa vào bảng")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    a, b = load_rows(args.a), load_rows(args.b)
    if [r["id"] for r in a["rows"]] != [r["id"] for r in b["rows"]]:
        raise SystemExit("hai lần chạy không cùng bộ câu")

    for side in (a, b):
        s = side["summary"]
        print(
            f"{side['label']}: chrF cả bài {s['chrf_corpus']} · chrF trung bình câu {s['chrf_sentence_mean']} · "
            f"còn chữ Nhật {s['with_japanese_left']} · dịch lại {s['retries']} · p95 {s['latency_p95_s']} s"
        )
    wins_a = sum(1 for x, y in zip(a["rows"], b["rows"], strict=True) if x["chrf"] > y["chrf"])
    wins_b = sum(1 for x, y in zip(a["rows"], b["rows"], strict=True) if y["chrf"] > x["chrf"])
    print(f"Câu tốt hơn: {a['label']} {wins_a} · {b['label']} {wins_b} · hoà {len(a['rows']) - wins_a - wins_b}")

    pairs = sorted(zip(a["rows"], b["rows"], strict=True), key=lambda p: -abs(p[0]["chrf"] - p[1]["chrf"]))[: args.top]
    lines = [
        f"# So sánh bản dịch: {a['label']} và {b['label']}",
        "",
        f"chrF cả bài: {a['summary']['chrf_corpus']} và {b['summary']['chrf_corpus']}. "
        f"Bảng dưới là {len(pairs)} câu chênh nhiều nhất.",
        "",
        f"| id | người nói | tiếng Nhật | tham chiếu | {a['label']} | {b['label']} |",
        "|---|---|---|---|---|---|",
    ]
    for x, y in pairs:
        lines.append(f"| {x['id']} | {x['speaker']} | {x['ja']} | {x['vi']} | {_cell(x)} | {_cell(y)} |")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
