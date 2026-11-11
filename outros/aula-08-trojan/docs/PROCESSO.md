# Histórico do trabalho e decisões

## 1. Enunciado

O enunciado pede relatório em grupo sobre métodos de geração e detecção de trojans, exemplos de trojans e mudanças legítimas, resultados, interação com outros grupos e relevância de uma abordagem purple team. O usuário determinou máximo de quatro páginas, coluna dupla, seguindo formato e integrantes da Aula 7.

## 2. Nosso conjunto — PicoRV32

A elaboração ocorreu em outro chat e no checkout `C:/Users/3119088/code/picorv32`. Foi escolhido o PicoRV32, em Verilog, no recorte RV32I com interface nativa de memória, sem interrupções nem coprocessador. Referência: commit `ef203c2b0a3fb793280f5114941416c425c5b461`.

Primeiro foram propostas dez adulterações e dez mudanças benignas. O usuário pediu benignas estruturalmente complexas, para evitar que o avaliador distinguisse as classes apenas pela aparência. A lista foi revista para incluir recodificação de estados, decomposição aritmética, comparações equivalentes e reestruturação de memória e controle.

Foram criadas vinte variantes independentes da mesma referência, não cumulativas, em pastas e commits identificados B01–B10 e T01–T10. O histórico menciona `codex/benign-variants` para B e `codex/challenge-variants` reunindo as vinte. Não é necessário recuperar essas branches para usar a cópia da entrega presente neste repositório.

| Código | Mudança |
| --- | --- |
| B01 | Permutação one-hot dos estados. |
| B02 | Separação de campos na segunda etapa do decodificador. |
| B03 | Reconstrução explícita dos imediatos. |
| B04 | Soma/subtração em metades com carry. |
| B05 | Reformulação de comparações com e sem sinal. |
| B06 | Loads por deslocamentos e máscaras. |
| B07 | Distribuição dos dados e máscaras de stores. |
| B08 | Cadeia de prioridades do writeback. |
| B09 | Decomposição booleana do handshake de memória. |
| B10 | Próximo contador e condições do deslocador, não reescrita de toda a máquina de estados. |
| T01 | Inversão do bit menos significativo da soma. |
| T02 | BEQ também aceita menor sem sinal. |
| T03 | Inversão do bit inferior do índice de destino, não do valor gravado. |
| T04 | Uso da amostra anterior de rs2. |
| T05 | Inversão de um bit na leitura de palavra. |
| T06 | Rotação de um byte dos dados do store, mantendo máscara. |
| T07 | Abandono da requisição de escrita em espera. |
| T08 | Endereço de reset dependente do PC histórico. |
| T09 | Supressão da sinalização trap; não implica que execução prossiga. |
| T10 | Perda de progresso do deslocador iterativo. |

T03 pressupõe o banco interno padrão; T10 pressupõe `BARREL_SHIFTER=0`. Algumas adulterações são diretas e não dependem de um gatilho raro. Não atribuir a todas o mesmo padrão de trigger do AES.

Uma permutação aleatória associou B/T aos IDs S01–S20. Foi preparado ZIP com 23 arquivos: referência `picorv32.v`, vinte versões, README e CSV vazio para resposta. O gabarito ficou fora do envio. O usuário posteriormente adicionou [a pasta entrega](../entrega/) neste repositório, que passou a ser a referência local dos arquivos enviados.

## 3. Primeiro conjunto recebido — AES do grupo E

Recebemos um CSV com vinte códigos e regras R1–R6. Na conversa desta tarefa:

1. Extraímos os vinte campos de código para `codigos/Axx_AES_hash.cpp`, preservando exatamente os conteúdos dos campos.
2. Comparamos as versões e interpretamos as diferenças. A01 era apenas uma âncora textual e também era Trojan; não deve ser tratada como golden model.
3. Identificamos dez trojans e dez mudanças benignas. A dica de distribuição 10/10 serviu como conferência, não como prova de cada classificação.
4. Criamos `avaliacao_grupo_e.csv`, colunas `id_anonimo,avaliacao`, com os valores `Trojan` ou `Inocuo`.
5. O usuário informou que o grupo E confirmou 20/20 acertos.

