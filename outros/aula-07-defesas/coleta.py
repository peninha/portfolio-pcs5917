"""Coleta pareada do Grupo A. Consulte PROTOCOLO.md ou execute --help."""
import argparse
import csv
import hashlib
import json
import os
import platform
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import defesas
from defesas import MODELO_ALVO, aplicar_defesa

VERSAO = "3.1.0"
REVISAO = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
GERACAO = dict(do_sample=False, num_beams=1, max_new_tokens=2048,
               temperature=None, top_p=None, top_k=None)
SEED = 42
# Os valores neutros "na" são metadados, não argumentos da API de defesas.
MATRIZ = {"B": ("nenhuma", "na", "na")}
for sigla, defesa, posicao in [
    ("SR", "self_reminder", "ambos"),
    ("IA", "intention_analysis", "inicio"),
    ("SRIA", "ambos", "ambos"),
]:
    for idioma in ("en", "pt"):
        MATRIZ[f"{sigla}_{idioma.upper()}"] = (defesa, idioma, posicao)

def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def digest(obj):
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True))

def ler(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def gravar(p, obj):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=p.parent, delete=False) as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(f.name, p)

def exigir(ok, msg):
    if not ok:
        raise ValueError(msg)

def ler_casos(p):
    casos = {}
    vistos = set()
    for c in ler(p):
        campos = ("id_caso", "autor", "tipo", "tecnica", "idioma_ataque", "objetivo", "prompt_original")
        exigir(all(isinstance(c.get(k), str) and c[k].strip() for k in campos),
               "Preencha todos os campos de cada caso.")
        i = c["id_caso"]
        exigir(c["autor"] in ("arthur", "caio", "roberto") and
               re.fullmatch(re.escape(c["autor"]) + r"-[0-9]{3,}", i), f"ID/autor inválido: {i}")
        exigir(c["tipo"] in ("manual", "automatico") and c["idioma_ataque"] in ("pt", "en"),
               f"Tipo ou idioma inválido: {i}")
        exigir(i not in casos and c["prompt_original"] not in vistos, f"ID ou prompt repetido: {i}")
        vistos.add(c["prompt_original"])
        casos[i] = c
    exigir(casos and len({c["autor"] for c in casos.values()}) == 1, "Use uma lista por integrante.")
    return casos

def selecionar(p, casos):
    sel = ler(p)
    exigir(isinstance(sel, dict) and Counter(sel.values()) == {"sucesso": 10, "falha": 5},
           "A seleção precisa conter 10 sucessos e 5 falhas.")
    exigir(set(sel) <= casos.keys(), "ID da seleção ausente em casos.json.")
    return sel

def entrada(c, cond):
    defesa, idioma, posicao = MATRIZ[cond]
    return aplicar_defesa(c["prompt_original"], defesa=defesa,
                          idioma="en" if idioma == "na" else idioma,
                          posicao="ambos" if posicao == "na" else posicao,
                          formato="mensagens")

def carregar():
    import torch
    import transformers as hf
    exigir(hf.__version__ == "4.57.6", "Instale transformers==4.57.6 para esta coleta.")
    tok = hf.AutoTokenizer.from_pretrained(MODELO_ALVO, revision=REVISAO)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = hf.AutoModelForCausalLM.from_pretrained(
        MODELO_ALVO, revision=REVISAO, dtype=torch.float16, attn_implementation="eager"
    ).to(device).eval()
    meta = {
        "protocolo": VERSAO, "versao_defesas": defesas.VERSAO_PROTOCOLO,
        "modelo": MODELO_ALVO, "revisao_modelo": REVISAO, "revisao_tokenizer": REVISAO,
        "classe_tokenizer": type(tok).__name__, "chat_template": tok.chat_template,
        "system_prompt": defesas.SYSTEM_PROMPT_QWEN,
        "sha_defesas": hashlib.sha256(Path(defesas.__file__).read_bytes()).hexdigest(),
        "sha_coletor": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geracao": GERACAO, "config_base": model.generation_config.to_dict(), "seed": SEED,
        "dtype": str(model.dtype), "quantizacao": "nenhuma", "atencao": "eager",
        "limite_contexto": model.config.max_position_embeddings,
        "python": platform.python_version(), "so": platform.platform(), "torch": torch.__version__,
        "transformers": hf.__version__, "cuda": torch.version.cuda, "device": device,
        "hardware": torch.cuda.get_device_name() if device == "cuda" else platform.processor(),
    }
    return model, tok, meta

def inferir(model, tok, msgs):
    import torch
    from transformers import set_seed
    set_seed(SEED)
    texto = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(texto, add_special_tokens=False, return_tensors="pt").to(model.device)
    n = inputs["input_ids"].shape[1]
    exigir(n + GERACAO["max_new_tokens"] <= model.config.max_position_embeddings,
           "Entrada e orçamento excedem o contexto.")
    with torch.inference_mode():
        novos = model.generate(**inputs, **GERACAO)[0, n:].tolist()
    eos = model.generation_config.eos_token_id
    eos = eos if isinstance(eos, list) else [eos]
    fim = "eos" if novos and novos[-1] in eos else "limite" if len(novos) == GERACAO["max_new_tokens"] else "outro"
    return dict(prompt_serializado=texto, resposta=tok.decode(novos, skip_special_tokens=True),
                tokens_entrada=n, tokens_gerados=len(novos), motivo_fim=fim)

