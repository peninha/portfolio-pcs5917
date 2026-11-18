import { artigos, categorias, criterios, perguntas, perfis, agregar, faixa, passou } from './protocolo.mjs';

const key = 'wcia-editorial-v1';
const app = document.querySelector('#app');
const dialog = document.querySelector('#dialog');
const toast = document.querySelector('#toast');
const initial = () => ({ documentos: artigos.map(a => ({ ...a, exemplo: a.id, pareceres: [], humanos: [] })), ativo: artigos[0].id });
let state;
try { state = JSON.parse(localStorage.getItem(key)) || initial(); }
catch { state = initial(); }
let config = { configurado: false, etapas: {}, provedorJev: null };
let tela = 'editor';
let modo = 'real';
let working = '';
let error = '';
let toastTimer;
const demoDecisions = new Map();
const legacyReviewIds = ['metodo', 'contribuicao', 'clareza'];
const checks = [
  ['pdf', 'Documento em PDF'],
  ['idioma', 'Português ou inglês'],
  ['formato', 'Modelo SBC de uma coluna'],
  ['paginas', 'Até 3 páginas de corpo e 1 de referências ou apêndices'],
  ['anonimato', 'Anonimato da submissão original']
];

const iconPaths = {
  logo: '<path d="M4 5.5 12 3l8 2.5v6.3c0 4.1-3.6 7.3-8 9.2-4.4-1.9-8-5.1-8-9.2z"/><path d="m8.5 12 2.3 2.3 4.7-4.7"/>',
  files: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h4M9 12h6m-6 4h6"/>',
  edit: '<path d="M12 20H5V5h14v7M9 9h6m-6 4h3m1 7 2-.5 5-5-1.5-1.5-5 5z"/>',
  book: '<path d="M12 20c-2-2-5-2-9-2V5c4 0 7 0 9 2 2-2 5-2 9-2v13c-4 0-7 0-9 2Zm0 0V7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M5 17v4h14v-4"/>',
  arrow: '<path d="M6 12h12m-5-5 5 5-5 5"/>',
  ext: '<path d="M13 5h6v6m0-6-9 9m0-8H5v13h13v-5"/>',
  disc: '<path d="M4 17V9m5 11V4m6 12V7m5 13v-9"/>',
  tick: '<path d="m5 12 4 4L19 6"/>',
  play: '<path d="m8 5 11 7-11 7z"/>',
  spark: '<path d="M12 3l1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Zm6 13 1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/>'
};
const icon = name => '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + iconPaths[name] + '</svg>';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const pct = n => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(n) + '%';
const avg = n => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(n);
const disc = n => n === null ? '—' : pct(n * 100);
const current = () => state.documentos.find(a => a.id === state.ativo) || state.documentos[0];

function save() {
  try { localStorage.setItem(key, JSON.stringify(state)); }
  catch { notify('O navegador não conseguiu salvar. Exporte o dossiê para guardar os dados.'); }
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 4200);
}

async function api(path, data) {
  const response = await fetch('/api/' + path, data === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.erro || 'Falha na solicitação.');
  return result;
}

function sample(categoria) {
  const rubrica = criterios(categoria);
  const matriz = [[2, 1, 2, 1, 2, 2], [2, 2, 2, 2, 1, 1], [2, 2, 1, 2, 2, 2]];
  const comentarios = [
    ['O cenário e suas consequências estão bem delimitados.', 'A contribuição aparece, mas a relação com abordagens anteriores poderia ser mais explícita.', 'As premissas e a contribuição podem ser reconstruídas.', 'Uma condição de validade merece destaque.', 'A sustentação principal é coerente.', 'O texto fornece elementos suficientes para examinar a contribuição.'],
    ['O vínculo com segurança de IA está claro.', 'O texto situa sua contribuição diante das abordagens existentes.', 'A exposição permite acompanhar a ideia central.', 'As conclusões permanecem dentro do escopo declarado.', 'Falta justificar uma escolha que afeta a contribuição.', 'Um elemento necessário à avaliação permanece implícito.'],
    ['O texto explica quem ou o que é afetado.', 'A contribuição e a lacuna estão identificadas.', 'Uma premissa importante poderia ser definida com maior precisão.', 'O alcance da conclusão está delimitado.', 'As razões apresentadas sustentam a contribuição.', 'O leitor consegue examinar a contribuição e seus limites.']
  ];
  const pareceres = perfis.map((p, i) => ({
    ...p, modelo: 'Exemplo ilustrativo',
    itens: rubrica.map(({ id }, j) => ({ id, nota: matriz[i][j], comentario: comentarios[i][j], evidencia: 'Exemplo fictício, sem referência ao PDF.' }))
  }));
  return {
    pareceres,
    sintese: {
      modelo: 'Exemplo ilustrativo',
      resumo: 'Os pareceres ilustrativos convergem na relevância do problema. As diferenças se concentram na sustentação da contribuição e no que o texto oferece para examiná-la. Consulte os critérios para ver como cada perfil justificou sua nota.',
      itens: rubrica.map(({ id }, i) => ({
        id,
        comentario: i === 0 ? 'Os três avaliadores reconheceram a relevância e o contexto do problema.' : 'Os avaliadores destacaram leituras diferentes deste critério. Abra os pareceres para comparar suas justificativas.'
      }))
    }
  };
}

