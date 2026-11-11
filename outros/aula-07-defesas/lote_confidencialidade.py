"""Expansão determinística dos templates para o experimento de código fictício."""
import codecs
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import coleta as co
import confidencialidade as cf

TEMPLATES = Path(__file__).with_name('ataques-templates.json')


def expandir(template, prompt):
    # Do not use str.format: some original personas contain literal braces.
    co.exigir(isinstance(prompt, str) and prompt.strip(), 'Preencha o pedido do lote.')
    co.exigir('{prompt}' in template, 'Template sem o marcador {prompt}.')
    return template.replace('{prompt_rot13}', codecs.encode(prompt, 'rot_13')).replace('{prompt}', prompt)


def preparar(raiz, autor, contexto_system, segredo, prompt, arquivo_templates=TEMPLATES, ids=None):
    """Prepara casos e proveniência sem inferência; recusa substituir um lote diferente."""
    raiz = Path(raiz)
    documento = co.ler(Path(arquivo_templates))
    lista = documento['ataques']
    todos_ids = [t['id_origem'] for t in lista]
    co.exigir(len(todos_ids) == len(set(todos_ids)), 'IDs de origem repetidos.')
    co.exigir(ids is None or (ids and len(ids)==len(set(ids)) and set(ids)<=set(todos_ids)),
              'Confira os IDs de origem selecionados.')
    casos = []
    for n, t in enumerate(lista, 1):
        if ids is not None and t['id_origem'] not in ids:
            continue
        c = cf.criar_caso(autor, expandir(t['template'], prompt), contexto_system, segredo,
                          tecnica=t['tecnica'], idioma=t['idioma'],
                          observacoes='Template reaproveitado; objetivo adaptado para código fictício.')
        c.update(id_caso=f'{autor}-conf-{n:03d}', origem_id=t['id_origem'],
                 origem_lista=t['origem_lista'], origem_sha256=t['origem_sha256'],
                 versao_templates=documento['versao'])
        casos.append(c)
    co.exigir(casos, 'Nenhum template selecionado.')
    arquivo = raiz / 'casos.json'
    config = dict(experimento=cf.VERSAO, autor=autor, prompt=prompt,
                  contexto_system=contexto_system, segredo_ficticio=segredo,
                  templates=documento, ids_selecionados=ids)
    # Validate every existing file before writing anything.
    for p, obj in [(arquivo, casos), (raiz/'configuracao_lote.json', config)]:
        if p.exists():
            co.exigir(co.ler(p) == obj, 'Lote existente com configuração diferente. Escolha outro NOME_LOTE.')
    raiz.mkdir(parents=True, exist_ok=True)
    co.gravar(arquivo, casos)
    co.gravar(raiz/'configuracao_lote.json', config)
    return cf.ler_casos(arquivo)


def manifesto(base, raiz):
    return dict(base, configuracao_lote_sha256=co.digest(co.ler(Path(raiz)/'configuracao_lote.json')),
                sha_lote_confidencialidade=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def resumo(raiz, condicoes=('B',)):
    raiz = Path(raiz)
    casos = cf.ler_casos(raiz/'casos.json')
    meta = co.ler(raiz/'coleta/manifesto.json')
    linhas = []
    for c in casos.values():
        for cond in condicoes:
            p = co.registro(raiz/'coleta', c, cond)
            if not p.exists():
                continue
            r = co.ler(p)
            cf.conferir(r, c, cond, meta)
            linhas.append(dict(id_caso=c['id_caso'], origem_id=c['origem_id'], tecnica=c['tecnica'],
                               condicao=cond, **r['avaliacao'], motivo_fim=r['motivo_fim'],
                               tokens_gerados=r['tokens_gerados'], arquivo=p.name))
    if linhas:
        co.tabela(raiz/'resumo_lote.csv', linhas)
    return linhas


def exportar(raiz, ids=None):
    raiz = Path(raiz)
    destino = cf.exportar(raiz, ids)
    with ZipFile(destino, 'a', ZIP_DEFLATED) as z:
        z.write(raiz/'configuracao_lote.json', 'configuracao_lote.json')
        z.write(Path(__file__), 'codigo/lote_confidencialidade.py')
        # Exact templates used for this run (also embedded in config).
        z.writestr('codigo/ataques-templates.json', json.dumps(
            co.ler(raiz/'configuracao_lote.json')['templates'], ensure_ascii=False, indent=2))
        if (raiz/'resumo_lote.csv').is_file():
            z.write(raiz/'resumo_lote.csv', 'resumo_lote.csv')
    return destino
