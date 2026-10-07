"""Seleciona 192 audios de treino e preserva os 96 de teste; --download baixa FLAC."""
import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / "subconjunto_192"
OUT = BASE / "subconjunto_288"
DATASET = "https://www.kaggle.com/api/v1/datasets/download/ulianazb/asvspoof-2024/"


def select():
    rng = random.Random(42)
    selected = []
    used_speakers = set()
    for split, first in (("train", 1), ("dev", 9)):
        groups = {}
        for line in (BASE / f"ASVspoof5.{split}.metadata.txt").read_text().splitlines():
            speaker, file_id, gender, unused, attack, label = line.split()
            row = dict(split=split, speaker_id=speaker, file_id=file_id,
                       gender=gender, attack=attack, label=label)
            groups.setdefault((attack, gender), []).append(row)
        for attack in [f"A{i:02}" for i in range(first, first + 8)] + ["bonafide"]:
            for gender in ("F", "M"):
                candidates = groups[(attack, gender)].copy()
                rng.shuffle(candidates)
                count = 24 if attack == "bonafide" else 3
                chosen = []
                for row in candidates:
                    if row["speaker_id"] not in used_speakers:
                        chosen.append(row)
                        used_speakers.add(row["speaker_id"])
                        if len(chosen) == count:
                            break
                if len(chosen) != count:
                    raise ValueError(f"Locutores insuficientes: {split}/{attack}/{gender}")
                selected.extend(chosen)
    # A selecao original e reproduzida integralmente antes da ampliacao.
    with (ORIGINAL / 'lista_192.csv').open(encoding='utf-8', newline='') as f:
        original_rows = list(csv.DictReader(f))
    assert {r['file_id'] for r in selected} == {r['file_id'] for r in original_rows}
    rng = random.Random(43)
    groups = {}
    for line in (BASE / 'ASVspoof5.train.metadata.txt').read_text().splitlines():
        speaker, file_id, gender, unused, attack, label = line.split()
        row = dict(split='train', speaker_id=speaker, file_id=file_id,
                   gender=gender, attack=attack, label=label)
        groups.setdefault((attack, gender), []).append(row)
    for attack in [f'A{i:02}' for i in range(1, 9)] + ['bonafide']:
        for gender in ('F', 'M'):
            candidates = groups[(attack, gender)].copy()
            rng.shuffle(candidates)
            count = 24 if attack == 'bonafide' else 3
            chosen = []
            for row in candidates:
                if row['speaker_id'] not in used_speakers:
                    chosen.append(row)
                    used_speakers.add(row['speaker_id'])
                    if len(chosen) == count:
                        break
            if len(chosen) != count:
                raise ValueError(f'Locutores insuficientes: train/{attack}/{gender}')
            selected.extend(chosen)
    selected.sort(key=lambda r: (r['split'] != 'train', r['attack'], r['gender'], r['file_id']))
    for row in selected:
        row['role'] = 'train' if row['split'] == 'train' else 'test'
        prefix = "T" if row["split"] == "train" else "D"
        row["kaggle_path"] = f"flac_{prefix}/flac_{prefix}/{row['file_id']}.flac"
        row["local_path"] = f"audio/{row['role']}/{row['label']}/{row['file_id']}.flac"
    assert len(selected) == len({r['file_id'] for r in selected}) == 288
    assert len(used_speakers) == 288
    assert Counter(r['label'] for r in selected) == {'bonafide': 144, 'spoof': 144}
    assert Counter(r['role'] for r in selected) == {'train': 192, 'test': 96}
    assert {r['file_id'] for r in selected if r['role'] == 'test'} == {
        r['file_id'] for r in original_rows if r['split'] == 'dev'}
    OUT.mkdir(exist_ok=True)
    for name, rows in [('lista_288', selected),
                       ('treino_192', [r for r in selected if r['role'] == 'train']),
                       ('teste_96', [r for r in selected if r['role'] == 'test'])]:
        with (OUT / f'{name}.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(selected[0]))
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "lista_288.txt").write_text("\n".join(r['kaggle_path'] for r in selected) + "\n")
    print("Lista criada: 192 de treino e 96 de teste; 288 locutores distintos.", flush=True)
    return selected


def inspect_flac(data):
    if data[:4] != b"fLaC" or len(data) < 42 or data[4] & 127 != 0:
        raise ValueError("Resposta nao e FLAC com STREAMINFO valido")
    packed = int.from_bytes(data[18:26], "big")
    rate = packed >> 44
    channels = ((packed >> 41) & 7) + 1
    samples = packed & ((1 << 36) - 1)
    if not rate or not samples:
        raise ValueError("FLAC sem amostras ou taxa valida")
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                sample_rate=rate, channels=channels, duration_seconds=round(samples / rate, 4))


def download(row):
    dest = OUT / row['local_path']
    if dest.exists():
        return dict(file_id=row['file_id'], **inspect_flac(dest.read_bytes()))
    old = ORIGINAL / 'audio' / row['split'] / row['label'] / dest.name
    if old.exists():
        info = inspect_flac(old.read_bytes())
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, dest)
        return dict(file_id=row['file_id'], **info)
    url = DATASET + urllib.parse.quote(row['kaggle_path'], safe='')
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'ASVspoof-subset/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            if data[:2] == b'PK':
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    matches = [n for n in archive.namelist() if Path(n).name == dest.name]
                    if len(matches) != 1:
                        raise ValueError('ZIP sem o audio solicitado')
                    data = archive.read(matches[0])
            info = inspect_flac(data)
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_suffix('.part')
            temp.write_bytes(data)
            temp.replace(dest)
            return dict(file_id=row['file_id'], **info)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    rows = select()
    if not args.download:
        return
    # Confere um arquivo de cada origem antes de iniciar o lote.
    results = [download(rows[0]), download(rows[192])]
    rest = [r for i, r in enumerate(rows) if i not in (0, 192)]
    failures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, row): row for row in rest}
        for future in as_completed(futures):
            row = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append(dict(file_id=row['file_id'], error=str(exc)))
            if (len(results) + len(failures)) % 16 == 0:
                print(f"Verificados: {len(results)}/{len(rows)}; falhas: {len(failures)}", flush=True)
    report = dict(original_seed=42, expansion_seed=43,
                  files=sorted(results, key=lambda r: r['file_id']), failures=failures)
    (OUT / 'verificacao.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if failures:
        raise SystemExit(f"{len(failures)} downloads falharam; execute novamente para retomar.")
    print(f"Concluido: {len(results)} FLAC, {sum(r['bytes'] for r in results)/1024**2:.2f} MiB", flush=True)


if __name__ == '__main__':
    main()
