"""Extração fiel e checagens locais das alterações AES recebidas do Gemini.

Não executa os C++: verifica integridade, diferenças e invariantes algébricos.
Uso: python outros/aula-08-trojan/analisar_gemini.py
"""
import csv
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'planilha_anonimizada_grupo_e_opcao2_gemini.csv'
OUT = ROOT / 'codigos_gemini'


def main():
    with SOURCE.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    rows.sort(key=lambda r: int(r['id']))
    assert [r['id'] for r in rows] == [str(i) for i in range(1, 21)]
    OUT.mkdir(exist_ok=True)
    manifest = []
    # Base auxiliar: amostra 7 com a limpeza inicial de _key restaurada.
    # Não é um AES.cpp original fornecido pelo grupo.
    anchor = 'void AES::set_key(const std::vector<byte> &word)\n{\n'
    base = rows[6]['codigo_completo'].replace('\r\n', '\n')
    assert base.count(anchor) == 1
    base = base.replace(anchor, anchor + '\tthis->_key = {};\n\n')
    for row in rows:
        code = row['codigo_completo']
        file = OUT / f"G{int(row['id']):02d}_AES.cpp"
        file.write_bytes(code.encode('utf-8'))
        assert file.read_bytes().decode('utf-8') == code
        diff = '\n'.join(difflib.unified_diff(
            base.splitlines(), code.splitlines(),
            fromfile='base_comparativa_reconstruida', tofile=file.name, n=2))
        file.with_suffix('.diff').write_text(diff + '\n', encoding='utf-8')
        manifest.append({'id': row['id'], 'arquivo': file.name,
                         'sha256_codigo_utf8': hashlib.sha256(file.read_bytes()).hexdigest()})

    # ID 4: mesma matriz de coeficientes, logo mesma transformação linear.
    coeff = [2, 3, 1, 1]
    original = [coeff[-r:] + coeff[:-r] if r else coeff[:] for r in range(4)]
    indexed = [[coeff[(4 + j - r) % 4] for j in range(4)] for r in range(4)]
    assert indexed == original
    # IDs 5/6: permutações idênticas para as quatro posições do estado.
    labels = list(range(4))
    assert labels[0:] + labels[:0] == labels
    for r in range(1, 4):
        assert labels[-r:] + labels[:-r] == labels[4-r:] + labels[:4-r]
    # ID 12: índices efetivamente produzidos pelo código e primeiro acesso inválido.
    indices = {}
    for nk, nr in [(4, 10), (6, 12), (8, 14)]:
        size = (4 * (nr + 1) - 1) // nk
        accesses = [{'i': i, 'correto': i // nk - 1, 'alterado': i // 4 - 1}
                    for i in range(nk, 4 * (nr + 1)) if i % nk == 0]
        oob = next((a for a in accesses if a['alterado'] >= size), None)
        indices[str(32 * nk)] = {'tamanho_rcon': size, 'acessos': accesses,
                                'primeiro_fora_dos_limites': oob}
    assert indices['128']['primeiro_fora_dos_limites'] is None
    assert indices['192']['primeiro_fora_dos_limites']['i'] == 36
    assert indices['256']['primeiro_fora_dos_limites']['i'] == 32
    # ID 16: conversões deixam de ser inversas, demonstrado sem cifragem.
    word = list(range(16))
    transposed = [word[c + 4 * r] for c in range(4) for r in range(4)]
    assert transposed != word
    # ID 20: a composição ShiftRows/InvShiftRows gira duas vezes à direita.
    rotate20 = {}
    for r in range(4):
        row = labels[-r:] + labels[:-r] if r else labels[:]
        restored = row[-r:] + row[:-r] if r else row[:]
        rotate20[str(r)] = restored
        assert (restored == labels) == (r in (0, 2))

    evidence = {'fonte_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'extracao_identica': len(manifest), 'manifesto': manifest,
                'id04_matriz_equivalente': indexed, 'id06_permutacao_equivalente': True,
                'id12_rcon': indices, 'id16_entrada': word,
                'id16_to_word_to_state': transposed,
                'id20_shift_seguido_de_invshift': rotate20,
                'escopo': 'Checagens locais das expressões. Não representam execução completa do AES.'}
    (OUT / 'evidencias.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print('20 códigos preservados; equivalências e contraexemplos locais conferidos.')


if __name__ == '__main__':
    main()
