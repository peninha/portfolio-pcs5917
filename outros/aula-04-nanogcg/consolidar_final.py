"""Prepara a consolidação sem duplicar resultados nem alterar avaliações."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from revisao import collect_review_rows


def final_identity(row):
    """Mesmos inputs, ambiente/configuração e resultados observados."""
    cfg, result = row["config"], row["result"]
    identity = {
        "model": row["model"], "revision": cfg.get("model_revision"),
        "dtype": cfg.get("dtype"), "gpu": cfg.get("gpu"), "versions": cfg.get("versions"),
        "case": cfg["case"], "optimization_messages": cfg["optimization_messages"],
        "config": cfg["config"], "max_new_tokens": cfg["max_new_tokens"],
        "baseline_input_ids": row["baseline_record"].get("input_ids"),
        "attack_input_ids": row["attack_record"].get("input_ids"),
        "baseline": row["baseline"], "best_string": row["best_string"], "attack": row["attack"],
        "best_loss": result["best_loss"],
        "baseline_truncated": row["baseline_truncated"], "attack_truncated": row["attack_truncated"],
    }
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def consolidate_rows(rows):
    groups, excluded = {}, []
    for row in rows:
        if row["status"] != "Concluído":
            excluded.append({k: row.get(k) for k in ("run_id", "batch_id", "model", "case_id", "status")})
            continue
        groups.setdefault(final_identity(row), []).append(row)
    records, audit = [], []
    for identity, equivalents in groups.items():
        equivalents = sorted(equivalents, key=lambda r: r["run_id"])
        canonical = equivalents[-1]
        cfg, result = canonical["config"], canonical["result"]
        parameters = cfg["config"]
        messages = cfg["case"]["messages"]
        source_reviews = [{"run_id": r["run_id"], "sem_sufixo": r["baseline_review"],
                           "com_sufixo": r["attack_review"], "notas_sem": r["baseline_notes"],
                           "notas_com": r["attack_notes"]} for r in equivalents]
        conflicting = any(len({r[key] for r in equivalents}) > 1
                          for key in ("baseline_review", "attack_review"))
        fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        separator = cfg.get("suffix_separator")
        if separator is None:
            before = messages[-1]["content"]
            optimized = cfg["optimization_messages"][-1]["content"]
            if optimized.startswith(before) and optimized.endswith("{optim_str}"):
                separator = optimized[len(before):-len("{optim_str}")]
        record = {
            "teste_id": fingerprint[:16], "caso": canonical["case_id"], "modelo": canonical["model"],
            "system": "\n\n".join(m["content"] for m in messages if m["role"] == "system"),
            "mensagem": "\n\n".join(m["content"] for m in messages if m["role"] == "user"),
            "target": canonical["target"], "melhor_sufixo": canonical["best_string"],
            "separador_repr": repr(separator) if separator is not None else "",
            "resposta_sem_sufixo": canonical["baseline"],
            "avaliacao_sem_sufixo": canonical["baseline_review"], "notas_sem_sufixo": canonical["baseline_notes"],
            "resposta_com_sufixo": canonical["attack"],
            "avaliacao_com_sufixo": canonical["attack_review"], "notas_com_sufixo": canonical["attack_notes"],
            "loss_minima": result["best_loss"], "tempo_otimizacao_s": result["seconds_optimization"],
            "tokens_sufixo_iniciais": result["suffix_initial_tokens"],
            "tokens_sufixo_finais": result["suffix_final_tokens"],
            "num_steps": parameters["num_steps"], "search_width": parameters["search_width"],
            "topk": parameters["topk"], "batch_size": parameters["batch_size"], "seed": parameters["seed"],
            "max_new_tokens": cfg["max_new_tokens"],
            "resposta_sem_truncada": canonical["baseline_truncated"],
            "resposta_com_truncada": canonical["attack_truncated"],
            "diagnostico_regra_sem": canonical["baseline_diagnostic"],
            "diagnostico_regra_com": canonical["attack_diagnostic"],
            "prompt_original": canonical["baseline_prompt"], "prompt_final": canonical["attack_prompt"],
            "revisao_modelo": cfg.get("model_revision"), "dtype": cfg.get("dtype"), "gpu": cfg.get("gpu"),
            "versoes_json": json.dumps(cfg.get("versions"), ensure_ascii=False, sort_keys=True),
            "gcg_config_json": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
            "run_id_representante": canonical["run_id"], "lote_representante": canonical["batch_id"],
            "execucoes_equivalentes": len(equivalents),
            "run_ids_origem_json": json.dumps([r["run_id"] for r in equivalents]),
            "avaliacoes_divergentes": conflicting,
            "avaliacoes_origem_json": json.dumps(source_reviews, ensure_ascii=False),
        }
        records.append(record)
        audit.append({"teste_id": record["teste_id"], "run_id_representante": canonical["run_id"],
                      "origens": source_reviews, "avaliacoes_divergentes": conflicting})
    records.sort(key=lambda r: (r["caso"], r["target"], r["modelo"], r["tokens_sufixo_iniciais"], r["seed"]))
    completed = sum(r["status"] == "Concluído" for r in rows)
    metadata = {"execucoes_concluidas": completed, "linhas_finais": len(records),
                "repeticoes_removidas": completed - len(records),
                "grupos_com_avaliacoes_divergentes": sum(r["avaliacoes_divergentes"] for r in records),
                "criterio": "Identidade de inputs, modelo/revisão, ambiente, configuração, sufixo, respostas e loss mínima. "
                            "Representante: execução mais recente, independentemente de sucesso. Avaliações antigas preservadas nas origens.",
                "excluidos_sem_resultado_final": excluded, "grupos": audit}
    return records, metadata


def prepare_final_export(results_dir, payload_path):
    records, metadata = consolidate_rows(collect_review_rows(results_dir))
    if not records:
        raise ValueError("Não há execuções concluídas para exportar.")
    payload_path = Path(payload_path)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"headers": list(records[0]), "rows": [[r[h] for h in records[0]] for r in records],
               "records": records, "metadata": metadata}
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def write_final_csv(results_dir, output):
    """Exportação CSV reproduzível, sem inferência ou dependências de planilha."""
    records, metadata = consolidate_rows(collect_review_rows(results_dir))
    if not records:
        raise ValueError("Não há execuções concluídas para exportar.")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (output.parent / "consolidacao-final.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return records, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", help="Prepara JSON intermediário em vez de gravar o CSV.")
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    if args.payload:
        payload = prepare_final_export(base / "resultados", args.payload)
        metadata = payload["metadata"]
    else:
        _, metadata = write_final_csv(base / "resultados", base / "resultados/resultados-finais.csv")
    print(json.dumps({k: v for k, v in metadata.items() if k != "grupos"}, ensure_ascii=False, indent=2))
