"""Verificações CPU, sem downloads, GPU ou registros de experimentos."""
import logging
import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
import warnings
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
runtime = ROOT / ".cache/aula04-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))

import torch
from transformers import BatchEncoding, Qwen2Config, Qwen2ForCausalLM
from transformers.cache_utils import DynamicCache
import experimento as e


class TokenizerForTest:
    eos_token_id = 63

    def apply_chat_template(self, messages, **kwargs):
        return "Pergunta sintética"

    def __call__(self, text, **kwargs):
        return BatchEncoding({"input_ids": torch.tensor([[1, 2, 3]]),
                              "attention_mask": torch.ones((1, 3), dtype=torch.long)})

    def decode(self, ids, **kwargs):
        return " ".join(str(x) for x in ids)


class CompatibilidadeTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(42)
        self.model = Qwen2ForCausalLM(Qwen2Config(
            vocab_size=64, hidden_size=16, intermediate_size=32,
            num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
            eos_token_id=63, pad_token_id=63, attn_implementation="eager",
        )).eval()
        self.model.requires_grad_(False)

    def test_greedy_ignora_amostragem_sem_avisos(self):
        config = self.model.generation_config
        config.do_sample = True
        config.temperature = .7
        config.top_p = .8
        config.top_k = 20
        tokenizer = TokenizerForTest()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            expected = self.model.generate(**tokenizer(""), do_sample=False, max_new_tokens=2,
                                           pad_token_id=63)[0, 3:].tolist()
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            actual = e.generate(self.model, tokenizer, [{"role": "user", "content": "2+2"}], 2)
        self.assertEqual(actual["generated_ids"], expected)
        self.assertFalse([w for w in emitted if "do_sample" in str(w.message)])
        self.assertEqual(config.temperature, .7)  # Config original não é modificada.

    def test_cache_preserva_logits_gradiente_e_prefixo(self):
        prefix = self.model(torch.tensor([[1, 2]]), use_cache=True).past_key_values
        original = tuple(tuple(t.clone() for t in layer) for layer in prefix)
        base = self.model.get_input_embeddings()(torch.tensor([[3, 4]])).detach()

        def evaluate(past=None):
            embeds = base.clone().requires_grad_(True)
            logits = self.model(inputs_embeds=embeds, past_key_values=prefix if past is None else past, use_cache=True).logits
            grad = torch.autograd.grad(logits.square().sum(), embeds)[0]
            return logits.detach(), grad

        logger = logging.getLogger("transformers.models.qwen2.modeling_qwen2")
        with self.assertLogs(logger, level="WARNING"):
            expected_logits, expected_grad = evaluate()
        handle = self.model.register_forward_pre_hook(e.normalize_legacy_cache, with_kwargs=True)
        try:
            with self.assertNoLogs(logger, level="WARNING"):
                for past in (prefix, [list(layer) for layer in prefix], prefix):
                    logits, grad = evaluate(past)
                    torch.testing.assert_close(logits, expected_logits, rtol=0, atol=0)
                    torch.testing.assert_close(grad, expected_grad, rtol=0, atol=0)
        finally:
            handle.remove()
        for before, after in zip(original, prefix):
            for a, b in zip(before, after):
                torch.testing.assert_close(a, b, rtol=0, atol=0)
        dynamic = DynamicCache.from_legacy_cache(prefix)
        _, kwargs = e.normalize_legacy_cache(self.model, (), {"past_key_values": dynamic})
        self.assertIs(kwargs["past_key_values"], dynamic)
        self.assertFalse(self.model._forward_pre_hooks)