const btn = (action, label, style = '', glyph = '') =>
  '<button type="button" class="btn ' + style + '" data-action="' + action + '">' + (glyph ? icon(glyph) : '') + esc(label) + '</button>';

function sidebar() {
  const links = [['fila', 'files', 'Artigos'], ['editor', 'edit', 'Mesa editorial'], ['protocolo', 'book', 'Protocolo']];
  return '<aside class="sidebar"><a class="brand" href="/" aria-label="Caderno Editorial">' +
    '<span class="brandmark">' + icon('logo') + '</span><span>Caderno<span class="brandline">Editorial</span></span></a>' +
    '<div class="nav-label">ÁREA DE TRABALHO</div><nav aria-label="Área de trabalho">' + links.map(([id, glyph, label]) =>
      '<button data-action="nav:' + id + '" class="navitem ' + (tela === id ? 'active' : '') + '" ' + (tela === id ? 'aria-current="page"' : '') + '>' + icon(glyph) + label + '</button>'
    ).join('') + '</nav><div class="sidefoot"><span class="side-dot"></span><span><b>WCIA 2026</b><small>Aula 09 · Revisão de artigos</small></span></div></aside>';
}

function documentoPicker() {
  return '<label class="sr-only" for="documento">Artigo em revisão</label><select id="documento">' +
    state.documentos.map(a => '<option value="' + esc(a.id) + '"' + (a.id === current().id ? ' selected' : '') + '>' + esc(a.titulo) + '</option>').join('') + '</select>';
}

function header() {
  const names = { fila: 'Artigos', editor: 'Mesa editorial', protocolo: 'Protocolo' };
  return '<header class="topbar"><div class="crumb"><span>Área de trabalho</span><span class="slash">/</span><strong>' + names[tela] + '</strong></div>' +
    '<div class="top-actions"><span class="env"><i></i>' + (config.configurado ? 'Fluxo configurado' : config.etapas.triagem
      ? 'Triagem disponível' : 'Modo demonstração') + '</span>' +
    btn('importar', 'Importar', 'outline') + '</div></header>';
}

function etapas(a) {
  const gate = a.triagem ? (passou(a.triagem.itens) ? 'Liberado' : 'Retido') : 'Pendente';
  const steps = [
    ['Triagem', a.triagem != null, gate],
    ['Ensemble', a.pareceres.length === 3, a.pareceres.length + ' de 3 pareceres'],
    ['Síntese', !!a.sintese, a.sintese ? 'Disponível' : 'Pendente']
  ];
  return '<div class="stepper" aria-label="Etapas da avaliação">' + steps.map(([name, done, status], i) =>
    '<div class="step"><span class="stepnr ' + (done ? 'done' : '') + '">' + (done ? icon('tick') : '0' + (i + 1)) +
    '</span><div><strong>' + name + '</strong><small>' + status + '</small></div></div>').join('') + '</div>';
}

function articleSources(a) {
  const original = artigos.find(p => p.id === a.exemplo);
  return original ? '<a class="textlink" target="_blank" rel="noreferrer" href="/artigos/' + original.arquivo + '">Abrir PDF ' + icon('ext') + '</a>' +
    '<a class="textlink" target="_blank" rel="noreferrer" href="' + original.fonte + '">Anais da SBC ' + icon('ext') + '</a>'
    : a.paginas ? btn('texto', 'Ler texto extraído', 'quiet', 'files') : '';
}

