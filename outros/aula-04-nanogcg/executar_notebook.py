"""Executa e persiste o notebook, inclusive saídas de eventual erro."""
import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "notebooks/aula-04-nanogcg.ipynb"
overlay = ROOT / ".cache/aula04-runtime"
if overlay.exists():
    os.environ["PYTHONPATH"] = str(overlay)
hf_home = Path("D:/huggingface") if os.name == "nt" else ROOT / ".cache/huggingface"
os.environ["HF_HOME"] = str(hf_home)
os.environ["HF_HUB_CACHE"] = str(hf_home / "hub")
os.environ["TRANSFORMERS_CACHE"] = os.environ["HF_HUB_CACHE"]
os.environ["JUPYTER_PLATFORM_DIRS"] = "1"
os.environ["IPYTHONDIR"] = str(ROOT / ".cache/ipython-aula04")
os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".cache/jupyter-runtime")
nb = nbformat.read(path, as_version=4)
client = NotebookClient(nb, timeout=3600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}},
                        on_cell_complete=lambda cell, cell_index, **kw: print("Célula", cell_index, "enviada", flush=True))
try:
    client.execute()
finally:
    nbformat.write(nb, path)
print("Notebook salvo:", path)
