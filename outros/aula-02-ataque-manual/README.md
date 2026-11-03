# Aula 02 — Ataque manual

- [Notebook entregável](../../notebooks/aula-02-llm-jailbreaks.ipynb): instalação, seleção manual, execução e discussão.
- [Dependências](requirements.txt): instale o PyTorch com CUDA separadamente, conforme o notebook.
- [Dados de entrada](dados/README.md): CSV original, tradução portuguesa e tabela bilíngue versionados, com IDs e marcadores correspondentes.
- [Perguntas-alvo EN/PT](dados/attack_questions.bilingual.csv): oito casos com categorias e critérios de avaliação para combinar com as estratégias.
- [Ataques verificáveis](dados/VERIFIABLE.md): cinco tarefas EN/PT, selecionáveis na célula CONFIG do notebook, com validação automática e comparação pareada com a baseline.
- [Validação dos templates](validar_templates.py): confere a integridade EN/PT sem carregar modelos.
- [Resultados](resultados/README.md): registros completos, CSVs compilados e regras de cálculo.
- [Evidências](../../images/aula-02/): capturas das células.

Os CSVs de resultados devem ser versionados. Pesos do modelo e downloads de entrada não precisam ser enviados ao Git. Referências e hashes dos dados usados ficam em `resultados/`.

Para recompilar sem carregar o modelo, execute na raiz do repositório:

```sh
python outros/aula-02-ataque-manual/compilar_resultados.py
```

Fonte: [Self-Reminder-Data](https://github.com/yjw1029/Self-Reminder-Data/blob/master/data/jailbreak_prompts.csv). Modelo: [DeepSeek-R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B).

## Fluxo do notebook

1. **CONFIG:** escolha `strategy` (nome ou ID), `attack` (V01–V05 ou Q01–Q08), `language` (`pt`, `en`, `both`), repetições, seed e parâmetros de geração. Modelo e cache ficam na mesma célula.
2. **Preparar e conferir:** carrega os CSVs e mostra as mensagens exatas, sem modelo ou GPU. Sempre reexecute após mudar CONFIG.
3. **Executar:** carrega/reutiliza o modelo e faz baseline + ataque por idioma e repetição. As repetições usam seeds consecutivas. A execução seguinte reutiliza os pesos se o modelo/revisão forem os mesmos.
4. **Avaliar, quando necessário:** casos V são automáticos. Para casos Q, edite somente verdict e notes nos arquivos `avaliacoes-<run_id>.csv` gerados e execute a célula de importação. Ela lê os arquivos de todas as execuções, mostra Q01/Q02/etc. juntos e informa arquivo/linha em caso de erro. notes é opcional. Não precisa copiar IDs nem chamar assess manualmente.
5. **Consultar CSVs:** os resultados são exportados automaticamente; a última célula atualiza e mostra as estatísticas acumuladas de todas as execuções. Reexecutá-la não gera novas respostas.

A infraestrutura fica em [experimento.py](experimento.py). A versão anterior do notebook, incluindo suas saídas, está em [notebooks/archive](../../notebooks/archive/README.md). Tentativas e avaliações já existentes continuam preservadas nos JSONL.