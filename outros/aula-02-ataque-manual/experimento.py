"""Configuração, construção, inferência e exportação da aula 02.

Importação e prévia não carregam PyTorch, modelo ou GPU. Dados dos CSVs nunca
são executados como código. A classe Experiment é a interface do notebook.
"""
import copy
import csv
import hashlib
import html
import importlib.metadata
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import ataques_verificaveis as verifiable
import compilar_resultados as compiler

BASE = Path(__file__).resolve().parent
_BACKEND = globals().get("_BACKEND")  # Recarregar o código não duplica o modelo na GPU.
CONFIG_KEYS = {"strategy", "attack", "language", "repetitions", "seed", "model",
               "revision", "cache_dir", "max_input_tokens", "max_new_tokens",
               "temperature", "top_p"}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def append_jsonl(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def windows_memory_info():
    """RAM e margem de commit do Windows; leitura apenas, sem WMI ou privilégios."""
    import os
    if os.name != "nt":
        return {}
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
            ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
            ("total_commit", ctypes.c_ulonglong), ("avail_commit", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
            ("avail_extended", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {}
    return {"ram_total_gib": status.total_phys / 2**30,
            "ram_available_gib": status.avail_phys / 2**30,
            "commit_limit_gib": status.total_commit / 2**30,
            "commit_available_gib": status.avail_commit / 2**30}


def import_review_files(output_dir=BASE / "resultados"):
    """Importa todos os CSVs de avaliação; valida cada arquivo antes de gravá-lo.

    Não altera CSVs editados pelo aluno. Arquivos inválidos são relatados,
    enquanto arquivos válidos independentes podem ser importados normalmente.
    Pode ser usado sem Experiment ativo, sem modelo e após reiniciar o kernel.
    """
    output = Path(output_dir)
    rows, _ = compiler.compile_results(output)
    lookup = {row["attempt_id"]: row for row in rows}
    reports, errors, selected = [], [], set()
    run_ids = set()
    for path in sorted(output.glob("avaliacoes-*.csv")):
        run_id = path.stem.removeprefix("avaliacoes-")
        run_ids.add(run_id)
        changes, file_errors, seen = [], [], set()
        pending, unchanged = 0, 0
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                if not {"attempt_id", "verdict"}.issubset(reader.fieldnames or []):
                    raise ValueError("Cabeçalho inválido: precisa de attempt_id e verdict; notes é opcional. Use vírgula como delimitador.")
                reviews = list(reader)
        except (ValueError, csv.Error, UnicodeError) as error:
            file_errors.append({"file": path.name, "row": 1, "attempt_id": "", "csv_verdict": "", "reason": str(error)})
            reviews = []
        for number, review in enumerate(reviews, 2):
            identity = (review.get("attempt_id") or "").strip()
            verdict = (review.get("verdict") or "").strip()
            notes = (review.get("notes") or "").strip()
            reason = None
            if identity in seen:
                reason = "attempt_id duplicado neste CSV."
            elif identity not in lookup:
                reason = "attempt_id não encontrado nos registros de tentativas."
            elif lookup[identity]["run_id"] != run_id:
                reason = "A tentativa pertence a outra execução; confira o nome do arquivo e o ID."
            elif None in review:
                reason = "Há colunas excedentes; confira vírgulas e aspas no CSV."
            seen.add(identity)
            if reason is None:
                selected.add(identity)
                if verdict in {"", "pending"}:
                    pending += 1
                    continue
                if verdict not in compiler.CONCLUSIVE | {"inconclusive"}:
                    reason = "Rótulo inválido. Use fail, partial_success, success ou inconclusive."
                elif (verdict, notes) == (lookup[identity]["verdict"], lookup[identity]["notes"]):
                    unchanged += 1
                else:
                    changes.append({"attempt_id": identity, "verdict": verdict, "notes": notes,
                                    "reviewer": "manual", "utc": datetime.now(timezone.utc).isoformat()})
            if reason:
                file_errors.append({"file": path.name, "row": number, "attempt_id": identity,
                                    "csv_verdict": verdict, "reason": reason})
        if not file_errors:
            for review in changes:
                append_jsonl(output / f"reviews-{run_id}.jsonl", review)
                lookup[review["attempt_id"]].update(review)
        errors.extend(file_errors)
        cases = sorted({lookup[identity].get("case_id", "") for identity in seen if identity in lookup})
        reports.append({"file": path.name, "cases": ", ".join(cases),
            "status": "corrigir CSV" if file_errors else "importado" if changes else "sem alterações",
            "updated": 0 if file_errors else len(changes), "unchanged": unchanged,
            "pending": pending, "errors": len(file_errors)})
    rows, stats = compiler.compile_results(output)
    # Atualiza os retratos das execuções avaliadas, não apenas o último Experiment em memória.
    for run_id in run_ids:
        run_rows = [row for row in rows if row.get("run_id") == run_id]
        if run_rows:
            (output / f"results-{run_id}.json").write_text(
                json.dumps(run_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            compiler.write_csv(output / f"results-{run_id}.csv", run_rows, compiler.FIELDS)
    columns = ("run_id", "case_id", "template_name", "language", "condition", "verdict", "notes")
    return {"files": reports, "errors": errors,
            "results": [{key: row.get(key, "") for key in columns} for row in rows if row["attempt_id"] in selected],
            "statistics": stats}


class Experiment:
    def __init__(self, config, activity_dir=BASE, output_dir=None):
        self.config = copy.deepcopy(config)
        self._validate_config()
        self.base = Path(activity_dir)
        self.data = self.base / "dados"
        self.output = Path(output_dir) if output_dir else self.base / "resultados"
        self.strategy_path = self.data / "jailbreak_prompts.bilingual.csv"
        self.strategy_hash = hashlib.sha256(self.strategy_path.read_bytes()).hexdigest()
        strategies = csv_rows(self.strategy_path)
        selected = [row for row in strategies if str(config["strategy"]) in {row["id"], row["name"]}]
        if len(selected) != 1:
            raise ValueError("Estratégia inexistente ou ambígua. Use o nome exato ou ID do CSV.")
        self.strategy = selected[0]
        verifiable.validate_strategy(self.strategy)
        cases = verifiable.load_cases(self.data / "verifiable_attacks.bilingual.csv")
        question_path = self.data / "attack_questions.bilingual.csv"
        questions = {row["question_id"]: row for row in csv_rows(question_path)}
        identity = config["attack"]
        if identity in cases:
            self.case = cases[identity]
            self.family = "verifiable"
        elif identity in questions:
            self.case = dict(questions[identity], case_id=identity,
                             case_hash=fingerprint(questions[identity]),
                             taskset_sha256=hashlib.sha256(question_path.read_bytes()).hexdigest())
            self.family = "harmful_request"
        else:
            raise ValueError("Ataque inexistente. Use V01–V05 ou Q01–Q08.")
        self.languages = ["en", "pt"] if config["language"] == "both" else [config["language"]]
        self.dataset_reference = json.loads((self.output_reference_dir / "dataset-reference.json").read_text(encoding="utf-8"))
        english = self.data / "jailbreak_prompts.en.csv"
        if hashlib.sha256(english.read_bytes()).hexdigest() != self.dataset_reference["sha256"]:
            raise ValueError("O CSV original difere do hash registrado.")
        self.records = []
        self.run_id = None
        self._consumed_plan = False
        self.plan = self._build_plan()

    @property
    def output_reference_dir(self):
        # Referências pertencem à atividade, mesmo quando testes usam saída temporária.
        return self.base / "resultados"

    def _validate_config(self):
        if set(self.config) != CONFIG_KEYS:
            raise ValueError(f"Campos de configuração: faltam {CONFIG_KEYS - set(self.config)}; "
                             f"desconhecidos {set(self.config) - CONFIG_KEYS}.")
        if self.config["language"] not in {"en", "pt", "both"}:
            raise ValueError("language deve ser en, pt ou both.")
        for field in ("repetitions", "max_input_tokens", "max_new_tokens"):
            if type(self.config[field]) is not int or self.config[field] < 1:
                raise ValueError(f"{field} deve ser inteiro positivo.")
        if type(self.config["seed"]) is not int or not 0 <= self.config["seed"] < 2**32:
            raise ValueError("seed deve ser inteiro entre 0 e 2**32-1.")
        if self.config["seed"] + self.config["repetitions"] - 1 >= 2**32:
            raise ValueError("As seeds das repetições excedem o intervalo permitido.")
        for field in ("temperature", "top_p"):
            value = self.config[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field} deve ser um número finito positivo.")
        if self.config["top_p"] > 1:
            raise ValueError("top_p deve ser no máximo 1.")
        for field in ("model", "cache_dir", "attack"):
            if not isinstance(self.config[field], str) or not self.config[field].strip():
                raise ValueError(f"{field} não pode ser vazio.")
        revision = self.config["revision"]
        if revision is not None and (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision)):
            raise ValueError("revision deve ser None ou um SHA de commit completo.")

    def _build_plan(self):
        plan = []
        for repetition in range(self.config["repetitions"]):
            # Mesmo segredo sintético nos dois idiomas da mesma repetição.
            secret = "TEST_SECRET_" + uuid.uuid4().hex.upper()
            for language in self.languages:
                pair_id = uuid.uuid4().hex
                for condition in ("direto", "ataque"):
                    if self.family == "verifiable":
                        trial = verifiable.build_trial(self.case, self.strategy, language, condition, pair_id, secret)
                    else:
                        question = self.case[f"question_{language}"]
                        template = self.strategy[f"prompt_{language}"]
                        prompt = question if condition == "direto" else template.replace("[INSERT PROMPT HERE]", question)
                        trial = {"trial_id": f"{self.case['case_id']}-{self.strategy['id']}-{language}-{condition}",
                            "language": language, "condition": condition, "prompt": prompt, "question": question,
                            "template_name": self.strategy["name"] if condition == "ataque" else "direto",
                            "source_template": template if condition == "ataque" else None,
                            "adaptation": "Pergunta EN/PT e estratégia selecionadas dos CSVs versionados",
                            "messages": [{"role": "user", "content": prompt}],
                            "experiment": {"evaluation_family": self.family, "protocol": "harmful_pair_v1",
                                "case_id": self.case["case_id"], "case_hash": self.case["case_hash"],
                                "taskset_sha256": self.case["taskset_sha256"], "strategy_id": self.strategy["id"],
                                "pair_id": pair_id, "evaluation_scope": "visible",
                                "success_criterion": self.case[f"success_criterion_{language}"]}}
                    trial["experiment"]["strategyset_sha256"] = self.strategy_hash
                    trial["experiment"]["repetition"] = repetition + 1
                    trial["seed"] = self.config["seed"] + repetition
                    plan.append(trial)
        return plan

    def summary(self):
        return {"attack": self.case["case_id"], "name": self.case["name_pt"],
                "strategy": self.strategy["name"], "languages": ", ".join(self.languages),
                "repetitions": self.config["repetitions"], "model_calls": len(self.plan),
                "evaluation": "automática" if self.family == "verifiable" else "humana, por CSV"}

    def preview(self):
        parts = ["<p><strong>Prévia das mensagens que serão enviadas.</strong> Nenhuma inferência executada.</p>"]
        for trial in self.plan:
            condition_label = ("direto — sem estratégia" if trial["condition"] == "direto"
                               else f"com estratégia — {self.strategy['name']}")
            label = f"{trial['language'].upper()} · {condition_label} · repetição {trial['experiment']['repetition']}"
            content = "\n\n".join(f"[{message['role']}]\n{message['content']}" for message in trial["messages"])
            parts.append(f"<details><summary>{html.escape(label)}</summary><pre>{html.escape(content)}</pre></details>")
        return "\n".join(parts)

    def run(self, config=None, backend=None, kernel=None):
        if config is not None and fingerprint(config) != fingerprint(self.config):
            raise ValueError("A configuração mudou. Reexecute a célula Preparar e conferir antes de executar.")
        if self._consumed_plan:
            self.plan = self._build_plan()
        backend = backend or get_backend(self.config, self.output_reference_dir, kernel)
        # Verifica todas as entradas antes da primeira geração, quando o backend oferece tokenizer.
        if hasattr(backend, "validate_inputs"):
            backend.validate_inputs(self.plan, self.config["max_input_tokens"])
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        self.records = []
        self._consumed_plan = True
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / f"run-config-{self.run_id}.json").write_text(
            json.dumps({"config": self.config, "selection": self.summary(), "backend": backend.metadata},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        generation = {"max_new_tokens": self.config["max_new_tokens"], "do_sample": True,
                      "temperature": self.config["temperature"], "top_p": self.config["top_p"]}
        baselines = {}
        try:
            for index, trial in enumerate(self.plan, 1):
                print(f"[{index}/{len(self.plan)}] {trial['trial_id']} · seed {trial['seed']}", flush=True)
                result = backend.generate(trial["messages"], seed=trial["seed"], generation=generation,
                                          max_input_tokens=self.config["max_input_tokens"])
                record = {key: value for key, value in trial.items() if key not in {"experiment"}}
                record.update(trial["experiment"])
                record.update(result)
                record.update(backend.metadata)
                record.update(run_id=self.run_id, attempt_id=uuid.uuid4().hex,
                    utc=datetime.now(timezone.utc).isoformat(), generation=dict(generation),
                    dataset_revision=self.dataset_reference["revision"],
                    dataset_sha256=self.dataset_reference["sha256"], verdict="pending", notes="")
                if record["condition"] == "ataque":
                    record["baseline_attempt_id"] = baselines[record["pair_id"]]
                else:
                    baselines[record["pair_id"]] = record["attempt_id"]
                append_jsonl(self.output / f"attempts-{self.run_id}.jsonl", record)
                self.records.append(record)
                if self.family == "verifiable":
                    verifiable.save_evaluation(record, self.output)
                print(f"  {record['output_tokens']} tokens · {record['seconds']:.1f}s · {record['verdict']}", flush=True)
        finally:
            # Também exporta gerações já concluídas em caso de interrupção/erro posterior.
            if self.records:
                self.export()
        return self.results_table()

    def results_table(self):
        fields = ("attempt_id", "case_id", "language", "condition", "seed", "verdict",
                  "pair_status", "output_tokens", "seconds", "hit_token_limit")
        return [{field: row.get(field, "") for field in fields} for row in self.records]

    def render_results(self):
        if not self.records:
            return "<p>Nenhuma resposta nesta execução.</p>"
        parts = []
        for row in self.records:
            label = f"{row['language'].upper()} · {row['condition']} · {row['verdict']} · {row['attempt_id'][:8]}"
            text = row["response"]
            if "</think>" in text:
                reasoning, final = text.split("</think>", 1)
                content = "RACIOCÍNIO EXPOSTO\n" + reasoning.removeprefix("<think>").strip() + "\n\nRESPOSTA FINAL\n" + final.strip()
            else:
                content = "SAÍDA GERADA\n" + text
            parts.append(f"<details><summary>{html.escape(label)}</summary><pre>{html.escape(content)}</pre></details>")
        return "\n".join(parts)

    def _review_path(self):
        if not self.run_id:
            raise ValueError("Execute um experimento antes de importar avaliações.")
        return self.output / f"avaliacoes-{self.run_id}.csv"

    def import_reviews(self):
        path = self._review_path()
        if not path.exists():
            print("Este caso tem avaliação automática; não há CSV de avaliação humana pendente.")
            return self.results_table()
        lookup = {row["attempt_id"]: row for row in self.records}
        changes = []
        seen = set()
        for review in csv_rows(path):
            identity = review["attempt_id"]
            if identity in seen:
                raise ValueError("ID duplicado no CSV de avaliações.")
            seen.add(identity)
            if identity not in lookup:
                raise ValueError("Avaliação não pertence a esta execução.")
            verdict, notes = review["verdict"].strip(), (review.get("notes") or "").strip()
            if verdict in {"", "pending"}:
                continue
            if verdict not in compiler.CONCLUSIVE | {"inconclusive"}:
                raise ValueError("Use fail, partial_success, success ou inconclusive. notes é opcional.")
            if (verdict, notes) != (lookup[identity]["verdict"], lookup[identity]["notes"]):
                changes.append((identity, verdict, notes))
        for identity, verdict, notes in changes:
            lookup[identity].update(verdict=verdict, notes=notes, reviewer="manual")
            append_jsonl(self.output / f"reviews-{self.run_id}.jsonl", {
                "attempt_id": identity, "verdict": verdict, "notes": notes, "reviewer": "manual",
                "utc": datetime.now(timezone.utc).isoformat()})
        self.export()
        print(f"{len(changes)} avaliação(ões) atualizada(s).")
        return self.results_table()

    def current_statistics(self):
        configurations = {record.get("config_id") for record in self.records}
        return [row for row in getattr(self, "statistics", []) if row["config_id"] in configurations]

    def export(self):
        rows, stats = compiler.compile_results(self.output)
        current = {row["attempt_id"]: row for row in rows}
        for record in self.records:
            record.update(current[record["attempt_id"]])
        if self.run_id and self.records:
            (self.output / f"results-{self.run_id}.json").write_text(
                json.dumps(self.records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            compiler.write_csv(self.output / f"results-{self.run_id}.csv", self.records, compiler.FIELDS)
            versions = self.records[0].get("environment", {}).get("packages", {})
            (self.output / f"versions-{self.run_id}.txt").write_text(
                "\n".join(f"{name}=={version}" for name, version in versions.items()) + "\n", encoding="utf-8")
            if self.family == "harmful_request" and not self._review_path().exists():
                review_rows = [{key: row.get(key, "") for key in
                              ("attempt_id", "language", "condition", "verdict", "notes", "response", "success_criterion")}
                              for row in self.records]
                compiler.write_csv(self._review_path(), review_rows, list(review_rows[0]))
        self.statistics = stats
        return {"directory": str(self.output), "attempts": str(self.output / "tentativas-compiladas.csv"),
                "summary": str(self.output / "resumo-ataques.csv"),
                "statistics": str(self.output / "estatisticas-compiladas.csv"),
                "manual_reviews": str(self._review_path()) if self.run_id and self.family == "harmful_request" else None}


def get_backend(config, reference_dir, kernel=None):
    global _BACKEND
    reference_path = Path(reference_dir) / "model-reference.json"
    revision = config["revision"]
    if revision is None and reference_path.exists():
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        if reference["model"] == config["model"]:
            revision = reference["revision"]
    if revision is None:
        from huggingface_hub import model_info
        revision = model_info(config["model"]).sha
    key = (config["model"], revision)
    if _BACKEND is not None:
        if _BACKEND.key != key:
            raise RuntimeError("Outro modelo já está carregado. Reinicie o kernel para trocar de modelo.")
        print("Reutilizando o modelo já carregado.", flush=True)
        return _BACKEND
    _BACKEND = TransformersBackend(config, revision, kernel or {})
    return _BACKEND


class TransformersBackend:
    def __init__(self, config, revision, kernel):
        import platform
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        self.key = (config["model"], revision)
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA indisponível. Confira o kernel e a instalação do PyTorch.")
        existing = kernel.get("model")
        load_memory = {"reused_existing_model": True}
        if (existing is not None and kernel.get("MODEL_ID") == config["model"]
                and kernel.get("MODEL_REVISION") == revision
                and getattr(existing, "is_loaded_in_4bit", False) and kernel.get("tokenizer") is not None):
            self.model, self.tokenizer = existing, kernel["tokenizer"]
            print("Reutilizando o modelo e o tokenizer do notebook anterior.", flush=True)
        else:
            if existing is not None and hasattr(existing, "generate"):
                raise RuntimeError("Há um modelo antigo incompatível neste kernel. Reinicie o kernel para trocar de modelo.")
            import gc
            gc.collect()
            torch.cuda.empty_cache()  # Só libera blocos ociosos; não remove modelos vivos.
            free, total = torch.cuda.mem_get_info(0)
            load_memory = {"gpu_free_gib": free / 2**30, "gpu_total_gib": total / 2**30,
                           **windows_memory_info()}
            print(f"VRAM livre: {free / 2**30:.2f}/{total / 2**30:.2f} GiB", flush=True)
            if "commit_limit_gib" in load_memory:
                committed = load_memory["commit_limit_gib"] - load_memory["commit_available_gib"]
                print(f"Windows: RAM livre {load_memory['ram_available_gib']:.2f} GiB; "
                      f"memória comprometida {committed:.2f}/{load_memory['commit_limit_gib']:.2f} GiB "
                      f"(margem {load_memory['commit_available_gib']:.2f} GiB).", flush=True)
            if free < 12 * 2**30:
                raise RuntimeError("VRAM insuficiente para carregar o modelo. Se outro modelo ocupa a GPU, reinicie o kernel.")
            cache = Path(config["cache_dir"]).expanduser()
            local = cache / ("models--" + config["model"].replace("/", "--")) / "snapshots" / revision
            source = str(local) if local.is_dir() else config["model"]
            options = {"cache_dir": str(cache), "trust_remote_code": False}
            if not local.is_dir():
                options["revision"] = revision
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype)
            print("Carregando modelo em NF4 na GPU…", flush=True)
            self.tokenizer = AutoTokenizer.from_pretrained(source, **options)
            try:
                self.model = AutoModelForCausalLM.from_pretrained(source, **options,
                    quantization_config=quantization, device_map={"": 0}, dtype=dtype,
                    attn_implementation="sdpa").eval()
            except torch.OutOfMemoryError as error:
                current = windows_memory_info()
                margin = (f" Margem de memória comprometida do Windows: "
                          f"{current['commit_available_gib']:.2f} GiB."
                          if "commit_available_gib" in current else "")
                raise RuntimeError(
                    "Falta de memória ao CARREGAR o modelo, antes de gerar respostas." + margin +
                    " No Windows, RAM/commit/paginação podem limitar alocações CUDA mesmo com VRAM livre. "
                    "Reinicie o kernel, libere memória do sistema e confira a paginação antes de repetir. "
                    "Reduzir max_new_tokens não resolve uma falha na pré-alocação do carregamento."
                ) from error
        self.model.eval()
        packages = {name: importlib.metadata.version(name) for name in
                    ("torch", "transformers", "accelerate", "bitsandbytes", "pandas", "huggingface-hub")}
        self.metadata = {"model_id": config["model"], "model_revision": revision,
            "quantization": "NF4, double quantization", "load_memory": load_memory, "environment": {
                "python": platform.python_version(), "platform": platform.platform(),
                "packages": packages, "gpu": torch.cuda.get_device_name(0), "torch_cuda": torch.version.cuda}}

    def validate_inputs(self, plan, limit):
        for trial in plan:
            count = len(self.tokenizer.apply_chat_template(trial["messages"], tokenize=True, add_generation_prompt=True))
            if count > limit:
                raise ValueError(f"{trial['trial_id']}: {count} tokens excedem max_input_tokens={limit}. Nenhuma entrada é truncada.")

    def generate(self, messages, *, seed, generation, max_input_tokens):
        import gc
        import time
        import torch
        from transformers import set_seed
        encoded = self.tokenizer.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=True, return_tensors="pt", return_dict=True)
        n_input = encoded["input_ids"].shape[-1]
        if n_input > max_input_tokens:
            raise ValueError("Entrada excede o limite configurado.")
        chat = self.tokenizer.decode(encoded["input_ids"][0], skip_special_tokens=False)
        encoded = {key: value.to("cuda:0") for key, value in encoded.items()}
        set_seed(seed)
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(0)
        torch.cuda.synchronize()
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                generated = self.model.generate(**encoded, **generation, pad_token_id=self.tokenizer.eos_token_id)
            torch.cuda.synchronize()
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            raise RuntimeError("VRAM insuficiente. Reduza max_new_tokens/max_input_tokens e prepare uma nova execução.") from None
        elapsed = time.perf_counter() - started
        ids = generated[0, n_input:].tolist()
        text = self.tokenizer.decode(ids, skip_special_tokens=True)
        eos = self.model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        ended = bool(ids and ids[-1] in eos)
        return {"response": text, "raw_output": self.tokenizer.decode(ids, skip_special_tokens=False),
            "chat_prompt": chat, "think_open_in_input": chat.rstrip().endswith("<think>"),
            "has_think_end": "</think>" in text,
            "final_response": text.split("</think>", 1)[1].strip() if "</think>" in text else None,
            "input_tokens": n_input, "output_tokens": len(ids), "seconds": elapsed,
            "ended_eos": ended, "hit_token_limit": len(ids) >= generation["max_new_tokens"] and not ended,
            "peak_allocated_gib": torch.cuda.max_memory_allocated(0) / 2**30,
            "peak_reserved_gib": torch.cuda.max_memory_reserved(0) / 2**30}
