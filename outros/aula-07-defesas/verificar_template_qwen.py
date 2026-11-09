"""Valida a renderização com Transformers e o chat_template oficial, sem pesos.

Uso: python verificar_template_qwen.py caminho/para/tokenizer_config.json
O arquivo deve ser baixado do repositório oficial do modelo; veja README.md.
Não tokeniza em IDs e não executa inferência.
"""

import argparse
import hashlib
from itertools import product
import json
from pathlib import Path

from transformers import PreTrainedTokenizerBase

from defesas import aplicar_defesa


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    conteudo = args.config.read_bytes()
    config = json.loads(conteudo)
    # Usa o renderizador real de apply_chat_template; vocabulário não é necessário
    # para tokenize=False. Nenhum template alternativo é usado como fallback.
    tokenizer = PreTrainedTokenizerBase(chat_template=config["chat_template"])
    total = 0
    for defesa, idioma, posicao in product(
        ("nenhuma", "self_reminder", "intention_analysis", "ambos"),
        ("pt", "en"), ("inicio", "fim", "ambos")
    ):
        mensagens = aplicar_defesa(
            "Explique a fotossíntese.\n", defesa, idioma, posicao, formato="mensagens"
        )
        texto = tokenizer.apply_chat_template(
            mensagens, tokenize=False, add_generation_prompt=True
        )
        esperado = "".join(
            f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
            for m in mensagens
        ) + "<|im_start|>assistant\n"
        if texto != esperado:
            raise AssertionError(f"Serialização inesperada: {defesa}, {idioma}, {posicao}")
        total += 1
    print(f"OK: {total} combinações renderizadas pelo template oficial via Transformers.")
    print(f"SHA256 tokenizer_config.json: {hashlib.sha256(conteudo).hexdigest()}")


if __name__ == "__main__":
    main()
