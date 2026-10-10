import json
import os
import time
from typing import List, Dict, Any

from rvt_ai.pipeline.mt_validator import mt_validator
from rvt_contracts.messages import Lang

def run_evaluation(manifest_path: str = "packs/evals/manifest.jsonl") -> Dict[str, Any]:
    print(f"Loading evaluation dataset from {manifest_path}...")
    if not os.path.exists(manifest_path):
        manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../packs/evals/manifest.jsonl"))

    samples = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    print(f"Evaluating {len(samples)} golden samples across 6 translation directions...")
    
    results = []
    for sample in samples:
        sid = sample["id"]
        source_lang: Lang = sample["lang"]
        ref_text = sample["reference_text"]
        refs = sample["translations"]

        for target_lang, ref_trans in refs.items():
            t0 = time.time()
            v_res = mt_validator.validate(ref_text, source_lang, target_lang, ref_trans)
            latency_ms = int((time.time() - t0) * 1000)

            results.append({
                "sample_id": sid,
                "direction": f"{source_lang}->{target_lang}",
                "valid": v_res.is_valid,
                "latency_ms": latency_ms,
                "input": ref_text,
                "output": v_res.cleaned_text
            })

    total = len(results)
    valid_count = sum(1 for r in results if r["valid"])
    accuracy = (valid_count / total) * 100 if total > 0 else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_test_cases": total,
        "valid_translations": valid_count,
        "script_validation_rate": f"{accuracy:.1f}%",
        "details": results
    }

    os.makedirs("eval/reports", exist_ok=True)
    out_path = "eval/reports/report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✓ Evaluation complete! Script validation rate: {accuracy:.1f}%. Report saved to {out_path}")
    return report

if __name__ == "__main__":
    run_evaluation()
