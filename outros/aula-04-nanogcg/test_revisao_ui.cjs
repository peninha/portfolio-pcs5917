// Testa o JavaScript da página sem navegador, modelos ou gravações reais.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const page = fs.readFileSync(process.argv[2], 'utf8');
const script = page.match(/<script>([\s\S]*?)<\/script>/)[1];
const rows = [{dataset:{model:'A',case:'V03',batch:'lote1',status:'Concluído'},
  textContent:'OVERRIDE', classList:{toggle(name,value){this[name]=value;}}}];
const callbacks = {}, events = {};
const verdict = {value:'pending'}, notes = {value:''};
const editor = {dataset:{run:'run1',condition:'attack'},
  querySelector:s=>s==='.verdict'?verdict:notes,
  closest:()=>rows[0], addEventListener:(event,callback)=>events[event]=callback};
const nodes = {};
for(const id of ['model','case','batch','status','search','count','save-reviews','save-status'])
  nodes[id] = {value:'',disabled:false,addEventListener:(event,callback)=>callbacks[id]=callback};
let request, fail = false;
const context = {document:{
  querySelectorAll:s=>s==='tbody tr'?rows:[editor], getElementById:id=>nodes[id]},
  window:{addEventListener:(event,callback)=>events[event]=callback},
  fetch:async(url,options)=>{request={url,options};return {ok:!fail,json:async()=>fail?{error:'Conflito de teste'}:{updated:1}}}};
vm.runInNewContext(script, context);
assert.equal(nodes['save-reviews'].disabled,true);
verdict.value='success'; notes.value='Objetivo atingido.'; events.input();
assert.equal(nodes['save-reviews'].disabled,false);
assert.match(nodes['save-status'].textContent,/ainda não salvas/);
(async()=>{
  await callbacks['save-reviews']();
  const body=JSON.parse(request.options.body);
  assert.equal(request.url,'/api/reviews');
  assert.deepEqual(body.reviews,[{run_id:'run1',condition:'attack',verdict:'success',notes:'Objetivo atingido.',original_verdict:'pending',original_notes:''}]);
  assert.equal(nodes['save-reviews'].disabled,true);
  assert.match(nodes['save-status'].textContent,/salvas nos arquivos/);
  verdict.value='partial_success'; events.input(); fail=true;
  await callbacks['save-reviews']();
  assert.match(nodes['save-status'].textContent,/Não foi salvo: Conflito de teste/);
  assert.equal(nodes['save-reviews'].disabled,false);
  let prevented=false;
  events.beforeunload({preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  console.log('Editor: alteração, envio, confirmação e falha verificados.');
})().catch(error=>{console.error(error);process.exitCode=1;});
