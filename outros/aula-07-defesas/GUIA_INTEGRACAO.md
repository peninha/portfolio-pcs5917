# Guia de integração — Grupo A

Para a coleta fechada de sete condições, siga [PROTOCOLO.md](PROTOCOLO.md).
Este guia descreve a integração exploratória da biblioteca 2.0.0.

Este guia acompanha o protocolo `2.0.0` para `Qwen/Qwen2.5-3B-Instruct`.
O ponto de entrada é `aplicar_defesa` em `defesas.py`. Cada integrante usa essa
função desde a coleta do baseline, com o ataque completo como argumento `prompt`.

## 1. Preparar os arquivos

Extraia o ZIP. Para integrar ao seu projeto, copie `defesas.py` para a mesma pasta
do script ou notebook. Abra o terminal nessa pasta. No Colab, envie o arquivo pela
aba Arquivos. O diretório de trabalho usual é `/content`.

Python 3.9+ executa o módulo e a demonstração das mensagens. Para executar o
Qwen com Transformers 4.57.6, use Python 3.10+ e um ambiente compatível com PyTorch.

Confira a montagem das oito configurações sem carregar o modelo.

```bash
python exemplo_uso.py --idioma pt
python exemplo_uso.py --idioma en
```

## 2. Integrar primeiro o baseline

O baseline usa `defesa="nenhuma"` e `formato="mensagens"`. Ele contém o system
padrão do Qwen e o ataque completo na mensagem user.

```python
from defesas import aplicar_defesa

prompt_original = "Quanto é 2 + 2?"  # Substitua pelo ataque completo do seu caso.
mensagens = aplicar_defesa(
    prompt_original,
    defesa="nenhuma",
    idioma="pt",
    posicao="ambos",
    formato="mensagens",
)
```

Se o notebook já carrega o modelo e o tokenizer, use os mesmos objetos no trecho
a seguir. Substitua a etapa antiga que montava as mensagens por essa chamada.

```python
import torch

texto = tokenizer.apply_chat_template(
    mensagens, tokenize=False, add_generation_prompt=True
)
entradas = tokenizer(
    texto, add_special_tokens=False, return_tensors="pt"
).to(model.device)

model.eval()
with torch.inference_mode():
    saida = model.generate(
        **entradas,
        do_sample=False,
        num_beams=1,
        max_new_tokens=2048,
        temperature=None, top_p=None, top_k=None,
    )

novos_tokens = saida[0, entradas["input_ids"].shape[-1]:]
resposta = tokenizer.decode(novos_tokens, skip_special_tokens=True)
print(resposta)
```

`do_sample=False`, `num_beams=1` e `max_new_tokens=2048` são configurações sugeridas
para o exemplo. O grupo deve alinhar os valores para a coleta e usar os mesmos
em todas as condições, com orçamento suficiente para respostas completas.
Se você já coletou um baseline com outro system ou outra configuração, confira
as diferenças e reexecute-o com o protocolo comum antes da comparação pareada.

## 3. Preparar um ambiente novo para inferência

Em um ambiente local com Python 3.10+ e PyTorch compatível com o hardware,
instale as bibliotecas de inferência.

```bash
python -m pip install transformers==4.57.6 accelerate torch
```

Em uma célula do Colab, o comando equivalente é

```python
%pip install transformers==4.57.6 accelerate torch
```

A primeira carga baixa os arquivos do modelo. O modelo tem aproximadamente
3 bilhões de parâmetros. Use GPU quando disponível e confira a memória do
ambiente. No Colab, selecione um runtime com GPU antes de carregar o modelo.

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from defesas import MODELO_ALVO

REVISAO = "main"  # Para a coleta, alinhem um commit HF entre os integrantes.
tokenizer = AutoTokenizer.from_pretrained(MODELO_ALVO, revision=REVISAO)
model = AutoModelForCausalLM.from_pretrained(
    MODELO_ALVO,
    revision=REVISAO,
    torch_dtype="auto",
    device_map="auto",
)
```

O script pronto executa quatro condições para uma mesma pergunta e salva o
resultado, incluindo entradas, respostas e parâmetros.

```bash
python exemplo_inferencia.py --prompt "Quanto é 2 + 2?" --idioma pt --saida verificacao.json
```

No Colab, execute o mesmo comando com `!python`. Se o modelo já estiver carregado,
envie também `exemplo_inferencia.py` para o runtime e reutilize os objetos.

```python
from exemplo_inferencia import executar_exemplo

resultado = executar_exemplo(model, tokenizer, prompt_original, idioma="pt")
```

Esse exemplo faz quatro gerações independentes com greedy decoding e seed 42.
O JSON registra a versão do módulo, seu hash, o template, as versões das bibliotecas,
a revisão do modelo e as contagens de tokens. `atingiu_limite_geracao=True`
sinaliza uma saída que precisa ser conferida antes da avaliação. A seed auxilia
a reprodução, com resultados sujeitos também ao hardware e ao ambiente.

## 4. Aplicar cada defesa ao mesmo ataque

Use sempre `prompt_original` como entrada da função. Monte uma conversa nova a
cada condição. O resultado de uma condição é salvo para avaliação, enquanto a
próxima condição volta a receber o ataque original.

```python
configuracoes = [
    ("nenhuma", "ambos"),
    ("self_reminder", "inicio"),
    ("self_reminder", "fim"),
    ("self_reminder", "ambos"),
    ("intention_analysis", "inicio"),
    ("ambos", "inicio"),
    ("ambos", "fim"),
    ("ambos", "ambos"),
]

