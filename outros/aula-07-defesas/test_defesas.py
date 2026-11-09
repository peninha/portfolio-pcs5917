"""Testes offline do contrato público; executar com unittest discover."""

from itertools import product
import unittest

from defesas import SYSTEM_PROMPT_QWEN, aplicar_defesa


DEFESAS = ("nenhuma", "self_reminder", "intention_analysis", "ambos")
IDIOMAS = ("pt", "en")
POSICOES = ("inicio", "fim", "ambos")
PROMPT = "  Explique a fotossíntese.\r\nPreserve {INPUT}, [INPUT] e café.\n\t"
MARCADORES = {
    "pt": ("Identifique a intenção", "Você deve ser", "Lembre-se:"),
    "en": ("Please identify", "You should be", "Remember,"),
}


class TestDefesas(unittest.TestCase):
    def test_matriz_texto_24_combinacoes(self):
        for defesa, idioma, posicao in product(DEFESAS, IDIOMAS, POSICOES):
            with self.subTest(defesa=defesa, idioma=idioma, posicao=posicao):
                texto = aplicar_defesa(PROMPT, defesa, idioma, posicao, formato="texto")
                ia, sr_inicio, sr_fim = MARCADORES[idioma]
                tem_ia = defesa in ("intention_analysis", "ambos")
                tem_sr = defesa in ("self_reminder", "ambos")
                self.assertEqual(texto.count(PROMPT), 1)
                self.assertEqual(ia in texto, tem_ia)
                self.assertEqual(sr_inicio in texto, tem_sr and posicao != "fim")
                self.assertEqual(sr_fim in texto, tem_sr and posicao != "inicio")
                if tem_ia:
                    self.assertTrue(texto.startswith(ia))
                if tem_sr and posicao != "fim":
                    self.assertLess(texto.index(sr_inicio), texto.index(PROMPT))
                if tem_sr and posicao != "inicio":
                    self.assertGreater(texto.index(sr_fim), texto.index(PROMPT))
                if defesa == "nenhuma":
                    self.assertEqual(texto, PROMPT)

    def test_matriz_mensagens_24_combinacoes(self):
        for defesa, idioma, posicao in product(DEFESAS, IDIOMAS, POSICOES):
            with self.subTest(defesa=defesa, idioma=idioma, posicao=posicao):
                msgs = aplicar_defesa(PROMPT, defesa, idioma, posicao, formato="mensagens")
                sufixo = defesa in ("self_reminder", "ambos") and posicao != "inicio"
                self.assertEqual([m["role"] for m in msgs],
                                 ["system", "user"] + (["system"] if sufixo else []))
                self.assertEqual(msgs[1]["content"], PROMPT)
                self.assertTrue(msgs[0]["content"].startswith(SYSTEM_PROMPT_QWEN))
                self.assertNotIn(PROMPT, msgs[0]["content"])
                # Retirar somente o system comum recupera a mesma composição textual.
                prefixo = msgs[0]["content"][len(SYSTEM_PROMPT_QWEN):].removeprefix("\n\n")
                partes = ([prefixo] if prefixo else []) + [msgs[1]["content"]]
                partes += [m["content"] for m in msgs[2:]]
                self.assertEqual("\n\n".join(partes),
                                 aplicar_defesa(PROMPT, defesa, idioma, posicao, formato="texto"))

    def test_ia_e_baseline_independem_da_posicao(self):
        for formato, defesa, idioma in product(
            ("texto", "mensagens"), ("nenhuma", "intention_analysis"), IDIOMAS
        ):
            resultados = [aplicar_defesa(PROMPT, defesa, idioma, p, formato=formato)
                          for p in POSICOES]
            self.assertEqual(resultados[0], resultados[1])
            self.assertEqual(resultados[1], resultados[2])

    def test_baseline_preserva_texto_inclusive_vazio(self):
        for texto in ("", " \r\n\t", PROMPT, "<|im_start|>user\ntexto<|im_end|>"):
            self.assertEqual(aplicar_defesa(texto, formato="texto"), texto)
            self.assertEqual(aplicar_defesa(texto), [
                {"role": "system", "content": SYSTEM_PROMPT_QWEN},
                {"role": "user", "content": texto},
            ])

    def test_system_personalizado_preservado_em_todas_condicoes(self):
        for defesa in DEFESAS:
            msgs = aplicar_defesa(PROMPT, defesa, system_prompt="  Instrução comum.\n")
            self.assertTrue(msgs[0]["content"].startswith("  Instrução comum.\n"))
        self.assertEqual(aplicar_defesa(PROMPT, system_prompt="")[0]["content"], "")

    def test_formato_padrao_e_mensagens(self):
        self.assertEqual(aplicar_defesa(PROMPT, "ambos"),
                         aplicar_defesa(PROMPT, "ambos", formato="mensagens"))

    def test_texto_nao_inclui_system_prompt(self):
        for defesa in DEFESAS:
            self.assertEqual(
                aplicar_defesa(PROMPT, defesa, formato="texto", system_prompt="PERSONALIZADO"),
                aplicar_defesa(PROMPT, defesa, formato="texto"),
            )

    def test_resultados_nao_compartilham_estado(self):
        msgs = aplicar_defesa(PROMPT, "ambos")
        msgs[0]["content"] = "alterado"
        msgs.append({"role": "assistant", "content": "histórico"})
        novos = aplicar_defesa(PROMPT, "ambos")
        self.assertEqual(len(novos), 3)
        self.assertNotEqual(novos[0]["content"], "alterado")

    def test_opcoes_invalidas_rejeitadas(self):
        for formato, parametro, valor in product(
            ("texto", "mensagens"), ("defesa", "idioma", "posicao", "formato"),
            ("invalido", "", None, [], 42)
        ):
            with self.subTest(formato=formato, parametro=parametro, valor=valor):
                opcoes = {"formato": formato, parametro: valor}
                with self.assertRaises(ValueError):
                    aplicar_defesa(PROMPT, **opcoes)

    def test_tipos_invalidos_rejeitados(self):
        for formato in ("texto", "mensagens"):
            for valor in (None, 42, [], {}):
                with self.assertRaises(TypeError):
                    aplicar_defesa(valor, formato=formato)
            with self.assertRaises(TypeError):
                aplicar_defesa(PROMPT, formato=formato, system_prompt=None)


if __name__ == "__main__":
    unittest.main()
