"""Valida o alinhamento EN/PT sem carregar modelos ou executar templates."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from traduzir_templates import MARKER, PROTECTED

DATA = Path(__file__).resolve().parent / "dados"


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate():
    english = read_csv("jailbreak_prompts.en.csv")
    portuguese = read_csv("jailbreak_prompts.pt-BR.csv")
    bilingual = read_csv("jailbreak_prompts.bilingual.csv")
    manifest = json.loads((DATA / "translation-reference.json").read_text(encoding="utf-8"))
    if not len(english) == len(portuguese) == len(bilingual) == manifest["rows"] == 75:
        raise ValueError("Quantidade de estratégias inconsistente")
    for name, expected_hash in manifest["files"].items():
        if hashlib.sha256((DATA / name).read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Hash alterado: {name}")
    if hashlib.sha256((DATA / "jailbreak_prompts.en.csv").read_bytes()).hexdigest() != manifest["source"]["sha256"]:
        raise ValueError("Original em inglês difere da revisão de origem")
    ids = []
    manual_adaptation = []
    for en, pt, pair in zip(english, portuguese, bilingual):
        identity = en[""]
        if identity != pt[""] or identity != pair["id"]:
            raise ValueError("IDs ou ordenação divergentes")
        ids.append(identity)
        if en["name"] != pt["name"] or en["name"] != pair["name"]:
            raise ValueError(f"Nome de estratégia alterado: {identity}")
        if en["prompt"] != pair["prompt_en"] or pt["prompt"] != pair["prompt_pt"]:
            raise ValueError(f"Tabela bilíngue divergente: {identity}")
        if not pt["prompt"].strip() or "\ufffd" in pt["prompt"]:
            raise ValueError(f"Tradução vazia ou codificação inválida: {identity}")
        if en["prompt"].count(MARKER) != pt["prompt"].count(MARKER):
            raise ValueError(f"Marcador de pergunta alterado: {identity}")
        if Counter(PROTECTED.findall(en["prompt"])) != Counter(PROTECTED.findall(pt["prompt"])):
            raise ValueError(f"Elemento técnico alterado: {identity}")
        has_marker = MARKER in en["prompt"]
        expected_mode = "replace_placeholder" if has_marker else "manual_adaptation_required"
        if pair["insertion_mode"] != expected_mode or pair["question_marker"] != (MARKER if has_marker else ""):
            raise ValueError(f"Modo de inserção inválido: {identity}")
        if not has_marker:
            manual_adaptation.append((identity, en["name"]))
        if en["name"] == "GPT-4 Simulator":
            block = en["prompt"][en["prompt"].index("def auto_regressive_modelling"):en["prompt"].index("Now generate")]
            if block not in pt["prompt"]:
                raise ValueError("Pseudocódigo original foi alterado")
    if len(set(ids)) != 75 or ids != [str(i) for i in range(75)]:
        raise ValueError("IDs duplicados ou inesperados")
    if manual_adaptation != [("35", "GPT-4 Simulator"), ("36", "GPT-4REAL")]:
        raise ValueError("Lista de exceções inesperada")
    return {"strategies": len(ids), "standard_placeholders": 73,
            "manual_adaptation": manual_adaptation,
            "review_status": dict(Counter(row["review_status"] for row in bilingual))}


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