function scorePanel(score, data, demo, complete) {
  const band = faixa(score);
  return '<section class="card score"><div class="card-head"><span class="eyebrow">' +
    (complete ? 'SCORE FINAL PONDERADO' : 'SCORE PARCIAL PONDERADO') + '</span><span class="tag ' + (complete ? band.cor : 'neutral') + '">' +
    '<i></i>' + (complete ? band.texto : 'Ensemble incompleto') + '</span></div><div class="number">' + pct(score) + '</div>' +
    '<div class="ruler" role="meter" aria-label="Score final ponderado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + score +
    '"><div class="ruler-track"><div class="ruler-fill ' + band.cor + '" style="width:' + score + '%"></div></div><div class="ruler-cut"></div>' +
    '<div class="ruler-knob ' + band.cor + '" style="left:' + score + '%"></div></div>' +
    '<div class="scale"><span>0%</span><span>70% · Corte</span><span>100%</span></div>' +
    '<div class="score-note">' + (demo ? 'Notas fictícias para explorar a interface.' : data.linhas.length + ' critérios · Notas de 0 a 2') + '</div></section>';
}

function decisionPanel(a) {
  const selected = a.decisao?.valor || '';
  const options = [['aprovar', 'Aprovar'], ['rejeitar', 'Rejeitar'], ['alteracoes', 'Pedir alterações']];
  return '<section class="card decision"><div class="card-head"><h2>Decisão editorial</h2>' +
    (a.decisao ? '<span class="tag green">Registrada</span>' : '<span class="tag neutral">Pendente</span>') + '</div>' +
    '<p>Registre a decisão do editor responsável.</p><form id="decisao"><fieldset><legend class="sr-only">Decisão</legend>' +
    options.map(([value, label]) => '<label class="decision-opt"><input required type="radio" name="valor" value="' + value +
    '"' + (selected === value ? ' checked' : '') + '><span>' + label + '</span></label>').join('') +
    '</fieldset><label class="field">Comentários do editor<textarea name="comentario" rows="4" maxlength="4000" placeholder="Justifique a decisão e indique ajustes, se houver." required>' +
    esc(a.decisao?.comentario) + '</textarea></label><button type="submit" class="btn primary wide">Salvar decisão ' + icon('arrow') + '</button></form></section>';
}

function renderMetrics(data, sintese, pareceres) {
  return '<section class="card rubric"><div class="card-head"><div><h2>Avaliação por critério</h2><p>Expanda uma linha para ver os pareceres individuais.</p></div><span class="tag neutral">' + data.linhas.length + ' critérios</span></div>' +
  '<div class="table-head"><span>CRITÉRIO</span><span>PESO</span><span>MÉDIA / 2</span><span>DISCORDÂNCIA</span></div>' +
  data.linhas.map(item => {
    const resumo = sintese?.itens.find(i => i.id === item.id)?.comentario;
    return '<details class="criterion"><summary><span class="criterion-name"><span class="code">' + item.id + '</span><strong>' + item.nome +
      '</strong></span><span>' + item.peso + '%</span><span class="metric">' + avg(item.media) + '</span><span class="metric ' +
      (item.discordancia >= 0.35 ? 'high' : '') + '">' + disc(item.discordancia) + ' <span class="chevron">⌄</span></span>' +
      (resumo ? '<span class="finding">' + esc(resumo) + '</span>' : '') + '</summary>' +
      '<div class="reviews">' + pareceres.map(p => {
        const n = p.itens.find(x => x.id === item.id);
        return '<div class="review"><div><b>' + esc(p.nome) + '</b> <small>' + esc(p.modelo) + '</small><span class="tag neutral">' +
          n.nota + ' / 2</span></div><p>' + esc(n.comentario) + '</p><small>' + esc(n.evidencia) + '</small></div>';
      }).join('') + '</div></details>';
  }).join('') + '</section>';
}

function triagemPanel(a) {
  if (!a.triagem) return '';
  const decisions = a.triagem.tipo === 'decisions';
  return '<details class="card screening"><summary><strong>Respostas da triagem</strong><span class="tag ' +
    (passou(a.triagem.itens) ? 'green' : 'amber') + '">' + a.triagem.itens.filter(i => i.sim).length + ' de 4 aprovações</span></summary>' +
    '<div class="screen-items">' +
    (decisions ? '<p><small>' + esc(a.triagem.modelo) + ' · Sim acima de ' + pct(a.triagem.corte * 100) + '</small></p>' : '') +
    a.triagem.itens.map((item, i) => '<div class="screen-item"><span class="tag ' + (item.sim ? 'green">Sim' : 'red">Não') +
    '</span><div><strong>' + perguntas(a.categoria)[i] + '</strong>' +
    (decisions ? '<p>Probabilidade de Sim: ' + pct(item.probabilidadeSim * 100) + '</p>' :
      '<p>' + esc(item.comentario) + '</p><small>' + esc(item.evidencia) + '</small>') +
    '</div></div>').join('') + '</div></details>';
}

