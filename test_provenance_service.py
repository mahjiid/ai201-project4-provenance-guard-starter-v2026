"""Unit 7 HTTP service tests with explicitly MOCKED local-model predictions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import audit
import config
import detector
import scoring
import stylometry

TEXT = ("The service measures two different features of writing, and it records "
        "what happened when a writer submits their work. Someone can appeal "
        "a mistaken guess with additional context.")

class ProvenanceGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="guard_tests_")
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "logs" / "audit.jsonl"
        p1 = patch.object(config, "LOG_DIR", self.log.parent)
        p2 = patch.object(config, "AUDIT_LOG", self.log)
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        self.client = app.app.test_client()

    def submit(self, text=TEXT, creator="example-writer"):
        return self.client.post("/submit", json={"text": text, "creator_id": creator})

    def test_ping_is_untouched(self):
        r = self.client.post("/ping", json={"message": "hello"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["you_sent"], "hello")

    def test_submit_combines_two_scores_and_audits(self):
        with patch("detector.model_signal", return_value=0.91) as model:
            with patch("stylometry.style_signal", return_value=0.90) as style:
                r = self.submit()
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(r.json["guess"], "ai")
        self.assertEqual(r.json["model_score"], 0.91)
        self.assertEqual(r.json["style_score"], 0.90)
        self.assertTrue(0 <= r.json["confidence"] <= 1)
        model.assert_called_once_with(TEXT)
        style.assert_called_once_with(TEXT)
        records = audit.read_entries()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["content_id"], r.json["content_id"])
        self.assertNotIn("text", records[0])

    def test_appeal_status_changes_without_rescoring(self):
        with patch("detector.model_signal", return_value=0.91) as model:
            submitted = self.submit()
            key = submitted.json["content_id"]
            appealed = self.client.post("/appeal", json={
                "content_id": key, "reasoning": "I have dated drafts of this writing."
            })
            self.assertEqual(appealed.status_code, 200)
            self.assertEqual(appealed.json["status"], "under_review")
            model.assert_called_once()
        self.assertEqual([e["status"] for e in audit.entries_for(key)],
                         ["decided", "under_review"])
        self.assertEqual(self.client.get("/content/"+key).json["status"], "under_review")
        again = self.client.post("/appeal", json={
            "content_id": key, "reasoning": "Please review my dated drafts."
        })
        self.assertEqual(again.status_code, 409)

    def test_missing_id_and_missing_model_fail_safely(self):
        self.assertEqual(self.client.post("/appeal", json={
            "content_id":"bad", "reasoning":"This was my original work."
        }).status_code, 404)
        with patch("detector.model_signal", side_effect=detector.DetectorUnavailable("offline")):
            r = self.submit()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json["error"], "model_unavailable")
        self.assertNotIn("guess", r.json)

    def test_invalid_input_fails_without_a_verdict(self):
        self.assertEqual(self.client.post("/submit", json=[]).status_code, 400)
        self.assertEqual(self.submit(text="").status_code, 422)
        self.assertEqual(self.submit(text="z" * 12001).status_code, 413)
        self.assertEqual(self.submit(creator="  ").status_code, 400)
        self.assertEqual(self.client.post("/appeal",json={
            "content_id": "a", "reasoning":"too short"
        }).status_code, 422)

    def test_all_three_labels_are_reachable(self):
        for score, expected in [(0,"human"),(0.2,"human"),(0.51,"unsure"),
                                (0.95,"ai"),(1,"ai")]:
            self.assertEqual(scoring.score_to_label(score)[0], expected)
        self.assertNotEqual(scoring.score_to_label(0.51)[1],
                            scoring.score_to_label(0.95)[1])

    def test_signal_disagreement_moves_towards_unsure(self):
        self.assertLess(abs(scoring.combine_signals(0.9,0.1)-0.5),
                        abs(scoring.combine_signals(0.9,0.9)-0.5))
        self.assertEqual(scoring.combine_signals(0,0), 0)
        self.assertEqual(scoring.combine_signals(1,1), 1)

    def test_style_methods_vary_independently_of_model(self):
        regular = "I see the issue. " * 8
        varied = ("Short! The red bus passed our market with a terrible noise. "
                  "After yesterday's rainfall I remembered my grandmother's garden. "
                  "Who could forget the mangoes, their scent and colour? "
                  "Our morning ended quietly by the riverbank.")
        self.assertNotEqual(stylometry.sentence_length_spread(regular),
                            stylometry.sentence_length_spread(varied))
        self.assertTrue(0 <= stylometry.type_token_ratio(varied) <= 1)
        self.assertTrue(0 <= stylometry.punctuation_density(varied) <= 1)
        self.assertTrue(0 <= stylometry.style_signal(varied) <= 1)
        self.assertEqual(stylometry.style_signal("Hello world."), 0.5)

if __name__=="__main__":
    unittest.main()
