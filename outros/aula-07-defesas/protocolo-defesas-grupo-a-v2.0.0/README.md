# Aula 7 — Protocolo de defesas do Grupo A

Módulo compartilhável: **`defesas.py`**, versão `2.0.0`, Python 3.9+ e nenhuma
dependência externa. Copie esse arquivo para a pasta do notebook ou script.
Modelo alvo: `Qwen/Qwen2.5-3B-Instruct`. A avaliação com JEV fica separada.

## Começar pelo pacote compartilhado

Leia [GUIA_INTEGRACAO.md](GUIA_INTEGRACAO.md) para preparar o ambiente, integrar o
baseline ao notebook, executar as defesas e orientar a IA que adapta seu código.

| Arquivo | Uso |
|---|---|
| `defesas.py` | Módulo único para copiar ao seu notebook ou script |
| `GUIA_INTEGRACAO.md` | Passo a passo, registro de resultados e instruções para sua IA |
| `exemplo_uso.py` | Oito configurações para conferir as mensagens, com Python padrão |
| `exemplo_inferencia.py` | Baseline e três condições defendidas no mesmo Qwen |
| `exemplos-prompts-qwen.md` | Dezesseis prompts completos em PT e EN com as tags do Qwen |
| `test_defesas.py` | Testes offline do módulo |
| `verificar_template_qwen.py` | Verificação adicional com o template oficial |
| `LICENSE` | Licença GPL v3 do repositório, incluída no ZIP |

Na pasta extraída, comece por `python exemplo_uso.py --idioma pt`.
Para integrar ao notebook, importe `aplicar_defesa` do arquivo `defesas.py`.

## Uma função, dois formatos

Use `aplicar_defesa` tanto no baseline quanto nas condições com defesa.
`formato="mensagens"` é o padrão para o Qwen: retorna uma lista com os papéis
`system` e `user`. `formato="texto"` retorna uma string com defesa e ataque
concatenados, sem papéis. As tags internas são inseridas depois pelo tokenizer.

```python
from defesas import aplicar_defesa

prompt_baseline = "Explique a fotossíntese."
mensagens = aplicar_defesa(
    prompt_baseline,
    defesa="ambos",
    idioma="pt",
    posicao="ambos",
    formato="mensagens",
)

# Baseline no mesmo formato, sem os blocos de defesa.
baseline = aplicar_defesa(prompt_baseline, defesa="nenhuma", formato="mensagens")

# Para obter somente uma string:
texto = aplicar_defesa(prompt_baseline, defesa="ambos", idioma="pt", formato="texto")
assert aplicar_defesa(prompt_baseline, defesa="nenhuma", formato="texto") == prompt_baseline
```

| Parâmetro | Opções | Padrão |
|---|---|---|
| `defesa` | `nenhuma`, `self_reminder`, `intention_analysis`, `ambos` | `nenhuma` |
| `idioma` | `pt`, `en` | `en` |
| `posicao` | `inicio`, `fim`, `ambos` | `ambos` |
| `formato` | `mensagens`, `texto` | `mensagens` |
| `system_prompt` | String; usada somente em `mensagens` | Instrução padrão do Qwen |

`formato` e `system_prompt` devem ser passados pelo nome.

`idioma` controla somente a defesa; o ataque completo permanece intacto, inclusive
espaços, quebras de linha e placeholders. Não há tradução ou interpolação do ataque.
Strings vazias são permitidas. Valores de opções inválidos geram `ValueError`,
mesmo quando a opção não afeta a defesa escolhida; prompt que não é string gera
`TypeError`.

Intention Analysis (IA) sempre vem antes do ataque e ignora a posição válida
selecionada. `posicao` controla exclusivamente o Self-Reminder (SR).
Na combinação, a ordem fixa é **IA → SR inicial → ataque → SR final**, omitindo os
blocos não selecionados. Os blocos são separados por duas quebras de linha.
`defesa="nenhuma"` não acrescenta defesa: no formato texto, devolve o original;
no formato mensagens, mantém o system comum e o ataque original em user.

## Mensagens com defesa em system: uso no Qwen

O Qwen tem papéis `system`, `user` e `assistant`, delimitados pelo template com
`<|im_start|>` e `<|im_end|>`. Use `aplicar_defesa(..., formato="mensagens")` para
atribuir a defesa a `system`, mantendo o ataque em `user`.

```python
from defesas import aplicar_defesa

# tokenizer e model são os mesmos já carregados no notebook do baseline.
mensagens = aplicar_defesa(
    "Explique a fotossíntese.",
    defesa="ambos",      # troque apenas para "nenhuma" no baseline
    idioma="pt",
    posicao="ambos",
    formato="mensagens",
)
prompt_serializado = tokenizer.apply_chat_template(
    mensagens,
    tokenize=False,
    add_generation_prompt=True,
)
entradas = tokenizer(
    prompt_serializado,
    add_special_tokens=False,
    return_tensors="pt",
).to(model.device)
# Use os mesmos parâmetros de geração do baseline em model.generate(**entradas, ...).
```

Para carregar somente o tokenizer, quando necessário:

```python
from transformers import AutoTokenizer
from defesas import MODELO_ALVO

tokenizer = AutoTokenizer.from_pretrained(MODELO_ALVO)
```

| Condição | Sequência de mensagens |
|---|---|
| Nenhuma | `system` comum → `user` com ataque |
| SR início | `system` comum + SR inicial → `user` com ataque |
| SR fim | `system` comum → `user` com ataque → `system` com SR final |
| SR ambos | `system` comum + SR inicial → `user` com ataque → `system` com SR final |
| IA, qualquer posição | `system` comum + IA → `user` com ataque |
| Duas defesas | `system` comum + IA + SR inicial opcional → `user` com ataque → `system` com SR final opcional |

