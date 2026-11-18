# Caderno Editorial · WCIA

Aplicação local da aula 9 para revisar artigos curtos do WCIA. Os dois artigos dos anais da SBC já vêm cadastrados. Novos trabalhos entram como PDF com texto selecionável e categoria declarada pelos autores.

## Executar

Na pasta da aula 9, com Node.js 22.16 ou mais recente:

```powershell
npm ci
npm start
```

Abra [http://127.0.0.1:4399](http://127.0.0.1:4399). O modo demonstração abre com notas e comentários fictícios. Ele permite experimentar o painel e o formulário editorial.

### Usar modelos para avaliar

Copie `.env.example` para `.env`. Para testar a triagem pelo OpenRouter, preencha as duas linhas abaixo e retire o `#` do início de cada uma.

```dotenv
OPENROUTER_JEV_API_KEY=cole_a_chave_aqui
OPENROUTER_JEV_MODEL=typesafe/jev-1.14
```

O Jev da TypeSafe é um modelo de decisão. A aplicação envia as quatro perguntas em uma chamada à Decisions API do OpenRouter (`POST /api/alpha/decisions`). O Jev retorna uma probabilidade de Sim para cada pergunta. No piloto, a aplicação conta como Sim uma probabilidade acima de 50% e mostra o valor no painel da triagem. Esse corte é provisório. A avaliação de mérito continua a cargo do ensemble. Se informar apenas a chave, o modelo padrão é `typesafe/jev-1.14`. [Guia do Jev no OpenRouter](https://openrouter.ai/blog/insights/what-is-jev/)

Com essa configuração, a aplicação executa e salva a triagem. Depois de configurar as outras etapas, use **Continuar avaliação** no dossiê para aproveitar a triagem salva.

| Variável | Função |
| --- | --- |
| `REVIEW_API_BASE_URL` | URL raiz do provedor compartilhado compatível com Chat Completions, incluindo `/v1` quando aplicável. |
| `REVIEW_API_KEY` | Chave do provedor compartilhado. Deixe vazia quando ele dispensar autenticação. |
| `REVIEW_MODEL` | Modelo padrão da síntese e da triagem alternativa por LLM no provedor compartilhado. |
| `REVIEW_MODEL_JEV` | Modelo da triagem alternativa por LLM quando a integração com o Jev está desativada. |
| `REVIEW_MODEL_AVALIADOR_1` | Modelo do primeiro avaliador. Padrão na API direta da OpenAI: `gpt-5.4-mini`. |
| `REVIEW_MODEL_AVALIADOR_2` | Modelo do segundo avaliador. Padrão na API direta da OpenAI: `gpt-5.4`. |
| `REVIEW_MODEL_AVALIADOR_3` | Modelo do terceiro avaliador. Padrão na API direta da OpenAI: `gpt-5.5`. |
| `REVIEW_MODEL_SINTESE` | Modelo que combina os pareceres em texto para o editor. |

O ensemble exige três identificadores distintos. Na API direta da OpenAI, os três modelos do piloto já vêm como padrão. Para outro provedor, preencha as três variáveis dos avaliadores com os identificadores do catálogo dele. As variáveis antigas dos perfis Método, Contribuição e Clareza foram substituídas pelas três posições numeradas. Pareceres antigos continuam visíveis. Use **Refazer avaliação** para executar o novo ensemble em um dossiê já avaliado. Reinicie a aplicação após editar `.env`.

### Esforço de raciocínio

Defina `REVIEW_REASONING_EFFORT` para escolher o esforço padrão no provedor compartilhado. Use `REVIEW_REASONING_EFFORT_ENSEMBLE` para ajustar os três avaliadores juntos, `REVIEW_REASONING_EFFORT_JEV` para a triagem alternativa por LLM ou `REVIEW_REASONING_EFFORT_SINTESE` para a síntese. O Jev da TypeSafe recebe perguntas tipadas. Nessa rota, a aplicação envia modelo, artigo e perguntas.

Para o piloto, comece com `medium` nos três pareceristas e na síntese. A aplicação já aplica `medium` ao trio padrão da OpenAI quando o esforço está em branco. Para as outras etapas e combinações de modelos, um campo vazio usa o padrão do provedor. Os níveis dependem do modelo. Na API da OpenAI, `gpt-5.4-mini` aceita `none`, `low`, `medium`, `high` e `xhigh`. Reinicie o servidor após editar `.env`.

[GPT-5.4 mini na OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini) · [Esforço de raciocínio no OpenRouter](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)

Ao executar a avaliação, o servidor encaminha o texto extraído ao provedor configurado. A síntese recebe os pareceres individuais e os indicadores calculados. O arquivo `.env` é ignorado pelo Git e a chave fica no processo local.

## Protocolo do piloto

1. O JEV responde quatro perguntas. O artigo avança com pelo menos três respostas afirmativas, incluindo a de enquadramento no WCIA.
2. Três modelos distintos avaliam o texto em paralelo com o mesmo prompt, o mesmo esforço configurado e a mesma rubrica de 0 a 2. Cada nota vem com justificativa e localização da evidência. A categoria declarada determina as perguntas e os critérios específicos.
3. O servidor solicita uma síntese dos pareceres por critério. O editor pode expandir cada linha para ler os pareceres originais. A decisão editorial pode ser aprovar, rejeitar ou pedir alterações, com comentário.

O formulário **Regras da chamada** registra a conferência manual de formato, extensão, anonimato e declaração de IA. Essas informações acompanham o dossiê editorial.

| Critério | Peso |
| --- | ---: |
| Relevância do problema | 10% |
| Contribuição e trabalhos relacionados | 15% |
| Clareza e precisão técnica | 10% |
| Alcance das conclusões | 15% |
| Desenho da avaliação, sustentação da tese ou coerência da proposta, conforme a categoria | 30% |
| Verificabilidade, implicações ou possibilidade de avaliação, conforme a categoria | 20% |

O score percentual é a soma da média de cada critério multiplicada pelo peso percentual, dividida por 2. A régua usa cinco faixas. Acima de 70% aparece **Aprovado** em verde. A partir de 90%, **Aprovado com louvor**. Exatamente 70% fica na faixa **Reprovado · próximo ao corte**.

A discordância por critério segue a aula 6. Some a diferença absoluta entre todos os pares de notas e divida por `n × (n − 1)`. O indicador geral é a média dos seis valores. Com menos de dois pareceres, a discordância fica não aferível.

## Troca entre grupos

Os pareceres humanos e a decisão ficam salvos no navegador. Exporte o dossiê em JSON para que o outro grupo possa importá-lo na própria instância e registrar a decisão. Os PDFs do piloto ficam em `artigos/`. Para um artigo acrescentado por upload, o dossiê leva o texto extraído. Compartilhe o PDF original junto do JSON quando o outro grupo precisar consultar figuras ou a formatação.

- [Chamada do WCIA 2026](https://www.sbseg2026.uff.br/workshops/wcia/)
- [Código de Conduta da SBC](https://sol.sbc.org.br/index.php/indice/conduta)
- [Protocolo e cálculo de discordância da aula 6](../aula-06-llm-como-juiz/hepic/README.md)
