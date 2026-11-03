# Resultados da aula 03

O [notebook de análise exploratória](../../../notebooks/aula-03-deteccao-audio-falso.ipynb) exporta as evidências para `eda/`:

- `integridade.csv`: auditoria técnica dos 288 arquivos, incluindo SHA-256 e erros de decodificação.
- `metadados_treino.csv`: rótulos e metadados dos 192 áudios explorados.
- `atributos_treino.csv`: 53 atributos acústicos por arquivo, com `file_id` apenas como chave, a excluir da entrada de um futuro modelo.
- `qualidade_treino.csv`: duração, pico, RMS global e proporção de amostras próximas de ±1.
- `resumo_por_classe.csv`: estatísticas descritivas de atributos selecionados, somente do treino.
- `execucao.json`: parâmetros, versões, exemplos escolhidos e hashes dos CSVs de entrada.

Figuras ficam em [images/aula-03/eda](../../../images/aula-03/eda/). As saídas são sobrescritas ao executar novamente. Não há predições nem métricas de classificação nesta etapa. O teste foi usado somente para integridade e conferência da separação das partições.
