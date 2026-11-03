# Aula 03 — Detecção de áudio falso

- [Notebook de análise exploratória](../../notebooks/aula-03-deteccao-audio-falso.ipynb): validação dos FLAC, escuta, formas de onda, espectrogramas Mel, MFCCs e outros atributos com Librosa. Abra no Jupyter/VS Code e selecione o Python de `.venv`.
- [Dependências](requirements.txt): instale na raiz com `.\.venv\Scripts\python.exe -m pip install -r outros/aula-03-deteccao-audio-falso/requirements.txt`.
- A exploração usa somente os 192 áudios de treino. Os 96 de teste passam apenas por auditoria de integridade, preservando a avaliação final. O notebook ainda não treina classificadores.
- Tabelas e parâmetros são exportados para `resultados/eda/`; figuras para `images/aula-03/eda/`. Anote suas interpretações nas células indicadas e salve o notebook com as saídas.
- [Preparação dos dados](preparar_subconjunto.py): script com caminhos relativos à própria pasta, independente do diretório de execução.
- [Subconjunto atualizado](dados/subconjunto_288/README.md): 192 áudios de treinamento e 96 de teste.
- [Seleção inicial](dados/subconjunto_192/README.md): preservada como registro.
- `dados/`: metadados, listas e áudios de entrada. Os metadados, listas e áudios que já faziam parte do repositório foram preservados e continuam elegíveis para versionamento.
- `resultados/`: destinado aos CSVs de predições, métricas e outros resultados da atividade, que deverão ser versionados.
- [Evidências](../../images/aula-03/).

Fonte: [ASVspoof no Kaggle](https://www.kaggle.com/datasets/ulianazb/asvspoof-2024).