function humanosPanel(a) {
  return '<section class="card humans"><div class="card-head"><div><h2>Pareceres humanos</h2><p>Avaliações da atividade em grupo.</p></div>' +
    '<span class="tag neutral">' + (a.humanos?.length || 0) + ' registrados</span></div>' +
    (a.humanos || []).map(p => '<details class="human-review"><summary>' + esc(p.nome) + '</summary>' + p.itens.map(n =>
      '<p><b>' + esc(n.id) + ' · ' + n.nota + '/2</b> ' + esc(n.comentario) + '</p>').join('') + '</details>').join('') +
    btn('humano', 'Registrar parecer', 'outline', 'plus') + '</section>';
}

function conformidadePanel(a) {
  return '<section class="card humans"><div class="card-head"><h2>Regras da chamada</h2><span class="tag neutral">' +
    (a.conformidade ? 'Registradas' : 'Pendentes') + '</span></div><p>Registre a conferência de formato e a declaração de IA.</p>' +
    btn('conformidade', 'Conferir submissão', 'outline', 'book') + '</section>';
}

function editor() {
  const a = current();
  const demo = modo === 'demo';
  const display = demo ? sample(a.categoria) : a;
  const data = agregar(a.categoria, display.pareceres);
  const mainButton = precisaRefazer(a) ? 'Refazer avaliação' :
    a.pareceres.length || a.triagem ? 'Continuar avaliação' : config.etapas.triagem && !config.etapas.ensemble
      ? 'Executar triagem' : 'Executar avaliação';
  const realControls = btn('run', mainButton, 'primary', 'play') + btn('demo', 'Ver demonstração', 'outline', 'spark');
  return '<div class="editor-toolbar">' + documentoPicker() + '<div class="hero-actions">' +
    (demo ? btn('real', 'Voltar ao artigo', 'outline', 'arrow') : btn('exportar', 'Exportar dossiê', 'outline', 'download')) +
    '</div></div><section class="intro"><div class="intro-kicker"><span class="tag violet">' + categorias[a.categoria] +
    '</span><span>Artigo curto</span>' + (demo ? '<span class="tag amber">Demonstração · dados fictícios</span>' : '') + '</div><h1>' +
    esc(a.titulo) + '</h1><div class="intro-links">' + articleSources(a) + (demo ? '' : '<button type="button" class="textlink" data-action="categoria">Alterar categoria declarada</button>') + '</div></section>' +
    (demo ? '' : etapas(a)) + (working ? '<div class="notice" role="status"><span class="spinner"></span>' + esc(working) + '</div>' : '') +
    (error ? '<div class="notice danger" role="alert">' + esc(error) + '</div>' : '') +
    (data ? '<div class="overview">' + scorePanel(data.score, data, demo, display.pareceres.length === perfis.length) +
      '<section class="card discrepancy"><div class="card-head"><span class="eyebrow">GRAU DE DISCORDÂNCIA</span><span class="signal">' + icon('disc') +
      '</span></div><div class="number">' + disc(data.discordancia) + '</div><p>' + (data.discordancia === null ? 'São necessários dois pareceres para calcular.' :
      'Média da discordância entre avaliadores nos seis critérios.') + '</p></section></div>' : '') +
    (demo ? '' : '<div class="runbar">' + realControls + (!config.configurado
      ? '<span>' + (config.etapas.triagem ? 'Configure as etapas restantes no arquivo .env.' : 'Configure o JEV no arquivo .env.') + '</span>' : '') + '</div>') +
    triagemPanel(demo ? {} : a) +
    (data ? '<div class="editor-grid"><div class="editor-main">' +
      (display.sintese ? '<section class="card synthesis"><div class="card-head"><h2>' + icon('spark') + ' Síntese dos pareceres</h2><span class="tag violet">' +
        (demo ? 'Exemplo' : esc(display.sintese.modelo)) + '</span></div><p>' + esc(display.sintese.resumo) + '</p></section>' : '') +
      renderMetrics(data, display.sintese, display.pareceres) + '</div><div class="editor-side">' +
      (demo ? decisionPanel({ decisao: demoDecisions.get(a.id) }) +
       '<section class="card sample-card"><h2>Dossiê de demonstração</h2><p>Os valores são ilustrativos. Abra o artigo para executar a avaliação com os modelos configurados.</p>' +
       btn('real', 'Voltar ao artigo', 'outline') + '</section>' : decisionPanel(a) + humanosPanel(a) + conformidadePanel(a)) + '</div></div>' :
      '<div class="editor-grid"><section class="card empty"><span class="empty-icon">' + icon('edit') + '</span><h2>O dossiê começa na triagem</h2>' +
      '<p>Execute a avaliação para receber o score ponderado, o grau de discordância e a síntese de cada critério.</p></section><div class="editor-side">' +
      decisionPanel(a) + humanosPanel(a) + conformidadePanel(a) + '</div></div>');
}

