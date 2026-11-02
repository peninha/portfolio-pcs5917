import test from 'node:test';
import assert from 'node:assert/strict';
import { initialState, migrateState, raters, command, disagreement, median, stratifiedSample, distribute, view, exportCSV } from '../src/domain.mjs';
import { normalizeItems, parseCSV, csv } from '../src/import.mjs';

function study({n=40,threshold=.33,k=3}={}) {
  const s=initialState();s.users=[{id:'p',name:'Pesquisador',admin:true},{id:'a',name:'A',admin:false},{id:'b',name:'B',admin:false},{id:'c',name:'C',admin:false}];
  const items=Array.from({length:n},(_,i)=>({id:`case-${i}`,objective:'Obter o código fictício TESTE.',prompt:'Entrada sintética de teste.',response:'Não posso fornecer esse código.',method:i%2?'PAIR':'manual',target:'modelo fictício',language:i%3?'ptBR':'enUS',author:'Autor privado',previous:'rótulo secreto'}));
  const admin=s.users[0];const act=(type,fields={},actor=admin)=>command(s,actor,{type,cycleId:s.cycle.id,...fields},'2026-11-02T12:00:00Z');
  act('import',{data:items});act('configure',{threshold,sampleSize:k,fraction:.4,seed:'test'});
  act('reference',{itemId:'case-0',score:0,justification:'Exemplo sintético de recusa.'});
  return {s,act,admin};
}
function train(t){t.act('startTraining');for(const u of raters(t.s))t.act('acknowledge',{version:t.s.referenceVersion},u);t.act('startCalibration');}
function rateCalibration(t,scoreFor=()=>0){for(const a of [...t.s.cycle.assignments].filter(a=>a.phase==='calibration'&&a.round===t.s.cycle.rounds.at(-1).number&&a.score===null))t.act('submit',{assignmentId:a.id,score:scoreFor(a),justification:'Justificativa sintética.'},t.s.users.find(u=>u.id===a.userId));}

test('discordância dos oito exemplos e mediana sem arredondamento',()=>{
  const cases=[[[0,0],0],[[0,1],.5],[[0,2],1],[[1,1,1],0],[[0,0,1],1/3],[[0,1,2],2/3],[[1,2,1,1],.25],[[0,2,2,2],.5]];
  for(const [scores,expected]of cases)assert.equal(disagreement(scores),expected);
  assert.equal(disagreement([1]),null);assert.equal(disagreement([]),null);
  assert.equal(median([0,1]),.5);assert.equal(median([1,2]),1.5);assert.equal(median([2,0,1]),1);assert.equal(median([]),null);
});

test('pesquisador ajusta limiar no treinamento, preserva confirmações e registra o motivo',()=>{
  const t=study({k:1});t.act('startTraining');
  for(const u of raters(t.s))t.act('acknowledge',{version:t.s.referenceVersion},u);
  const trained=structuredClone(t.s.cycle.trained),version=t.s.referenceVersion;
  const config=structuredClone(t.s.cycle.config);
  t.act('updateThreshold',{threshold:.35,reason:'Aceitar a diferença média correspondente a um terço.'});
  assert.equal(t.s.cycle.config.threshold,.35);assert.equal(t.s.cycle.phase,'training');
  assert.deepEqual(t.s.cycle.trained,trained);assert.equal(t.s.referenceVersion,version);
  assert.deepEqual({...t.s.cycle.config,threshold:config.threshold},config);
  assert.equal(t.s.cycle.thresholdChanges[0].previous,.33);
  assert.equal(t.s.cycle.thresholdChanges[0].next,.35);assert.equal(t.s.cycle.thresholdChanges[0].actor,t.admin.id);
  assert(t.s.audit.some(e=>e.type==='threshold_changed'&&e.details.reason.includes('um terço')));
  t.act('startCalibration');rateCalibration(t,a=>a.userId==='c'?1:0);
  assert.equal(t.s.cycle.phase,'calibrated');assert.equal(t.s.cycle.rounds[0].failed.length,0);
});

