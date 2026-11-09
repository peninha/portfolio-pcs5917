"""Mostra oito configurações em PT ou EN, sem instalar bibliotecas.

Execute: python exemplo_uso.py --idioma pt
Cada saída é a lista a ser passada ao chat template do Qwen.
"""

import argparse
import json

from defesas import VERSAO_PROTOCOLO, aplicar_defesa


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idioma", choices=("pt", "en"), default="pt")
    parser.add_argument("--prompt", default="Quanto é 2 + 2?")
    args = parser.parse_args()
    configuracoes = [
        ("nenhuma", "ambos"),
        ("self_reminder", "inicio"),
        ("self_reminder", "fim"),
        ("self_reminder", "ambos"),
        ("intention_analysis", "inicio"),
        ("ambos", "inicio"),
        ("ambos", "fim"),
        ("ambos", "ambos"),
    ]
    for defesa, posicao in configuracoes:
        registro = {
            "versao_protocolo": VERSAO_PROTOCOLO,
            "defesa": defesa,
            "idioma_defesa": args.idioma,
            "posicao": posicao,
            "mensagens": aplicar_defesa(
                args.prompt, defesa, args.idioma, posicao, formato="mensagens"
            ),
        }
        print(json.dumps(registro, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
