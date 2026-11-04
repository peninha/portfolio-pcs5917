# Resultados da avaliação humana — HEPIC

Esta pasta reúne exportações dos estudos realizados com o HEPIC. O software fica na pasta irmã `../hepic/`.

## Exportação de 4 de novembro de 2026

- Arquivo: `hepic-results-2026-11-04.csv`, preservado integralmente como exportado pelo sistema, em UTF-8.
- Ciclo: `ecd2f7f6-1a36-436e-b03a-ec50c35733de`.
- Conteúdo: 152 itens únicos e 35 colunas; 140 itens de avaliação, 9 de calibração e 3 da preparação de referências (2 exemplos válidos e 1 inconclusivo). Não há duplicação de itens neste ciclo.
- Situações: 112 `single`, 36 `agreement`, 1 `adjudicated`, 1 `inconclusive` e 2 `reference`.
- Respostas individuais: 197, todas enviadas; Pena 65, Caio 65 e Arthur 67. As contagens incluem calibração e avaliação.
- Limiar de discordância: 35%.
- SHA-256: `76db5538f4d0f4808bb8d2f085f383ca3e79c5438b814834894afb6367bccbe0`.
- Cópia na planilha principal: aba [HEPIC_Resultados_2026-11-04](https://docs.google.com/spreadsheets/d/1Ln_UxzuvmUPfp69SuYsfncdUiAr2jH3O0TJxQZumO5g/edit#gid=202611040), intervalo `A1:AI153`.

Os campos e os textos originais foram mantidos. Na planilha, contagens e notas são valores numéricos, discordância e limiar são exibidos como percentuais, e `adjudicated` e as marcas `is_reference`, `is_calibration` e `is_evaluation` são booleanas. Valores ausentes continuam vazios; não representam nota zero. Os campos JSON preservam atribuições individuais e históricos de referências, calibração e decisões.

Para analisar a etapa de avaliação, filtre `item_phase = evaluation`. Um item pode ter vários usos, identificados pelas marcas de etapa e pelos históricos. O arquivo contém resultados consolidados por item, acompanhados dos históricos individuais em JSON; o CSV de notas individuais facilita analisar essas notas em linhas separadas, e o backup completo também preserva os dados administrativos do estudo.

Esta versão completa substitui a exportação anterior de 141 registros. A validação confirmou a cobertura dos 152 itens, a consistência das contagens, notas consolidadas, discordâncias e decisões, e a preservação das 22 colunas originais dos 141 registros anteriores. As 5.320 células de dados da aba foram conferidas contra este CSV, sem diferenças. Novas exportações devem ser salvas com a data correspondente, preservando esta versão.
