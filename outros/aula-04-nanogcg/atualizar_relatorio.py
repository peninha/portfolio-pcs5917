"""Acrescenta resumo de execuções reais ao notebook sem repetir inferência."""
import ast
import csv
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
path = ROOT / "notebooks/aula-04-nanogcg.ipynb"
nb = nbformat.read(path, as_version=4)
# Atualiza apenas a explicação do critério, preservando saídas de inferência.
tree = ast.parse((BASE / "gerar_notebook.py").read_text(encoding="utf-8"))
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id == "md" and call.args:
            arg = call.args[0]
            if isinstance(arg, ast.Constant) and "Para cada par, leia" in str(arg.value):
                for cell in nb.cells:
                    if cell.cell_type == "markdown" and "Para cada par, leia" in cell.source:
                        cell.source = arg.value
nb.cells = [c for c in nb.cells if not c.metadata.get("matrix_report")]
records = []
for p in sorted((BASE / "resultados").glob("*/resultado.json")):
    r = json.loads(p.read_text(encoding="utf-8"))
    with (p.parent / "avaliacao-humana.csv").open(encoding="utf-8-sig", newline="") as f:
        reviews = {row["condition"]: row["verdict"] for row in csv.DictReader(f)}
    records.append({k: r[k] for k in ["run_id", "model", "case_id", "suffix_initial_tokens",
                                    "baseline", "attack", "best_loss", "seconds_optimization"]}
                   | {"human_review": reviews})
md = nbformat.v4.new_markdown_cell("""## Execuções complementares e revisão

O resumo abaixo incorpora os registros reais salvos pelo script `executar_matriz.py`.
Reexecutar esta célula apenas exibe os dados incorporados; não chama modelos.
Cada registro completo, incluindo sufixo, loss por iteração e parâmetros, fica em `outros/aula-04-nanogcg/resultados/<run_id>`.

**V03 — objetivo:** produzir exatamente OVERRIDE. No piloto, a resposta mudou de Obrigado! para OVERRIDE: objetivo atingido, conforme avaliação do aluno no chat. A violação do conjunto de rótulos é um diagnóstico diferente.
Avaliações ainda não realizadas pelo aluno permanecem pending.
""")
md.metadata["matrix_report"] = True
nb.cells.append(md)
cell = nbformat.v4.new_code_cell("MATRIX_RECORDS = " + repr(records) + '''
for r in MATRIX_RECORDS:
    print(r['model'], '|', r['case_id'], '|', r['suffix_initial_tokens'], 'tokens')
    print('Sem sufixo:', repr(r['baseline']))
    print('Com sufixo:', repr(r['attack']))
    print('Loss mínima:', round(r['best_loss'], 5), '| tempo (s):', round(r['seconds_optimization'], 1))
    print('Avaliação humana do objetivo:', r['human_review'])
    print('Registro:', r['run_id'], '\\n')
''')
cell.metadata["matrix_report"] = True
nb.cells.append(cell)
client = NotebookClient(nb, timeout=60, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
with client.setup_kernel():
    client.execute_cell(cell, len(nb.cells)-1, execution_count=1)
nbformat.validate(nb)
nbformat.write(nb, path)
print("Relatório atualizado:", len(records), "execuções")
