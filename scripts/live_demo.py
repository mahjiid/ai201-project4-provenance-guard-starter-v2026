"""Produce an honest, real-model Unit 7 sample in disposable GitHub Actions.

This is NOT a security/accuracy benchmark. The writing is fictional.
The script uses an isolated results-directory audit log so a rerun never writes to the committed instructional audit history.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app
import audit
import config

SAMPLE = (
    "The first rain reached the small library just before sunset. "
    "A woman at the entrance folded a yellow umbrella and stepped inside. "
    "Across the room, a student carefully copied the date into a notebook. "
    "The city grew quieter as the shutters came down, and everyone waited "
    "for the clouds to pass before walking home."
)

def main():
    # The repository contains a previously verified sample log. Never mutate it.
    # Use a fresh, isolated, untracked audit path per clean GitHub Actions run.
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.LOG_DIR = config.RESULTS_DIR
    config.AUDIT_LOG = config.RESULTS_DIR / "unit7_live_audit.jsonl"
    if config.AUDIT_LOG.exists():
        raise RuntimeError("Refusing to overwrite a previously generated demo log")
    client = app.app.test_client()
    sent = {"text": SAMPLE, "creator_id": "fictional-test-writer"}
    submission = client.post("/submit", json=sent)
    print("SUBMIT_HTTP", submission.status_code, flush=True)
    if submission.status_code != 201:
        print(submission.get_json(), flush=True)
        raise RuntimeError("A real model response (201) was not obtained")
    answer = submission.get_json()
    assertion = {"content_id": answer["content_id"],
                 "reasoning": "This is my original story. I kept timestamped working notes."}
    appealed = client.post("/appeal", json=assertion)
    print("APPEAL_HTTP", appealed.status_code, flush=True)
    if appealed.status_code != 200:
        raise RuntimeError("Appeal failed")
    status = client.get("/content/"+answer["content_id"])
    if status.get_json()["status"] != "under_review":
        raise RuntimeError("Status did not update")
    entries = audit.entries_for(answer["content_id"])
    if len(entries) != 2:
        raise RuntimeError("Expected one original decision and one appeal")
    output = {
        "environment": "GitHub Actions Linux CPU, local GPT-2 (no hosted API)",
        "note": "Fictional sample; one example only. Not calibrated proof of authorship.",
        "submit_request": sent,
        "submit_response": answer,
        "appeal_request": assertion,
        "appeal_response": appealed.get_json(),
        "status_response": status.get_json(),
        "audit_entries": entries,
    }
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR/"unit7_live_sample.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("BEGIN_UNIT7_LIVE_JSON", flush=True)
    print(json.dumps(output, indent=2, ensure_ascii=False), flush=True)
    print("END_UNIT7_LIVE_JSON", flush=True)

if __name__ == "__main__":
    main()
