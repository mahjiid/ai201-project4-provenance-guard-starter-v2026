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
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

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

The service and appeal behavior have **passed automated tests with mocked model-signal values**, including audit and error cases. That verifies service logic, **not** the quality of the real detector. A real local GPT-2 score and genuine HTTP submission/appeal transcript have not yet been confirmed, so no sample output is invented here.

**PowerShell commands for a real run:**

```powershell
# Terminal 1
.\.venv\Scripts\python.exe app.py

# Terminal 2
curl.exe -X POST http://127.0.0.1:5000/ping -H "Content-Type: application/json" -d '{\"message\":\"hello\"}'

# Submission (replace the text with your own original writing)
curl.exe -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d '{\"text\":\"The long summer rain came without warning. I crossed the road and kept my notebook dry. When I reached the bakery, the lights were already on.\",\"creator_id\":\"demo-writer\"}'

# Copy the returned content_id into the appeal body
curl.exe -X POST http://127.0.0.1:5000/appeal -H "Content-Type: application/json" -d '{\"content_id\":\"REPLACE_WITH_ID\",\"reasoning\":\"I kept timestamped drafts of this original work.\"}'

curl.exe "http://127.0.0.1:5000/log?limit=3"
```

**The audit contract:** Submission appends `status: decided` with both scores. An appeal appends a second event with `event: appeal`, `status: under_review` and the same content ID; it does not overwrite the original decision. Automated tests verify this sequence. Raw writing is not logged.

**Current environment limitation:** ZairPlanet had fewer than the 9 GB of free disk space requested by the starter's full environment check. The GitHub workflow installs only Flask to check HTTP logic with explicit test doubles. The actual model installation and real reading remain a separate verification step.

---

## How I Used AI

**Moment 1 — backend and signal implementation:** I asked for help connecting the two independent signals to a Flask JSON endpoint with conservative uncertainty handling. Code and test cases were drafted. The design retains explicit errors and an appeal channel rather than treating any model output as proven cheating.

**Moment 2 — test and documentation quality:** I requested checks for invalid inputs, label boundary coverage, missing local model, and audit consistency. A test suite and README explanation were prepared. The suite clearly marks model predictions as mocked, so it does not claim to validate detector accuracy or to have completed a live-model run.

**Criterion ownership:** The five numbered acceptance criteria are intentionally left for my own selections and reasons in `criteria.md` before a held-out evaluation. No five targets have been invented and attributed to me.

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
