"""Executa quatro condições no mesmo Qwen e salva entradas e respostas em JSON.

Uso: python exemplo_inferencia.py --prompt "Quanto é 2 + 2?" --idioma pt
Dependências e integração no Colab estão em GUIA_INTEGRACAO.md.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from defesas import MODELO_ALVO, VERSAO_PROTOCOLO, aplicar_defesa


def executar_exemplo(model, tokenizer, prompt, idioma="pt", seed=42, max_new_tokens=2048):
    """Reutiliza modelo/tokenizer já carregados, em quatro conversas independentes.

    Retorna entradas, respostas e configuração. Os parâmetros de geração são
    sugestões iniciais do exemplo a alinhar pelo grupo antes da coleta.
    """
    import torch
    import transformers

    model.eval()
    condicoes = [
        ("nenhuma", "ambos"),
        ("self_reminder", "ambos"),
        ("intention_analysis", "inicio"),
        ("ambos", "ambos"),
    ]
    parametros = {
        "do_sample": False,
        "num_beams": 1,
        "max_new_tokens": max_new_tokens,
        "temperature": None,
        "top_p": None,
        "top_k": None,
    }
    registros = []
    for defesa, posicao in condicoes:
        transformers.set_seed(seed)
        mensagens = aplicar_defesa(
            prompt, defesa, idioma, posicao, formato="mensagens"
        )
        texto = tokenizer.apply_chat_template(
            mensagens, tokenize=False, add_generation_prompt=True
        )
        entradas = tokenizer(texto, add_special_tokens=False, return_tensors="pt")
        entradas = entradas.to(model.device)
        tokens_entrada = entradas["input_ids"].shape[-1]
        limite_contexto = model.config.max_position_embeddings
        if tokens_entrada + max_new_tokens > limite_contexto:
            raise ValueError(
                f"Contexto insuficiente para {defesa}: entrada de {tokens_entrada} "
                f"tokens + reserva de {max_new_tokens} > {limite_contexto}."
            )
        with torch.inference_mode():
            saida = model.generate(**entradas, **parametros)
        novos_tokens = saida[0, tokens_entrada:]
        registros.append({
            "defesa": defesa,
            "idioma_defesa": idioma,
            "posicao": posicao,
            "posicao_efetiva": (
                "na" if defesa == "nenhuma" else
                "inicio" if defesa == "intention_analysis" else posicao
            ),
            "prompt_original": prompt,
            "mensagens": mensagens,
            "prompt_serializado": texto,
            "resposta": tokenizer.decode(novos_tokens, skip_special_tokens=True),
            "tokens_entrada": tokens_entrada,
            "tokens_gerados": len(novos_tokens),
            "atingiu_limite_geracao": len(novos_tokens) >= max_new_tokens,
        })
    return {
        "versao_protocolo": VERSAO_PROTOCOLO,
        "sha256_defesas_py": hashlib.sha256(
            Path(__file__).with_name("defesas.py").read_bytes()
        ).hexdigest(),
        "modelo": MODELO_ALVO,
        "revisao_modelo": getattr(model.config, "_commit_hash", None),
        "transformers": transformers.__version__,
        "torch": torch.__version__,
        "dtype_modelo": str(model.dtype),
        "classe_tokenizer": type(tokenizer).__name__,
        "chat_template": tokenizer.chat_template,
        "generation_config_modelo": model.generation_config.to_dict(),
        "parametros_geracao_exemplo": parametros,
        "seed": seed,
        "data_utc": datetime.now(timezone.utc).isoformat(),
        "registros": registros,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", default="Quanto é 2 + 2?")
    parser.add_argument("--idioma", choices=("pt", "en"), default="pt")
    parser.add_argument("--saida", type=Path, default=Path("exemplo-resultados.json"))
    parser.add_argument("--revision", default="main", help="Revisão HF comum ao modelo e tokenizer.")
    args = parser.parse_args()
    if args.saida.exists():
        parser.error("O arquivo de saída já existe. Escolha outro nome com --saida.")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODELO_ALVO, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(
        MODELO_ALVO, revision=args.revision, torch_dtype="auto", device_map="auto"
    )
    resultados = executar_exemplo(model, tokenizer, args.prompt, args.idioma)
    args.saida.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Quatro condições salvas em {args.saida.resolve()}")


if __name__ == "__main__":
    main()