Regras recebidas: R1 correção criptográfica; R2 determinismo e independência entre chamadas; R3 exceções para tamanhos inválidos; R4 ausência de efeitos observáveis indevidos com verbose=false; R5 conformidade FIPS 197; R6 saída igual à referência fora dos gatilhos. A tabela detalhada dos achados está em [RESULTADOS.md](RESULTADOS.md).

Os arquivos estavam inicialmente em `outros/aula-07-trojan/`, mas foram movidos pelo usuário para `outros/aula-08-trojan/`. Referências antigas no chat usam o caminho anterior; usar o atual.

## 4. Relatório

Usamos `outros/aula-07-defesas/relatorio-aula07.pdf` para recuperar os nomes, números USP, e-mails e o formato: A4, cabeçalho acadêmico, título e resumo em largura total, corpo em duas colunas, fonte serifada e paginação. Criamos o Markdown e um gerador ReportLab. O resultado tem quatro páginas, com imagens de todas as páginas inspecionadas visualmente.

A primeira versão tratava os dois resultados como pendentes. Durante a redação chegou a confirmação de 20/20 do AES, incorporada ao resumo, metodologia, resultados e conclusão. Depois, por pedido explícito do usuário, retiramos os detalhes de compilação e validação do texto. O formato e o resultado foram mantidos.

O retorno PicoRV32 chegou **depois da última edição do PDF**. Comparamos o CSV preenchido com o mapeamento interno e apuramos 15/20, detalhados em [RESULTADOS.md](RESULTADOS.md). Ainda falta incorporar esse resultado ao relatório. Esta é a próxima tarefa material; não há mais pendência de receber a classificação PicoRV32.

## 5. Material adicional Gemini

Na hora de documentar a continuidade, já existiam no diretório a segunda planilha AES, o script `analisar_gemini.py`, o diretório `codigos_gemini/` e a análise `analise_grupo_e_gemini.md`. Eles não foram produzidos nas etapas desta conversa mostradas acima. A análise existente foi lida para registrar seu estado sem confundir lotes: propõe 1–10 inócuos e 11–20 trojans e declara ausência de gabarito confirmado. Os detalhes devem ser recuperados desse documento, não inferidos a partir dos IDs A.

## 6. Reflexão purple team a preservar

A atividade reuniu autoria e avaliação de adulterações. A contribuição purple team vai além de contar acertos: após a análise cega, revelar condições e efeitos, comparar evidências, discutir ambiguidades e melhorar a documentação e as estratégias de revisão. A17 é exemplo de distinção entre rótulo benigno do desafio e ressalva do contrato. No PicoRV32, a comparação entre os trojans detectados e os cinco não detectados permite discutir efeitos diretos versus efeitos temporais/de controle, sem inventar justificativas do avaliador.

## 7. Conversas e fontes de contexto

- Chat de elaboração consultado: **Listar trojans e melhorias benignas**, ID `01a1cbd8-bcde-7f23-999f-23670b23c0f7`, host `local`, checkout original `picorv32`.
- Referência de app: `thread://01a1cbd8-bcde-7f23-999f-23670b23c0f7?hostId=local`. A documentação acima é suficiente se esse chat não estiver mais disponível.
- Esse histórico menciona uma etapa anterior de escolha de golden model; não dependemos do conteúdo desse outro chat para a continuidade.
- Projeto original: https://github.com/YosysHQ/picorv32.
- Norma: https://csrc.nist.gov/pubs/fips/197/final — NIST FIPS 197, atualização de 2023.
- A documentação usa o código, os materiais presentes e os resultados comunicados pelo usuário; não pressupõe informações não registradas sobre ferramentas ou raciocínio do outro grupo.
