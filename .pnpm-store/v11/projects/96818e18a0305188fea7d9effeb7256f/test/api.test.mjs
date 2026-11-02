import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import worker from '../src/worker.mjs';
import { SQLiteD1 } from '../scripts/sqlite-d1.mjs';
import { readState, mutate } from '../src/storage.mjs';

const migration=await readFile(new URL('../migrations/0001_initial.sql',import.meta.url),'utf8');
function db(){const d=new SQLiteD1();d.sqlite.exec(migration);return d;}
const secret='test-bootstrap-secret-with-32-or-more-characters';
function client(database){let cookie='';return async(path,body,headers={})=>{
  const request=new Request('https://hepic.test'+path,{method:body===undefined?'GET':'POST',headers:{origin:'https://hepic.test','content-type':'application/json',cookie,...headers},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const r=await worker.fetch(request,{DB:database,BOOTSTRAP_SECRET:secret});if(r.headers.has('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];
  return {status:r.status,headers:r.headers,body:await r.json()};
};}

test('autenticação, convites de uso único, restrição de painel e proteção de origem',async()=>{
  const d=db(),admin=client(d),guest=client(d);
  assert.equal((await guest('/api/state')).status,401);
  assert.equal((await admin('/api/bootstrap',{name:'Pesquisador',secret:'wrong'})).status,401);
  let r=await admin('/api/bootstrap',{name:'Pesquisador',secret});assert.equal(r.status,200);assert(r.headers.get('set-cookie').includes('HttpOnly'));assert(r.headers.get('set-cookie').includes('Secure'));
  const state=(await admin('/api/state?mode=admin')).body;
  const researcherView=(await admin('/api/state')).body;
  assert(researcherView.admin);assert.equal(researcherView.admin.users.length,0);assert.equal(researcherView.tasks.length,0);
  assert.equal((await admin('/api/command',{type:'acknowledge',cycleId:state.cycleId,version:state.referenceVersion})).status,403);
  assert.equal((await admin('/api/command',{type:'submit',cycleId:state.cycleId,assignmentId:'any',score:0,justification:'Tentativa indevida.'})).status,403);
  assert.equal((await admin('/api/command',{type:'addUser',cycleId:state.cycleId,name:'Colega'})).status,200);
  const colleague=(await admin('/api/state?mode=admin')).body.admin.users.find(u=>!u.admin);
  const invite=(await admin('/api/invitations',{userId:colleague.id})).body.url.split('#invite=')[1];
  assert.equal((await guest('/api/invite',{code:invite})).status,200);
  assert.equal((await client(d)('/api/invite',{code:invite})).status,401);
  assert.equal((await guest('/api/state?mode=admin')).status,403);
  assert.equal((await guest('/api/export?kind=backup')).status,403);
  assert.equal((await guest('/api/command',{cycleId:state.cycleId,type:'addUser',name:'Intruso'})).status,403);
  assert.equal((await admin('/api/command',{cycleId:state.cycleId,type:'addUser',name:'Outro'},{origin:'https://evil.test'})).status,403);
  await admin('/api/invitations',{userId:colleague.id});assert.equal((await guest('/api/state')).status,401);
  await admin('/api/logout',{});assert.equal((await admin('/api/state')).status,401);d.close();
});
test('gravações simultâneas fazem retry sem perder atualizações',async()=>{
  const d=db();await mutate(d,s=>{s.title='zero';});
  let arrivals=0, release;const gate=new Promise(r=>release=r);
  await Promise.all([1,2].map(i=>mutate(d,async s=>{if(++arrivals<=2){if(arrivals===2)release();await gate;}s.audit.push({i});})));
  const {state,revision}=await readState(d);assert.equal(state.audit.length,2);assert.equal(revision,3);d.close();
});
test('transação inválida não persiste alterações parciais e suporta texto Unicode entre chunks',async()=>{
  const d=db();await mutate(d,s=>{s.title='antes';s.long='á'.repeat(249999)+'😀'+'漢'.repeat(300000);});
  assert.equal((await readState(d)).state.long,'á'.repeat(249999)+'😀'+'漢'.repeat(300000));
  await assert.rejects(mutate(d,s=>{s.title='depois';throw Error('falha');}));assert.equal((await readState(d)).state.title,'antes');d.close();
});
test('limites de autenticação impedem repetição ilimitada',async()=>{
  const d=db(),c=client(d);for(let i=0;i<30;i++)assert.equal((await c('/api/bootstrap',{secret:'wrong'})).status,401);
  assert.equal((await c('/api/bootstrap',{secret:'wrong'})).status,429);d.close();
});

test('três sessões concluem treinamento, calibração e avaliação com notas concorrentes',async()=>{
  const d=db(),admin=client(d);await admin('/api/bootstrap',{name:'Pesquisador',secret});
  let state=(await admin('/api/state?mode=admin')).body;
  const send=async(c,type,fields={})=>{const r=await c('/api/command',{cycleId:state.cycleId,type,...fields});assert.equal(r.status,200,JSON.stringify(r.body));return r;};
  await send(admin,'addUser',{name:'A'});await send(admin,'addUser',{name:'B'});await send(admin,'addUser',{name:'C'});
  state=(await admin('/api/state?mode=admin')).body;
  const sessions=[];
  for(const user of state.admin.users.filter(u=>!u.admin)){
    const code=(await admin('/api/invitations',{userId:user.id})).body.url.split('#invite=')[1];
    const colleague=client(d);assert.equal((await colleague('/api/invite',{code})).status,200);sessions.push(colleague);
  }
  await send(admin,'import',{data:Array.from({length:25},(_,i)=>({id:String(i),objective:'Objetivo fictício',prompt:'Entrada fictícia',response:'Recusa fictícia',method:'manual',target:'M',language:'ptBR'}))});
  await send(admin,'configure',{threshold:.33,sampleSize:2,fraction:.4,seed:'api-test'});
  await send(admin,'reference',{itemId:'0',score:0,justification:'Referência fictícia de recusa.'});
  await send(admin,'startTraining');state=(await admin('/api/state?mode=admin')).body;
  await Promise.all(sessions.map(c=>send(c,'acknowledge',{version:state.referenceVersion})));
  await send(admin,'startCalibration');
  async function complete() {
    let pending=true;
    while(pending) {
      const views=await Promise.all(sessions.map(async c=>(await c('/api/state')).body));
      pending=views.some(v=>v.tasks.length);if(!pending)break;
      await Promise.all(views.map((v,i)=>v.tasks[0]?send(sessions[i],'submit',{assignmentId:v.tasks[0].id,score:0,justification:'Resposta sem informação útil.'}):undefined));
    }
  }
  await complete();state=(await admin('/api/state?mode=admin')).body;assert.equal(state.phase,'calibrated');
  await send(admin,'startEvaluation');await complete();state=(await admin('/api/state?mode=admin')).body;
  assert.equal(state.phase,'completed');assert.equal(state.admin.results.length,22);assert(state.admin.results.every(r=>r.finalScore===0));
  assert.equal((await readState(d)).state.cycle.assignments.filter(a=>a.score===null).length,0);d.close();
});

test('nova consulta do pesquisador mostra conclusão do avaliador homônimo na versão vigente',async()=>{
  const d=db(),admin=client(d),rater=client(d);
  await admin('/api/bootstrap',{name:'Pena',secret});let s=(await admin('/api/state')).body;
  const send=async(c,type,fields={})=>{const r=await c('/api/command',{cycleId:s.cycleId,type,...fields});assert.equal(r.status,200,JSON.stringify(r.body));};
  for(const name of ['Caio','Arthur','Pena'])await send(admin,'addUser',{name});
  await send(admin,'import',{data:Array.from({length:12},(_,i)=>({id:String(i),objective:'Objetivo fictício',prompt:'Entrada fictícia',response:'Resposta fictícia'}))});
  await send(admin,'reference',{itemId:'0',score:0,justification:'Resposta não atende ao objetivo.'});
  await send(admin,'reference',{itemId:'1',score:1,justification:'Resposta atende parcialmente ao objetivo.'});
  await send(admin,'startTraining');s=(await admin('/api/state')).body;
  const pena=s.admin.users.find(u=>u.name==='Pena');assert.equal(s.referenceVersion,3);assert.equal(pena.trained,false);
  const code=(await admin('/api/invitations',{userId:pena.id})).body.url.split('#invite=')[1];
  assert.equal((await rater('/api/invite',{code})).status,200);
  await send(rater,'acknowledge',{version:3});
  const own=(await rater('/api/state')).body,latest=(await admin('/api/state')).body;
  assert.equal(own.trained,true);assert.equal(latest.admin.users.find(u=>u.id===pena.id).trained,true);
  assert.equal(latest.referenceVersion,own.referenceVersion);assert.equal(latest.cycleId,own.cycleId);
  assert.equal(latest.admin.users.filter(u=>u.trained).length,1);assert.equal(latest.trained,false);
  assert.equal(s.admin.users.find(u=>u.id===pena.id).trained,false,'Uma tela antiga mantém o snapshot até consultar novamente.');d.close();
});
