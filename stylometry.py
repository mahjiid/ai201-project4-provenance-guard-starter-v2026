"""Signal two: shallow text shape, not meaning or verified provenance."""
import re
import statistics
import string

PUNCTUATION = set(string.punctuation + "—–…“”‘’")

def sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]

def words(text: str) -> list[str]:
    return re.findall(r"\b[^\W_]+(?:['’][^\W_]+)*\b", text.lower(), re.UNICODE)

def sentence_length_spread(text: str) -> float:
    """Coefficient of variation of nonempty sentence lengths."""
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n]
    if len(lengths) < 2:
        return 0.0
    mean = statistics.mean(lengths)
    return round(statistics.pstdev(lengths) / mean, 4) if mean else 0.0

def type_token_ratio(text: str) -> float:
    """Mean ratio of distinct to total tokens in adjacent <=40-word windows."""
    tokens = words(text)
    if not tokens:
        return 0.0
    parts = [tokens[i:i+40] for i in range(0, len(tokens), 40)]
    return round(statistics.mean(len(set(p)) / len(p) for p in parts), 4)

def punctuation_density(text: str) -> float:
    """Ratio of punctuation to non-whitespace characters."""
    nonspace = [ch for ch in text if not ch.isspace()]
    if not nonspace:
        return 0.0
    return round(sum(ch in PUNCTUATION for ch in nonspace) / len(nonspace), 4)

def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))

def style_signal(text: str) -> float:
    """Uncalibrated 0–1 AI-likeness heuristic from three measured style traits."""
    tokens = words(text)
    if len(tokens) < 20 or len(sentences(text)) < 2:
        return 0.5
    cv = sentence_length_spread(text)
    diversity = type_token_ratio(text)
    density = punctuation_density(text)
    regularity = 1 - _clamp(cv / 0.70)
    repetition = 1 - _clamp((diversity - 0.40) / 0.55)
    sparse_punct = 1 - _clamp(density / 0.11)
    return round(_clamp(0.40 * regularity + 0.40 * repetition +
                        0.20 * sparse_punct), 4)

if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or (
        "We reviewed our original notes. The report was clear enough to read. "
        "We checked every part together. The evidence did not prove authorship."
    )
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}")
