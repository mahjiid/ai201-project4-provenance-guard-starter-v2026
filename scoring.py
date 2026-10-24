"""Combine independent model-predictability and surface-shape signals cautiously.

Scores indicate uncalibrated AI-like text patterns, NOT authorship or guilt.
"""
import math
import config

AI_LABEL = ("This text shows some patterns associated with automated writing. "
            "That is not proof of authorship; the writer may request human review.")
HUMAN_LABEL = ("The available signals lean toward human-written text, but "
               "they cannot verify who wrote it.")
UNSURE_LABEL = ("We cannot reliably determine how this text was written. "
                "No authorship accusation has been made, and the writer may request review.")

def _score(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Signal scores must be finite values between 0 and 1")
    return value

def combine_signals(model_score: float, style_score: float) -> float:
    """Weighted mean with disagreement shrinkage toward 0.5 (unsure)."""
    m, s = _score(model_score), _score(style_score)
    if not math.isclose(config.WEIGHT_MODEL_SIGNAL + config.WEIGHT_STYLE_SIGNAL,
                        1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Signal weights must add to 1.0")
    raw = config.WEIGHT_MODEL_SIGNAL * m + config.WEIGHT_STYLE_SIGNAL * s
    shrinkage = min(0.70, max(0.0, abs(m-s)-0.20))
    return round(max(0.0, min(1.0,
        (1-shrinkage)*raw + shrinkage*0.5)), 4)

def score_to_label(score: float) -> tuple[str, str]:
    score = _score(score)
    if score >= config.AI_THRESHOLD:
        return "ai", AI_LABEL
    if score <= config.HUMAN_THRESHOLD:
        return "human", HUMAN_LABEL
    return "unsure", UNSURE_LABEL

def label_ranges() -> list[tuple[str,str]]:
    return [
      ("human", f"0.00 <= score <= {config.HUMAN_THRESHOLD:.2f}"),
      ("unsure", f"{config.HUMAN_THRESHOLD:.2f} < score < {config.AI_THRESHOLD:.2f}"),
      ("ai", f"{config.AI_THRESHOLD:.2f} <= score <= 1.00")
    ]
