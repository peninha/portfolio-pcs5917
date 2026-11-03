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
import compilar_resultados as compiler
from experimento import BASE, Experiment, import_review_files


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
        text = "ABACAXI" if "🤓" in messages[-1]["content"] else "Não vou escrever a palavra proibida."
        return {"response": f"Raciocínio.</think>{text}", "raw_output": text,
                "output_tokens": 10, "input_tokens": 20, "seconds": 0.01,
                "peak_allocated_gib": 1, "hit_token_limit": False,
                "think_open_in_input": True, "final_response": text}


class ExperimentTests(unittest.TestCase):
    def test_simple_summary_uses_only_attacks_and_conclusive_denominator(self):
        common = {"evaluation_family": "verifiable", "case_id": "V01", "strategy_id": "0",
                  "config_id": "fixture", "language": "pt", "partial_success": 1}
        stats = [dict(common, condition="direto", template_name="direto", total=4,
                      conclusive=2, success=1, success_rate=0.5),
                 dict(common, condition="ataque", template_name="3-Liner", total=5,
                      conclusive=3, success=2, success_rate=2/3)]
        summary = compiler.summarize_attacks(stats)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["tentativas"], 5)
        self.assertEqual(summary[0]["avaliadas"], 3)
        self.assertEqual(summary[0]["sucessos"], 2)
        self.assertEqual(summary[0]["parciais"], 1)
        self.assertEqual(summary[0]["taxa_sucesso_pct"], 66.67)
        self.assertEqual(summary[0]["taxa_direto_pct"], 50)
        stats[1].update(conclusive=0, success=0, partial_success=0, success_rate=None)
        self.assertIsNone(compiler.summarize_attacks(stats)[0]["taxa_sucesso_pct"])

    def make_review_file(self, experiment, missing_note=False):
        path = Path(experiment.export()["manual_reviews"])
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        for index, row in enumerate(rows):
            row.update(verdict="fail" if row["condition"] == "direto" else "success",
                       notes="" if missing_note and index == 0 else "Evidência de teste")
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_global_reviews_import_two_cases_and_do_not_overwrite_csvs(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            paths = []
            for case in ("Q01", "Q02"):
                experiment = Experiment(dict(CONFIG, attack=case), output_dir=directory)
                experiment.run(backend=FakeBackend())
                paths.append(self.make_review_file(experiment))
            originals = {path: path.read_bytes() for path in paths}
            report = import_review_files(directory)
            self.assertEqual(len(report["files"]), 2)
            self.assertEqual(report["errors"], [])
            self.assertEqual(sum(row["updated"] for row in report["files"]), 4)
            self.assertEqual({row["case_id"] for row in report["results"]}, {"Q01", "Q02"})
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)
            reviews = {path: path.read_bytes() for path in Path(directory).glob("reviews-*.jsonl")}
            repeated = import_review_files(directory)
            self.assertEqual(sum(row["updated"] for row in repeated["files"]), 0)
            for path, content in reviews.items():
                self.assertEqual(path.read_bytes(), content)

    def test_global_reviews_accept_empty_notes_for_all_runs(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            first = Experiment(dict(CONFIG, attack="Q01"), output_dir=directory)
            first.run(backend=FakeBackend())
            self.make_review_file(first, missing_note=True)
            second = Experiment(dict(CONFIG, attack="Q02"), output_dir=directory)
            second.run(backend=FakeBackend())
            self.make_review_file(second)
            report = import_review_files(directory)
            self.assertEqual(report["errors"], [])
            self.assertEqual(sum(row["updated"] for row in report["files"]), 4)
            self.assertEqual({row["verdict"] for row in report["results"] if row["case_id"] == "Q01"}, {"fail", "success"})
            self.assertEqual({row["verdict"] for row in report["results"] if row["case_id"] == "Q02"}, {"fail", "success"})
            self.assertEqual(next(row["notes"] for row in report["results"]
                                  if row["case_id"] == "Q01" and row["condition"] == "direto"), "")

    def test_reviews_accept_csv_without_optional_notes_column(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            experiment = Experiment(dict(CONFIG, attack="Q01"), output_dir=directory)
            experiment.run(backend=FakeBackend())
            path = Path(experiment.export()["manual_reviews"])
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["attempt_id", "verdict"])
                writer.writeheader()
                writer.writerows({"attempt_id": row["attempt_id"], "verdict": "success"}
                                 for row in experiment.records)
            report = import_review_files(directory)
            self.assertEqual(report["errors"], [])
            self.assertEqual([row["notes"] for row in report["results"]], ["", ""])

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
