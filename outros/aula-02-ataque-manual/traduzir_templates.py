"""Traduz templates como dados, sem executar ataques nem o conteúdo do CSV.

Requer torch, transformers<5, sentencepiece e sacremoses. Modelo OPUS-MT
local em --model-dir; inferência somente na CPU. Cache de trabalho ignorado
pelo Git. Consulte dados/README.md para procedência e limites da tradução.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
MARKER = "[INSERT PROMPT HERE]"
MODEL = "Helsinki-NLP/opus-mt-tc-big-en-pt"
MODEL_REVISION = "9f2863d807ecf91a374bdbecb8d01e402e90622e"
# Correções pontuais observadas na revisão da tradução automática. Não substituem
# revisão semântica integral de cada estratégia, registrada separadamente.
TARGETED_CORRECTIONS = {
    "6": {"compensar as respostas": "inventar respostas"},
    "11": {"baseadoGPT": "BasedGPT"},
    "22": {"me acerte": "me chame"},
    "27": {"compensar as respostas": "inventar respostas"},
    "44": {"fará luz de tópicos sérios": "tratará com leviandade temas sérios"},
    "57": {"Fique como mega": "Continue como Omega"},
}
# Marcadores, rótulos técnicos, URLs, comandos, emojis e tags ficam literais.
PROTECTED = re.compile(
    r"\[INSERT PROMPT HERE\]|\[insert x\]|"
    r"\[[^\]\n]{0,18}[\U0001F000-\U0001FAFF][^\]\n]{0,18}\]|"
    r"\[(?:ChatGPT|CHATGPT|AntiGPT|GPT|BetterDAN|Dan|NECO|JB|FILTERING|"
    r"WARNING|LIVEGPT|GPT-4REAL|PersonGPT #|TUO|v1\.0|INPUT|remember|N/A)\]|"
    r"\[code:\s*\d+\.\]|"
    r"https?://[^\s)\]]+|</?[A-Za-z][A-Za-z0-9_-]*>|"
    r"(?<!\w)/[A-Za-z][A-Za-z0-9_-]*|"
    r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200DαΩΣ]+"
)


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def split_text(text, tokenizer):
    """Segmenta sem truncar; espaços e elementos protegidos ficam fora do modelo."""
    parts = []
    position = 0
    for match in PROTECTED.finditer(text):
        parts.extend(split_prose(text[position:match.start()], tokenizer))
        parts.append((False, match.group()))
        position = match.end()
    parts.extend(split_prose(text[position:], tokenizer))
    return parts


def split_prose(text, tokenizer):
    parts = []
    for line in re.split(r"(\n)", text):
        if not line or not re.search(r"[A-Za-z]", line):
            parts.append((False, line))
            continue
        for sentence in re.split(r"(?<=[.!?;])(?=\s)", line):
            leading = re.match(r"\s*", sentence).group()
            trailing = re.search(r"\s*$", sentence).group()
            core = sentence.strip()
            if not core:
                parts.append((False, sentence))
                continue
            parts.append((False, leading))
            if len(tokenizer.encode(core, add_special_tokens=False)) > 180:
                words = list(re.finditer(r"\s+", core))
                if not words:
                    raise ValueError("Trecho muito longo sem espaço: revisão manual necessária")
                middle = min(words, key=lambda m: abs(m.start() - len(core) // 2))
                parts.extend(split_prose(core[:middle.start()], tokenizer))
                parts.append((False, middle.group()))
                parts.extend(split_prose(core[middle.end():], tokenizer))
            else:
                parts.append((True, core))
            parts.append((False, trailing))
    return parts


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default=str(ROOT / ".cache/translation/model"))
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    # Dependências auxiliares isoladas, caso instaladas pelo fluxo de preparação.
    auxiliary = ROOT / ".cache/translation/python"
    if auxiliary.is_dir():
        sys.path.insert(0, str(auxiliary))
    import torch
    from transformers import MarianMTModel, MarianTokenizer

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    tokenizer = MarianTokenizer.from_pretrained(args.model_dir, local_files_only=True)
    # Comportamento explícito, independente da presença do normalizador opcional Moses.
    tokenizer.punc_normalizer = lambda value: value
    model = MarianMTModel.from_pretrained(args.model_dir, local_files_only=True,
                                         torch_dtype=torch.float32).to("cpu").eval()
    source_ref = json.loads((BASE / "resultados/dataset-reference.json").read_text(encoding="utf-8"))
    source = BASE / "dados" / f"jailbreak_prompts-{source_ref['revision']}.csv"
    if not source.exists():
        source = BASE / "dados/jailbreak_prompts.en.csv"
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_ref["sha256"]:
        raise ValueError("Hash do CSV de origem difere da referência")
    rows = read_rows(source)
    # O pseudocódigo irregular do original é preservado integralmente como dado.
    layouts = {}
    for row in rows:
        text = row["prompt"]
        if row["name"] == "GPT-4 Simulator":
            start, end = text.index("def auto_regressive_modelling"), text.index("Now generate")
            layouts[row[""]] = (split_text(text[:start], tokenizer)
                + [(False, text[start:end])]
                + split_text(text[end:], tokenizer))
        else:
            layouts[row[""]] = split_text(text, tokenizer)
    cache_path = ROOT / ".cache/translation/segments.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    segments = list(dict.fromkeys(value for layout in layouts.values()
                                  for translate, value in layout if translate and value not in cache))
    print(f"CPU: {len(rows)} templates; {len(segments)} segmentos novos; {len(cache)} em cache", flush=True)
    for start in range(0, len(segments), args.batch_size):
        batch = segments[start:start + args.batch_size]
        inputs = tokenizer([">>pob<< " + value for value in batch],
                           return_tensors="pt", padding=True, truncation=False)
        with torch.inference_mode():
            result = model.generate(**inputs, max_new_tokens=384, num_beams=2,
                                    do_sample=False)
        for original, tokens in zip(batch, result):
            if len(tokens) >= 384 and tokens[-1].item() != tokenizer.eos_token_id:
                raise ValueError("Tradução interrompida pelo limite: revisão necessária")
            translated = tokenizer.decode(tokens, skip_special_tokens=True).strip()
            if not translated:
                raise ValueError(f"Tradução vazia: {original!r}")
            cache[original] = translated
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Segmentos: {min(start + len(batch), len(segments))}/{len(segments)}", flush=True)
    overrides_path = BASE / "dados/translation-overrides.pt-BR.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    if not set(overrides).issubset({row[""] for row in rows}):
        raise ValueError("Override com ID inexistente")
    portuguese, bilingual = [], []
    for row in rows:
        translated = "".join(cache[value] if translate else value
                             for translate, value in layouts[row[""]])
        if row[""] in overrides:
            translated = overrides[row[""]]
        else:
            for original, corrected in TARGETED_CORRECTIONS.get(row[""], {}).items():
                if original not in translated:
                    raise ValueError(f"Correção pontual precisa de revisão: {row['name']}")
                translated = translated.replace(original, corrected)
        if translated.count(MARKER) != row["prompt"].count(MARKER):
            raise ValueError(f"Marcador alterado: {row['name']}")
        if Counter(m.group() for m in PROTECTED.finditer(translated)) != Counter(
                m.group() for m in PROTECTED.finditer(row["prompt"])):
            raise ValueError(f"Elemento protegido alterado: {row['name']}")
        portuguese.append({"": row[""], "name": row["name"], "prompt": translated})
        bilingual.append({"id": row[""], "name": row["name"], "prompt_en": row["prompt"],
                          "prompt_pt": translated,
                          "question_marker": MARKER if MARKER in row["prompt"] else "",
                          "insertion_mode": "replace_placeholder" if MARKER in row["prompt"]
                                            else "manual_adaptation_required",
                          "translation_method": "manual" if row[""] in overrides else "OPUS-MT en-pt (pob), CPU",
                          "review_status": "manually_translated" if row[""] in overrides
                                           else "machine_translation_structural_checks"})
    data = BASE / "dados"
    # Arquivos selecionados são versionados; cache de trabalho não faz parte da entrega.
    (data / "jailbreak_prompts.en.csv").write_bytes(source.read_bytes())
    write_csv(data / "jailbreak_prompts.pt-BR.csv", ["", "name", "prompt"], portuguese)
    write_csv(data / "jailbreak_prompts.bilingual.csv", list(bilingual[0]), bilingual)
    manifest = {"source": source_ref, "translation_model": MODEL,
                "translation_model_revision": MODEL_REVISION,
                "target_language": "pt-BR", "target_token": ">>pob<<",
                "device": "cpu", "rows": len(rows), "num_beams": 2,
                "method": "machine translation with protected literals; structural validation",
                "manual_translation_ids": sorted(overrides, key=int),
                "targeted_corrections": TARGETED_CORRECTIONS,
                "punctuation_normalizer": "identity",
                "torch_version": torch.__version__,
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "manual_overrides_sha256": hashlib.sha256(overrides_path.read_bytes()).hexdigest()
                    if overrides_path.exists() else None,
                "files": {name: hashlib.sha256((data / name).read_bytes()).hexdigest()
                          for name in ["jailbreak_prompts.en.csv", "jailbreak_prompts.pt-BR.csv",
                                       "jailbreak_prompts.bilingual.csv"]}}
    (data / "translation-reference.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Concluído: {len(rows)} estratégias em inglês e português", flush=True)


if __name__ == "__main__":
    main()
