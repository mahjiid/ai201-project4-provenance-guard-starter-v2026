# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> The service also exposes `POST /submit`, `POST /appeal`, and
> `GET /content/<content_id>`. See the sections below for the API contract,
> scoring rules, reader labels, and demonstrated results.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

Provenance Guard is a **local instructional backend service**, not an author-identification tool. It returns a cautious assessment of writing patterns and provides the writer with an appeal route.

1. A writer sends JSON with `text` and `creator_id` to `POST /submit`. The service rejects missing, invalid, very short and oversized inputs before scoring.
2. `detector.py::model_signal` measures GPT-2 word-sequence predictability. A higher value is more AI-like *according to that model*, not proof of authorship.
3. `stylometry.py::style_signal` independently measures sentence-length variation, word variety, and punctuation density as a text-shape signal.
4. `scoring.py::combine_signals` combines both readings and moves large disagreements toward uncertainty.
5. `scoring.py::score_to_label` maps the combined result to one of three complete, non-accusatory reader messages.
6. `audit.log_decision` writes a timestamped record with content ID, creator ID, two signals, score, label, and status in `logs/audit.jsonl`, without saving the submitted text.
7. The response returns `content_id`, guess, confidence, both signal scores, reader label, and status. An author can challenge it via `POST /appeal`; `GET /content/<id>` shows whether the item is now `under_review`.

**False-positive path:** If genuine human writing looks machine-like to GPT-2 and stylometry, the service may return the high-AI-pattern label. The message explicitly says this is **not proof**; the author may supply their explanation in an appeal, and the item is moved to `under_review` without automatic rescoring or punishment.

This is an instructional service only. It lacks authenticated ownership checks, a private moderator console, calibration data, and access controls on the demo audit log. It should **not** be deployed publicly or used to sanction writers.

---

## Signals and Scoring

### Signal one — the model signal

**What it measures:** `detector.py::model_signal` transforms local GPT-2 perplexity (predictability) into a number from 0 to 1, where larger means a more predictable, AI-like word sequence.

**Why it could differ:** Some model-generated prose follows very predictable sequences; human writing may contain more surprising language.

**What it cannot see:** The person's identity, draft history, writing process, original ideas, AI assistance, or attribution. Plain human writing—including many second-language writers' prose—can be predictable; unusual generated writing can be unpredictable. This is a biased and uncalibrated heuristic.

### Signal two — the style signal

**What it measures:** `stylometry.py::style_signal` independently computes:
- **Sentence-length spread:** population standard deviation of words per sentence divided by average words per sentence. Low spread contributes more AI-like evidence.
- **Word variety:** mean unique-word ratio in windows of up to 40 tokens. Repetition contributes more AI-like evidence.
- **Punctuation density:** punctuation divided by the total non-whitespace characters. Sparse punctuation contributes more AI-like evidence.

The three normalized features contribute **40%, 40%, and 20%** respectively. Texts shorter than 20 words or two sentences get neutral `0.5` from the shape signal.

**Why it could differ:** Some generated passages use fairly even sentence lengths, limited word variety and repetitive punctuation.

**What it cannot see:** Meaning, authorship, quotation boundaries, genre, or language context. Edited or translated text can shift these measurements without changing who authored the work. The signals are *different* but not proven statistically independent.

### The combining rule

**Where it lives:** `scoring.py::combine_signals`. Weights and thresholds are in `config.py`.

**Rule with numbers:**

```text
raw = 0.65 * model_score + 0.35 * style_score
shrinkage = min(0.70, max(0, abs(model_score - style_score) - 0.20))
combined = (1 - shrinkage) * raw + shrinkage * 0.50
```

For disagreement at model = `0.90`, style = `0.10`, the raw `0.62` shrinks to roughly `0.548`, which is **unsure**. This numeric example demonstrates the formula; it is not claimed to be an observed detector prediction.

`confidence` in the response is the **uncalibrated AI-likeness combined score** from 0–1, not the statistical probability of AI authorship. `decision_confidence` is merely the scaled distance from 0.5. Neither is proof that a human cheated.

---

## Label Variants

| Label variant | Combined score range | Exact wording |
|---|---|---|
| High-confidence human pattern | `0.00 ≤ score ≤ 0.28` | The available signals lean toward human-written text, but they cannot verify who wrote it. |
| Unsure | `0.28 < score < 0.78` | We cannot reliably determine how this text was written. No authorship accusation has been made, and the writer may request review. |
| High-confidence AI-like pattern | `0.78 ≤ score ≤ 1.00` | This text shows some patterns associated with automated writing. That is not proof of authorship; the writer may request human review. |

The unsure label acknowledges uncertainty and makes no accusation. The AI-pattern label is deliberately cautious, because a wrong allegation against a genuine author is especially harmful.

---

## Sample Run

**Verified on October 24, 2026** through Flask's HTTP test client running the **actual local GPT-2 model on a GitHub Actions Linux CPU runner**. No model signal was mocked in this example. The submitted text and creator identifier are fictional. This single example tests workflow operation, **not accuracy or calibrated authorship probability**.

