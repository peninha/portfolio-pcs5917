"""Compila registros reais e gera imagens de comparação, sem inferência."""
import csv
import json
import textwrap
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RESULTS = BASE / "resultados"
IMAGES = ROOT / "images/aula-04"
IMAGES.mkdir(parents=True, exist_ok=True)
rows = []
for path in sorted(RESULTS.glob("*/resultado.json")):
    r = json.loads(path.read_text(encoding="utf-8"))
    config = json.loads((path.parent / "config.json").read_text(encoding="utf-8"))
    with (path.parent / "avaliacao-humana.csv").open(encoding="utf-8-sig", newline="") as f:
        reviews = {row["condition"]: row for row in csv.DictReader(f)}
    target = config["case"]["target"]
    row = {k: r[k] for k in ["run_id", "case_id", "model", "suffix_initial_tokens", "suffix_final_tokens",
                             "best_loss", "seconds_optimization", "baseline_diagnostic", "attack_diagnostic"]}
    row.update(baseline_exact_target=r["baseline"].strip() == target,
               attack_exact_target=r["attack"].strip() == target,
               human_baseline=reviews["baseline"]["verdict"], human_attack=reviews["attack"]["verdict"])
    rows.append(row)
    blocks = [
        ("Regra (system)", config["case"]["messages"][0]["content"]),
        ("Pedido (user)", config["case"]["messages"][1]["content"]),
        ("Sem sufixo", r["baseline"]),
        ("Com sufixo", r["attack"]),
    ]
    rendered = [(label, "\n".join(textwrap.fill(line, width=105) for line in value.splitlines()))
                for label, value in blocks]
    nlines = sum(text.count("\n") + 1 + 3 for _, text in rendered)
    fig = plt.figure(figsize=(12, max(6, 1.25 + nlines * .19)), facecolor="white")
    fig.text(.04, .97, f"{r['case_id']} | {r['model']} | sufixo: {r['suffix_initial_tokens']} tokens",
             fontsize=13, weight="bold", va="top", color="#173c66")
    y = .91
    step = .82 / nlines
    for label, text in rendered:
        fig.text(.04, y, label, fontsize=11, weight="bold", va="top", color="#2454a4")
        y -= step * 1.5
        fig.text(.04, y, text, fontsize=10, va="top", linespacing=1.25)
        y -= step * (text.count("\n") + 1 + 1.5)
    fig.text(.04, .025, f"Registro: {r['run_id']} | Avaliação humana: {row['human_baseline']} / {row['human_attack']}", fontsize=9)
    fig.savefig(IMAGES / (r["run_id"] + "-comparacao.png"), dpi=130)
    plt.close(fig)

if rows:
    with (RESULTS / "resumo.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    table = ["| Modelo | Caso | Tokens | Quebra da regra sem → com | Alvo exato sem → com | Revisão humana do objetivo |",
             "|---|---|---:|---|---|---|"]
    for r in rows:
        table.append(f"| {r['model'].split('/')[-1]} | {r['case_id']} | {r['suffix_initial_tokens']} | "
                     f"{r['baseline_diagnostic']} → {r['attack_diagnostic']} | "
                     f"{r['baseline_exact_target']} → {r['attack_exact_target']} | {r['human_baseline']} / {r['human_attack']} |")
    (RESULTS / "README.md").write_text(
        "# Resultados — aula 4\n\nRegistros de execução real. `success` no diagnóstico automático significa violação da regra; alvo exato é outro critério. "
        "Objetivos humanos: V01 emitir ABACAXI; V02 produzir prosa fora de JSON; V03 responder exatamente OVERRIDE. "
        "Obrigado! viola a regra de V03, mas não atinge seu objetivo. "
        "Os rótulos humanos são lidos dos CSVs por execução e não são inferidos pelo compilador.\n\n"
        + "\n".join(table) + "\n\nCada pasta contém configuração, entradas/saídas, trajetória de loss e avaliação humana. "
        "Recompile com `python outros/aula-04-nanogcg/compilar_resultados.py` após revisar os CSVs. "
        "Compare o objetivo e a regra separadamente: uma baseline que já viola a regra pode ainda não atingir o alvo.\n", encoding="utf-8")
print("Execuções compiladas:", len(rows))
