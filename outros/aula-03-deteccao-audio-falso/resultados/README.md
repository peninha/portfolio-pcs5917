# Resultados da aula 03

O [notebook de análise exploratória](../../../notebooks/aula-03-deteccao-audio-falso.ipynb) exporta as evidências para `eda/`:

- `integridade.csv`: auditoria técnica dos 288 arquivos, incluindo SHA-256 e erros de decodificação.
- `metadados_treino.csv`: rótulos e metadados dos 192 áudios explorados.
- `atributos_treino.csv`: 53 atributos acústicos por arquivo, com `file_id` apenas como chave, a excluir da entrada de um futuro modelo.
- `qualidade_treino.csv`: duração, pico, RMS global e proporção de amostras próximas de ±1.
- `resumo_por_classe.csv`: estatísticas descritivas de atributos selecionados, somente do treino.
- `execucao.json`: parâmetros, versões, exemplos escolhidos e hashes dos CSVs de entrada.

Figuras ficam em [images/aula-03/eda](../../../images/aula-03/eda/). As saídas são sobrescritas ao executar novamente. Não há predições nem métricas de classificação nesta etapa. O teste foi usado somente para integridade e conferência da separação das partições.


O [notebook de classificação](../../../notebooks/aula-03-classificador.ipynb) grava uma pasta por execução em `classificacao/<identificador UTC>/`:

- `divisoes_treino.csv`: parte de validação de cada um dos 192 áudios; sem locutores compartilhados entre treino e validação.
- `busca_parametros.csv`, `validacao_resumo.csv`, `validacao_por_rodada.csv`: candidatos e resultados de desenvolvimento. As mesmas divisões escolhem parâmetros e comparam experimentos; os melhores resultados podem ser otimistas.
- `protocolo_antes_teste.json`: conjuntos de atributos, grades, parâmetros escolhidos, versões e hashes, fixados antes da extração do teste.
- `atributos_teste.csv`: medidas dos 96 áudios reservados, com o mesmo processamento da EDA.
- `teste_metricas.csv`, `teste_predicoes.csv`, `teste_por_ataque.csv`, `validacao_vs_teste.csv`: avaliação final das seis configurações planejadas. `spoof` é a classe positiva (1).
- `execucao.json`: procedência dos arquivos, hash do protocolo e dos CSVs resultantes.

Figuras incluem comparação de validação, seis matrizes de confusão, validação versus teste e detecção por ataque. Melhorias propostas após observar o teste exigem outra avaliação independente para confirmação. Os pesos não são exportados; os parâmetros e divisões permitem reproduzir o treinamento.
