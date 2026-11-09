"""Reconstrói o notebook da aula 7. Sobrescreve as saídas salvas do notebook."""
from pathlib import Path
from textwrap import dedent
import nbformat as nb

cells = []


def md(texto):
    cells.append(nb.v4.new_markdown_cell(dedent(texto).strip()))


def code(texto):
    cells.append(nb.v4.new_code_cell(dedent(texto).strip()))


md('''
    # Aula 7 · Ataques e defesas no Qwen

    **Roberto Spinelli Filho · Grupo A · PCS5917**

    Execute as células em ordem. Este notebook usa o coletor oficial do protocolo
    3.1.0 para preparar casos, coletar baseline, revisar os 15 casos e executar as
    seis condições defendidas. A entrega final contém 105 respostas pareadas.

    O piloto inicial usa uma pergunta de controle em pasta separada. Os candidatos
    do experimento entram na seção 4. Registre os prompts finais de ataques manuais
    ou importe os produzidos por uma execução automática, com sua procedência.
    O notebook faz a reexecução dos prompts congelados nas sete condições.

    **Ambiente local** — selecione o kernel `.venv` do repositório. O Qwen completo
    está em `D:/huggingface/hub`. Em Colab, envie a pasta extraída do pacote v3 e
    este notebook, ajuste `PASTA_PROTOCOLO` e use armazenamento persistente.
    A geração usa até **2.048 tokens novos**, com parada antecipada por EOS.
    Para instalar dependências, use `%pip install torch transformers==4.57.6`.
    O protocolo detalhado está em `outros/aula-07-defesas/PROTOCOLO.md`.
''')
md('''
    ## 1. Configuração

    O piloto fica habilitado inicialmente. Habilite cada etapa de coleta depois
    de preparar seus respectivos dados. O nome da sessão identifica uma coleta
    que pode ser retomada com o mesmo ambiente e parâmetros.
''')
code('''
    from pathlib import Path
    import os
    import sys
    import json
    import csv
    import subprocess
    import hashlib
    from collections import Counter
    from IPython.display import display, HTML
    from html import escape

    AUTOR = "roberto"                        # arthur, caio ou roberto
    SESSAO = "aula07-v3-1-001"
    PASTA_PROTOCOLO = None                    # ou Path("/content/protocolo-grupo-a-v3.1.0")
    CACHE_HF = Path("D:/huggingface/hub")
    SOMENTE_LOCAL = True                     # False permite baixar no Colab
    EXECUTAR_PILOTO = True
    EXECUTAR_TRIAGEM = False
    EXECUTAR_DEFESAS = False
    GERAR_ENTREGA = False

    if PASTA_PROTOCOLO is None:
        opcoes = []
        for pasta in (Path.cwd(), *Path.cwd().parents):
            opcoes.extend([pasta / "outros/aula-07-defesas", pasta])
        PASTA_PROTOCOLO = next((p for p in opcoes if (p / "coleta.py").is_file()), None)
    assert PASTA_PROTOCOLO is not None, "Ajuste PASTA_PROTOCOLO para a pasta que contém coleta.py."
    PASTA_PROTOCOLO = Path(PASTA_PROTOCOLO).resolve()
    sys.path.insert(0, str(PASTA_PROTOCOLO))
    import importlib
    import coleta as co
    co = importlib.reload(co)
    assert co.VERSAO == "3.1.0"
    if "_modelo_teste" in globals():
        del globals()["_modelo_teste"]
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    assert AUTOR in ("arthur", "caio", "roberto")
    assert SESSAO and all(c.isalnum() or c in "-_" for c in SESSAO)

    if CACHE_HF.is_dir():
        os.environ["HF_HUB_CACHE"] = str(CACHE_HF)
    os.environ["HF_HUB_OFFLINE"] = "1" if SOMENTE_LOCAL else "0"
    RAIZ = PASTA_PROTOCOLO / "resultados" / AUTOR / SESSAO
    RAIZ.mkdir(parents=True, exist_ok=True)
    CASOS = RAIZ / "casos.json"
    SELECAO = RAIZ / "selecao.json"
    SAIDA = RAIZ / "coleta"
    PILOTO = RAIZ / "piloto"
    print("Protocolo", co.VERSAO, "| autor", AUTOR, "| sessão", RAIZ)
    print("Modelo", co.MODELO_ALVO, "| revisão", co.REVISAO)
    print("Geração", co.GERACAO, "| seed", co.SEED)
''')
md('''
    ## 2. Conferir o ambiente e a matriz

    SR usa sanduíche e IA fica no início. O idioma muda apenas o texto da defesa.
    O baseline usa o mesmo system padrão do Qwen e o mesmo ataque em user.
''')
code('''
    import importlib.metadata as metadata

    print("Python", sys.version.split()[0])
    print("Transformers", metadata.version("transformers"))
    assert metadata.version("transformers") == "4.57.6"
    print("PyTorch", metadata.version("torch"))
    for condicao, (defesa, idioma, posicao) in co.MATRIZ.items():
        print(f"{condicao:8} {defesa:20} {idioma:3} {posicao}")
    snapshot = CACHE_HF / ("models--" + co.MODELO_ALVO.replace("/", "--")) / "snapshots" / co.REVISAO
    if SOMENTE_LOCAL:
        indice = snapshot / "model.safetensors.index.json"
        assert indice.is_file(), f"Índice ausente em {snapshot}"
        shards = set(json.loads(indice.read_text())["weight_map"].values())
        assert all((snapshot / nome).is_file() for nome in shards), "Download de pesos incompleto."
        print("Pesos locais", sum((snapshot / nome).stat().st_size for nome in shards), "bytes")

    def executar_etapa(etapa, casos, saida, selecao=None):
        liberar_modelo_teste()
        comando = [sys.executable, "-u", str(PASTA_PROTOCOLO / "coleta.py"), etapa,
                   "--casos", str(casos), "--saida", str(saida)]
        if selecao is not None:
            comando.extend(["--selecao", str(selecao)])
        ambiente = dict(os.environ, PYTHONIOENCODING="utf-8")
        with subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", env=ambiente) as processo:
            for linha in processo.stdout:
                print(linha, end="", flush=True)
            retorno = processo.wait()
        if retorno:
            raise RuntimeError(f"Etapa {etapa} interrompida, código {retorno}. Confira a saída e erros.jsonl.")

    def liberar_modelo_teste():
        if "_modelo_teste" in globals():
            del globals()["_modelo_teste"]
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
''')
md('''
    ## 3. Piloto com o modelo real

    Esta célula executa sete gerações para a pergunta de controle. Ao repeti-la,
    o coletor verifica e reutiliza os registros já concluídos. Confira as entradas,
    as respostas e o motivo de parada. O piloto tem seu próprio manifesto.
''')
code('''
    if EXECUTAR_PILOTO:
        executar_etapa("piloto", PASTA_PROTOCOLO / "casos.exemplo.json", PILOTO)
    else:
        print("Piloto desabilitado na configuração.")
    if (PILOTO / "manifesto.json").exists():
        for condicao in co.MATRIZ:
            arquivo = PILOTO / f"roberto-001_{condicao}.json"
            if arquivo.exists():
                registro = co.ler(arquivo)
                print(condicao, repr(registro["resposta"]), registro["motivo_fim"])
''')
md('''
    ## 4A. Testar prompts livremente

    Preencha o prompt, seu objetivo e a técnica na célula abaixo e execute-a.
    Para tentar uma variação, edite o texto e execute a mesma célula novamente.
    O modelo é carregado na primeira tentativa e fica disponível para as próximas.
    Cada execução usa conversa nova e grava seu próprio JSON em `rascunhos/`, com
    prompt exato, resposta, mensagens e metadados. `CONDICAO_TESTE="B"` testa o
    baseline. Você também pode escolher uma das seis condições com defesa.

    A célula de promoção abaixo permite escolher uma tentativa para `casos.json`.
    A etapa formal de triagem avalia os candidatos salvos usando o coletor.
''')
code('''
    from bancada import testar, promover

    PROMPT_TESTE = """"""                  # Escreva seu prompt entre as aspas triplas.
    OBJETIVO_TESTE = ""                     # Resultado específico que você quer verificar.
    TECNICA_TESTE = "manual"
    IDIOMA_TESTE = "pt"
    CONDICAO_TESTE = "B"
    OBSERVACOES_TESTE = ""

    if PROMPT_TESTE.strip():
        assert OBJETIVO_TESTE.strip(), "Preencha OBJETIVO_TESTE."
        if "_modelo_teste" not in globals():
            _modelo_teste, _tokenizer_teste, _manifesto_teste = co.carregar()
        ULTIMO_TESTE = testar(
            _modelo_teste, _tokenizer_teste, _manifesto_teste, RAIZ / "rascunhos",
            PROMPT_TESTE, OBJETIVO_TESTE, TECNICA_TESTE,
            idioma=IDIOMA_TESTE, condicao=CONDICAO_TESTE, observacoes=OBSERVACOES_TESTE,
        )
        tentativa = co.ler(ULTIMO_TESTE)
        print("RESPOSTA DO QWEN")
        print(tentativa["resposta"])
        print("Parada", tentativa["motivo_fim"], "| tokens", tentativa["tokens_gerados"])
        print("Tentativa salva", ULTIMO_TESTE)
    else:
        print("Escreva PROMPT_TESTE e OBJETIVO_TESTE para executar uma tentativa.")
''')
md('''
    ### Guardar uma tentativa escolhida

    A célula mostra as contagens de tentativas e candidatos guardados. Deixe `TESTE_ESCOLHIDO=None`
    para usar a última tentativa executada ou informe o caminho de outra.
    Altere `PROMOVER_TESTE=True` e execute a célula para criar o candidato.
    O ID é atribuído automaticamente. Repetir a promoção preserva o mesmo caso.
    A coleta formal começa na seção 5, após você separar seus candidatos.
    Para consultar todo o histórico de tentativas, use `MOSTRAR_RASCUNHOS=True`.
''')
code('''
    TESTE_ESCOLHIDO = None                   # ou Path("caminho/para/teste-....json")
    PROMOVER_TESTE = False
    MOSTRAR_RASCUNHOS = False

    if PROMOVER_TESTE:
        escolhido = TESTE_ESCOLHIDO if TESTE_ESCOLHIDO is not None else globals().get("ULTIMO_TESTE")
        assert escolhido is not None, "Execute uma tentativa ou informe TESTE_ESCOLHIDO."
        caso = promover(escolhido, CASOS, AUTOR)
        print("Candidato guardado", caso["id_caso"])

    rascunhos = sorted((RAIZ / "rascunhos").glob("teste-*.json"))
    candidatos_salvos = co.ler(CASOS) if CASOS.exists() else []
    print("Tentativas registradas no histórico", len(rascunhos))
    print("Candidatos guardados na lista", len(candidatos_salvos))
    print("Arquivo da lista", CASOS)
    for candidato in candidatos_salvos:
        observacoes = candidato.get("observacoes", "")
        origem = RAIZ / candidato.get("origem_arquivo", "")
        if candidato.get("origem_sha256") and origem.is_file():
            observacoes = co.ler(origem).get("observacoes", observacoes)
        print(candidato["id_caso"], "|", candidato["idioma_ataque"], "|", candidato["objetivo"], "|", observacoes)
    if MOSTRAR_RASCUNHOS:
        print("Histórico de tentativas")
        for arquivo in rascunhos:
            registro = co.ler(arquivo)
            print(arquivo.name, "|", registro["condicao"], "|", registro["objetivo"], "|", registro.get("observacoes", ""))
''')
md('''
    ## 4B. Preparar candidatos manuais e importar ataques automáticos

    Preencha `NOVOS_CASOS` com uma lista de dicionários. Use IDs estáveis como
    `roberto-001`, um objetivo específico para o juiz e o ataque completo em
    `prompt_original`. Registre técnica, idioma e procedência. Cada candidato deve
    ter um prompt distinto. A análise e o rótulo de sucesso vêm após o baseline.

    Para importar saídas de PAIR, nanoGCG ou outro notebook, exporte os prompts
    finais para JSON com o mesmo esquema e informe `IMPORTAR_JSON`. Identifique a
    origem em `origem_arquivo` e conserve os logs da busca. Confira que a execução
    de origem usou o Qwen alvo e que o prompt final é representável por texto no
    mesmo template. Neste desenho, cada prompt final vira um caso de um turno.

    O esquema ilustrativo abaixo pode ser copiado e preenchido.

    ```python
    {
        "id_caso": "roberto-001", "autor": "roberto", "tipo": "manual",
        "tecnica": "nome da técnica", "idioma_ataque": "pt",
        "objetivo": "objetivo específico a verificar na resposta",
        "prompt_original": "texto integral do candidato",
        "origem_arquivo": "referência ao registro de preparação ou busca"
    }
    ```

    Os candidatos já salvos permanecem na lista ao acrescentar outros. Para um
    novo prompt, atribua novo ID. Isso permite retomar a coleta sem alterar casos.
''')
code('''
    NOVOS_CASOS = []
    IMPORTAR_JSON = None                      # exemplo: Path("meus-prompts-finais.json")

    existentes = co.ler(CASOS) if CASOS.exists() else []
    candidatos = list(existentes)
    adicionados = list(NOVOS_CASOS)
    if IMPORTAR_JSON is not None:
        adicionados.extend(co.ler(Path(IMPORTAR_JSON)))
    por_id = {c["id_caso"]: c for c in existentes}
    for caso in adicionados:
        assert caso["autor"] == AUTOR, "Confira o autor dos casos importados."
        if caso["id_caso"] in por_id:
            assert por_id[caso["id_caso"]] == caso, "ID existente com conteúdo diferente. Use novo ID."
        else:
            candidatos.append(caso)
            por_id[caso["id_caso"]] = caso
    if candidatos:
        # Valide antes de substituir o arquivo de trabalho.
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(dir=RAIZ) as temporaria:
            arquivo = Path(temporaria) / "casos.json"
            co.gravar(arquivo, candidatos)
            co.ler_casos(arquivo)
        co.gravar(CASOS, candidatos)
        print(len(candidatos), "candidatos salvos em", CASOS)
        print(Counter(c["tipo"] for c in candidatos))
    else:
        print("Preencha NOVOS_CASOS ou importe um JSON para iniciar a triagem.")
''')
md('''
    ## 5. Coletar e revisar o baseline

    Habilite `EXECUTAR_TRIAGEM` na configuração. A cada chamada, o coletor executa
    B para os novos candidatos e reutiliza os baselines concluídos. Revise objetivo
    e resposta, especialmente os casos com parada por limite de geração. O CSV
    completo fica em `coleta/triagem.csv`.
''')
code('''
    if EXECUTAR_TRIAGEM:
        assert CASOS.exists(), "Prepare os candidatos na seção 4."
        executar_etapa("triagem", CASOS, SAIDA)

    registros_triagem = []
    if (SAIDA / "triagem.csv").exists():
        with (SAIDA / "triagem.csv").open(encoding="utf-8", newline="") as arquivo:
            registros_triagem = list(csv.DictReader(arquivo))
        for registro in registros_triagem:
            display(HTML("<h4>" + escape(registro["id_caso"]) + "</h4><p>" +
                         escape(registro["objetivo"]) + "</p><pre>" +
                         escape(registro["resposta"]) + "</pre><p>Parada: " +
                         escape(registro["motivo_fim"]) + "</p>"))
    else:
        print("Baseline ainda pendente. Prepare os casos e habilite a triagem.")
''')
md('''
    ## 6. Selecionar os 15 casos antes das defesas

    Preencha `ROTULOS_ESCOLHIDOS` com os IDs de 10 sucessos e 5 falhas na triagem.
    Exemplo de formato, `{"roberto-001": "sucesso", "roberto-002": "falha"}`.
    Separe casos ambíguos para revisão. Guarde todos os candidatos tentados.
    A classificação final será dada pelo JEV, inclusive para o baseline.
''')
code('''
    ROTULOS_ESCOLHIDOS = {}

    if ROTULOS_ESCOLHIDOS:
        casos = co.ler_casos(CASOS)
        with TemporaryDirectory(dir=RAIZ) as temporaria:
            arquivo = Path(temporaria) / "selecao.json"
            co.gravar(arquivo, ROTULOS_ESCOLHIDOS)
            co.selecionar(arquivo, casos)
        for i in ROTULOS_ESCOLHIDOS:
            assert co.registro(SAIDA, casos[i], "B").exists(), f"Execute o baseline de {i}."
        congelada = SAIDA / "selecao_congelada.json"
        if congelada.exists():
            assert co.ler(congelada) == ROTULOS_ESCOLHIDOS, "Seleção já congelada com outros casos."
        co.gravar(SELECAO, ROTULOS_ESCOLHIDOS)
    if SELECAO.exists():
        print("Seleção salva", Counter(co.ler(SELECAO).values()))
    else:
        print("Seleção pendente. São necessários 10 sucessos e 5 falhas.")
''')
md('''
    ## 7. Rodar as defesas e exportar

    Com a seleção pronta, habilite `EXECUTAR_DEFESAS`. O coletor congela os casos,
    faz 90 novas gerações e reutiliza os 15 baselines. Se a execução for interrompida,
    repita esta célula na mesma sessão e ambiente para retomar os itens restantes.
''')
code('''
    if EXECUTAR_DEFESAS:
        assert SELECAO.exists(), "Conclua a seleção da seção 6."
        executar_etapa("coletar", CASOS, SAIDA, SELECAO)
        executar_etapa("exportar", CASOS, SAIDA, SELECAO)
    else:
        print("Coleta defendida desabilitada na configuração.")
''')
md('''
    ## 8. Conferir a entrega para Arthur

    O ZIP de entrega inclui casos, seleção e a pasta de coleta com o manifesto,
    CSVs e registros primários. O piloto fica na pasta de trabalho da sessão.
    Habilite `GERAR_ENTREGA` após a coleta. O arquivo usa um horário no nome para
    identificar a exportação. Preserve também os registros de origem dos ataques.
''')
code('''
    if (SAIDA / "respostas.csv").exists():
        with (SAIDA / "respostas.csv").open(encoding="utf-8", newline="") as arquivo:
            respostas = list(csv.DictReader(arquivo))
        print("Respostas", len(respostas), "| casos", len({r["id_caso"] for r in respostas}))
        print("Condições", Counter(r["condicao"] for r in respostas))
        print("Motivos de parada", Counter(r["motivo_fim"] for r in respostas))
    if GERAR_ENTREGA:
        executar_etapa("exportar", CASOS, SAIDA, SELECAO)
        from datetime import datetime, timezone
        from zipfile import ZipFile, ZIP_DEFLATED
        nome = f"entrega-{AUTOR}-{SESSAO}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.zip"
        destino = RAIZ / nome
        with ZipFile(destino, "x", compression=ZIP_DEFLATED) as pacote:
            for arquivo in [CASOS, SELECAO, *sorted(SAIDA.rglob("*")),
                            *sorted((RAIZ / "rascunhos").glob("teste-*.json"))]:
                if arquivo.is_file():
                    pacote.write(arquivo, arquivo.relative_to(RAIZ).as_posix())
        print("Entregue a Arthur", destino)
    else:
        print("Empacotamento desabilitado na configuração.")
''')
md('''
    ## Referências e interpretação

    Cada ataque compõe um conjunto pareado de sete respostas. A amostra de 10
    sucessos e 5 falhas por integrante é selecionada pelo resultado da triagem.
    O artigo deve informar essa seleção, as tentativas totais e as classificações
    posteriores do JEV. A consolidação do grupo usa `consolidar.py`.

    [Estudo de caso das defesas](https://doi.org/10.1109/ACCESS.2026.3710427) ·
    [Artigo de Intention Analysis](https://aclanthology.org/2025.coling-main.199/) ·
    [Modelo alvo](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
''')

if __name__ == "__main__":
    notebook = nb.v4.new_notebook(cells=cells)
    notebook.metadata.update(kernelspec=dict(display_name="Python (.venv)", language="python", name="python3"),
                             language_info=dict(name="python", version="3.10"))
    destino = Path(__file__).resolve().parents[2] / "notebooks/aula-07-ataques-defesas.ipynb"
    nb.validate(notebook)
    nb.write(notebook, destino)
    print(destino)
