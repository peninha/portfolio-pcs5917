"""Executa a matriz pequena e reutiliza resultados compatíveis já concluídos."""
import gc
import json
from pathlib import Path
import torch
import experimento as e

for model_id in ["Qwen/Qwen2.5-0.5B-Instruct", "HuggingFaceTB/SmolLM2-135M-Instruct"]:
    model = tokenizer = None
    for case_id, units in [("V01", 8), ("V02", 8), ("V03", 8), ("V03", 16)]:
        saved = []
        for path in sorted((e.BASE / "resultados").glob("*/resultado.json")):
            config = json.loads((path.parent / "config.json").read_text(encoding="utf-8"))
            c = config["config"]
            expected = {"num_steps": 40, "optim_str_init": " ".join(["x"] * units),
                        "seed": 42, "search_width": 32, "topk": 32, "batch_size": 16,
                        "n_replace": 1, "buffer_size": 0, "use_mellowmax": False,
                        "use_prefix_cache": True, "filter_ids": True, "early_stop": False}
            if (config["model_id"] == model_id and config["case"] == e.prepare(case_id)
                    and all(c.get(k) == v for k, v in expected.items())
                    and config["max_new_tokens"] == 96):
                saved.append(path)
        if saved:
            print("Reutilizado:", model_id, case_id, units, saved[-1].parent.name, flush=True)
            continue
        if model is None:
            model, tokenizer = e.load_model(model_id)
        result = e.run_case(model, tokenizer, case_id, units, num_steps=40, seed=42)
        e.plot_result(result)
        import matplotlib.pyplot as plt
        plt.close("all")
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