[Real execution record](https://github.com/mahjiid/ai201-project4-provenance-guard-starter-v2026/actions/runs/40071278674) · [Saved complete response](results/unit7_live_sample.json) · [Append-only audit log](logs/audit.jsonl)

**Submission request — `POST /submit`**

```json
{
  "text": "The first rain reached the small library just before sunset. A woman at the entrance folded a yellow umbrella and stepped inside. Across the room, a student carefully copied the date into a notebook. The city grew quieter as the shutters came down, and everyone waited for the clouds to pass before walking home.",
  "creator_id": "fictional-test-writer"
}
```

**Response — HTTP 201 Created**

```json
{
  "confidence": 0.4938,
  "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
  "creator_id": "fictional-test-writer",
  "decision_confidence": 0.0124,
  "guess": "unsure",
  "label": "We cannot reliably determine how this text was written. No authorship accusation has been made, and the writer may request review.",
  "model_score": 0.5224,
  "status": "decided",
  "style_score": 0.4407
}
```

The model and surface signal produced `0.5224` and `0.4407`. The combined AI-likeness value was `0.4938`, which falls in the **unsure** band. The text was not declared AI-generated and no sanction occurred.

**Appeal request — `POST /appeal`**

```json
{
  "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
  "reasoning": "This is my original story. I kept timestamped working notes."
}
```

**Response — HTTP 200 OK**

```json
{
  "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
  "message": "Your appeal is recorded for human review. No automated authorship finding is final.",
  "status": "under_review"
}
```

**After the appeal — `GET /content/63e3d00d-07d8-4454-809f-0cf4123ff1e2`**

```json
{
  "confidence": 0.4938,
  "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
  "guess": "unsure",
  "label": "We cannot reliably determine how this text was written. No authorship accusation has been made, and the writer may request review.",
  "status": "under_review"
}
```

**Audit log — the original decision remains, followed by the appeal**

```json
[
  {
    "timestamp": "2026-10-24T06:43:23+00:00",
    "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
    "creator_id": "fictional-test-writer",
    "guess": "unsure",
    "model_score": 0.5224,
    "style_score": 0.4407,
    "combined_score": 0.4938,
    "label": "We cannot reliably determine how this text was written. No authorship accusation has been made, and the writer may request review.",
    "status": "decided",
    "text_chars": 312
  },
  {
    "timestamp": "2026-10-24T06:43:23+00:00",
    "content_id": "63e3d00d-07d8-4454-809f-0cf4123ff1e2",
    "creator_id": "fictional-test-writer",
    "event": "appeal",
    "status": "under_review",
    "reasoning": "This is my original story. I kept timestamped working notes."
  }
]
```

The live result verifies that the same `content_id` links both events, the status becomes `under_review`, and both signal scores are retained. The audit log does not contain the submitted story itself.

---

## How I Used AI

1. **Service implementation:** I used AI tools to help connect the Flask submission route, model and writing-style signals, scoring, and audit records. The resulting implementation includes input validation, distinct signal scores, and a separate appeal route rather than treating automated scores as proof of authorship.

2. **Testing and documentation:** I used AI tools to draft test cases, improve the README, and propose five measurable acceptance criteria. I retained explicit checks for uncertain labels, invalid input, and appeals. The proposed criteria still require my personal review; simulated tests do not establish detector accuracy.

**Sequence of work:** The initial live-model demonstration was recorded on October 24, 2026. The five acceptance-criteria proposals were added on October 30, 2026, ahead of the separate Unit 8 attack evaluation, not before the earlier demonstration.

## Verification

Run the criteria structure check and API contract tests:

```bash
python check_criteria.py
python -m unittest -v test_provenance_service test_unit7_acceptance
```

The GitHub Actions workflow `.github/workflows/unit7-readiness.yml` also runs these checks. Controlled signal values verify routes, label boundaries, appeals, and rejection behavior; they do not measure real-world authorship accuracy. The false-positive criterion remains **unevaluated** pending ten genuinely human-authored passages.

## Unit 8 Preparation

For the false-positive evaluation, save ten original human-written passages as a JSON array in `data/human_originals.private.json`. This file is gitignored. Alternatively, set `PROVENANCE_HUMAN_CORPUS` to the path of the corpus file. Do not use synthetic passages as human ground truth.

Run the following in the project environment:

```powershell
python check_criteria.py
python -m unittest -v test_provenance_service test_unit7_acceptance
python scenarios.py
python app.py
```

In a second terminal, once the official Unit 8 attack set is provided:

```powershell
python run_eval.py --label before
python run_attacks.py --set PATH_TO_OFFICIAL_UNIT8_ATTACK_SET --label before
```

The held-out attack evaluation and subsequent before/after analysis are **not yet complete**. Rate limiting remains off during Unit 7 and is enabled separately in Unit 8.

---

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
