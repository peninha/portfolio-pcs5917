"""Confere os rótulos devolvidos ao desafio PicoRV32; não altera arquivos."""
import csv
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parent
CLASS = DOCS.parent


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def compare():
    mapping = read_csv(DOCS / 'mapeamento_picorv32.csv')
    answers = read_csv(CLASS / 'classificacao-preenchida.csv')
    expected_ids = {f'S{i:02d}' for i in range(1, 21)}
    assert len(mapping) == len(answers) == 20
    assert {r['id_saida'] for r in mapping} == expected_ids
    assert {r['id'] for r in answers} == expected_ids
    truth = {r['id_saida']: r['codigo_interno'] for r in mapping}
    rows = []
    counts = dict(VP=0, VN=0, FP=0, FN=0)
    for answer in sorted(answers, key=lambda r: r['id']):
        sid = answer['id']
        internal = truth[sid]
        expected = 'trojan' if internal.startswith('T') else 'inocuo'
        actual = answer['classificacao'].strip().lower()
        assert actual in ('trojan', 'inocuo'), (sid, actual)
        correct = expected == actual
        key = ('VP' if actual == 'trojan' else 'FN') if expected == 'trojan' else ('FP' if actual == 'trojan' else 'VN')
        counts[key] += 1
        rows.append(dict(id=sid, codigo_interno=internal, esperado=expected,
                         resposta=actual, acertou='sim' if correct else 'nao'))
    return rows, counts


if __name__ == '__main__':
    rows, counts = compare()
    for row in rows:
        print(','.join(row.values()))
    print(json.dumps(counts, ensure_ascii=False))
    print(f"Acertos: {counts['VP'] + counts['VN']}/20")
    print(f"Acuracia: {100 * (counts['VP'] + counts['VN']) / 20:g}%")
    assert counts == dict(VP=5, VN=10, FP=0, FN=5), 'Resultado mudou: revisar a documentação.'
    archived = read_csv(DOCS / 'comparacao_picorv32.csv')
    assert rows == archived, 'A comparação arquivada diverge dos arquivos de entrada.'
    print('Comparacao arquivada confere com a resposta recebida e o gabarito.')
