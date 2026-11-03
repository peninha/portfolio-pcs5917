# Aula 03 — Detecção de áudio falso

- [Notebook de análise exploratória](../../notebooks/aula-03-deteccao-audio-falso.ipynb): validação dos FLAC, escuta, formas de onda, espectrogramas Mel, MFCCs e outros atributos com Librosa. Abra no Jupyter/VS Code e selecione o Python de `.venv`.
- [Notebook de classificação](../../notebooks/aula-03-classificador.ipynb): SVM e Random Forest em três conjuntos de atributos (duração, MFCCs e completo). Use as tabelas exportadas pela EDA. A seleção de parâmetros usa quatro divisões fixas dentro do treino; as seis configurações são fixadas antes da avaliação nos 96 áudios reservados.
- [Extração para classificação](atributos_audio.py): reproduz o processamento da EDA; o notebook verifica equivalência numérica em quatro exemplos antes de processar o teste.
- [Dependências](requirements.txt): instale na raiz com `.\.venv\Scripts\python.exe -m pip install -r outros/aula-03-deteccao-audio-falso/requirements.txt`.
- A exploração usa somente os 192 áudios de treino. Na EDA, os 96 de teste passam apenas por auditoria de integridade; no notebook de classificação são usados para avaliação final, após a seleção dos parâmetros.
- Tabelas e parâmetros são exportados para `resultados/eda/`; figuras para `images/aula-03/eda/`. Anote suas interpretações nas células indicadas e salve o notebook com as saídas.
- A classificação cria uma pasta por execução em `resultados/classificacao/` e em `images/aula-03/classificacao/`, com métricas de validação e teste, predições, parâmetros, hashes e figuras. Repetir o mesmo teste não fornece uma avaliação independente.
- [Preparação dos dados](preparar_subconjunto.py): script com caminhos relativos à própria pasta, independente do diretório de execução.
- [Subconjunto atualizado](dados/subconjunto_288/README.md): 192 áudios de treinamento e 96 de teste.
- [Seleção inicial](dados/subconjunto_192/README.md): preservada como registro.
- `dados/`: metadados, listas e áudios de entrada. Os metadados, listas e áudios que já faziam parte do repositório foram preservados e continuam elegíveis para versionamento.
- `resultados/`: destinado aos CSVs de predições, métricas e outros resultados da atividade, que deverão ser versionados.
- [Evidências](../../images/aula-03/).

Fonte: [ASVspoof no Kaggle](https://www.kaggle.com/datasets/ulianazb/asvspoof-2024).
