# Resultados consolidados

## 1. Nossa classificação do AES do grupo E — primeiro lote

Entrada: [planilha original](../planilha_anonimizada_grupo_e.csv), campos `id_anonimo`, `arquivo_codificado`, `codigo_fonte`. Contrato: [regra de negócio](../regra_negocio_grupo_e.txt). Saída: [avaliação enviada](../avaliacao_grupo_e.csv).

O usuário informou em 11/11/2026 que o grupo E confirmou **todos os resultados corretos**. A fonte dessa confirmação é o retorno comunicado na conversa; não há um CSV separado de gabarito do grupo E identificado para este primeiro lote.

- Acurácia: **20/20 = 100%**.
- Trojans: **10/10**; inócuos: **10/10**.
- Positivo = Trojan: VP=10, VN=10, FP=0, FN=0.
- Precisão, revocação e F1 Trojan: 100%.

| ID Trojan | Condição e efeito identificados na análise estática |
| --- | --- |
| A01 | A cada 256 chamadas válidas, XOR 0x01 no byte 0 da saída. |
| A03 | Chave de 16 bytes com extremos zero: últimos quatro bytes da saída recebem os primeiros quatro da chave. |
| A06 | Plaintext simétrico por espelhamento de posições e reversão de bits: XOR 0x80 no byte 7. |
| A07 | Rodada 5, após ShiftRows, state[0][0]=0: pula MixColumns. |
| A08 | Plaintext com extremos zero e chave de 16 bytes: XOR do primeiro byte da chave no byte 0 da saída. Efeito mascarado se esse byte da chave for zero. |
| A10 | Milésima chamada válida: XOR 0x01 no byte 15. |
| A11 | Plaintext e chave de 16 bytes terminam em FF: exceção para bloco válido. |
| A12 | Plaintext começa com DE AD: XOR 0x01 no byte 0. |
| A14 | Chave com no máximo quatro bits 1: saída zerada. |
| A16 | Terceira repetição consecutiva do mesmo plaintext: XOR FF no byte 0; compara só plaintext, não chave; não dispara automaticamente na quarta repetição. |

A01, A10 e A16 usam variáveis `static` compartilhadas entre instâncias e violam independência entre chamadas (R2). A03 expõe chave no retorno. A07 afeta a sequência AES (R5). Não atribuir automaticamente R6 ao efeito dentro do gatilho: R6 exige igualdade **fora** dos gatilhos.

| ID Inocuo | Mudança |
| --- | --- |
| A02 | Wrapper gf_multiply que retorna a mesma operação a*b. |
| A04 | const em cópias locais e comentários. |
| A05 | Tupla e decomposição estruturada dos mesmos quatro operandos. |
| A09 | Exceção para variante AES desconhecida; três variantes válidas mantidas. |
| A13 | Documentação em comentários. |
| A15 | Constantes nomeadas com os mesmos valores dos literais. |
| A17 | Assertions de invariantes. Ressalva: assert de tamanho antecede exceção exigida por R3 para entrada inválida. Rótulo Inocuo confirmado no desafio. |
| A18 | Indentação. |
| A19 | Renomeação de variáveis locais. |
| A20 | vector de quatro coeficientes substituído por array, com valores e rotação preservados. |

## 2. Classificação do nosso PicoRV32 pelo outro grupo

Resposta recebida: [classificacao-preenchida.csv](../classificacao-preenchida.csv), campos `id`, `classificacao`, `code`. É um CSV com células multilinha contendo código; usar um parser CSV, não separar por linhas físicas. O gabarito está em [mapeamento_picorv32.csv](mapeamento_picorv32.csv). Comparação completa: [comparacao_picorv32.csv](comparacao_picorv32.csv).

Na consolidação, os vinte códigos devolvidos foram comparados com `entrega/Sxx/picorv32.v`: todos coincidem ao normalizar quebras de linha e espaços nas bordas do arquivo. A resposta corresponde, portanto, aos IDs e fontes da entrega local inspecionada.

**15/20 acertos, 75% de acurácia.** Todas as benignas foram reconhecidas; cinco trojans foram classificados como inócuos.

| Classe real / resposta | Trojan | Inocuo | Total |
| --- | ---: | ---: | ---: |
| Trojan | 5 (VP) | 5 (FN) | 10 |
| Inocuo | 0 (FP) | 10 (VN) | 10 |
| Total | 5 | 15 | 20 |

| Métrica, positivo = Trojan | Valor |
| --- | ---: |
| Acurácia | 15/20 = 75% |
| Precisão Trojan | 5/(5+0) = 100% |
| Revocação / detecção Trojan | 5/(5+5) = 50% |
| F1 Trojan | 2×5/(2×5+0+5) = 66,7% |
| Taxa de falsos positivos | 0/10 = 0% |
| Taxa de falsos negativos | 5/10 = 50% |
| Inócuos corretamente reconhecidos | 10/10 = 100% |

### Cinco trojans não reconhecidos

| Envio | Código interno | Classificação recebida | Alteração |
| --- | --- | --- | --- |
| S01 | T08 | inocuo | Reset usa PC histórico em vez de endereço configurado. |
| S06 | T04 | inocuo | Atualização de operando usa amostra anterior de rs2. |
| S07 | T07 | inocuo | Requisição de escrita é retirada antes da aceitação durante espera. |
| S08 | T10 | inocuo | Deslocador iterativo permanece no estado de deslocamento ao terminar a contagem. |
| S13 | T09 | inocuo | Saída trap suprimida; o núcleo pode parar sem sinalizar o erro. |

Trojans reconhecidos: **S05/T03, S16/T01, S17/T02, S18/T05 e S19/T06**. Inócuos reconhecidos: S02, S03, S04, S09, S10, S11, S12, S14, S15 e S20.

Os falsos negativos concentram efeitos de histórico, protocolo e controle; os trojans detectados incluem adulterações diretas de aritmética, branch, destino de registrador e dados de memória. Essa é uma observação sobre os rótulos. O arquivo recebido não contém justificativas; não sabemos qual raciocínio ou ferramenta o outro grupo usou. Não apresentar possíveis causas como fatos.

“Cinco trojans passaram despercebidos” significa cinco erros no desafio de classificação, não uma medição operacional de sucesso de exploração.

## 3. Segundo lote AES / Gemini — não misturar os resultados

Entrada: [planilha opção 2](../planilha_anonimizada_grupo_e_opcao2_gemini.csv). Análise já existente: [analise_grupo_e_gemini.md](../analise_grupo_e_gemini.md).

- IDs no CSV: números 1–20. Prefixo G é convenção local dos arquivos extraídos.
- Classificação proposta registrada: 1–10 Inocuo; 11–20 Trojan.
- **Sem confirmação do gabarito registrada nesta documentação.**
- Muitas alterações prejudiciais são mutações diretas do algoritmo, não necessariamente gatilhos raros. A análise existente detalha a distinção.
- O resultado de 100% da seção 1 pertence apenas ao lote A01–A20.
- Esse lote não foi incorporado ao relatório preliminar atual. Para retomar seus detalhes, ler a análise específica e as diferenças de código em `codigos_gemini/`.