test('ajuste de limiar exige pesquisador, justificativa e fase de treinamento',()=>{
  const t=study();
  assert.throws(()=>t.act('updateThreshold',{threshold:.35,reason:'Motivo válido.'}),/não está disponível/);
  t.act('startTraining');
  assert.throws(()=>t.act('updateThreshold',{threshold:.35,reason:'Motivo válido.'},raters(t.s)[0]),/exclusiva/);
  assert.throws(()=>t.act('updateThreshold',{threshold:.35,reason:''}),/justificativa/);
  for(const threshold of [NaN,Infinity,-.01,1.01,'35'])assert.throws(()=>t.act('updateThreshold',{threshold,reason:'Motivo válido.'}),/inválido/);
  assert.equal(t.s.cycle.config.threshold,.33);
  for(const u of raters(t.s))t.act('acknowledge',{version:t.s.referenceVersion},u);
  t.act('startCalibration');
  assert.throws(()=>t.act('updateThreshold',{threshold:.35,reason:'Motivo válido.'}),/não está disponível/);
});
test('amostra estratificada proporcional, sem reposição e reproduzível',()=>{
  const items=Array.from({length:100},(_,i)=>({id:i,method:i<80?'A':'B',target:'M',language:'ptBR'}));
  const a=stratifiedSample(items,10,'seed');assert.deepEqual(a,stratifiedSample(items,10,'seed'));
  assert.equal(a.filter(i=>i.method==='A').length,8);assert.equal(new Set(a.map(i=>i.id)).size,10);
  assert.throws(()=>stratifiedSample(items,101,'seed'),/inéditos/);
});
test('distribuição cobre a base e equilibra cargas e sobreposição',()=>{
  for(const n of [1,2,3,7,10,100])for(const q of [1/3,.4,.6,1]) {
    const ids=Array.from({length:n},(_,i)=>String(i));const list=distribute(ids,['a','b','c'],q,'seed');
    assert.equal(new Set(list.map(a=>a.itemId)).size,n);
    assert.equal(new Set(list.map(a=>`${a.itemId}:${a.userId}`)).size,list.length);
    for(const u of ['a','b','c'])assert.equal(list.filter(a=>a.userId===u).length,Math.ceil(q*n));
    assert.deepEqual(list,distribute(ids,['a','b','c'],q,'seed'));
  }
  const list=distribute(Array.from({length:100},(_,i)=>i),['a','b','c'],.4,'seed');
  assert.equal(list.length,120);assert.equal(new Set(list.filter(a=>list.filter(b=>b.itemId===a.itemId).length===2).map(a=>a.itemId)).size,20);
});
test('treinamento é obrigatório para os três e usa a versão atual',()=>{
  const t=study();t.act('startTraining');assert.throws(()=>t.act('startCalibration'),/Todos precisam/);
  assert.throws(()=>t.act('acknowledge',{version:0},t.s.users[1]),/atualizado/);
  t.act('acknowledge',{version:t.s.referenceVersion},t.s.users[1]);
  t.act('reference',{itemId:'case-1',score:1,justification:'Justificativa da referência.'});
  assert.deepEqual(t.s.cycle.trained,{});
});
test('calibração com discordância retorna a treinamento e usa amostra inédita',()=>{
  const t=study();train(t);const first=new Set(t.s.cycle.rounds[0].itemIds);
  rateCalibration(t,a=>a.userId==='c'?2:0);assert.equal(t.s.cycle.phase,'calibration_review');
  for(const id of t.s.cycle.rounds[0].failed)t.act('adjudicate',{itemId:id,score:0,justification:'Decisão sobre caso difícil.'});
  assert.equal(t.s.cycle.phase,'training');assert.deepEqual(t.s.cycle.trained,{});
  for(const u of raters(t.s))t.act('acknowledge',{version:t.s.referenceVersion},u);t.act('startCalibration');
  assert(t.s.cycle.rounds[1].itemIds.every(id=>!first.has(id)));
  rateCalibration(t);assert.equal(t.s.cycle.phase,'calibrated');t.act('startEvaluation');
  const seen=new Set(t.s.cycle.rounds.flatMap(r=>r.itemIds));
  assert(t.s.cycle.evaluationIds.every(id=>!seen.has(id)&&!t.s.references[id]));
});
test('avaliação adiciona terceiro avaliador, adjudica e preserva histórico em novo ciclo',()=>{
  const t=study();train(t);rateCalibration(t);t.act('startEvaluation');
  const c=t.s.cycle;
  const overlap=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===2);
  const pair=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===overlap);
  for(let i=0;i<pair.length;i++)t.act('submit',{assignmentId:pair[i].id,score:i*2,justification:'Interpretação independente.'},t.s.users.find(u=>u.id===pair[i].userId));
  const third=c.assignments.find(a=>a.itemId===overlap&&a.phase==='evaluation'&&a.score===null);
  assert(third);assert(!pair.some(a=>a.userId===third.userId));
  t.act('submit',{assignmentId:third.id,score:2,justification:'Terceira avaliação independente.'},t.s.users.find(u=>u.id===third.userId));
  assert.equal(view(t.s,t.admin,true).admin.review[0].itemId,overlap);
  t.act('adjudicate',{itemId:overlap,score:1,justification:'Adjudicação prevalece sobre a mediana.'});
  assert.equal(view(t.s,t.admin,true).admin.results.find(r=>r.itemId===overlap).finalScore,1);
  for(const a of [...c.assignments].filter(a=>a.phase==='evaluation'&&a.score===null))t.act('submit',{assignmentId:a.id,score:0,justification:'Recusa observada na resposta.'},t.s.users.find(u=>u.id===a.userId));
  assert.equal(c.phase,'completed');const oldId=c.id, count=c.assignments.length;
  t.act('restart',{promoteAdjudications:true});assert.equal(t.s.cycle.phase,'setup');assert.equal(t.s.archives[0].assignments.length,count);assert.equal(t.s.references[overlap].score,1);
  assert.throws(()=>command(t.s,t.admin,{type:'submit',cycleId:oldId,assignmentId:third.id,score:0,justification:'Nota atrasada.'}),/ciclo mudou/);
  assert(exportCSV(t.s).includes(oldId));assert(exportCSV(t.s,'ratings').includes('calibration'));
});
test('terceira nota pode resolver discordância sem adjudicação',()=>{
  const t=study({threshold:.4});train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===2);
  const pair=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);
  for(let i=0;i<2;i++)t.act('submit',{assignmentId:pair[i].id,score:i,justification:'Leitura independente.'},t.s.users.find(u=>u.id===pair[i].userId));
  const third=c.assignments.find(a=>a.itemId===id&&a.phase==='evaluation'&&a.score===null);
  t.act('submit',{assignmentId:third.id,score:0,justification:'Recusa sem informação útil.'},t.s.users.find(u=>u.id===third.userId));
  const result=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);assert.equal(result.status,'agreement');assert.equal(result.finalScore,0);assert.equal(result.disagreement,1/3);
});
test('limiar inclusivo e mediana fracionária são respeitados',()=>{
  const t=study({threshold:.5});train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===2);
  const pair=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);
  for(let i=0;i<2;i++)t.act('submit',{assignmentId:pair[i].id,score:i,justification:'Leitura independente.'},t.s.users.find(u=>u.id===pair[i].userId));
  const result=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);assert.equal(result.assigned,2);assert.equal(result.finalScore,.5);assert.equal(result.status,'agreement');
});
test('visão de avaliador não revela identidade da fonte, rótulos, colegas ou itens não atribuídos',()=>{
  const t=study();train(t);const b=t.s.users[1];const v=view(t.s,b);
  assert(!v.admin);assert.equal(v.tasks.length,3);
  const text=JSON.stringify(v);for(const secret of ['Autor privado','rótulo secreto','case-','Pesquisador'])assert(!text.includes(secret));
  assert.throws(()=>view(t.s,b,true),/restrito/);
  const others=t.s.cycle.assignments.find(a=>a.userId!==b.id);
  assert.throws(()=>t.act('submit',{assignmentId:others.id,score:0,justification:'Tentativa indevida.'},b),/não encontrada/);
  const a=t.s.cycle.assignments.find(a=>a.userId===b.id);t.act('submit',{assignmentId:a.id,score:0,justification:'Justificativa válida.'},b);
  assert.throws(()=>t.act('submit',{assignmentId:a.id,score:1,justification:'Sobrescrever nota.'},b),/já foi enviada/);
  assert.throws(()=>t.act('configure',{},b),/exclusiva/);
});
test('importação da aba Dados_Caio e CSV multilinha sem perda de texto',()=>{
  const rows=parseCSV('ID;Autoria;Método;Modelo alvo;Idioma;Tarefa;Entrada completa;Resposta;Resultado anterior\r\n"1";"Caio";"PAIR";"modelo";"ptBR";"objetivo";"linha 1\nlinha ""2""";"resposta";"recusa"');
  const [item]=normalizeItems(rows);assert.equal(item.prompt,'linha 1\nlinha "2"');assert.equal(item.previous,'recusa');assert.equal(item.author,'Caio');
  assert.deepEqual(normalizeItems([item]),[item]);assert.throws(()=>parseCSV('id,response\n1,"aspas'),/não fechadas/);
  assert.throws(()=>normalizeItems([item,item]),/duplicado/);assert.throws(()=>normalizeItems([{ID:1,Tarefa:'x'}]),/obrigatórios/);
  assert(csv([['=1+1','+CMD','texto']]).includes("'=1+1"));
});

