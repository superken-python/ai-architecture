from rvt_ai.pipeline.lid_policy import pick_language


def test_pick_language_certain():
    asr_probs = {"vi": 0.8, "en": 0.1, "ja": 0.05, "fr": 0.05}
    side_prior = {"vi": 0.33, "en": 0.33, "ja": 0.33}  # Equal prior
    decision = pick_language(asr_probs, side_prior, prior_weight=1.0, uncertain_below=0.5)

    assert decision.lang == "vi"
    assert decision.uncertain is False
    assert decision.probs["vi"] > 0.8


def test_pick_language_uncertain():
    asr_probs = {"vi": 0.4, "en": 0.4, "ja": 0.1}
    side_prior = {"vi": 0.33, "en": 0.33, "ja": 0.33}
    decision = pick_language(asr_probs, side_prior, prior_weight=1.0, uncertain_below=0.6)

    # either vi or en, but should be uncertain
    assert decision.uncertain is True


def test_pick_language_with_strong_prior():
    asr_probs = {"vi": 0.4, "en": 0.5, "ja": 0.1}
    # Strong prior towards vi
    side_prior = {"vi": 0.9, "en": 0.05, "ja": 0.05}
    decision = pick_language(asr_probs, side_prior, prior_weight=1.0, uncertain_below=0.5)

    assert decision.lang == "vi"  # Prior overrides the slight edge of 'en' in ASR probs
