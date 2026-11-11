"""Tentativas exploratórias e promoção de prompts ao protocolo da aula 7."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import coleta as co


def testar(model, tokenizer, manifesto, pasta, prompt, objetivo, tecnica,
           idioma="pt", condicao="B", observacoes=""):
    """Salva uma nova tentativa e devolve seu caminho, preservando o texto original."""
    co.exigir(all(isinstance(t, str) and t.strip() for t in (prompt, objetivo, tecnica)),
              "Preencha prompt, objetivo e técnica.")
    co.exigir(idioma in ("pt", "en") and condicao in co.MATRIZ, "Idioma ou condição inválida.")
    mensagens = co.entrada({"prompt_original": prompt}, condicao)
    saida = co.inferir(model, tokenizer, mensagens)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc)
    registro = dict(prompt_original=prompt, objetivo=objetivo, tecnica=tecnica,
                    idioma_ataque=idioma, condicao=condicao, observacoes=observacoes,
                    manifesto=manifesto, utc=agora.isoformat(), mensagens=mensagens, **saida)
    registro["integridade"] = co.digest(registro)
    destino = pasta / f"teste-{agora:%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}.json"
    co.gravar(destino, registro)
    return destino


def promover(tentativa, arquivo_casos, autor):
    """Acrescenta o prompt escolhido aos candidatos com ID automático.

    Repetir a promoção do mesmo prompt devolve o caso já existente.
    Os baselines da coleta formal são produzidos pelo coletor.
    """
    tentativa, arquivo_casos = Path(tentativa), Path(arquivo_casos)
    r = co.ler(tentativa)
    co.exigir(r["integridade"] == co.digest({k:v for k,v in r.items() if k != "integridade"}),
              "Tentativa alterada desde a execução.")
    casos = co.ler(arquivo_casos) if arquivo_casos.exists() else []
    co.exigir(autor in ("arthur", "caio", "roberto") and all(c["autor"] == autor for c in casos),
              "Confira o autor da lista de candidatos.")
    for caso in casos:
        if caso["prompt_original"] == r["prompt_original"]:
            return caso
    numero = max((int(c["id_caso"].rsplit("-",1)[1]) for c in casos), default=0) + 1
    caso = {k:r[k] for k in ("prompt_original", "objetivo", "tecnica", "idioma_ataque")}
    caso.update(id_caso=f"{autor}-{numero:03d}", autor=autor, tipo="manual",
                origem_arquivo="rascunhos/" + tentativa.name,
                origem_sha256=r["integridade"])
    casos.append(caso)
    arquivo_casos.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=arquivo_casos.parent) as tmp:
        p = Path(tmp) / "casos.json"
        co.gravar(p, casos)
        co.ler_casos(p)
    # Conserve a procedência também ao promover um rascunho de outra sessão.
    origem = arquivo_casos.parent / caso["origem_arquivo"]
    origem.parent.mkdir(parents=True, exist_ok=True)
    if origem.exists():
        co.exigir(co.ler(origem) == r, "Já existe outro rascunho com esse nome.")
    else:
        co.gravar(origem, r)
    co.gravar(arquivo_casos, casos)
    return caso