test('pesquisador não ocupa vaga, não treina, não recebe atribuições e não envia notas',()=>{
  const t=study();const removed=t.s.users.pop();
  assert.throws(()=>t.act('startTraining'),/pesquisador não entra/);
  t.s.users.push(removed);t.act('startTraining');
  assert.throws(()=>t.act('acknowledge',{version:t.s.referenceVersion}),/acesso de avaliador/);
  for(const u of raters(t.s))t.act('acknowledge',{version:t.s.referenceVersion},u);
  t.act('startCalibration');assert.equal(t.s.cycle.assignments.length,9);
  assert(t.s.cycle.assignments.every(a=>a.userId!==t.admin.id));
  assert.throws(()=>t.act('submit',{assignmentId:t.s.cycle.assignments[0].id,score:2,justification:'Nota administrativa indevida.'}),/acesso de avaliador/);
  rateCalibration(t);t.act('startEvaluation');assert(t.s.cycle.assignments.every(a=>a.userId!==t.admin.id));
  assert.equal(view(t.s,t.admin).tasks.length,0);
  assert.equal(view(t.s,t.admin,true).admin.users.length,3);
});

test('mesma pessoa em papéis distintos tem voto comum e só depois adjudica sem alterar a discordância',()=>{
  const t=study();const evaluator=raters(t.s)[0];evaluator.name=t.admin.name;
  train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>{const a=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);return a.length===2&&a.some(a=>a.userId===evaluator.id);});
  assert(id);const pair=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);
  for(const a of pair)t.act('submit',{assignmentId:a.id,score:a.userId===evaluator.id?0:2,justification:'Interpretação independente do avaliador.'},t.s.users.find(u=>u.id===a.userId));
  let result=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(result.disagreement,1);assert.equal(result.status,'pending');assert.equal(result.assigned,3);assert.equal(result.finalScore,null);
  const third=c.assignments.find(a=>a.phase==='evaluation'&&a.itemId===id&&a.score===null);
  assert.notEqual(third.userId,t.admin.id);
  t.act('submit',{assignmentId:third.id,score:2,justification:'Terceira avaliação independente.'},t.s.users.find(u=>u.id===third.userId));
  result=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(result.status,'adjudication');assert.equal(result.disagreement,2/3);
  assert.throws(()=>t.act('adjudicate',{itemId:id,score:1,justification:'Sem permissão para adjudicar.'},evaluator),/exclusiva/);
  const before=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).map(a=>a.score);
  t.act('adjudicate',{itemId:id,score:1,justification:'Após reflexão, adoto outro critério para definir a nota final.'});
  const after=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(after.finalScore,1);assert.equal(after.disagreement,2/3);assert.equal(after.ratings,3);
  assert.deepEqual(c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).map(a=>a.score),before);
  assert.equal(c.adjudications[id].actor,t.admin.id);
});

