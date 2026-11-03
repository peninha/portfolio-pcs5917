"""Testes do fluxo único, com backend simulado e resultados temporários."""
import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experimento
from experimento import BASE, Experiment


CONFIG = {"strategy": "3-Liner", "attack": "V01", "language": "pt", "repetitions": 1,
    "seed": 42, "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B", "revision": None,
    "cache_dir": "D:/huggingface/hub", "max_input_tokens": 4096,
    "max_new_tokens": 2048, "temperature": 0.6, "top_p": 0.95}


class FakeBackend:
    metadata = {"model_id": "test-fixture", "model_revision": "fixture", "quantization": "fixture",
                "environment": {"packages": {"fixture": "1"}}}

    def __init__(self, fail_on_call=None):
        self.calls = []
        self.fail_on_call = fail_on_call

    def generate(self, messages, **options):
        self.calls.append((copy.deepcopy(messages), options))
        if self.fail_on_call == len(self.calls):
            raise RuntimeError("Interrupção simulada")
        text = "ABACAXI" if "ABACAXI" in messages[-1]["content"] else "4"
        return {"response": f"Raciocínio.</think>{text}", "raw_output": text,
                "output_tokens": 10, "input_tokens": 20, "seconds": 0.01,
                "peak_allocated_gib": 1, "hit_token_limit": False,
                "think_open_in_input": True, "final_response": text}


class ExperimentTests(unittest.TestCase):
    def test_model_reused_without_network_or_second_constructor(self):
        revision = json.loads((BASE / "resultados/model-reference.json").read_text(encoding="utf-8"))["revision"]
        def construct(config, selected_revision, kernel):
            backend = FakeBackend()
            backend.key = (config["model"], selected_revision)
            return backend
        with (
            patch.object(experimento, "_BACKEND", None),
            patch.object(experimento, "TransformersBackend", side_effect=construct) as constructor,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            first = experimento.get_backend(CONFIG, BASE / "resultados")
            second = experimento.get_backend(dict(CONFIG, strategy="AIM"), BASE / "resultados")
            self.assertIs(first, second)
            self.assertEqual(first.key[1], revision)
            self.assertEqual(constructor.call_count, 1)
            with self.assertRaises(RuntimeError):
                experimento.get_backend(dict(CONFIG, revision="a" * 40), BASE / "resultados")

    def test_selection_preview_and_validation_without_backend(self):
        experiment = Experiment(CONFIG)
        self.assertEqual(experiment.summary()["model_calls"], 2)
        self.assertIn("ABACAXI", experiment.preview())
        self.assertEqual(experiment.records, [])
        for patch in ({"language": "es"}, {"strategy": "35"}, {"attack": "missing"},
                      {"repetitions": 0}, {"temperature": float("nan")}, {"top_p": 2}):
            with self.assertRaises(ValueError):
                Experiment(dict(CONFIG, **patch))

    def test_both_languages_repetitions_and_secret_consistency(self):
        experiment = Experiment(dict(CONFIG, attack="V04", language="both", repetitions=2))
        self.assertEqual(len(experiment.plan), 8)
        for repetition in (1, 2):
            trials = [trial for trial in experiment.plan if trial["experiment"]["repetition"] == repetition]
            self.assertEqual(len({trial["experiment"]["target"] for trial in trials}), 1)
            self.assertEqual({trial["seed"] for trial in trials}, {41 + repetition})
        self.assertNotEqual(experiment.plan[0]["experiment"]["target"], experiment.plan[4]["experiment"]["target"])

    def test_run_uses_preview_saves_and_exports_automatically(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            experiment = Experiment(CONFIG, output_dir=directory)
            planned = [copy.deepcopy(trial["messages"]) for trial in experiment.plan]
            backend = FakeBackend()
            table = experiment.run(config=CONFIG, backend=backend)
            self.assertEqual([call[0] for call in backend.calls], planned)
            self.assertEqual([row["verdict"] for row in table], ["fail", "success"])
            self.assertEqual(table[1]["pair_status"], "eligible")
            self.assertTrue((Path(directory) / "tentativas-compiladas.csv").exists())
            self.assertEqual(next(row for row in experiment.current_statistics() if row["condition"] == "ataque")["paired_attack_success_rate"], 1)
            first_ids = [row["attempt_id"] for row in experiment.records]
            experiment.run(backend=backend)
            self.assertNotEqual(first_ids, [row["attempt_id"] for row in experiment.records])
            self.assertEqual(len(list(Path(directory).glob("attempts-*.jsonl"))), 2)
            with self.assertRaises(ValueError):
                experiment.run(config=dict(CONFIG, attack="V02"), backend=backend)

    def test_harmful_questions_are_paired_and_reviewed_from_csv(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            experiment = Experiment(dict(CONFIG, attack="Q01"), output_dir=directory)
            self.assertEqual(len(experiment.plan[0]["messages"]), 1)
            self.assertIn("histórico", experiment.plan[0]["prompt"])
            self.assertIn(experiment.plan[0]["question"], experiment.plan[1]["prompt"])
            experiment.run(backend=FakeBackend())
            path = Path(experiment.export()["manual_reviews"])
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                fields, rows = reader.fieldnames, list(reader)
            rows[0].update(verdict="fail", notes="Recusa observada na resposta simulada")
            rows[1].update(verdict="success", notes="Atendimento observado na resposta simulada")
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            experiment.import_reviews()
            self.assertEqual([row["verdict"] for row in experiment.records], ["fail", "success"])
            self.assertEqual(experiment.records[1]["pair_status"], "eligible")
            reviews = Path(directory) / f"reviews-{experiment.run_id}.jsonl"
            before = reviews.read_bytes()
            experiment.import_reviews()  # Sem mudanças, não duplica avaliações.
            self.assertEqual(before, reviews.read_bytes())

    def test_completed_baseline_survives_later_interruption(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            experiment = Experiment(CONFIG, output_dir=directory)
            with self.assertRaisesRegex(RuntimeError, "simulada"):
                experiment.run(backend=FakeBackend(fail_on_call=2))
            self.assertEqual(len(experiment.records), 1)
            self.assertTrue((Path(directory) / f"results-{experiment.run_id}.csv").exists())
            with (Path(directory) / "tentativas-compiladas.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["condition"], "direto")


if __name__ == "__main__":
    unittest.main()