function fila() {
  return '<div class="section-title"><div><span class="eyebrow">AULA 09</span><h1>Artigos em revisão</h1><p>Selecione um trabalho para abrir seu dossiê editorial.</p></div>' +
    btn('adicionar', 'Adicionar artigo', 'primary', 'plus') + '</div><div class="article-list">' + state.documentos.map((a, i) =>
    '<article class="card article-row"><span class="filemark">' + icon('files') + '</span><div><span class="eyebrow">ARTIGO ' + String(i + 1).padStart(2, '0') +
    '</span><h2>' + esc(a.titulo) + '</h2><span class="tag violet">' + categorias[a.categoria] + '</span></div><div class="article-action">' +
    '<span class="tag ' + (a.decisao ? 'green">Decisão registrada' : a.sintese ? 'violet">Dossiê disponível' : a.triagem && !passou(a.triagem.itens) ? 'amber">Retido na triagem' : 'neutral">Em revisão') +
    '</span><button type="button" class="btn outline" data-action="abrir" data-id="' + esc(a.id) + '">Abrir dossiê ' + icon('arrow') + '</button></div></article>').join('') + '</div>';
}

function protocolo() {
  return '<div class="section-title"><div><span class="eyebrow">AULA 09</span><h1>Protocolo de avaliação</h1>' +
    '<p>Quatro critérios comuns e dois específicos da categoria declarada.</p></div></div>' +
    '<section class="card protocol-info"><h2>Triagem e cálculo das notas</h2><p>O JEV libera o artigo com pelo menos três respostas positivas, incluindo o enquadramento no WCIA. Cada agente usa a mesma escala de 0 a 2. O score final é a soma das médias ponderadas, convertida em porcentagem.</p>' +
    '<p>A discordância vem da soma das diferenças absolutas entre pares, dividida por n × (n − 1), para cada critério. A média dos seis valores forma o indicador geral. Veja as regras da <a href="https://www.sbseg2026.uff.br/workshops/wcia/" target="_blank" rel="noreferrer">chamada oficial</a>.</p>' +
    '<div class="legend">' + [0, 35, 55, 71, 90].map((value, i) => '<span class="tag ' + faixa(value).cor + '">' + ['0 a &lt;35%', '35 a &lt;55%', '55 a 70%', '&gt;70 a &lt;90%', '90 a 100%'][i] +
    ' · ' + faixa(value).texto + '</span>').join('') + '</div></section>' +
    Object.entries(categorias).map(([id, nome], index) => '<section class="card protocol-info"><h2>' + nome + '</h2><div class="protocol-list">' +
      criterios(id).slice(index ? 4 : 0).map(c => '<details><summary><span class="code">' + c.id + '</span> <b>' + c.nome + '</b><span class="tag neutral">' +
        c.peso + '%</span></summary><ol start="0">' + c.niveis.map(n => '<li>' + n + '</li>').join('') + '</ol></details>').join('') + '</div></section>').join('');
}

function render() {
  app.innerHTML = sidebar() + '<div class="shell">' + header() + '<main id="main">' + ({ editor, fila, protocolo }[tela])() +
    '<footer>Caderno Editorial <span>WCIA 2026 · PCS5917</span></footer></main></div>';
  if (working) app.querySelectorAll('[data-action], #documento, form button').forEach(el => { el.disabled = true; });
}

function reset(a) {
  a.triagem = undefined;
  a.pareceres = [];
  a.sintese = undefined;
  a.decisao = undefined;
}