test('migração separa histórico de avaliador sem alterar as decisões do pesquisador',()=>{
  const t=study();train(t);rateCalibration(t);const legacy=structuredClone(t.s);legacy.schema=1;
  legacy.users=legacy.users.filter(u=>u.id!=='a');
  for(const a of legacy.cycle.assignments)if(a.userId==='a')a.userId='p';
  legacy.cycle.trained.p=legacy.cycle.trained.a;delete legacy.cycle.trained.a;
  legacy.cycle.adjudications['case-9']={score:1,actor:'p',justification:'Decisão histórica.'};
  legacy.audit.push({actor:'p',type:'submit'},{actor:'p',type:'adjudicate'});
  const scores=legacy.cycle.assignments.map(a=>a.score);
  migrateState(legacy);assert.equal(legacy.schema,2);assert.equal(raters(legacy).length,3);
  assert(legacy.cycle.assignments.every(a=>a.userId!=='p'));
  assert(legacy.cycle.assignments.some(a=>a.userId==='p:rater'));
  assert.deepEqual(legacy.cycle.assignments.map(a=>a.score),scores);
  assert.equal(legacy.cycle.adjudications['case-9'].actor,'p');
  assert.equal(legacy.audit.at(-2).actor,'p:rater');assert.equal(legacy.audit.at(-1).actor,'p');
  assert(!legacy.cycle.trained.p);assert(legacy.cycle.trained['p:rater']);
  const once=structuredClone(legacy);assert.deepEqual(migrateState(legacy),once);
});

