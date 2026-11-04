# HEPIC

**Human Evaluation Protocol with Iterative Calibration**

Aplicação web para três avaliadores remotos e um acesso separado de pesquisador. A mesma pessoa pode exercer as duas funções usando perfis e acessos distintos. Implementa treinamento por exemplos, calibração em amostra comum e avaliação com sobreposição e resolução progressiva de discordâncias.

## Arquitetura

- **Interface:** HTML, CSS e JavaScript, em português, sem serviços de terceiros no navegador.
- **Servidor:** Cloudflare Worker. O mesmo código atende a API local.
- **Persistência:** Cloudflare D1; no desenvolvimento, SQLite local com a mesma interface de consultas e transações.
- **Acesso:** pesquisador com chave secreta; colegas com convites individuais de uso único. Sessões em cookies HttpOnly, Secure em HTTPS e SameSite=Strict. O servidor decide o acesso a cada atribuição.
- **Concorrência:** revisões com exclusão otimista e transações D1. Gravações simultâneas são refeitas sobre a revisão mais recente, sem sobrescrever notas de outros avaliadores.

O projeto foi pensado para o plano gratuito do Cloudflare e estudos pequenos. Não requer domínio próprio, assinatura paga, LLM nem computador pessoal ligado após a publicação. O Cloudflare aplica cotas de requisições, CPU e banco; o aplicativo não contrata upgrades automaticamente.

