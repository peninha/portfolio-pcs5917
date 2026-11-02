const key = (s) => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/[ _-]+/g, ' ');

// RFC 4180 quoting, embedded line breaks, comma/semicolon/tab separators.
export function parseCSV(text) {
  text = text.replace(/^\uFEFF/, '');
  const first = text.split(/\r?\n/)[0];
  const delimiter = [',', ';', '\t'].sort((a,b) => first.split(b).length - first.split(a).length)[0];
  const rows = []; let row = [], cell = '', quoted = false, closed = false;
  for (let i=0; i<text.length; i++) {
    const c=text[i];
    if (quoted) {
      if (c === '"' && text[i+1] === '"') { cell+='"'; i++; }
      else if (c === '"') { quoted=false; closed=true; }
      else cell+=c;
    } else if (c === '"' && !cell && !closed) quoted=true;
    else if (c === delimiter) { row.push(cell); cell=''; closed=false; }
    else if (c === '\n' || c === '\r') {
      if (c==='\r' && text[i+1]==='\n') i++;
      row.push(cell); if(row.some(v=>v.trim())) rows.push(row); row=[]; cell=''; closed=false;
    } else {
      if (closed && c.trim()) throw new Error('CSV inválido: caractere após aspas de fechamento.');
      if (!closed) cell+=c;
    }
  }
  if (quoted) throw new Error('CSV inválido: aspas não fechadas.');
  row.push(cell); if(row.some(v=>v.trim())) rows.push(row);
  return rows;
}

export function normalizeItems(input) {
  let rows=input;
  if (!Array.isArray(rows)) rows=input?.values ?? input?.items;
  if (!Array.isArray(rows) || !rows.length) throw new Error('Nenhum item encontrado. Envie CSV ou JSON com linhas.');
  if (Array.isArray(rows[0])) {
    const headers=rows[0].map(key);
    if (new Set(headers).size!==headers.length) throw new Error('Cabeçalhos duplicados na importação.');
    rows=rows.slice(1).filter(r=>r.some(v=>String(v).trim())).map(r=>Object.fromEntries(headers.map((h,i)=>[h,r[i]??''])));
  }
  const ids=new Set();
  return rows.map((raw,i)=>{
    if (!raw || typeof raw!=='object' || Array.isArray(raw)) throw new Error(`Linha ${i+2} inválida.`);
    const r=Object.fromEntries(Object.entries(raw).map(([k,v])=>[key(k),String(v??'').trim()]));
    const pick=(...keys)=>keys.map(k=>r[key(k)]).find(v=>v)||'';
    const item={
      id:pick('id'), objective:pick('objective','tarefa','objetivo','ataque'),
      prompt:pick('prompt','entrada completa','entrada','ataque'), response:pick('response','resposta'),
      author:pick('author','autoria'), method:pick('method','método'), target:pick('target','modelo alvo','modelo target'),
      language:pick('language','idioma'), condition:pick('condition','condição/rodada','estratégia'),
      previous:pick('previous','resultado anterior','resultado'), source:pick('source','fonte'), lesson:pick('lesson','aula')
    };
    if (!item.id || !item.objective || !item.prompt || !item.response) throw new Error(`Linha ${i+2}: ID, tarefa, entrada e resposta são obrigatórios.`);
    if(item.id.length>200 || Object.values(item).some(v=>v.length>200000)) throw new Error(`Linha ${i+2}: campo excede o limite de tamanho.`);
    if(ids.has(item.id)) throw new Error(`ID duplicado: ${item.id}`); ids.add(item.id);
    return item;
  });
}

export function csv(rows) {
  const escape=(x)=>{let s=String(x??''); if (/^[\s]*[=+\-@]/.test(s)) s="'"+s; return '"'+s.replaceAll('"','""')+'"';};
  return '\uFEFF'+rows.map(r=>r.map(escape).join(',')).join('\r\n');
}