test('migração não presume participação de pesquisador sem histórico de avaliador',()=>{
  const s=initialState();s.schema=1;s.users=[{id:'p',name:'Pesquisador',admin:true}];
  migrateState(s);assert.equal(s.users.length,1);assert.equal(raters(s).length,0);
});

test('inconclusivo na preparação exige observação, não vira referência e fica fora das amostras',()=>{
  const t=study();const version=t.s.referenceVersion;
  assert.throws(()=>t.act('reference',{itemId:'case-1',outcome:'inconclusive',score:null,justification:''}),/justificativa/);
  assert.throws(()=>t.act('reference',{itemId:'case-1',outcome:'inconclusive',score:0,justification:'Prompt incompleto.'}),/sem nota/);
  t.act('reference',{itemId:'case-1',outcome:'inconclusive',score:null,justification:'Prompt incompleto: falta o contexto necessário.'});
  assert(!t.s.references['case-1']);assert.equal(t.s.cycle.inconclusives['case-1'].score,null);
  assert.equal(t.s.referenceVersion,version);train(t);
  assert(!t.s.cycle.rounds[0].itemIds.includes('case-1'));rateCalibration(t);t.act('startEvaluation');
  assert(!t.s.cycle.evaluationIds.includes('case-1'));
  const rows=parseCSV(exportCSV(t.s));const row=rows.find(r=>r[1]==='case-1');
  assert.equal(row[5],'inconclusive');assert.equal(row[8],'');assert.equal(row[18],'inconclusive');
  assert.equal(row[19],'Prompt incompleto: falta o contexto necessário.');assert.equal(row[20],'reference');
});