def conferir(r, c, k, meta):
    exigir(r["caso"] == c and r["condicao"] == k and r["manifesto_sha256"] == digest(meta)
           and r["mensagens"] == entrada(c, k), f"Registro incompatível: {c['id_caso']} {k}")
    exigir(r["integridade"] == digest({a:b for a,b in r.items() if a != "integridade"}),
           f"Conteúdo alterado: {c['id_caso']} {k}")

def registro(pasta, c, k):
    return pasta / (c["id_caso"] + "_" + k + ".json")

def executar(pasta, casos, sel, piloto=False):
    pasta.mkdir(parents=True, exist_ok=True)
    model, tok, meta = carregar()
    meta["finalidade"] = "piloto" if piloto else "coleta"
    mp = pasta / "manifesto.json"
    if mp.exists():
        exigir(ler(mp) == meta, "Ambiente ou configuração divergente do manifesto.")
    else:
        gravar(mp, meta)
    if sel is not None:
        for i in sel:
            p = registro(pasta, casos[i], "B")
            exigir(p.is_file(), f"Baseline ausente: {i}. Execute triagem.")
            r = ler(p)
            conferir(r, casos[i], "B", meta)
            exigir(r["resposta"].strip(), f"Baseline vazio: {i}")
        sp = pasta / "selecao_congelada.json"
        if sp.exists():
            exigir(ler(sp) == sel, "Seleção divergente da congelada.")
        else:
            gravar(sp, sel)
    for i in (casos if sel is None else sel):
        c = casos[i]
        for k in (["B"] if sel is None and not piloto else MATRIZ):
            p = registro(pasta, c, k)
            if p.exists():
                conferir(ler(p), c, k, meta)
                continue
            msgs = entrada(c, k)
            try:
                saida = inferir(model, tok, msgs)
            except Exception as err:
                with (pasta / "erros.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(dict(id_caso=i, condicao=k, erro=repr(err),
                                            utc=datetime.now(timezone.utc).isoformat())) + "\n")
                raise
            r = dict(caso=c, condicao=k, manifesto_sha256=digest(meta), mensagens=msgs,
                     utc=datetime.now(timezone.utc).isoformat(), **saida)
            r["integridade"] = digest(r)
            gravar(p, r)
            print(i, k, r["motivo_fim"], flush=True)
    if sel is None and not piloto:
        triagem = []
        for i, c in casos.items():
            r = ler(registro(pasta, c, "B"))
            triagem.append(dict(id_caso=i, tecnica=c["tecnica"], objetivo=c["objetivo"],
                                prompt_original=c["prompt_original"], resposta=r["resposta"],
                                motivo_fim=r["motivo_fim"]))
        tabela(pasta / "triagem.csv", triagem)

def tabela(p, linhas):
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=p.parent, delete=False) as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    os.replace(f.name, p)

def exportar(pasta, casos, sel):
    meta = ler(pasta / "manifesto.json")
    exigir(meta["protocolo"] == VERSAO and meta["finalidade"] == "coleta"
           and ler(pasta / "selecao_congelada.json") == sel,
           "Protocolo ou seleção incompatível.")
    linhas, juiz = [], []
    for i in sorted(sel):
        c = casos[i]
        for k, (defesa, idioma, posicao) in MATRIZ.items():
            r = ler(registro(pasta, c, k))
            conferir(r, c, k, meta)
            chave = sha(f"{VERSAO}|{i}|{k}")[:24]
            linha = dict(id_resposta=chave, **{campo:c[campo] for campo in
                         ("id_caso","autor","tipo","tecnica","idioma_ataque","objetivo","prompt_original")},
                         rotulo_triagem=sel[i], condicao=k, defesa=defesa, idioma_defesa=idioma,
                         posicao=posicao, sha_prompt=sha(c["prompt_original"]),
                         mensagens_json=json.dumps(r["mensagens"], ensure_ascii=False),
                         manifesto_sha256=r["manifesto_sha256"])
            linha.update({campo:r[campo] for campo in ("utc","prompt_serializado","resposta",
                                                       "tokens_entrada","tokens_gerados","motivo_fim")})
            linhas.append(linha)
            juiz.append({campo:linha[campo] for campo in ("id_resposta","objetivo","resposta")})
    tabela(pasta / "respostas.csv", linhas)
    tabela(pasta / "para_jev.csv", sorted(juiz, key=lambda x:x["id_resposta"]))
    print(f"{len(linhas)} registros validados e exportados em {pasta}.")

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("etapa", choices=("planejar", "piloto", "triagem", "coletar", "exportar"))
    a.add_argument("--casos", type=Path, default=Path("casos.json"))
    a.add_argument("--selecao", type=Path, default=Path("selecao.json"))
    a.add_argument("--saida", type=Path, default=Path("coleta"))
    args = a.parse_args()
    casos = ler_casos(args.casos)
    if args.etapa == "planejar":
        for k, config in MATRIZ.items():
            print(k, *config)
        print(f"{len(casos)} candidatos; coleta final por integrante: 15 casos x 7 = 105.")
        return
    sel = selecionar(args.selecao, casos) if args.etapa in ("coletar", "exportar") else None
    if args.etapa == "exportar":
        exportar(args.saida, casos, sel)
    else:
        executar(args.saida, casos, sel, piloto=args.etapa == "piloto")

if __name__ == "__main__":
    main()

