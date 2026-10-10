import time
from rvt_ai.packs.loader import get_pack_registry
from rvt_ai.engines.registry import build_engines_from_profile

def benchmark_profiles():
    pack_reg = get_pack_registry()
    print("Benchmarking configured profiles...")

    for name, profile in pack_reg.profiles.items():
        print(f"\n--- Profile: {name} ({profile.description}) ---")
        t0 = time.time()
        vad, asr, mt = build_engines_from_profile(profile)
        load_time_ms = int((time.time() - t0) * 1000)
        print(f"  Engines initialized in {load_time_ms}ms")
        print(f"  VAD: {profile.vad.engine}, ASR: {profile.asr.engine}, MT: {profile.mt.engine}")

        # Quick inference test with fake or fallback
        t_asr = time.time()
        sample_pcm = b"\x01" * 3200
        text, lang, probs = asr.transcribe(sample_pcm)
        asr_time_ms = int((time.time() - t_asr) * 1000)
        print(f"  ASR Transcribe test: {asr_time_ms}ms -> text='{text}' ({lang})")

if __name__ == "__main__":
    benchmark_profiles()