test('inconclusivo na calibração preserva notas, exige nova amostra e não cria referência sem score',()=>{
  const t=study({k:1});train(t);rateCalibration(t,a=>a.userId==='c'?2:0);
  const id=t.s.cycle.rounds[0].failed[0],version=t.s.referenceVersion;
  assert(id);t.act('adjudicate',{itemId:id,outcome:'inconclusive',score:null,justification:'Resposta truncada: não há evidência suficiente.'});
  assert.equal(t.s.cycle.phase,'training');assert(!t.s.references[id]);assert.equal(t.s.referenceVersion,version);
  const result=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(result.status,'inconclusive');assert.equal(result.finalScore,null);assert.equal(result.ratings,3);assert.equal(result.disagreement,2/3);
  t.act('startCalibration');assert(!t.s.cycle.rounds[1].itemIds.includes(id));
  rateCalibration(t);t.act('startEvaluation');assert(!t.s.cycle.evaluationIds.includes(id));
  assert(exportCSV(t.s,'ratings').includes(id));assert(exportCSV(t.s).includes('Resposta truncada'));
});

test('inconclusivo na avaliação não usa mediana nem zero e permite concluir e reiniciar o ciclo',()=>{
  const t=study();train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===2);
  const pair=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);
  for(const [i,a] of pair.entries())t.act('submit',{assignmentId:a.id,score:i*2,justification:'Leitura independente.'},t.s.users.find(u=>u.id===a.userId));
  const last=c.assignments.find(a=>a.phase==='evaluation'&&a.itemId===id&&a.score===null);
  t.act('submit',{assignmentId:last.id,score:1,justification:'Informação insuficiente para decidir.'},t.s.users.find(u=>u.id===last.userId));
  const before=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).map(a=>a.score);
  t.act('adjudicate',{itemId:id,outcome:'inconclusive',score:null,justification:'Entrada malformada e resposta incompleta.'});
  const r=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(r.status,'inconclusive');assert.equal(r.finalScore,null);assert.equal(r.disagreement,2/3);
  assert.deepEqual(c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).map(a=>a.score),before);
  for(const a of [...c.assignments].filter(a=>a.phase==='evaluation'&&a.score===null))t.act('submit',{assignmentId:a.id,score:0,justification:'Recusa sem informação útil.'},t.s.users.find(u=>u.id===a.userId));
  assert.equal(c.phase,'completed');t.act('restart',{promoteAdjudications:true});
  assert(!t.s.references[id]);assert(t.s.cycle.inconclusives[id]);assert.equal(t.s.archives[0].adjudications[id].score,null);
});

test('sinalização do avaliador conclui atribuição sem nota e exige revisão mesmo com notas iguais',()=>{
  const t=study({k:1});train(t);const c=t.s.cycle,a=c.assignments[0],actor=t.s.users.find(u=>u.id===a.userId);
  assert.throws(()=>t.act('submit',{assignmentId:a.id,outcome:'inconclusive',score:null,justification:''},actor),/justificativa/);
  assert.throws(()=>t.act('submit',{assignmentId:a.id,outcome:'inconclusive',score:0,justification:'Entrada incompleta.'},actor),/sem nota/);
  t.act('submit',{assignmentId:a.id,outcome:'inconclusive',score:null,justification:'Não consigo julgar: falta contexto no prompt.'},actor);
  assert.equal(a.score,null);assert.equal(view(t.s,actor).progress.completed,1);assert.equal(view(t.s,actor).tasks.length,0);
  assert.throws(()=>t.act('submit',{assignmentId:a.id,score:0,justification:'Tentativa de sobrescrever a sinalização.'},actor),/já foi enviada/);
  assert.equal(c.phase,'calibration');assert(!c.inconclusives[a.itemId]);
  for(const task of c.assignments.filter(task=>task.id!==a.id))t.act('submit',{assignmentId:task.id,score:0,justification:'Recusa sem informação útil.'},t.s.users.find(u=>u.id===task.userId));
  assert.equal(c.phase,'calibration_review');const review=view(t.s,t.admin,true).admin.review[0];
  assert.equal(review.disagreement,0);assert.equal(review.flagged,1);assert.equal(review.scores.find(x=>x.userId===actor.id).outcome,'inconclusive');
  t.act('adjudicate',{itemId:a.itemId,score:1,justification:'O contexto permite concluir sucesso parcial.'});
  assert.equal(t.s.references[a.itemId].score,1);assert.equal(a.score,null);assert.equal(a.outcome,'inconclusive');
  const exported=parseCSV(exportCSV(t.s,'ratings')).find(r=>r[4]===actor.id);
  assert.equal(exported[7],'');assert.equal(exported[10],'inconclusive');assert(exported[8].includes('falta contexto'));
});

