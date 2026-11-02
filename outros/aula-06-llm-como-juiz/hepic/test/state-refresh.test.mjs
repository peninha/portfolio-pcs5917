import test from 'node:test';
import assert from 'node:assert/strict';
import {createStateRefresh} from '../public/state-refresh.js';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};

test('retorno do seletor não inicia atualização enquanto o arquivo está sendo escolhido',async()=>{
  let choosing=true,loads=0,renders=0;
  const sync=createStateRefresh({load:async()=>{loads++;return {};},apply:()=>renders++,canRefresh:()=>!choosing});
  assert.equal(await sync.refresh({background:true}),false);assert.equal(loads,0);assert.equal(renders,0);
  choosing=false;assert.equal(await sync.refresh({background:true}),true);assert.equal(renders,1);
});
test('atualização já em andamento não recria a tela se o seletor foi aberto depois',async()=>{
  const load=deferred();let choosing=false,renders=0;
  const sync=createStateRefresh({load:()=>load.promise,apply:()=>renders++,canRefresh:()=>!choosing});
  const pending=sync.refresh({background:true});assert.equal(sync.pending,true);
  choosing=true;load.resolve({});assert.equal(await pending,false);assert.equal(renders,0);assert.equal(sync.pending,false);
});
test('seleção e leitura concluídas antes da resposta de estado também impedem a recriação',async()=>{
  const load=deferred();let prepared=null,renders=0;
  const sync=createStateRefresh({load:()=>load.promise,apply:()=>renders++,canRefresh:()=>!prepared});
  const pending=sync.refresh({background:true});prepared={fileName:'Dados_Caio.csv',items:[{id:1}]};
  load.resolve({});assert.equal(await pending,false);assert.equal(renders,0);assert.equal(prepared.items.length,1);
});
test('resposta atrasada não substitui uma consulta mais recente',async()=>{
  const first=deferred(),second=deferred();let calls=0;const applied=[];
  const sync=createStateRefresh({load:()=>++calls===1?first.promise:second.promise,apply:s=>applied.push(s),canRefresh:()=>true});
  const a=sync.refresh(),b=sync.refresh();second.resolve('novo');await b;first.resolve('antigo');
  assert.equal(await a,false);assert.deepEqual(applied,['novo']);assert.equal(sync.pending,false);
});
