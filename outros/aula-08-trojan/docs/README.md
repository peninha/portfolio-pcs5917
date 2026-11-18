# Aula 8 — ponto de retomada

Documentação consolidada em **11/11/2026** para continuar o trabalho sem acesso às conversas anteriores. Os caminhos desta documentação são relativos a esta pasta, para funcionar em outro computador.

## Estado atual em um minuto

| Frente | Material | Resultado conhecido |
| --- | --- | --- |
| Nossa detecção do AES do grupo E, primeiro lote | IDs A01–A20 | **20/20 acertos, 100%**, confirmado pelo grupo E e comunicado pelo usuário. |
| Detecção do nosso PicoRV32 pelo outro grupo | IDs S01–S20 | **15/20 acertos, 75%**: dez inócuos e cinco trojans corretamente identificados. Cinco trojans foram classificados como inócuos. |
| Segundo lote AES, opção Gemini | IDs 1–20, arquivos locais G01–G20 | Classificação proposta: 1–10 inócuos, 11–20 trojans. **Não há confirmação registrada do gabarito deste lote.** |

**Relatório final de 17/11/2026.** A versão em duas páginas incorpora a classificação recebida do PicoRV32. O gráfico está incluído na própria fonte LaTeX. [Abrir o PDF](../../../output/pdf/relatorio-aula08.pdf) · [Editar a fonte](../relatorio/relatorio-aula08.tex)

## Por onde continuar

1. [RETOMADA.md](RETOMADA.md) preserva as preferências da atividade e o roteiro histórico da versão preliminar.
2. Consulte [RESULTADOS.md](RESULTADOS.md): métricas, matriz de confusão, erros e interpretação das duas frentes confirmadas.
3. Consulte [PROCESSO.md](PROCESSO.md): histórico de geração, anonimização, análise e decisões do relatório.
4. Use [ARQUIVOS.md](ARQUIVOS.md) para localizar entradas, códigos, relatório e ferramentas.
5. Para conferir a contagem, execute `python outros/aula-08-trojan/docs/conferir_resultados.py` na raiz do repositório. O script usa apenas a biblioteca padrão e imprime o resultado, sem alterar os arquivos.

## Gabarito e evidências preservados

- [mapeamento_picorv32.csv](mapeamento_picorv32.csv): cópia do mapeamento interno, antes existente apenas no repositório local separado `picorv32`.
- [catalogo_picorv32.md](catalogo_picorv32.md): catálogo interno original das variantes, preservado como referência histórica. Seus links B/T eram relativos ao repositório de origem; neste repositório, use o mapeamento para localizar os arquivos em `../entrega/Sxx/picorv32.v`.
- [comparacao_picorv32.csv](comparacao_picorv32.csv): gabarito, resposta do outro grupo e acerto por ID.
- [../classificacao-preenchida.csv](../classificacao-preenchida.csv): resposta recebida, incluindo código-fonte. Não confundir com o CSV vazio do pacote enviado.
- [../entrega/](../entrega/): **cópia dos nossos códigos efetivamente enviados ao outro grupo**, adicionada pelo usuário. Inclui referência original, S01–S20, README e CSV vazio.

Esta documentação e o catálogo interno contêm o gabarito. Eles não faziam parte do pacote cego enviado ao outro grupo.

## Preservação em outro computador

Para editar a versão final, abra `outros/aula-08-trojan/relatorio/relatorio-aula08.tex` e compile com pdfLaTeX. O PDF publicado no repositório fica em `output/pdf/relatorio-aula08.pdf`.
