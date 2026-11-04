"""Testes da consolidação: somente arquivos temporários, sem inferência."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from http.client import HTTPConnection
from urllib.parse import urlsplit
import re
from html.parser import HTMLParser
from revisao import collect_review_rows, render_review_table, write_review_table, save_human_reviews, start_review_server


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = 0
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "tr" and "data-model" in dict(attrs):
            self.rows += 1
        if tag == "script":
            self.scripts += 1


class RevisaoTest(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_junta_concluido_incompleto_e_pendente_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            message = '<script>alert("dado, não código")</script>'
            case = {"case_id": "MANUAL", "target": "ALVO", "messages": [{"role": "user", "content": message}]}
            cfg = {"case": case, "batch_id": "lote1", "model_id": "org/modelo", "config": {"seed": 42, "optim_str_init": "x x", "num_steps": 40}}
            complete = base / "run1"
            self.write(complete / "config.json", cfg)
            self.write(complete / "resultado.json", {"baseline": "A", "attack": "ALVO", "best_string": " sufixo"})
            self.write(complete / "baseline.json", {"response": "A", "prompt_rendered": "original", "input_ids": [1, 2]})
            self.write(complete / "ataque.json", {"response": "ALVO", "prompt_rendered": "final"})
            with (complete / "avaliacao-humana.csv").open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["condition", "verdict", "notes"])
                w.writeheader()
                w.writerow({"condition": "baseline", "verdict": "fail", "notes": "Não atingiu"})
                w.writerow({"condition": "attack", "verdict": "success", "notes": "Conferido pelo aluno"})
            self.write(base / "run2/config.json", {**cfg, "model_id": "org/parcial"})
            jobs = [{"model_id": model, "case_id": "MANUAL", "suffix_units": 2, "seed": 42, "num_steps": 40, "case": case}
                    for model in ["org/modelo", "org/parcial", "org/pendente"]]
            self.write(base / "lotes/lote1/plano.json", {"tests": jobs})
            self.write(base / "lotes/lote1/andamento.json", {"batch_id": "lote1", "tests": [
                {"test": 1, "status": "completed"}, {"test": 2, "status": "running"}, {"test": 3, "status": "pending"}]})
            rows = collect_review_rows(base)
            self.assertEqual(len(rows), 3)
            self.assertEqual({r["status"] for r in rows}, {"Concluído", "Sem resultado final", "Sem execução salva"})
            reviewed = next(r for r in rows if r["run_id"] == "run1")
            self.assertEqual(reviewed["attack_review"], "success")
            self.assertEqual(reviewed["attack_notes"], "Conferido pelo aluno")
            self.assertEqual(reviewed["baseline_record"]["input_ids"], [1, 2])
            output, exported = write_review_table(base)
            page = output.read_text(encoding="utf-8")
            parser = TableParser()
            parser.feed(page)
            self.assertEqual(parser.rows, 3)
            self.assertEqual(parser.scripts, 1)  # Só o filtro; o texto do usuário é escapado.
            self.assertNotIn(message, page)
            self.assertIn("&lt;script&gt;", page)
            self.assertEqual(json.loads((base / "revisao-dados.json").read_text(encoding="utf-8")), exported)
            self.assertEqual(next(r for r in exported if r["run_id"] == "run1")["messages"][0]["content"], message)

    def test_json_invalido_aponta_arquivo(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run/config.json"
            path.parent.mkdir()
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "config.json"):
                collect_review_rows(Path(temp))

    def review_fixture(self, base):
        folder = base / "run1"
        self.write(folder / "config.json", {"case": {"case_id": "V03", "target": "OVERRIDE"}})
        self.write(folder / "baseline.json", {"response": "Obrigado!"})
        self.write(folder / "ataque.json", {"response": "OVERRIDE"})
        path = folder / "avaliacao-humana.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["condition", "response", "verdict", "notes"])
            w.writeheader()
            for condition, response in [("baseline", "Obrigado!"), ("attack", "OVERRIDE")]:
                w.writerow({"condition": condition, "response": response, "verdict": "pending", "notes": ""})
        return path

    def test_salva_julgamento_preserva_respostas_e_faz_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            path = self.review_fixture(base)
            original = path.read_bytes()
            changes = [{"run_id": "run1", "condition": "attack", "verdict": "success", "notes": "Alvo atingido.",
                        "original_verdict": "pending", "original_notes": ""}]
            result = save_human_reviews(base, changes)
            self.assertEqual(result["updated"], 1)
            self.assertEqual((Path(result["backup"]) / "run1.csv").read_bytes(), original)
            with path.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["verdict"], "pending")
            self.assertEqual(rows[1]["response"], "OVERRIDE")
            self.assertEqual(rows[1]["verdict"], "success")
            self.assertEqual(rows[1]["notes"], "Alvo atingido.")
            saved = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "mudou"):
                save_human_reviews(base, changes)
            self.assertEqual(path.read_bytes(), saved)

    def test_valida_todo_envio_antes_de_gravar_e_rejeita_caminhos(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            path = self.review_fixture(base)
            before = path.read_bytes()
            valid = {"run_id": "run1", "condition": "attack", "verdict": "success", "notes": "", "original_verdict": "pending", "original_notes": ""}
            with self.assertRaises(ValueError):
                save_human_reviews(base, [valid, {**valid, "run_id": "../fora"}])
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError):
                save_human_reviews(base, [{**valid, "verdict": "inventado"}])
            self.assertEqual(path.read_bytes(), before)

    def test_html_editavel_tem_campos_sem_julgar_automaticamente(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.review_fixture(base)
            page = render_review_table(collect_review_rows(base), editable=True, csrf_token="token-teste")
            self.assertIn('id="save-reviews"', page)
            self.assertEqual(page.count('class="evaluation"'), 2)
            self.assertEqual(page.count('value="pending" selected'), 2)
            self.assertIn("Não atingiu o objetivo", page)
            self.assertIn("/api/reviews", page)

    def test_editor_http_salva_so_com_origem_e_token_corretos(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review_file = self.review_fixture(root)
            server = start_review_server(root)
            url = urlsplit(server.review_url)

            def request(method, path, body=None, headers=None):
                conn = HTTPConnection(url.hostname, url.port, timeout=5)
                try:
                    conn.request(method, path, body=body, headers=headers or {})
                    response = conn.getresponse()
                    return response.status, response.read().decode("utf-8")
                finally:
                    conn.close()

            try:
                status, page = request("GET", "/")
                self.assertEqual(status, 200)
                token = re.search(r"'X-Review-Token':'([a-f0-9]+)'", page).group(1)
                change = {"run_id": "run1", "condition": "attack", "verdict": "success", "notes": "Confirmado no editor.",
                          "original_verdict": "pending", "original_notes": ""}
                body = json.dumps({"reviews": [change]})
                original = review_file.read_bytes()
                self.assertEqual(request("POST", "/api/reviews", body, {"Content-Type": "application/json"})[0], 403)
                self.assertEqual(review_file.read_bytes(), original)
                headers = {"Content-Type": "application/json", "X-Review-Token": token,
                           "Origin": server.review_url.rstrip("/")}
                status, result = request("POST", "/api/reviews", body, headers)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(result)["updated"], 1)
                self.assertIn("Confirmado no editor.", review_file.read_text(encoding="utf-8-sig"))
                headers["Origin"] = "https://example.com"
                self.assertEqual(request("POST", "/api/reviews", body, headers)[0], 403)
            finally:
                server.shutdown()
                server.server_close()

    def test_funcoes_incorporadas_no_notebook_incluem_rotulos(self):
        from notebook_lotes import review_cells
        cells = review_cells(Path(__file__).parent / "experimento.py")
        namespace = {}
        setup = next(c for c in cells if c.metadata.get("consolidated_review") == "definitions")
        exec(setup.source, namespace)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.review_fixture(root)
            page = namespace["render_review_table"](namespace["collect_review_rows"](root), editable=True)
            self.assertIn("Salvar avaliações", page)
            self.assertIn("Ainda não avaliei", page)


if __name__ == "__main__":
    unittest.main()
