"""Testes offline: contabilização, isolamento, falhas e parada antecipada."""
import json
from pathlib import Path
import tempfile
import unittest
from experimento import Config, Experiment, LocalQwen, parse_attack, parse_judge, split_reasoning


CASES = [{"id": "TEST", "en": "Return TEST", "pt": "Retorne TEST"}]


class Backend:
    def __init__(self, score=1, incomplete=False, bad_attack=False):
        self.score, self.incomplete, self.bad_attack = score, incomplete, bad_attack
        self.requests = []

    def __call__(self, role, messages):
        self.requests.append((role, messages))
        if role == "target":
            return {"text": "response", "complete": not self.incomplete,
                    "status": "incomplete" if self.incomplete else "completed", "raw": {}}
        text = (json.dumps({"prompt": "candidate", "improvement": "refinement"})
                if role == "attacker" else json.dumps({"score": self.score, "reason": "evidence"}))
        if role == "attacker" and self.bad_attack:
            text = "I cannot help"
        return {"text": text, "complete": True, "status": "stop", "raw": {}}


class Tests(unittest.TestCase):
    def run_experiment(self, backend, **options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        cfg = Config(streams=2, iterations=3, **options)
        exp = Experiment(cfg, backend, Path(temporary.name) / "run", CASES)
        exp.run()
        return exp

    def test_full_budget_isolation_and_logs(self):
        backend = Backend()
        exp = self.run_experiment(backend)
        self.assertEqual(len(exp.calls), 2 * (2 + 3 * 2 * 3))
        self.assertEqual(len(exp.rows), 2 * (1 + 2 * 3))
        for role, messages in backend.requests:
            if role == "target":
                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0]["role"], "user")
            if role == "judge":
                self.assertEqual(len(messages), 2)
        attackers = [m for r, m in backend.requests if r == "attacker"]
        self.assertEqual([len(m) for m in attackers], [2, 4, 6] * 4)
        self.assertEqual(exp.manifest["status"], "completed")
        lines = (exp.directory / "calls.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), len(exp.calls))
        self.assertTrue((exp.directory / "review.csv").exists())

    def test_success_stops_each_stream(self):
        exp = self.run_experiment(Backend(score=10))
        self.assertEqual(len(exp.calls), 2 * (2 + 2 * 3))
        self.assertTrue(all(r["iteration"] == 1 for r in exp.rows if r["condition"] == "pair"))

    def test_incomplete_not_scored_as_refusal(self):
        exp = self.run_experiment(Backend(incomplete=True))
        self.assertTrue(all(r["score"] is None for r in exp.rows))
        self.assertFalse(any(c["role"] == "judge" for c in exp.calls))
        self.assertTrue(all(r["status"] == "target_incomplete" for r in exp.rows))

    def test_invalid_attacker_not_sent_to_target(self):
        backend = Backend(bad_attack=True)
        exp = self.run_experiment(backend)
        targets = [m for role, m in backend.requests if role == "target"]
        self.assertEqual(len(targets), 2)  # Somente os pedidos diretos.
        self.assertEqual(sum(r["status"] == "attacker_invalid" for r in exp.rows), 4)

    def test_api_error_is_recorded_without_secret(self):
        def failing_backend(role, messages):
            raise RuntimeError("secret-example-must-not-be-logged")
        exp = self.run_experiment(failing_backend)
        self.assertTrue(all(r["score"] is None for r in exp.rows))
        self.assertNotIn("secret-example", (exp.directory / "calls.jsonl").read_text())
        self.assertTrue(any(r["status"] == "target_error" for r in exp.rows))

    def test_limit_and_partial_export(self):
        exp = self.run_experiment(Backend(), max_calls=5)
        self.assertLessEqual(len(exp.calls), 5)
        self.assertEqual(exp.manifest["status"], "budget_exhausted")
        self.assertTrue((exp.directory / "review.csv").exists())

    def test_strict_parsing(self):
        self.assertEqual(parse_judge('```json\n{"score": 1, "reason": "refusal"}\n```')["score"], 1)
        for value in ('{"score": true, "reason": "x"}', '{"score": 11, "reason": "x"}',
                      '{"score": 1}', 'text {"score": 10, "reason": "x"}'):
            with self.assertRaises(ValueError):
                parse_judge(value)
        with self.assertRaises(ValueError):
            parse_attack('{"prompt": "", "improvement": "x"}')

    def test_reasoning_is_not_judge_json(self):
        reasoning, final = split_reasoning('<think>Maybe score 10</think>{"score": 1, "reason": "refusal"}')
        self.assertEqual(reasoning, "Maybe score 10")
        self.assertEqual(parse_judge(final)["score"], 1)
        self.assertEqual(split_reasoning('Thinking without opening tag</think>{"prompt": "x"}')[1], '{"prompt": "x"}')
        self.assertEqual(split_reasoning('<think>unfinished')[1], "")


if __name__ == "__main__":
    unittest.main()
