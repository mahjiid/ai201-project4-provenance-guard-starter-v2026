# Provenance Guard — Unit 7 Acceptance Criteria

The test criteria are intentionally more demanding than a "server responds"
check. A missed target is evidence to investigate, not a reason to silently
lower a threshold. Results from synthetic/mock-model tests establish API
behavior, **not** real detector accuracy.

---

## 1. Protect real writers from false positive AI labels

For a set of **10 distinct, verifiably human-authored passages** supplied by
the writer and documented before the Unit 8 evaluation, **at most 1 of the 10
may receive the high-confidence `ai` label in each of 3 independent trials**
(therefore a maximum false-positive rate of 10% per trial). An `unsure`
label does **not** count as an accusation. Report all 30 classifications and
their underlying scores, even if the target is missed.

**Why this target:** Wrongly accusing an original writer can permanently damage
their trust in a writing platform, while saying "unsure" is safer than an
unsupported accusation. A tight one-in-ten ceiling gives the next unit a
challenging, measurable safety target; it is **not** a proven acceptable
real-world false-positive rate. The authentic human-authored corpus **must not
be synthetically generated or selected after seeing scores**.

---

## 2. Make all three labels and their decision boundaries testable

Across **3 repeat trials**, each of the three labels (`human`, `unsure`,
`ai`) must be produced **at least once per trial** when valid submissions
receive controlled, documented signal pairs. In the same trials, verify that
combined scores **0.28, 0.50, and 0.78** map respectively to `human`,
`unsure`, and `ai`, with **zero gaps or contradictory labels** anywhere
on the closed interval [0,1].

**Why this target:** A three-label safety design is useless if a category
is unreachable or scores at boundaries fall through. Controlled signal
injection checks the actual HTTP contract and threshold implementation; it
does **not** pretend to demonstrate that real prose will reliably land in
every score band. Empirical reachability remains a separate Unit 8 question.

---

## 3. Record successful appeals without automatically re-accusing anyone

In **each of 3 repeat trials**, submit **3 valid content items** and lodge a
valid appeal for each: **all 3 of 3 appeals** must receive HTTP 200 with
`status=under_review`, append exactly one appeal record linked to the
correct original `content_id`, preserve the original decision, and require
**zero additional model-scoring calls**. A second appeal for the same item
must return HTTP **409**; an unknown `content_id` must return HTTP **404**.

**Why this target:** The appeal is the writer's only remedy when the system
is wrong. The system must not silently ignore disputes, overwrite its
history, or perform another automated accusation instead of recording a
human-review request.

---

## 4. Reject malformed input safely and log the rejection

In **each of 3 repeat trials**, all **8 of 8** request cases must be rejected
with the expected status and structured JSON error, with **no `guess` or
`content_id`** returned, and no `decided` audit entry created:

1. JSON array instead of object → HTTP **400**.
2. Missing `creator_id` → HTTP **400**.
3. Numeric `creator_id` → HTTP **400**.
4. Missing `text` → HTTP **422**.
5. Empty `text` → HTTP **422**.
6. `text: null` → HTTP **422**.
7. Fewer than 20 characters of `text` → HTTP **422**.
8. More than 12,000 characters of `text` → HTTP **413**.

All **8 of 8** rejections must be traceable in the append-only audit file,
without storing the submitted text itself.

**Why this target:** Invalid submissions should not crash the server, receive
fictitious classifications, or disappear from the record. Explicit
failure statuses support debugging and make abuse easier to investigate.

---

## 5. Prefer uncertainty when the two signals strongly disagree

For the controlled signal pairs **(0.90 model, 0.10 style)** and
**(0.10 model, 0.90 style)**, the combined score must fall in
**[0.40, 0.60]** and return `unsure` in **all 3 repeat trials**. For
agreement pairs **(0.90, 0.90)** and **(0.10, 0.10)** the combined scores
must be respectively **>= 0.78** (`ai`) and **<= 0.28** (`human`) in
**all 3 trials**.

**Why this target:** If two meaningfully different signals strongly
disagree, automatic certainty is especially unjustified. The test checks
the documented disagreement-shrinkage rule without claiming that the
underlying model correctly identifies authorship.

---

## Evaluation notes

- These targets are ready for the writer to review and approve before the official Unit 8 evaluation.
- Unit 7 tests use controlled scores to verify API behavior, not real-world authorship accuracy.
- Criterion 1 needs ten authentic, human-written passages before a false-positive rate can be measured.
- Keep the earlier sample results and audit history intact, and document any future criteria revisions.
