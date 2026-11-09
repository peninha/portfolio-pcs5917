"""Ciclo de entrega sintético de três integrantes, independente de GPU ou rede."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import coleta as co
from consolidar import consolidar, linhas

class TestColeta(unittest.TestCase):
    def test_entrega_e_julgamento_pareado(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pastas = []
            for autor in ("arthur", "caio", "roberto"):
                pasta = raiz / autor
                pastas.append(pasta)
                casos = [dict(id_caso=f"{autor}-{n:03d}", autor=autor, tipo="manual",
                              tecnica="controle", idioma_ataque="pt", objetivo="Repetir um número",
                              prompt_original=f"Repita {n}.\n") for n in range(16)]
                arq = raiz / "casos.json"
                co.gravar(arq, casos)
                casos = co.ler_casos(arq)
                sel = {i:("sucesso" if j < 10 else "falha") for j,i in enumerate(list(casos)[:15])}
                co.gravar(raiz / "selecao.json", sel)
                co.selecionar(raiz / "selecao.json", casos)
                meta = dict.fromkeys(("modelo revisao_modelo revisao_tokenizer chat_template system_prompt "
                                      "sha_defesas sha_coletor geracao config_base seed dtype quantizacao "
                                      "atencao transformers").split(), "simulado")
                meta["protocolo"] = co.VERSAO
                saida = dict(prompt_serializado="controle",resposta='Resposta, com "aspas"\ne linha.',
                             tokens_entrada=7,tokens_gerados=4,motivo_fim="eos")
                with patch.object(co,"carregar", return_value=(None,None,meta)), \
                     patch.object(co,"inferir",return_value=saida) as inferir:
                    co.executar(pasta, casos, None)
                    co.executar(pasta, casos, sel)
                    co.executar(pasta, casos, sel)
                    self.assertEqual(inferir.call_count, 16 + 90)
                co.exportar(pasta, casos, sel)
                self.assertEqual(len(linhas(pasta/"respostas.csv")),105)
                self.assertEqual(len(linhas(pasta/"triagem.csv")),16)
            grupo = raiz / "grupo"
            consolidar(pastas, grupo)
            dados = linhas(grupo / "respostas_grupo.csv")
            self.assertEqual(len(dados),315)
            notas = [dict(id_resposta=r["id_resposta"], rotulo_jev=(
                "inconclusivo" if r["condicao"] == "IA_PT" else
                "sucesso" if r["condicao"] == "B" else "falha"
            )) for r in reversed(dados)]
            co.tabela(raiz/"juiz.csv",notas)
            consolidar(pastas, grupo, raiz/"juiz.csv")
            resumo = {r["condicao"]:r for r in linhas(grupo/"resumo_asr.csv") if r["tipo"] == "todos"}
            self.assertEqual(resumo["SR_EN"]["sucesso_para_falha"], "45")
            self.assertEqual(resumo["B"]["asr_pct"],"100.0")
            self.assertEqual(resumo["IA_PT"]["asr_pct"],"")
            co.tabela(raiz/"juiz.csv",notas[:-1])
            with self.assertRaises(ValueError):
                consolidar(pastas, grupo, raiz/"juiz.csv")
            p = co.registro(pasta, casos[next(iter(sel))], "B")
            alterado = co.ler(p)
            alterado["resposta"] = "alterada"
            co.gravar(p, alterado)
            with self.assertRaises(ValueError):
                co.exportar(pasta, casos, sel)

if __name__ == "__main__":
    unittest.main()

