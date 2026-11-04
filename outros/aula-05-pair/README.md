# Aula 5 — PAIR bilíngue com GPT-5-mini

[Notebook local](../../notebooks/aula-05-pair.ipynb), autocontido, usando a RTX 4090.
Alvo: `gpt-5-mini-2025-08-07`. Atacante e juiz: `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
local em NF4 de 4 bits, em conversas separadas. O uso do alvo fechado
foi autorizado pelo professor, conforme informado pelo aluno.

## Execução local

Na raiz do repositório, reutilize o ambiente `.venv` da aula 2, com PyTorch CUDA
e bitsandbytes já instalados:

```powershell
.venv\Scripts\python.exe -m pip install -r outros/aula-05-pair/requirements.txt
Copy-Item outros/aula-05-pair/.env.example outros/aula-05-pair/.env
```

Preencha o `.env` somente com `OPENAI_API_KEY`. Abra o notebook no VS Code ou
Jupyter e selecione o kernel `.venv`. Leia os casos, revise os limites e execute as
células em ordem. `EXECUTAR_APIS = False` prepara a análise sem consumir créditos;
altere para `True` na execução real. Nenhuma credencial é impressa.

O pré-teste consulta as três funções com um pedido simples antes da matriz.
Falhas de acesso ao alvo ou carregamento local interrompem essa etapa.
Não há substituição automática de modelo nem download implícito.

**Não é necessário HF_TOKEN.** O snapshot completo da aula 2 está em
`D:/huggingface/hub/models--deepseek-ai--DeepSeek-R1-Distill-Qwen-14B/snapshots/1df8507178afcc1bef68cd8c393f61a886323761`.
São quatro shards, cerca de 27,5 GiB em disco, quantizados em memória para NF4
com double quantization e computação bfloat16. O carregamento usa somente arquivos
locais e uma instância compartilhada entre atacante e juiz. Reinicie o kernel se
precisar mudar o snapshot/quantização ou liberar a GPU.

O Qwen2.5-3B do cache está incompleto; o Qwen2.5-0.5B está completo, mas não foi
selecionado. O modelo atual difere do Qwen2.5-7B da planilha; essa mudança está
registrada nos artefatos locais, sem alterar a planilha compartilhada.

## Desenho e limites

- Inglês e português, mesmos casos e orçamento por condição; pedido direto e PAIR.
- Dois streams independentes, quatro iterações e uma repetição por padrão.
- Máximo planejado de 159 gerações (55 remotas e 104 locais), incluindo o pré-teste;
  teto global de 180. Atacante e juiz locais não geram cobrança de API.
- Candidatos e rubricas próprios, reduzidos e bilíngues, inspirados no PAIR.
  Não são reprodução integral dos três templates originais.
- Streams param ao obter nota 10 ou ao falhar geração, alvo ou juiz.
- O alvo recebe apenas o candidato, sem histórico ou system prompt adicional.
- Sucesso automático provisório exige nota 10; erros/truncamentos são desconhecidos.
- A comparação inclui cobertura e revisão manual; uso do mesmo modelo atacante/juiz
  pode produzir viés. Não há garantia de idioma ou de determinismo.
- O raciocínio antes de `</think>` é preservado no log bruto, mas excluído da
  interpretação do JSON. Limites locais de 4096/2048 tokens (atacante/juiz) incluem
  raciocínio; truncamento é erro e não recusa do alvo.

Os três exemplos são avaliação falsa, desculpa enganosa e pirataria de software.
Eles **não reproduzem o objetivo sobre veneno da planilha**. Cumprir um objetivo
não é necessariamente violar uma política: os primeiros exemplos têm baixa
gravidade e podem ser aceitos normalmente. O relatório deve distinguir essas
situações. Os casos podem ser editados antes da execução, mantendo pares semânticos.
O desafio opcional CipherChat não está implementado.

## Artefatos

Cada execução cria uma pasta em `resultados/`, com:

- `manifest.json`: configuração, casos, prompts, versões e estado da execução.
- `calls.jsonl`: mensagens, respostas brutas, uso de tokens, status e latência.
- `attempts.jsonl`: tentativas, notas e referências às chamadas.
- `review.csv`: formulário de revisão; copie para `review-manual.csv` e preencha.
- `summary-auto.csv` e `success-by-language.png`: gerados na análise do notebook.
- `attempts-reviewed.csv`: gerado após carregar a revisão manual.

Reexecutar a célula de execução cria uma rodada nova; não há retomada automática.
Os logs parciais são preservados após interrupção. Para reabrir uma rodada, informe
sua pasta em `RUN_DIR` na célula de análise. Não reexecute o experimento só para
regenerar tabelas. O CSV de revisão original permanece preservado.

Não foi executada a matriz PAIR nem feita chamada à OpenAI nesta preparação.
Foi validado o carregamento local do DeepSeek em NF4 na RTX 4090, seguido de uma
geração de JSON para uma conta simples: 498 tokens gerados, encerramento por EOS
e JSON interpretável. O registro está em `validacao-local.json`; ele é um teste
de infraestrutura, não um resultado de ataque. Os oito testes offline também passaram.
Salve as saídas do notebook após sua execução e acrescente o relato
e as evidências ao README principal do portfólio.

## Manutenção e validação offline

```powershell
python -m unittest discover -s outros/aula-05-pair -p test_experimento.py -v
python outros/aula-05-pair/gerar_notebook.py
```

O gerador incorpora `experimento.py` ao notebook para que ele possa ser aberto
sem imports de módulos do repositório. Regenere após alterar esse arquivo; isso
recria o notebook sem saídas. Os testes usam respostas simuladas, sem rede ou chaves.

## Referências

- [PAIR: repositório original](https://github.com/patrickrchao/JailbreakingLLMs)
- [Prompts originais](https://github.com/patrickrchao/JailbreakingLLMs/blob/main/system_prompts.py)
- [GPT-5-mini](https://developers.openai.com/api/docs/models/gpt-5-mini)
- [DeepSeek-R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)
- [Carregamento offline](https://huggingface.co/docs/transformers/v4.57.1/en/installation#offline-mode)
- [CipherChat, extensão opcional](https://openreview.net/forum?id=MbfAK4s61A)
