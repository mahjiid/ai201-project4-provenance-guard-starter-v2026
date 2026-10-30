"""Executable Unit 7 acceptance-contract checks.

Tests 2-5 use CONTROLLED signal injection, never pretend to measure
real-world detector accuracy. Criterion 1 requires authentic writer text.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skip
from unittest.mock import patch

import app
import audit
import config
import scoring


ORIGINAL = (
    "On Friday morning I opened my notebook and reviewed the whole draft. "
    "I made a small correction to the final paragraph, then compared my "
    "changes with the notes that I had saved the previous evening."
)


class AcceptanceContractTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="unit7_acceptance_")
        self.addCleanup(self.temp.cleanup)
        log = Path(self.temp.name) / "logs" / "audit.jsonl"
        p1 = patch.object(config, "LOG_DIR", log.parent)
        p2 = patch.object(config, "AUDIT_LOG", log)
        p1.start()
        p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)
        self.client = app.app.test_client()

    def submit(self, model=0.5, style=0.5, creator="writer-test"):
        with patch("detector.model_signal", return_value=model), patch(
            "stylometry.style_signal", return_value=style
        ):
            return self.client.post(
                "/submit", json={"text": ORIGINAL, "creator_id": creator}
            )

    @skip(
        "Criterion 1 requires 10 independently documented, genuinely "
        "human-authored passages supplied by the writer. AI text is NOT a substitute."
    )
    def test_criterion_1_real_writers_false_positive_rate(self):
        pass

    def test_criterion_2_three_labels_and_exact_boundaries(self):
        expected = [(0.28, "human"), (0.50, "unsure"), (0.78, "ai")]
        for trial in range(3):
            observed = set()
            for score, label in expected:
                with self.subTest(trial=trial, score=score):
                    response = self.submit(score, score, creator=f"labels-{trial}")
                    self.assertEqual(response.status_code, 201)
                    self.assertEqual(response.json["guess"], label)
                    self.assertEqual(response.json["confidence"], score)
                    observed.add(response.json["guess"])
            self.assertEqual(observed, {"ai", "human", "unsure"})

        # Prove all 1001 sampled points cover [0,1] with no holes;
        # exact boundary checks above cover the pivotal decision points.
        for step in range(1001):
            result, label_text = scoring.score_to_label(step / 1000)
            self.assertIn(result, {"ai", "human", "unsure"})
            self.assertIsInstance(label_text, str)
            self.assertGreater(len(label_text), 20)

    def test_criterion_3_appeals_are_recorded_without_rescoring(self):
        for trial in range(3):
            with patch("detector.model_signal", return_value=0.85) as model:
                with patch("stylometry.style_signal", return_value=0.90):
                    ids = []
                    for n in range(3):
                        response = self.client.post("/submit", json={
                            "text": ORIGINAL,
                            "creator_id": f"appeal-{trial}-{n}",
                        })
                        self.assertEqual(response.status_code, 201)
                        ids.append(response.json["content_id"])
                    self.assertEqual(model.call_count, 3)
                    for content_id in ids:
                        response = self.client.post("/appeal", json={
                            "content_id": content_id,
                            "reasoning": "I have dated original drafts and handwritten notes.",
                        })
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json["status"], "under_review")
                        self.assertEqual(
                            [e.get("status") for e in audit.entries_for(content_id)],
                            ["decided", "under_review"],
                        )
                        self.assertEqual(
                            self.client.get(f"/content/{content_id}").json["status"],
                            "under_review",
                        )
                    self.assertEqual(model.call_count, 3)

            dupe = self.client.post("/appeal", json={
                "content_id": ids[0], "reasoning": "Please review my notes again.",
            })
            self.assertEqual(dupe.status_code, 409)

            unknown = self.client.post("/appeal", json={
                "content_id": f"unknown-{trial}",
                "reasoning": "This is my own writing, please review it.",
            })
            self.assertEqual(unknown.status_code, 404)

    def test_criterion_4_eight_invalid_payloads(self):
        cases = [
            ([], 400),
            ({"text": ORIGINAL}, 400),
            ({"text": ORIGINAL, "creator_id": 2}, 400),
            ({"creator_id": "writer"}, 422),
            ({"text": "", "creator_id": "writer"}, 422),
            ({"text": None, "creator_id": "writer"}, 422),
            ({"text": "short", "creator_id": "writer"}, 422),
            ({"text": "x" * 12001, "creator_id": "writer"}, 413),
        ]
        for trial in range(3):
            before = len(audit.read_entries())
            for n, (body, expected_status) in enumerate(cases):
                with self.subTest(trial=trial, case=n):
                    response = self.client.post("/submit", json=body)
                    self.assertEqual(response.status_code, expected_status, response.json)
                    self.assertIsInstance(response.json, dict)
                    self.assertIn("error", response.json)
                    self.assertNotIn("guess", response.json)
                    self.assertNotIn("content_id", response.json)

            entries = audit.read_entries()[before:]
            self.assertEqual(len(entries), 8)
            self.assertTrue(all(e["status"] == "rejected" for e in entries))
            self.assertTrue(all(e.get("event") == "rejected" for e in entries))
            self.assertTrue(all("text" not in e for e in entries))

    def test_criterion_5_disagreement_maps_to_unsure(self):
        for trial in range(3):
            for m, s in [(0.90, 0.10), (0.10, 0.90)]:
                with self.subTest(trial=trial, model=m, style=s):
                    response = self.submit(m, s, creator=f"conflict-{trial}")
                    self.assertEqual(response.status_code, 201)
                    self.assertGreaterEqual(response.json["confidence"], 0.40)
                    self.assertLessEqual(response.json["confidence"], 0.60)
                    self.assertEqual(response.json["guess"], "unsure")

            for m, s, desired in [
                (0.90, 0.90, "ai"),
                (0.10, 0.10, "human"),
            ]:
                response = self.submit(m, s, creator=f"agreement-{trial}")
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json["guess"], desired)
                if desired == "ai":
                    self.assertGreaterEqual(response.json["confidence"], 0.78)
                else:
                    self.assertLessEqual(response.json["confidence"], 0.28)


if __name__ == "__main__":
    import unittest
    unittest.main()