test('três sinalizações não produzem falsa concordância e podem ser confirmadas como inconclusivo',()=>{
  const t=study({k:1});train(t);const id=t.s.cycle.rounds[0].itemIds[0];
  for(const a of [...t.s.cycle.assignments])t.act('submit',{assignmentId:a.id,outcome:'inconclusive',score:null,justification:'Resposta truncada, sem condições de julgamento.'},t.s.users.find(u=>u.id===a.userId));
  assert.equal(t.s.cycle.phase,'calibration_review');const r=view(t.s,t.admin,true).admin.review[0];
  assert.equal(r.disagreement,null);assert.equal(r.flagged,3);
  t.act('adjudicate',{itemId:id,outcome:'inconclusive',score:null,justification:'Confirmada a falta de dados para avaliação.'});
  assert(!t.s.references[id]);assert.equal(t.s.cycle.phase,'training');
  const result=view(t.s,t.admin,true).admin.results[0];assert.equal(result.ratings,0);assert.equal(result.flagged,3);assert.equal(result.finalScore,null);
});

test('sinalização em item de avaliação única vai ao pesquisador sem gerar avaliador adicional',()=>{
  const t=study();train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===1);
  const a=c.assignments.find(a=>a.phase==='evaluation'&&a.itemId===id);
  t.act('submit',{assignmentId:a.id,outcome:'inconclusive',score:null,justification:'Entrada não corresponde à tarefa apresentada.'},t.s.users.find(u=>u.id===a.userId));
  let r=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(r.status,'adjudication');assert.equal(r.ratings,0);assert.equal(r.flagged,1);assert.equal(r.assigned,1);assert.equal(r.disagreement,null);assert.equal(r.finalScore,null);
  assert.equal(view(t.s,t.admin,true).admin.review[0].itemId,id);
  t.act('adjudicate',{itemId:id,score:2,justification:'A entrada é suficiente para julgar o resultado.'});
  r=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(r.status,'adjudicated');assert.equal(r.finalScore,2);assert.equal(r.disagreement,null);assert.equal(a.score,null);
});

test('sinalização na sobreposição aguarda a outra resposta e não é convertida em zero',()=>{
  const t=study();train(t);rateCalibration(t);t.act('startEvaluation');const c=t.s.cycle;
  const id=c.evaluationIds.find(id=>c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id).length===2);
  const [first,other]=c.assignments.filter(a=>a.phase==='evaluation'&&a.itemId===id);
  t.act('submit',{assignmentId:first.id,outcome:'inconclusive',score:null,justification:'Não há contexto suficiente na entrada.'},t.s.users.find(u=>u.id===first.userId));
  assert(!view(t.s,t.admin,true).admin.review.some(r=>r.itemId===id));
  t.act('submit',{assignmentId:other.id,score:2,justification:'Objetivo atendido segundo minha interpretação.'},t.s.users.find(u=>u.id===other.userId));
  const r=view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id);
  assert.equal(r.status,'adjudication');assert.equal(r.assigned,2);assert.equal(r.ratings,1);assert.equal(r.disagreement,null);
  assert.equal(r.finalScore,null);assert.equal(r.flagged,1);
  t.act('adjudicate',{itemId:id,outcome:'inconclusive',score:null,justification:'Confirmo que a entrada está incompleta.'});
  assert.equal(view(t.s,t.admin,true).admin.results.find(r=>r.itemId===id).finalScore,null);
  assert.equal(other.score,2);assert.equal(first.score,null);
});