Referências oficiais: [Workers com arquivos estáticos](https://developers.cloudflare.com/workers/static-assets/binding/), [D1 e transações em batch](https://developers.cloudflare.com/d1/worker-api/d1-database/), [limites do D1](https://developers.cloudflare.com/d1/platform/limits/).

## Executar localmente

Requer Node.js 22.13 ou superior. O iniciador Windows procura primeiro no PATH e, se necessário, usa o Node incluído no runtime local do Codex. Nesta máquina, não é necessário instalar outro Node nem alterar o PATH. Não é necessário instalar dependências para executar localmente ou rodar os testes.

```powershell
cd D:\Code\portfolio-pcs5917\outros\aula-06-llm-como-juiz\hepic
.\run.cmd
```

Abra <http://127.0.0.1:8787>. Em **Acesso do pesquisador**, informe seu nome e a chave contida em `.local/bootstrap.key`. Esse arquivo é criado automaticamente na primeira execução. O banco fica em `.local/hepic.sqlite`. A pasta `.local` está excluída do Git e não integra os arquivos públicos.

Para outro diretório ou porta, use `DATA_DIR` e `PORT`. O servidor local escuta somente em `127.0.0.1`; ele não é a hospedagem remota.

## Publicar na sua conta Cloudflare

### Publicação automática pelo GitHub

O caminho recomendado é Workers Builds, conectado ao repositório `peninha/portfolio-pcs5917`. Um push na branch de produção dispara os testes e, se passarem, publica o Worker. O Git contém o software; os dados do estudo permanecem no D1 e a chave do pesquisador permanece nos segredos da Cloudflare.

Antes da primeira publicação, crie o D1 `hepic`, substitua o placeholder `database_id` em `wrangler.jsonc` pelo ID real e configure `BOOTSTRAP_SECRET` como segredo do Worker `hepic`. O ID do banco pode ser versionado; a chave de acesso não deve ser versionada. As instruções por terminal estão abaixo.

No painel Cloudflare, abra **Workers & Pages → Create application → GitHub**, conecte o repositório e configure:

| Campo | Valor |
| --- | --- |
| Worker name | `hepic` |
| Production branch | `main` |
| Root directory | `outros/aula-06-llm-como-juiz/hepic` |
| Build command | `pnpm test` |
| Deploy command | `pnpm run deploy` |
| Build variable `NODE_VERSION` | `24.22.1` |
| Build variable `PNPM_VERSION` | `11.25.0` |

Se o Worker já existir, conecte o GitHub em **Settings → Builds → Connect**. O nome do Worker deve coincidir com `name` no `wrangler.jsonc`. Configure a chave na seção de **segredos de execução do Worker**, não somente nas variáveis do ambiente de build. O comando de deploy aplica apenas migrações D1 pendentes antes de publicar; o token utilizado pelo build precisa permitir migrações no D1 vinculado.

O provedor instala as dependências a partir do lockfile. O script `deploy` usa o binding `DB`, sem depender do nome físico do banco. Não execute esse script em builds de preview contra o banco de produção; mantenha previews desativados até configurar um banco e segredos separados para eles.

Envie os arquivos do HEPIC ao GitHub com um commit e push, preservando alterações de outras atividades. `.local/`, `.wrangler/`, bancos SQLite, segredos e `node_modules/` estão no `.gitignore` do aplicativo. A integração não migra os dados do SQLite local para o D1 remoto.

Referência: [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/) e [configuração de builds](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/).

### Publicação por terminal e configuração inicial

No Windows, `run.cmd` também aceita argumentos do Node. Por exemplo, `.\run.cmd --version` mostra a versão encontrada e `.\run.cmd node_modules/wrangler/bin/wrangler.js login` inicia a autenticação no Cloudflare. O iniciador só ajusta o PATH do próprio processo.

O projeto inclui o Wrangler oficial e um lockfile. As dependências já estão instaladas nesta máquina. Em uma instalação nova, execute `pnpm install --frozen-lockfile` primeiro. Para autenticar e criar o banco no Windows:

```powershell
.\run.cmd node_modules/wrangler/bin/wrangler.js login
.\run.cmd node_modules/wrangler/bin/wrangler.js d1 create hepic
```

O login abre a autorização da sua conta. Selecione a conta correta caso participe de mais de uma. Copie o `database_id` retornado pelo comando para `wrangler.jsonc`, substituindo `REPLACE_WITH_D1_DATABASE_ID`. Mantenha o binding `DB`.

```powershell
.\run.cmd node_modules/wrangler/bin/wrangler.js d1 migrations apply hepic --remote
.\run.cmd node_modules/wrangler/bin/wrangler.js secret put BOOTSTRAP_SECRET
.\run.cmd node_modules/wrangler/bin/wrangler.js deploy
```

Na solicitação de `BOOTSTRAP_SECRET`, informe uma chave aleatória com pelo menos 32 caracteres. Ela não deve ser escrita no código, versionada ou enviada aos colegas. Guarde-a em seu gerenciador de senhas. Essa chave dá acesso ao pesquisador e permite recuperar sua sessão.

O último comando retorna a URL permanente `workers.dev`. Abra-a e inicialize o estudo. **O banco local e o banco remoto são separados:** dados e sessões locais não são enviados no deploy. Importe o CSV/JSON na aplicação publicada.

Se o Wrangler tiver dificuldade para escrever logs no ambiente do Codex, mantenha sua configuração no projeto:

```powershell
$env:XDG_CONFIG_HOME = Join-Path (Get-Location) '.local\config'
$env:WRANGLER_LOG_PATH = Join-Path (Get-Location) '.local\logs'
$env:WRANGLER_SEND_METRICS = 'false'
```

Não publique antes de configurar o segredo. Não envie `.local`, `.dev.vars` ou bancos SQLite como arquivos estáticos. `public/` é a única pasta de arquivos públicos. O login do Cloudflare ainda é necessário para publicar na sua conta.

## Usar a aba Dados_Caio

A fonte escolhida é a aba **Dados_Caio** da [planilha Ataques](https://docs.google.com/spreadsheets/d/1Ln_UxzuvmUPfp69SuYsfncdUiAr2jH3O0TJxQZumO5g/edit?gid=1387432759). Em 2 de novembro de 2026, foram encontrados 152 itens nessa aba.

Uma captura desses itens foi preparada em `.local/Dados_Caio.json`, para importação no painel **Base de dados**. O arquivo fica apenas nesta máquina e não é versionado ou publicado automaticamente. Alternativamente, selecione a aba no Google Sheets e use **Arquivo → Fazer download → CSV**. A conexão com o Google Drive é usada para preparar a importação; a aplicação publicada não depende das credenciais do Codex e não exige tornar a planilha pública.

| Coluna da planilha | Uso no HEPIC |
| --- | --- |
| ID | Identificador estável da tentativa |
| Tarefa | Objetivo exibido ao avaliador |
| Entrada completa | Contexto e prompt exibidos ao avaliador |
| Resposta | Saída a ser julgada |
| Método, Modelo alvo, Idioma | Estratificação da amostra; exportação |
| Autoria, Aula, Condição/rodada, Fonte | Metadados preservados para pesquisa |
| Resultado anterior | Preservado; oculto no julgamento independente |

CSV aceita vírgula, ponto e vírgula ou tabulação, aspas escapadas e respostas multilinha. JSON aceita objetos normalizados ou uma matriz `values` com cabeçalhos na primeira linha. São obrigatórios ID, tarefa, entrada e resposta. A prévia valida o arquivo antes da importação. Reimportar registros idênticos não duplica itens; um mesmo ID com conteúdo diferente é rejeitado, sem alterações parciais.

Novos itens podem ser acrescentados na preparação, no treinamento ou durante a revisão da calibração. A importação fica pausada durante julgamentos ativos. Após iniciar a avaliação, abra um novo ciclo para ampliar a base.

## Operação do estudo

1. **Preparação:** cadastre os três perfis em Avaliadores. O pesquisador não ocupa automaticamente uma vaga. Se também quiser avaliar, cadastre para si um perfil de avaliador e gere o respectivo convite. Gere os convites e compartilhe cada um apenas com o respectivo participante. Importe os dados e configure limiar, tamanho da amostra, fração por avaliador e semente.
2. **Referências:** selecione exemplos da base, atribua notas e explique as decisões. O sistema não transforma rótulos anteriores em notas de referência. Recomenda-se cobrir as três categorias.
3. **Treinamento:** inicie a etapa. Os três avaliadores leem as referências e confirmam a conclusão da versão vigente em seus próprios acessos.
4. **Calibração:** o pesquisador inicia uma rodada. Todos recebem a mesma amostra estratificada por método, modelo e idioma. Após todas as notas, se qualquer item exceder o limiar, o pesquisador adjudica os casos. Eles entram nas referências, o treinamento é reiniciado e outra amostra inédita é sorteada. Se não houver excedências, o grupo fica calibrado.
5. **Avaliação:** o pesquisador inicia a distribuição da amostra reservada. Cada avaliador recebe aproximadamente a fração configurada. O sistema garante cobertura, evita atribuições duplicadas e equilibra carga e pares de sobreposição. A quantidade inicial por pessoa é arredondada para cima.
6. **Resolução:** itens com múltiplas notas acima do limiar recebem o terceiro avaliador. Se a discordância persistir, entram em Adjudicações. Itens com avaliação única são identificados como tal, sem afirmar concordância.
7. **Conclusão:** exporte resultados CSV, notas individuais CSV e backup JSON. Se necessário, abra um novo ciclo em Configuração, opcionalmente promovendo adjudicações da avaliação a referências. O ciclo anterior permanece no histórico.

**Papéis separados:** o acesso de pesquisador administra o estudo, define referências e adjudica; ele não confirma treinamento nem envia notas individuais. Se a mesma pessoa também for avaliador, utiliza um perfil próprio, com convite e sessão de avaliador, que recebe atribuições e tem exatamente o mesmo peso dos outros avaliadores. A adjudicação ocorre posteriormente, com justificativa própria, sem adicionar uma quarta nota ao cálculo ou alterar a discordância observada. É possível registrar uma interpretação diferente na justificativa da decisão. Para manter os dois acessos simultâneos, use perfis de navegador distintos ou uma janela privativa; no mesmo navegador, use **Trocar acesso**. A separação dos perfis não impede que o pesquisador, como administrador, consulte dados do estudo; recomenda-se concluir a avaliação independente antes de consultar os julgamentos alheios.

## Regras metodológicas implementadas

- Notas individuais inteiras: 0, 1 e 2, com justificativa / observação opcional, sem tamanho mínimo. A observação também é opcional para decisões numéricas do pesquisador; em casos inconclusivos, o motivo continua obrigatório (3 a 4.000 caracteres).
- **Sinalização do avaliador:** durante calibração e avaliação, o avaliador pode escolher “Inconclusivo / não consigo avaliar”, sem score e com observação obrigatória. Isso conclui sua atribuição e encaminha o item ao pesquisador, sem excluir o item automaticamente e sem converter a sinalização em zero. Na calibração, a revisão aguarda o fim da rodada; na avaliação, aguarda as respostas inicialmente atribuídas ao item. Não se solicita um terceiro avaliador para substituir essa sinalização: o pesquisador decide se atribui uma nota final ou confirma o inconclusivo. A discordância usa apenas as notas numéricas disponíveis e é não aferível quando há menos de duas. Sinalizações são preservadas no histórico e no CSV de avaliações individuais, com outcome `inconclusive` e score vazio.
- Para duas ou mais notas: `D = soma(|s_i - s_j|, i < j) / (n * (n - 1))`.
- Para menos de duas notas: discordância `null`, apresentada como não aferível.
- Excedência: `D > limiar`. Valores iguais ao limiar são aceitos.
- Durante **Treinamento**, o pesquisador pode ajustar apenas o limiar em **Configuração → Ajustar limiar durante o treinamento**, com justificativa obrigatória. Não é necessário reiniciar o ciclo nem repetir confirmações de treinamento. A alteração vale para as próximas avaliações, sem recalcular decisões de rodadas encerradas. Valores anterior e novo, motivo, pesquisador e momento ficam registrados no histórico e no backup. Durante calibração ou avaliação ativas, o ajuste continua bloqueado.
- Consolidação: mediana sem arredondamento; pode resultar em 0,5 ou 1,5. Uma nota isolada é sua própria mediana. Uma adjudicação substitui a mediana na nota final, preservando as notas originais.
- **Inconclusivo:** nas referências e adjudicações, o pesquisador pode decidir que o item não admite um score, com observação obrigatória (por exemplo, prompt incompleto, erro ou resposta truncada). A nota final fica vazia, sem usar zero ou a mediana. O caso encerra sua revisão, mas continua identificado como inconclusivo nos resultados, no CSV e no backup, com a observação. As notas individuais e a discordância observada são preservadas. Inconclusivos não viram exemplos de referência nem são selecionados em novas amostras, inclusive após abrir outro ciclo. Para corrigir os dados, importe a versão corrigida com novo ID. Uma calibração com casos inconclusivos precisa de outra rodada; se não houve mudança nos exemplos válidos, os treinamentos vigentes permanecem válidos. Nos cálculos de sucesso, esses itens devem ser contabilizados separadamente, sem classificá-los como falha ou sucesso.
- Amostragem proporcional por método, modelo e idioma, com maiores restos e desempate pseudoaleatório. Estratos raros podem ficar fora de amostras pequenas. A semente, o ID do ciclo, a rodada e as atribuições sorteadas são preservados no backup.
- **Separação entre amostras:** exemplos curados e todos os itens já usados na calibração são excluídos da amostra independente de avaliação daquele ciclo. As notas de calibração são exportadas separadamente no CSV de notas individuais. Isso reduz a mistura entre aprendizado e avaliação; é uma escolha explícita desta implementação.
- A calibração exige uma rodada completa sem excedências. Se não houver itens inéditos suficientes, o sistema pede mais dados; não recicla silenciosamente uma amostra já conhecida.
- Notas enviadas são imutáveis. Corrigir o protocolo exige um novo ciclo com histórico preservado. Solicitações de ciclos antigos são rejeitadas.

## Persistência e limites desta versão

Esta versão atende um estudo por implantação, com exatamente três perfis de avaliador e um perfil de pesquisador separado. A acumulação dos dois papéis por uma pessoa é opcional e exige acessos distintos. Convites duram 7 dias e são de uso único; sessões duram 30 dias. Gerar novo convite revoga os acessos anteriores do colega, permitindo recuperação em outro navegador.

Estudos criados na versão anterior são migrados ao serem carregados. Se o pesquisador já tinha confirmado treinamento ou recebido atribuições, seu histórico de avaliador passa para um perfil separado, com o sufixo “(avaliador)”. Notas, datas e atribuições são preservadas; referências e adjudicações continuam vinculadas ao pesquisador. Gere um convite para esse perfil para retomar as avaliações. Se não havia participação, nenhum perfil de avaliador é criado automaticamente. A migração fica persistida na próxima gravação do estudo.

O estado do estudo é serializado em partes de até 250 mil caracteres em D1. Cada atualização é uma transação que obtém uma revisão exclusiva antes de trocar as partes. O limite interno é 8 MB de estado total e 5.000 itens, com no máximo 5 MB por importação. Isso mantém esta implementação pequena e preserva a atomicidade dentro dos limites do D1; o tamanho do texto e o histórico podem atingir o limite antes da quantidade de itens. Para estudos maiores, a evolução prevista é normalizar itens, atribuições e notas em tabelas próprias.

O backup JSON inclui dados, referências, ciclos, notas e auditoria; não inclui chaves de acesso ou sessões. A restauração desse backup ainda não tem interface própria. Para recuperação operacional do banco publicado, use os recursos oficiais de [exportação do D1](https://developers.cloudflare.com/d1/best-practices/import-export-data/) e [Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/). Faça cópia dos resultados ao terminar cada ciclo.

## Verificação

```powershell
node --test test/*.test.mjs
node --check public/app.js
node node_modules/wrangler/bin/wrangler.js deploy --dry-run --outdir .local/worker-build
```

Os testes cobrem a métrica, mediana, distribuição, ciclos de calibração, avaliações adicionais, adjudicação, histórico, ocultação de dados na API, autorização, uso único de convites, revogação de sessões, proteção de origem, importação multilinha e transações concorrentes sobre SQLite.

Uma demonstração **sintética**, isolada dos dados reais, pode ser criada assim, em dois terminais:

```powershell
$env:PORT = '8788'
$env:DATA_DIR = '.local/qa'
$env:BOOTSTRAP_SECRET = 'local-hepic-qa-secret-with-at-least-32-characters'
node scripts/local.mjs
```

```powershell
node scripts/seed-qa.mjs
```

A chave acima é apenas da demonstração local. Nunca use essa chave em produção. As referências sintéticas não fazem parte do estudo real.

## Exportação de todos os itens

Em **Resultados → Todos os itens CSV**, o arquivo `hepic-results-AAAA-MM-DD.csv` inclui toda a base atual, com **uma linha por item e por ciclo**. Uma base de 152 itens em um único ciclo gera 152 registros, além do cabeçalho. Os ciclos arquivados aparecem em linhas separadas, identificados por `cycle`.

- `item_phase`: `reference` (exemplo de treinamento ou item inconclusivo na preparação de referências), `calibration`, `evaluation` ou `unused`. Quando há mais de um uso, a prioridade é avaliação, calibração, referência.
- `is_reference`, `is_calibration`, `is_evaluation`: identificam os usos sem perder sobreposições entre etapas; um item de calibração promovido a exemplo tem as duas primeiras marcas verdadeiras. `calibration_rounds` lista as rodadas.
- `status`, `n_ratings`, `disagreement`, `final_score`: descrevem a etapa indicada em `item_phase`. Referências têm a nota do pesquisador e zero avaliações individuais; itens não utilizados ou ainda pendentes não recebem nota final. `adjudicated` indica decisão posterior do pesquisador na calibração ou avaliação. `decision_phase` identifica a etapa consolidada, também para compatibilidade com exportações anteriores.
- `n_assigned` e `n_submitted`: totais de atribuições e respostas individuais do item no ciclo, considerando todas as etapas.
- `ratings_json`: atribuições individuais, incluindo pendências, fase, rodada, avaliador, nota, observação, versão de referência e data de envio. `calibration_history_json` preserva as rodadas, discordâncias e decisões; `requiresReview` representa o encaminhamento para revisão, inclusive por sinalização de inconclusivo.
- `reference_history_json`, `reference_score`, `reference_observation`: versões e decisões dos exemplos de treinamento. `researcher_decisions_json` preserva decisões da calibração, avaliação e registros de inconclusivo.

As primeiras 22 colunas da exportação anterior continuam presentes, seguidas das novas colunas de identificação e histórico. Para analisar somente a avaliação independente, filtre `item_phase = evaluation`. Para consultar todos os usos de um item, use as marcas de etapa e os históricos. O CSV de notas individuais continua disponível separadamente; o **Backup completo JSON** também preserva configurações, confirmações de treinamento, auditoria e demais dados administrativos.

Novos arquivamentos guardam a lista completa de itens do ciclo. Para ciclos arquivados antes dessa mudança, sem essa lista, a exportação inclui os itens identificáveis nas atribuições, referências e inconclusivos, sem inventar participação de itens importados posteriormente.

