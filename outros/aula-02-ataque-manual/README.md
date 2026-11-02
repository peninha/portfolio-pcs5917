# Aula 02 — Ataque manual

- [Notebook entregável](../../notebooks/aula-02-llm-jailbreaks.ipynb): instalação, seleção manual, execução e discussão.
- [Dependências](requirements.txt): instale o PyTorch com CUDA separadamente, conforme o notebook.
- `dados/`: cópia local do CSV de entrada; download ignorado pelo Git.
- [Resultados](resultados/README.md): registros completos, CSVs compilados e regras de cálculo.
- [Evidências](../../images/aula-02/): capturas das células.

Os CSVs de resultados devem ser versionados. Pesos do modelo e downloads de entrada não precisam ser enviados ao Git. Referências e hashes dos dados usados ficam em `resultados/`.

Para recompilar sem carregar o modelo, execute na raiz do repositório:

```sh
python outros/aula-02-ataque-manual/compilar_resultados.py
```

Fonte: [Self-Reminder-Data](https://github.com/yjw1029/Self-Reminder-Data/blob/master/data/jailbreak_prompts.csv). Modelo: [DeepSeek-R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B).
