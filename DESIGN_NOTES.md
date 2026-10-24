# Provenance Guard — Unit 7 design record

## Decision flow, decided before implementation
1. Receive and validate `{"text": "...", "creator_id": "..."}` at POST /submit.
2. Compute local GPT-2 word-sequence predictability in `detector.py::model_signal`.
3. Separately compute sentence-length spread, word variety, and punctuation density in `stylometry.py::style_signal`.
4. Combine the two 0–1 AI-likeness signals conservatively in `scoring.py::combine_signals`. Disagreement is a reason for greater uncertainty.
5. Select a complete reader-facing human/unsure/AI-pattern sentence; no verdict is proof of authorship.
6. Append an audit decision with both signals and a unique `content_id`, without the raw submitted text.
7. POST /appeal appends a new `under_review` event for an existing content id. No automated re-scoring or sanction.

## Blind spots
GPT-2 predictability can falsely flag plain human writing and miss unusual AI text. It does not identify authors.
Stylometry cannot read meaning or provenance: punctuation edits, genre, English as a second language, quotations, and length can change its measurements.

## Reader and appeal safeguards
The unsure region is wide. The high-AI-pattern label explicitly says it is **not proof of authorship**. An appeal must be available and recorded. No missing-model fallback can fabricate a score.

## Boundaries
This is a local classroom demo, not a deployment-ready cheating detector. There is no creator authentication, private audit-log ACL, retention system, calibration study, or appeal reviewer interface. It must not be used to sanction writers.

## Unit 7 ownership
`criteria.md` is intentionally not filled with five author-attributed targets by an assistant: CodePath says the student must choose, explain, and commit their **own** five targets before measuring against them. The numbers remain a decision for the student.