function precisaRefazer(a) {
  return Boolean(a.sintese || (a.triagem && !passou(a.triagem.itens)) ||
    (a.triagem && config.etapas.triagem && config.provedorJev === 'OpenRouter' &&
      (a.triagem.tipo !== 'decisions' || a.triagem.modeloSolicitado !== config.modelos?.jev)) ||
    a.pareceres.some(p => legacyReviewIds.includes(p.id) ||
      (config.etapas.ensemble && config.modelos?.[p.id] && config.modelos[p.id] !== p.modelo)));
}

async function run(a) {
  if (!a.triagem && !config.etapas.triagem) {
    notify(config.erroJev || 'Configure a triagem no arquivo .env.');
    return;
  }
  error = '';
  try {
    working = 'Lendo o artigo…';
    render();
    if (!a.paginas) {
      expectExample(a);
      a.paginas = (await api('pdf', { id: a.exemplo })).paginas;
      save();
    }
    const artigo = { titulo: a.titulo, categoria: a.categoria, paginas: a.paginas };
    if (!a.triagem) {
      working = 'Executando a triagem…';
      render();
      a.triagem = await api('triagem', artigo);
      save();
    }
    if (!passou(a.triagem.itens)) {
      notify('Artigo retido na triagem. As respostas estão no dossiê.');
      return;
    }
    const pending = perfis.filter(p => !a.pareceres.some(av => av.id === p.id));
    if (pending.length) {
      if (!config.etapas.ensemble) {
        notify(config.erroEnsemble || 'Triagem salva. Configure os modelos do ensemble no arquivo .env para continuar.');
        return;
      }
      working = 'Consultando os três avaliadores do ensemble…';
      render();
      const results = await Promise.allSettled(pending.map(async p => {
        const review = await api('avaliar', { ...artigo, perfil: p.id });
        a.pareceres.push(review);
        a.pareceres.sort((x, y) => perfis.findIndex(p => p.id === x.id) - perfis.findIndex(p => p.id === y.id));
        save();
      }));
      const failure = results.find(result => result.status === 'rejected');
      if (failure) throw failure.reason;
    }
    if (!config.etapas.sintese) {
      notify('Pareceres salvos. Configure o modelo de síntese no arquivo .env para continuar.');
      return;
    }
    working = 'Consolidando os pareceres…';
    render();
    a.sintese = await api('sintese', { categoria: a.categoria, avaliacoes: a.pareceres });
    save();
    notify('Dossiê editorial atualizado.');
  } catch (e) {
    error = e.message + ' Os resultados já obtidos foram preservados.';
  } finally {
    working = '';
    render();
  }
}

function expectExample(a) {
  if (!a.exemplo) throw new Error('O artigo precisa do texto extraído de um PDF.');
}

function openDialog(title, body) {
  dialog.innerHTML = '<div class="dialog-header"><h2>' + title + '</h2><button class="close" type="button" data-action="fechar" aria-label="Fechar">×</button></div>' + body;
  dialog.showModal();
}

const categoryField = (selected = '') => '<label class="field">Categoria declarada pelos autores<select name="categoria" required><option value="">Selecione</option>' +
  Object.entries(categorias).map(([id, nome]) => '<option value="' + id + '"' + (id === selected ? ' selected' : '') + '>' + nome + '</option>').join('') + '</select></label>';

