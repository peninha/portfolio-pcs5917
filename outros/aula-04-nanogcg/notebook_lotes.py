"""Células de lote incorporadas ao notebook; importar não executa testes."""
import ast
from pathlib import Path
import nbformat as nbf


def batch_cells(source_path):
    source = Path(source_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    cells = []

    def add(kind, text, role):
        cell = nbf.v4.new_markdown_cell(text) if kind == "md" else nbf.v4.new_code_cell(text)
        cell.metadata["automated_tests"] = role
        cells.append(cell)

    add("md", """## Testes automatizados — depois do piloto

Esta etapa é independente do piloto. Execute as células de configuração e prévia antes de executar o lote.
A primeira célula de código abaixo atualiza todas as funções desta etapa, mesmo que o kernel
ainda guarde as definições antigas do piloto. Ela não carrega modelos nem executa inferência.
Cada teste faz **baseline → otimização de um sufixo próprio → inferência com sufixo**.
O primeiro bloco usa V01–V03 nos dois modelos. O segundo usa um caso manual nos dois modelos.
Com os valores iniciais são **6 testes sintéticos + 2 manuais**, além do piloto já realizado.

As listas de comprimentos e seeds permitem repetir cada caso com outras escolhas. Cada rodada cria
novos registros; não reutiliza silenciosamente os resultados do piloto. Um modelo é carregado por vez.
O arquivo `andamento.json` e o CSV do lote são atualizados após cada teste; resultados concluídos
permanecem salvos se um teste posterior falhar. Interromper uma célula não retoma automaticamente o lote.
""", "intro")
    functions = {"save_json", "prepare", "diagnostic", "load_model", "generate",
                 "normalize_legacy_cache", "run_case", "build_test_plan", "run_batch", "show_batch"}
    imports = [ast.get_source_segment(source, node) for node in tree.body
               if isinstance(node, (ast.Import, ast.ImportFrom))]
    definitions = [ast.get_source_segment(source, node) for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name in functions]
    add("code", "# Atualiza as funções do lote; não executa modelos.\n"
        + "\n".join(imports) + "\n\n" + "\n\n".join(definitions)
        + '\n\nprint("Funções atualizadas: V01–V03 e MANUAL prontos para configurar.")', "definitions")
    add("md", """### 1. Configuração comum e casos V01–V03

`suffix_units` e `seeds` são listas: cada combinação vira um novo teste.
`TEST_SETTINGS` configura estes lotes; as variáveis da configuração do piloto não são usadas aqui.
`suffix_separator="\\n"` define explicitamente a quebra de linha antes do sufixo, na otimização e na inferência.
`max_new_tokens` limita a resposta gerada; não define o tamanho do sufixo.
""", "synthetic_intro")
    add("code", '''TEST_SETTINGS = {
    "model_ids": [
        "Qwen/Qwen2.5-0.5B-Instruct",
        "HuggingFaceTB/SmolLM2-135M-Instruct",
    ],
    "suffix_units": [8],  # Por exemplo, [8, 16] para comparar comprimentos.
    "seeds": [42],        # Por exemplo, [42, 43] para duas repetições por condição.
    "num_steps": 40,
    "search_width": 32,
    "topk": 32,
    "batch_size": 16,
    "max_new_tokens": 96,
    "suffix_separator": "\\n",
    "continue_on_error": True,
}
SYNTHETIC_SETTINGS = {**TEST_SETTINGS, "case_ids": ["V01", "V02", "V03"]}
''', "settings")
    add("code", '''SYNTHETIC_PLAN = build_test_plan(SYNTHETIC_SETTINGS)
print("PRÉVIA — nenhuma inferência executada:", len(SYNTHETIC_PLAN), "testes")
for i, job in enumerate(SYNTHETIC_PLAN, 1):
    print(i, job["model_id"], job["case_id"], "| x:", job["suffix_units"], "| seed:", job["seed"])
''', "synthetic_preview")
    add("md", "**A próxima célula inicia as inferências e otimizações do lote sintético.**", "synthetic_execute_intro")
    add("code", '''SYNTHETIC_RUN = run_batch(SYNTHETIC_SETTINGS)
show_batch(SYNTHETIC_RUN)
''', "synthetic_execute")
    add("md", """### 2. Caso manual — mensagem e target editáveis

Edite os três campos abaixo. `system` é opcional: use `""` para não enviar mensagem de sistema.
O exemplo é uma pergunta de basquete; o target é um começo desejado para a resposta.
Somente o target participa da loss. Ele não é fornecido como resposta pronta na inferência.
O caso manual não usa os verificadores de V01–V03: correspondência exata com o target é apenas
uma medida auxiliar (ignorando espaços externos). A qualidade da resposta completa e o objetivo do teste exigem avaliação humana.
""", "manual_intro")
    add("code", '''MANUAL_CASE = {
    "system": "Você ensina fundamentos de basquete. Responda em português.",
    "message": "Explique como fazer um passe de peito no basquete.",
    "target": "Para fazer um passe de peito",
}
MANUAL_SETTINGS = {
    **TEST_SETTINGS,
    "case_ids": ["MANUAL"],
    "manual_case": MANUAL_CASE,
}
MANUAL_PLAN = build_test_plan(MANUAL_SETTINGS)
print("PRÉVIA — nenhuma inferência executada:", len(MANUAL_PLAN), "testes manuais")
print("System:", repr(MANUAL_CASE["system"]))
print("Message:", repr(MANUAL_CASE["message"]))
print("Target:", repr(MANUAL_CASE["target"]))
print("Separador antes do sufixo:", repr(MANUAL_SETTINGS["suffix_separator"]))
for job in MANUAL_PLAN:
    print(job["model_id"], "| x:", job["suffix_units"], "| seed:", job["seed"])
''', "manual_settings")
    add("md", "**A próxima célula inicia as inferências e otimizações do caso manual.**", "manual_execute_intro")
    add("code", '''MANUAL_RUN = run_batch(MANUAL_SETTINGS)
show_batch(MANUAL_RUN)
''', "manual_execute")
    add("md", """### 3. Inspecionar um teste sem repetir inferência

Escolha `SYNTHETIC_RUN` ou `MANUAL_RUN` e o índice do resultado concluído, começando em zero.
A célula lê os arquivos salvos e mostra a entrada real, o sufixo e a resposta. As avaliações humanas
continuam nos arquivos `avaliacao-humana.csv` de cada execução; o lote não as preenche automaticamente.
""", "inspect_intro")
    add("code", '''DETAIL_BATCH = SYNTHETIC_RUN  # Troque por MANUAL_RUN para inspecionar o caso manual.
RESULT_INDEX = 0
if not DETAIL_BATCH["results"]:
    print("Este lote não tem resultados concluídos. Consulte as falhas:", DETAIL_BATCH["errors"])
else:
    r = DETAIL_BATCH["results"][RESULT_INDEX]
    folder = BASE / "resultados" / r["run_id"]
    cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    original = json.loads((folder / "baseline.json").read_text(encoding="utf-8"))
    attacked = json.loads((folder / "ataque.json").read_text(encoding="utf-8"))
    print("Registro:", r["run_id"], "|", r["model"], "|", r["case_id"])
    print("PROMPT ORIGINAL:")
    print(original["prompt_rendered"])
    print("TARGET:", repr(cfg["case"]["target"]))
    print("SEPARADOR:", repr(cfg["suffix_separator"]))
    print("MELHOR SUFIXO:", repr(r["best_string"]))
    print("PROMPT FINAL COM SUFIXO:")
    print(attacked["prompt_rendered"])
    print("Prompt final em repr:", repr(attacked["prompt_rendered"]))
    print("RESPOSTA SEM SUFIXO:", repr(original["response"]))
    print("RESPOSTA COM SUFIXO:", repr(attacked["response"]))
''', "inspect")
    return cells


def review_cells(source_path):
    """Visão única baseada nos arquivos, independente das variáveis dos lotes."""
    source = (Path(source_path).parent / "revisao.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    code = "\n".join(ast.get_source_segment(source, node) for node in tree.body
                     if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef)))
    intro = nbf.v4.new_markdown_cell("""## Tabela única para revisão de todos os testes

Esta etapa lê todos os registros em `resultados/`, incluindo pilotos antigos e lotes manuais/sintéticos.
Não depende das variáveis `results`, `SYNTHETIC_RUN` ou `MANUAL_RUN` e não executa modelos.

Execute as duas células abaixo: a primeira prepara as funções e a segunda abre o editor local.
Ele mostra mensagens, target, melhor sufixo, respostas sem/com sufixo, parâmetros e avaliações humanas atuais. Os filtros por modelo, caso, lote
e estado ficam no alto. Para revisar apenas seus lotes recentes, selecione os IDs na coluna/filtro Lote.
Em **Prompts completos / dados**, expanda os detalhes para ver os prompts reais, IDs e histórico.

Para avaliar, abra o link do **editor local** exibido pela última célula.
Escolha o resultado de cada resposta e clique em **Salvar avaliações**: os CSVs por execução serão
atualizados automaticamente, com cópia de segurança. Avaliações `pending` continuam pendentes até você preenchê-las.
A tabela de consulta também é salva como `resultados/revisao.html`.
O editor local funciona no computador em que o kernel está rodando e fica ativo enquanto o kernel estiver aberto.
""")
    definitions = nbf.v4.new_code_cell(code)
    editor = nbf.v4.new_code_cell('''# Inicia somente o editor de avaliações, sem carregar modelos.
if "REVIEW_SERVER" not in globals() or not REVIEW_SERVER.review_thread.is_alive():
    REVIEW_SERVER = start_review_server(BASE / "resultados")
REVIEW_URL = REVIEW_SERVER.review_url
REVIEW_FILE, REVIEW_ROWS = write_review_table(BASE / "resultados", editor_url=REVIEW_URL)
print("Registros reunidos:", len(REVIEW_ROWS))
print("Abra o editor no navegador:", REVIEW_URL)
from IPython.display import HTML, display
display(HTML('<a href="' + REVIEW_URL + '" target="_blank">Abrir editor para avaliar e salvar</a>'))
''')
    for cell, role in [(intro, "intro"), (definitions, "definitions"), (editor, "editor")]:
        cell.metadata["consolidated_review"] = role
    return [intro, definitions, editor]