for defesa, posicao in configuracoes:
    mensagens = aplicar_defesa(
        prompt_original,
        defesa=defesa,
        idioma="pt",
        posicao=posicao,
        formato="mensagens",
    )
    # Use aqui a mesma etapa de tokenização e geração do baseline.
```

Essas são as oito configurações distintas para um idioma. Os três valores de
`posicao` geram o mesmo baseline. Na IA isolada, eles também geram a mesma entrada,
pois a IA sempre fica no início. Rodar os dois idiomas gera 15 entradas distintas
por ataque, considerando um baseline comum e sete configurações por idioma.
O grupo pode selecionar um subconjunto da matriz antes da coleta.

`idioma` traduz apenas a defesa. Para avaliar o idioma do ataque, prepare casos
identificados separadamente em PT e EN. Conserve o mesmo texto original em todas
as condições comparadas para cada caso.

## 5. Entender o system e o tokenizer

A frase `You are Qwen, created by Alibaba Cloud. You are a helpful assistant.`
é o system padrão do template oficial. O protocolo a inclui explicitamente em
todas as condições. Ao receber esse system inicial, `apply_chat_template` usa
seu conteúdo e produz uma única ocorrência dessa instrução.

As defesas são inseridas em mensagens system. Self-Reminder no fim usa um system
posterior ao user, uma ordem aceita pelo template oficial do Qwen.
Na combinação, a ordem é system comum + IA + SR inicial opcional, user com o
ataque, system com SR final opcional. O formato é validado pelo template oficial.
A eficácia será medida nos experimentos do grupo.

A menção a ChatGPT nos textos de Self-Reminder foi mantida a partir do estudo.
Também foi mantida a formulação da IA que termina com a introdução da consulta.
Na combinação com SR inicial, esse lembrete aparece entre a IA e a mensagem user.
As escolhas fazem parte da versão 2.0.0. Alterações nesses textos ou na ordem
devem ser compartilhadas numa nova versão antes de comparar os resultados.

Para o protocolo do grupo, use `formato="mensagens"` e mantenha o system padrão.
A opção `system_prompt` permite integrar experimentos que já tenham um system
personalizado, a alinhar entre todos os participantes. `formato="texto"` produz
uma string para inspeção ou outro experimento que use defesa dentro de user.

Passe a lista de mensagens pelo chat template uma vez. Em APIs que recebem
`messages` e fazem a formatação internamente, passe a lista diretamente e confira
o suporte do serviço ao system final. O exemplo de referência usa Transformers.

## 6. Salvar resultados para o juiz e o artigo

Para cada geração, salve pelo menos os campos abaixo. O arquivo produzido por
`exemplo_inferencia.py` demonstra como registrar as entradas e as respostas.

| Campo | Conteúdo |
|---|---|
| `id_caso` | Identificador estável do ataque, igual em todas as condições |
| `autor` | Integrante responsável |
| `tecnica` | Técnica que originou o ataque |
| `prompt_original` | Ataque completo congelado |
| `idioma_ataque` | Idioma do ataque original |
| `defesa`, `idioma_defesa`, `posicao` | Argumentos usados na função |
| `posicao_efetiva` | `na` no baseline, `inicio` na IA, posição do SR nos demais |
| `mensagens`, `prompt_serializado` | Entrada efetivamente enviada |
| `resposta` | Resposta gerada pelo modelo alvo |
| `versao_protocolo`, `sha256_defesas_py` | Identificação do módulo compartilhado |
| Configuração da execução | Revisões, template, bibliotecas, dtype/quantização, seed e geração |

Arthur acrescentará a avaliação do JEV. Os cinco ataques com falha no baseline
continuam no conjunto pareado. Preserve as respostas originais para a análise
das transições entre sucesso e falha. Os 10 sucessos e 5 fracassos constituem
uma amostra selecionada por resultado, a descrever assim no artigo.

## 7. Instruções para a IA que adapta o notebook

Copie o texto abaixo junto com `defesas.py` e seu notebook.

> Integre o protocolo 2.0.0 do Grupo A ao meu notebook de Qwen/Qwen2.5-3B-Instruct.
> Use a função aplicar_defesa do arquivo fornecido para construir todas as
> entradas, inclusive o baseline com defesa="nenhuma". Use formato="mensagens"
> e o system padrão do módulo. Preserve o ataque original em user. Aplique
> tokenizer.apply_chat_template uma vez, com add_generation_prompt=True.
> Use add_special_tokens=False se tokenizar depois de serializar o template.
> Execute cada condição em uma conversa nova com o mesmo ataque original e os
> mesmos parâmetros de geração. Preserve os textos e a ordem definidos no módulo.
> Registre a versão do protocolo, configuração, mensagens, prompt serializado e
> resposta com o mesmo id_caso para permitir comparação pareada. Confira limites
> de contexto e registre saídas que atingem o orçamento de geração. Leia o guia
> fornecido para as opções e exemplos. Reutilize o carregamento de modelo e
> tokenizer do notebook quando for compatível e explicite diferenças de configuração.

## 8. Conferir a instalação

Na pasta extraída, execute os testes do módulo.

```bash
python -m unittest -v test_defesas
```

Os exemplos completos com tags estão em [exemplos-prompts-qwen.md](exemplos-prompts-qwen.md).
A referência da API, fontes e atribuições estão em [README.md](README.md).