O system comum padrão é o texto usado pelo próprio template oficial:
`You are Qwen, created by Alibaba Cloud. You are a helpful assistant.`
Ele permanece em todos os cenários. Se o baseline existente usa outro system,
passe exatamente o mesmo `system_prompt` em todas as condições. Um valor vazio
mantém uma mensagem system explicitamente vazia e impede a inserção automática
do system padrão pelo template.

O template oficial **serializa mensagens system após user**. Usamos esse suporte
para preservar a posição final do SR sem transferir o ataque para system.
Isso valida o formato de entrada, não garante que o modelo siga esse system final
nem que a defesa seja eficaz. Esse posicionamento e a combinação das defesas são
decisões deste protocolo, não uma reprodução integral do estudo de caso.

Com `formato="texto"`, o retorno não atribui papéis nem inclui `system_prompt`:
se inserido em uma mensagem user, toda a defesa terá papel user. Para o protocolo
com system, use `formato="mensagens"` diretamente no ataque original. Aplique a
defesa uma vez e o chat template uma vez. APIs que recebem `messages` devem receber
a lista diretamente, sem serialização manual. A compatibilidade de system final
em outros modelos/provedores deve ser verificada separadamente.

### Migração da versão 1

A versão 2 unifica a API: chamadas anteriores a `preparar_mensagens(...)` passam
a ser `aplicar_defesa(..., formato="mensagens")`. Chamadas que esperavam uma
string de `aplicar_defesa(...)` devem explicitar `formato="texto"`. A função
`preparar_mensagens` foi removida. Os templates das defesas permanecem iguais.

## Comparação e reprodução

- Congele e reutilize o mesmo ataque completo nas condições, em conversas novas.
- Fixe revisão do modelo/tokenizer, system comum, chat template, quantização,
  parâmetros de geração e sementes; registre-os junto com a versão do protocolo.
- Salve prompt original, mensagens/prompt efetivamente enviados, resposta,
  defesa, idioma e posição. Para IA isolada e baseline, registre a posição como
  não aplicável na análise, pois seus três valores produzem a mesma entrada.
- Verifique o limite de contexto: truncar o ataque ou uma defesa invalida a
  comparação. O módulo não trunca nem executa inferência.
- `ambos` é um cenário adicional; mantenha também cada defesa isolada.
- Os 10 sucessos e 5 fracassos por integrante formam uma amostra selecionada por
  resultado. Reporte ASR nessa amostra e transições sucesso→falha/falha→sucesso,
  sem interpretá-la como estimativa geral de vulnerabilidade.

## Testes

Na pasta extraída, usando Python 3.9+:

```text
python -m unittest -v test_defesas
```

Na raiz do repositório, o comando equivalente é

```text
python -m unittest discover -s outros/aula-07-defesas -p test_defesas.py -v
```

São 10 testes, incluindo a matriz de 24 combinações para cada formato,
preservação do baseline, ordem das defesas, isolamento entre chamadas, system
personalizado, formato padrão e rejeição de parâmetros inválidos. Não precisam
de rede ou modelo.

A verificação adicional usa `transformers` e o JSON oficial, sem pesos nem
vocabulário. Baixe `tokenizer_config.json` pelo link abaixo e execute:

```text
python outros/aula-07-defesas/verificar_template_qwen.py caminho/para/tokenizer_config.json
```

Na pasta extraída, use `python verificar_template_qwen.py caminho/para/tokenizer_config.json`.

Esse teste compara as 24 renderizações de `apply_chat_template(tokenize=False)`
com a sequência esperada de papéis, conteúdo e delimitadores, incluindo o início
da resposta assistant. Não mede geração, tokenização em IDs, ASR ou eficácia.
O script imprime o SHA256 da configuração utilizada.

Validação local da versão 2 em 06/11/2026: **10 testes offline aprovados** e **24 combinações
renderizadas corretamente** com Transformers `4.57.6`. SHA256 da configuração
oficial utilizada:
`5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583`.
Não foi executada inferência com o modelo nesta validação.

Validação do material compartilhável em 07/11/2026: os 10 testes do módulo e as
24 renderizações oficiais passaram novamente. O exemplo de inferência foi
verificado com modelo simulado e template oficial, incluindo preservação da
entrada, extração da resposta, metadados e detecção de contexto insuficiente.
O exemplo com os pesos reais do Qwen fica para a execução no ambiente do grupo.

## Fontes e adaptações

- Hayashi et al., *DeepSeek Under Attack: An Analysis of Jailbreak Attacks and
  Prompt-Level Defenses*, DOI [10.1109/ACCESS.2026.3710427](https://doi.org/10.1109/ACCESS.2026.3710427).
  [Texto disponibilizado pelos autores](https://www.researchgate.net/publication/408534172_DeepSeek_under_Attack_an_Analysis_of_Jailbreak_Attacks_and_Prompt-Level_Defenses),
  seção de contramedidas. Os templates EN derivam dos trechos publicados sob
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), com normalização de
  espaços e pontuação. A menção a ChatGPT é preservada para manter a formulação
  experimental, embora o modelo alvo seja Qwen. Os templates PT são traduções
  deste protocolo, não traduções validadas pelos autores.
- Zhang et al., [Intention Analysis Makes LLMs A Good Jailbreak Defender](https://aclanthology.org/2025.coling-main.199/).
  Aqui usamos a variante de passagem única do estudo de Hayashi et al.; não
  implementamos o procedimento original em duas etapas de inferência.
- Qwen: [model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) e
  [tokenizer_config.json oficial](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/resolve/main/tokenizer_config.json).
  Uso de system, variações de posição e combinação são decisões deste protocolo.