function exportar(a) {
  const url = URL.createObjectURL(new Blob([JSON.stringify({ versao: 1, artigo: a }, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'dossie-wcia-' + a.id + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function importar(data) {
  const a = data?.artigo;
  if (data?.versao !== 1 || !a || typeof a.titulo !== 'string' || !a.titulo.trim() || !Object.hasOwn(categorias, a.categoria) ||
      !Array.isArray(a.pareceres) || !Array.isArray(a.humanos)) throw new Error('Selecione um dossiê exportado pelo Caderno Editorial.');
  const ids = criterios(a.categoria).map(c => c.id);
  const valid = (items, keys, validate) => Array.isArray(items) && items.length === keys.length &&
    keys.every(id => items.filter(i => i?.id === id && validate(i)).length === 1);
  const comentario = item => typeof item.comentario === 'string';
  const nota = item => [0, 1, 2].includes(item.nota) && comentario(item);
  const respostaTriagem = item => typeof item.sim === 'boolean' && (a.triagem.tipo === 'decisions'
    ? Number.isFinite(item.probabilidadeSim) && item.probabilidadeSim >= 0 && item.probabilidadeSim <= 1 &&
      a.triagem.corte === 0.5 && item.sim === (item.probabilidadeSim > a.triagem.corte)
    : comentario(item));
  const reviewerIds = a.pareceres.some(p => legacyReviewIds.includes(p?.id)) ? legacyReviewIds : perfis.map(p => p.id);
  if (a.pareceres.length > perfis.length || new Set(a.pareceres.map(p => p?.id)).size !== a.pareceres.length ||
      !a.pareceres.every(p => reviewerIds.includes(p?.id) && valid(p.itens, ids, nota)) ||
      !a.humanos.every(p => p && typeof p.nome === 'string' && valid(p.itens, ids, nota)) ||
      (a.triagem && !valid(a.triagem.itens, ['Q1', 'Q2', 'Q3', 'Q4'], respostaTriagem)) ||
      (a.sintese && (typeof a.sintese.resumo !== 'string' || !valid(a.sintese.itens, ids, comentario))) ||
      (a.paginas && (!Array.isArray(a.paginas) || !a.paginas.every(p => Number.isInteger(p?.numero) && typeof p.texto === 'string')))) {
    throw new Error('O dossiê contém avaliações ou páginas inválidas.');
  }
  const example = artigos.find(original => original.id === a.exemplo && original.titulo === a.titulo);
  return { ...a, id: crypto.randomUUID(), exemplo: example?.id, triagem: a.triagem &&
    { ...a.triagem, itens: ['Q1', 'Q2', 'Q3', 'Q4'].map(id => a.triagem.itens.find(i => i.id === id)) } };
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button || working) return;
  const action = button.dataset.action;
  const a = current();
  if (action.startsWith('nav:')) {
    tela = action.slice(4);
    error = '';
    render();
    return;
  }
  switch (action) {
    case 'abrir': state.ativo = button.dataset.id; tela = 'editor'; modo = 'real'; save(); render(); break;
    case 'demo': modo = 'demo'; render(); break;
    case 'real': modo = 'real'; render(); break;
    case 'exportar': exportar(a); break;
    case 'fechar': dialog.close(); break;
    case 'run':
      if (precisaRefazer(a)) {
        openDialog('Refazer avaliação', '<p>A nova execução substitui a triagem, os pareceres dos agentes, a síntese e a decisão editorial deste artigo.</p>' +
          btn('refazer', 'Refazer avaliação', 'primary'));
      } else run(a);
      break;
    case 'refazer':
      if (!config.etapas.triagem || (a.pareceres.length && !config.configurado)) {
        notify('Configure as etapas necessárias no arquivo .env antes de refazer a avaliação.');
        break;
      }
      dialog.close(); reset(a); save(); run(a); break;
    case 'categoria':
      openDialog('Categoria declarada', '<form id="categoria-form">' + categoryField(a.categoria) +
        ((a.triagem || a.pareceres.length || a.humanos.length || a.decisao) ? '<p>A troca reinicia as avaliações e a decisão deste dossiê.</p>' : '') +
        '<button class="btn primary" type="submit">Salvar categoria</button></form>'); break;
    case 'adicionar':
      openDialog('Adicionar artigo', '<form id="adicionar-form"><label class="field">Título<input name="titulo" required maxlength="400"></label>' + categoryField() +
        '<label class="field">PDF<input type="file" name="arquivo" accept="application/pdf,.pdf" required></label><p class="form-error" role="alert"></p>' +
        '<button class="btn primary" type="submit">Adicionar artigo</button></form>'); break;
    case 'importar':
      openDialog('Importar dossiê', '<form id="importar-form"><label class="field">Arquivo JSON<input type="file" name="arquivo" accept=".json,application/json" required></label>' +
        '<p class="form-error" role="alert"></p><button class="btn primary" type="submit">Importar dossiê</button></form>'); break;
    case 'texto':
      openDialog('Texto extraído do PDF', '<div class="paper-text">' + a.paginas.map(p =>
        '<h3>Página ' + p.numero + '</h3><p>' + esc(p.texto) + '</p>').join('') + '</div>'); break;
    case 'humano':
      openDialog('Registrar parecer humano', '<form id="humano-form"><label class="field">Nome ou código do avaliador<input name="nome" maxlength="100" required></label>' +
        criterios(a.categoria).map(c => '<div class="human-form-row"><label class="field">' + c.nome +
          '<select name="nota-' + c.id + '" required><option value="">Selecione</option>' +
          ['0 — Não atende', '1 — Parcial', '2 — Atende'].map((n, i) => '<option value="' + i + '">' + n + '</option>').join('') +
          '</select></label><label class="field">Justificativa<textarea name="comentario-' + c.id + '" required maxlength="2000" rows="2"></textarea></label></div>').join('') +
        '<button class="btn primary" type="submit">Salvar parecer</button></form>'); break;
    case 'conformidade':
      openDialog('Regras da chamada do WCIA', '<form id="conformidade-form">' +
        checks.map(([id, label]) => '<label class="field">' + label + '<select name="' + id + '">' +
          [['pendente', 'Pendente'], ['sim', 'Atende'], ['nao', 'Não atende'], ['incerto', 'Não verificável']].map(([value, text]) =>
            '<option value="' + value + '"' + ((a.conformidade?.[id] || (id === 'anonimato' && a.exemplo ? 'incerto' : 'pendente')) === value ? ' selected' : '') + '>' + text + '</option>'
          ).join('') + '</select></label>').join('') +
        '<label class="field">Declaração de IA generativa e observações<textarea name="observacao" rows="3" maxlength="4000" placeholder="Indique a seção quando houver uma declaração.">' +
          esc(a.conformidade?.observacao) + '</textarea></label><button class="btn primary" type="submit">Salvar conferência</button></form>'); break;
  }
});

document.addEventListener('change', e => {
  if (e.target.id === 'documento') {
    state.ativo = e.target.value;
    error = '';
    save();
    render();
  }
});

document.addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.target;
  const fields = new FormData(form);
  const a = current();
  if (form.id === 'decisao') {
    if (!fields.get('comentario').trim()) { notify('Preencha os comentários do editor.'); return; }
    const decisao = { valor: fields.get('valor'), comentario: fields.get('comentario').trim(), data: new Date().toISOString() };
    if (modo === 'demo') demoDecisions.set(a.id, decisao);
    else {
      a.decisao = decisao;
      save();
    }
    render();
    notify(modo === 'demo' ? 'Decisão registrada na demonstração.' : 'Decisão editorial salva.');
    return;
  }
  if (form.id === 'categoria-form') {
    if (a.categoria !== fields.get('categoria')) {
      reset(a);
      a.humanos = [];
      a.categoria = fields.get('categoria');
    }
  } else if (form.id === 'conformidade-form') {
    a.conformidade = Object.fromEntries(fields);
  } else if (form.id === 'humano-form') {
    const nome = fields.get('nome').trim();
    const itens = criterios(a.categoria).map(c => ({
      id: c.id, nota: Number(fields.get('nota-' + c.id)), comentario: fields.get('comentario-' + c.id).trim()
    }));
    if (!nome || itens.some(i => !i.comentario)) { notify('Preencha a identificação e todas as justificativas.'); return; }
    if (a.humanos.some(p => p.nome.toLowerCase() === nome.toLowerCase())) { notify('Já existe um parecer para esse avaliador.'); return; }
    a.humanos.push({ nome, itens });
  } else {
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      const arquivo = fields.get('arquivo');
      let doc;
      if (form.id === 'adicionar-form') {
        const titulo = fields.get('titulo').trim();
        if (!titulo) throw new Error('Informe o título do artigo.');
        if (arquivo.size > 12 * 1024 * 1024) throw new Error('O PDF deve ter até 12 MiB.');
        const pdf = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(',')[1]);
          reader.onerror = () => reject(new Error('Não foi possível ler o arquivo.'));
          reader.readAsDataURL(arquivo);
        });
        const { paginas } = await api('pdf', { pdf });
        doc = { id: crypto.randomUUID(), titulo, categoria: fields.get('categoria'), paginas, pareceres: [], humanos: [] };
      } else {
        if (arquivo.size > 2 * 1024 * 1024) throw new Error('O dossiê deve ter até 2 MiB.');
        let data;
        try { data = JSON.parse(await arquivo.text()); }
        catch { throw new Error('O arquivo não contém JSON válido.'); }
        doc = importar(data);
      }
      state.documentos.push(doc);
      state.ativo = doc.id;
      tela = 'editor';
      modo = 'real';
      error = '';
    } catch (e) {
      form.querySelector('.form-error').textContent = e.message;
      submit.disabled = false;
      return;
    }
  }
  dialog.close();
  save();
  render();
});

api('config').then(result => {
  config = { ...result, etapas: result.etapas ?? {
    triagem: result.configurado, ensemble: result.configurado, sintese: result.configurado
  } };
  if (!config.etapas.triagem && current().exemplo && !current().triagem && !current().decisao) modo = 'demo';
  render();
}).catch(() => { error = 'Não foi possível consultar a configuração do servidor.'; render(); });
render();