class LotesTest(unittest.TestCase):
    def settings(self):
        return {"model_ids": ["modelo-a", "modelo-b"], "case_ids": ["V01", "V02", "V03"],
                "suffix_units": [8], "seeds": [42], "num_steps": 2}

    def test_plano_enumera_combinacoes_e_valida_antes_de_carregar(self):
        settings = self.settings()
        settings.update(suffix_units=[8, 16], seeds=[42, 43])
        with patch.object(e, "load_model") as load:
            jobs = e.build_test_plan(settings)
            self.assertEqual(len(jobs), 24)
            self.assertEqual(len({(j['model_id'], j['case_id'], j['suffix_units'], j['seed']) for j in jobs}), 24)
            for invalid in ([], [0], [True]):
                with self.assertRaises(ValueError):
                    e.build_test_plan({**settings, "suffix_units": invalid})
            with self.assertRaises(ValueError):
                e.build_test_plan({**settings, "seeds": [42, 42]})
            load.assert_not_called()

    def test_manual_mensagens_target_separador_e_persistencia(self):
        manual = {"system": "Somente rótulos.", "message": "Diga ALVO.", "target": "ALVO"}
        model = types.SimpleNamespace(config=types.SimpleNamespace(_name_or_path="modelo-teste"),
                                      dtype=torch.float32, register_forward_pre_hook=Mock())
        tokenizer = types.SimpleNamespace(encode=lambda text, **kw: text.split())
        generated_messages = []

        def generate(_m, _t, messages, limit):
            self.assertEqual(limit, 73)
            generated_messages.append(messages)
            return {"response": "OUTRO" if len(generated_messages) == 1 else "ALVO",
                    "truncated": False, "prompt_rendered": repr(messages), "input_ids": [1]}

        fake_result = types.SimpleNamespace(best_string=" foo bar", best_loss=.5, losses=[.5], strings=[" foo bar"])
        with tempfile.TemporaryDirectory() as temp, patch.object(e, "BASE", Path(temp)), \
                patch.object(e, "DATA", Path(temp) / "inexistente.csv"), \
                patch.object(e, "generate", side_effect=generate), \
                patch("nanogcg.run", return_value=fake_result) as optimize, \
                patch("torch.cuda.get_device_name", return_value="GPU simulada"), \
                contextlib.redirect_stdout(io.StringIO()):
            result = e.run_case(model, tokenizer, "MANUAL", suffix_units=2, num_steps=2,
                                manual_case=manual, suffix_separator="\n\n", max_new_tokens=73,
                                search_width=4, topk=3, batch_size=2, batch_id="lote-teste")
            cfg = json.loads((Path(temp) / "resultados" / result["run_id"] / "config.json").read_text(encoding="utf-8"))
            self.assertIsNone(cfg["data_sha256"])
            self.assertEqual(cfg["case"]["target"], "ALVO")
            self.assertEqual(cfg["batch_id"], "lote-teste")
            self.assertEqual(cfg["suffix_separator"], "\n\n")
            self.assertEqual(generated_messages[0][-1]["content"], "Diga ALVO.")
            self.assertEqual(generated_messages[1][-1]["content"], "Diga ALVO.\n\n foo bar")
            self.assertEqual(optimize.call_args.args[2][-1]["content"], "Diga ALVO.\n\n{optim_str}")
            self.assertEqual(optimize.call_args.args[3], "ALVO")
            self.assertEqual(optimize.call_args.args[4].topk, 3)
            self.assertEqual(result["baseline_diagnostic"], "not_applicable")
            self.assertEqual(result["attack_diagnostic"], "not_applicable")
            self.assertFalse(result["baseline_target_exact"])
            self.assertTrue(result["attack_target_exact"])
            model.register_forward_pre_hook.return_value.remove.assert_called_once()
        self.assertEqual(manual["message"], "Diga ALVO.")
        self.assertEqual(e.prepare("MANUAL", {**manual, "system": ""})["messages"],
                         [{"role": "user", "content": "Diga ALVO."}])
        for invalid in ({**manual, "target": ""}, {**manual, "message": "{optim_str}"}):
            with self.assertRaises(ValueError):
                e.prepare("MANUAL", invalid)

    def test_lote_carrega_cada_modelo_uma_vez_e_continua_apos_falha(self):
        def load(name):
            return types.SimpleNamespace(name=name), object()

        def run(model, tokenizer, **kwargs):
            if model.name == "modelo-a" and kwargs["case_id"] == "V02":
                raise ValueError("falha simulada")
            return {"run_id": model.name + kwargs["case_id"]}

        with tempfile.TemporaryDirectory() as temp, patch.object(e, "BASE", Path(temp)), \
                patch.object(e, "load_model", side_effect=load) as loading, \
                patch.object(e, "run_case", side_effect=run), \
                patch("torch.cuda.is_available", return_value=False), \
                contextlib.redirect_stdout(io.StringIO()):
            result = e.run_batch(self.settings())
            self.assertEqual(loading.call_count, 2)
            self.assertEqual(len(result["results"]), 5)
            self.assertEqual(len(result["errors"]), 1)
            states = json.loads((Path(result["folder"]) / "andamento.json").read_text(encoding="utf-8"))
            self.assertEqual([s["status"] for s in states["tests"]].count("completed"), 5)
            self.assertEqual(states["tests"][1]["status"], "error")
            self.assertTrue((Path(result["folder"]) / "resumo.csv").is_file())

    def test_notebook_previa_seis_sinteticos_e_dois_manuais(self):
        from notebook_lotes import batch_cells
        cells = batch_cells(Path(e.__file__))
        namespace = {"build_test_plan": e.build_test_plan}
        with contextlib.redirect_stdout(io.StringIO()), patch.object(e, "load_model") as loading:
            for cell in cells:
                if cell.metadata.get("automated_tests") in {"settings", "synthetic_preview", "manual_settings"}:
                    exec(cell.source, namespace)
            self.assertEqual(len(namespace["SYNTHETIC_PLAN"]), 6)
            self.assertEqual(len(namespace["MANUAL_PLAN"]), 2)
            self.assertEqual(namespace["MANUAL_PLAN"][0]["case"]["target"], namespace["MANUAL_CASE"]["target"])
            loading.assert_not_called()

    def test_secao_de_lote_substitui_funcoes_antigas_no_kernel(self):
        from notebook_lotes import batch_cells
        import inspect
        cells = batch_cells(Path(e.__file__))
        namespace = {"ROOT": ROOT, "BASE": e.BASE, "DATA": e.DATA, "TARGETS": e.TARGETS,
                     "prepare": lambda case_id: None, "run_case": lambda model, tokenizer: None}
        with contextlib.redirect_stdout(io.StringIO()):
            setup = next(c for c in cells if c.metadata.get("automated_tests") == "definitions")
            exec(setup.source, namespace)
            self.assertIn("manual_case", inspect.signature(namespace["prepare"]).parameters)
            self.assertIn("manual_case", inspect.signature(namespace["run_case"]).parameters)
            loading = Mock(side_effect=AssertionError("A prévia não deve carregar modelos."))
            namespace["load_model"] = loading
            for cell in cells:
                if cell.metadata.get("automated_tests") in {"settings", "synthetic_preview", "manual_settings"}:
                    exec(cell.source, namespace)
            self.assertEqual(len(namespace["SYNTHETIC_PLAN"]), 6)
            self.assertEqual(len(namespace["MANUAL_PLAN"]), 2)
            loading.assert_not_called()


if __name__ == "__main__":
    unittest.main()
