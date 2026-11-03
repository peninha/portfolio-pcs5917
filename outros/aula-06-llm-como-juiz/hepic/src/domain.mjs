import { normalizeItems, csv } from './import.mjs';

export class Problem extends Error {
  constructor(message, status=400) { super(message); this.status=status; }
}
const must=(condition,message,status=400)=>{if(!condition) throw new Problem(message,status);};
const uid=()=>crypto.randomUUID();
export const raters=s=>s.users.filter(u=>!u.admin);
const validScore=s=>Number.isInteger(s)&&s>=0&&s<=2;
const rationale=x=>{must(typeof x==='string' && x.trim().length>=3 && x.length<=4000,'Escreva uma justificativa de 3 a 4.000 caracteres.'); return x.trim();};
const optionalObservation=x=>{if(x==null)return '';must(typeof x==='string'&&x.length<=4000,'A observação deve ter até 4.000 caracteres.');return x.trim();};
function researcherDecision(cmd,actor,now) {
  must(cmd.outcome==null||['scored','inconclusive'].includes(cmd.outcome),'Tipo de decisão inválido.');
  const inconclusive=cmd.outcome==='inconclusive';
  must(inconclusive?cmd.score==null:validScore(cmd.score),'Escolha uma nota de 0 a 2 ou Inconclusivo, sem nota numérica.');
  return {outcome:inconclusive?'inconclusive':'scored',score:inconclusive?null:cmd.score,justification:inconclusive?rationale(cmd.justification):optionalObservation(cmd.justification),at:now,actor:actor.id};
}
const excluded=(c,id)=>Boolean(c.inconclusives?.[id]);
const resultIds=c=>[...new Set([...c.evaluationIds,...Object.keys(c.inconclusives??{})])];
const submitted=a=>validScore(a.score)||a.outcome==='inconclusive';
const numericScores=list=>list.filter(a=>validScore(a.score)).map(a=>a.score);
function needsReview(list,threshold){const d=disagreement(numericScores(list));return list.some(a=>a.outcome==='inconclusive')||(d!==null&&d>threshold);}

export function disagreement(scores) {
  if(scores.length<2) return null;
  must(scores.every(validScore),'Notas inválidas.');
  let sum=0;
  for(let i=0;i<scores.length;i++) for(let j=i+1;j<scores.length;j++) sum+=Math.abs(scores[i]-scores[j]);
  return sum/(scores.length*(scores.length-1));
}
export function median(scores) {
  if(!scores.length) return null;
  const s=[...scores].sort((a,b)=>a-b), n=s.length;
  return n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;
}
export function random(seed) {
  let h=2166136261;
  for(const c of String(seed)) h=Math.imul(h^c.charCodeAt(0),16777619);
  return ()=>{h+=0x6D2B79F5;let t=h;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
}
export function shuffle(items,seed) {
  const a=[...items], rng=random(seed);
  for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];} return a;
}
export function stratifiedSample(items,k,seed) {
  must(k>0&&items.length>=k,`A rodada precisa de ${k} itens inéditos; há ${items.length}. Importe mais itens antes de iniciar a próxima rodada.`);
  const groups=new Map();
  for(const item of items){const key=[item.method,item.target,item.language].join('|');if(!groups.has(key)) groups.set(key,[]);groups.get(key).push(item);}
  const strata=[...groups].map(([key,rows])=>({key,rows:shuffle(rows,`${seed}:${key}`),count:0,weight:rows.length/items.length}));
  // Largest remainders preserve proportions; seeded tie order avoids lexical bias.
  const order=shuffle(strata,seed);
  for(const g of order) g.count=Math.floor(k*g.weight);
  let left=k-order.reduce((a,g)=>a+g.count,0);
  for(const g of [...order].sort((a,b)=>(k*b.weight-b.count)-(k*a.weight-a.count))) if(left>0&&g.count<g.rows.length){g.count++;left--;}
  return shuffle(order.flatMap(g=>g.rows.slice(0,g.count)),`${seed}:final`);
}
export function distribute(itemIds,userIds,q,seed) {
  const n=itemIds.length,m=userIds.length;
  must(q>=1/m&&q<=1,'A fração individual deve cobrir a base e não ultrapassar 100%.');
  const capacity=Math.ceil(q*n), loads=Object.fromEntries(userIds.map(id=>[id,0]));
  const owners=new Map(itemIds.map(id=>[id,[]])); const pairs={};
  const pair=(a,b)=>[a,b].sort().join(':');
  const orderedUsers=shuffle(userIds,seed), orderedItems=shuffle(itemIds,seed);
  const assign=(itemId,userId)=>{
    for(const other of owners.get(itemId)){const k=pair(other,userId);pairs[k]=(pairs[k]||0)+1;}
    owners.get(itemId).push(userId);loads[userId]++;
  };
  for(const id of orderedItems){const u=[...orderedUsers].sort((a,b)=>loads[a]-loads[b])[0];assign(id,u);}
  for(const u of orderedUsers) while(loads[u]<capacity) {
    const candidates=orderedItems.filter(id=>!owners.get(id).includes(u));
    candidates.sort((a,b)=>owners.get(a).length-owners.get(b).length ||
      owners.get(a).reduce((s,o)=>s+(pairs[pair(o,u)]||0),0)-owners.get(b).reduce((s,o)=>s+(pairs[pair(o,u)]||0),0));
    must(candidates.length,'Não foi possível distribuir os itens.'); assign(candidates[0],u);
  }
  return [...owners].flatMap(([itemId,owners])=>owners.map(userId=>({itemId,userId})));
}

const newCycle=(config={})=>({id:uid(),phase:'setup',config:{threshold:0.33,sampleSize:9,fraction:0.4,seed:'hepic-2026',...config},trained:{},rounds:[],assignments:[],adjudications:{},inconclusives:{},evaluationIds:[],startedAt:null});
export function initialState() {
  return {schema:2,title:'HEPIC · Aula 6',users:[],items:[],references:{},referenceVersion:1,referenceHistory:[],cycle:newCycle(),archives:[],audit:[]};
}
// Separate historical evaluator activity from the researcher without changing
// any scores, decisions, assignments or timestamps. IDs are deterministic so
// concurrent reads see the same migration before the next atomic write.
export function migrateState(s) {
  if(s.schema!==1)return s;
  for(const researcher of s.users.filter(u=>u.admin)) {
    const cycles=[...s.archives,s.cycle];
    const participated=cycles.some(c=>c.assignments.some(a=>a.userId===researcher.id)||c.trained[researcher.id]);
    if(!participated)continue;
    const id=`${researcher.id}:rater`;
    s.users.push({id,name:`${researcher.name} (avaliador)`,admin:false});
    for(const c of cycles) {
      for(const a of c.assignments)if(a.userId===researcher.id)a.userId=id;
      if(c.trained[researcher.id]){c.trained[id]=c.trained[researcher.id];delete c.trained[researcher.id];}
    }
    for(const event of s.audit)if(event.actor===researcher.id&&['submit','acknowledge'].includes(event.type))event.actor=id;
  }
  s.schema=2;return s;
}
export function addAudit(s,actor,type,details,now) {s.audit.push({id:uid(),at:now,actor:actor.id,type,details});}
function rememberReferences(s,now) {
  s.referenceHistory.push({version:s.referenceVersion,at:now,references:structuredClone(s.references)});
}
function assignment(c,itemId,userId,phase,round,version) {return {id:uid(),cycleId:c.id,itemId,userId,phase,round,version,score:null,justification:null,submittedAt:null};}
function evaluationResult(s,itemId) {
  const c=s.cycle, exclusion=c.inconclusives?.[itemId];
  const list=c.assignments.filter(a=>a.itemId===itemId&&(exclusion?.phase==='calibration'?a.phase==='calibration'&&a.round===exclusion.round:a.phase==='evaluation'));
  const scores=numericScores(list),flagged=list.filter(a=>a.outcome==='inconclusive').length;
  const d=disagreement(scores), decision=c.adjudications[itemId]??c.inconclusives?.[itemId];
  let status=decision?.outcome==='inconclusive'?'inconclusive':list.some(a=>!submitted(a))?'pending':decision?'adjudicated':flagged?'adjudication':scores.length===1?'single':d>c.config.threshold?'adjudication':'agreement';
  return {itemId,status,ratings:scores.length,flagged,assigned:list.length,disagreement:d,finalScore:['single','agreement','adjudicated'].includes(status)?decision?.score??median(scores):null,decision};
}
function advanceEvaluation(s,itemId) {
  const c=s.cycle, result=evaluationResult(s,itemId);
  if(result.status==='adjudication'&&!result.flagged) {
    const used=c.assignments.filter(a=>a.itemId===itemId&&a.phase==='evaluation').map(a=>a.userId);
    const candidates=raters(s).filter(u=>!used.includes(u.id));
    candidates.sort((a,b)=>c.assignments.filter(x=>x.userId===a.id).length-c.assignments.filter(x=>x.userId===b.id).length);
    if(candidates.length) c.assignments.push(assignment(c,itemId,candidates[0].id,'evaluation',null,s.referenceVersion));
  }
  if(c.evaluationIds.every(id=>['single','agreement','adjudicated','inconclusive'].includes(evaluationResult(s,id).status))) c.phase='completed';
}

export function command(s,actor,cmd,now=new Date().toISOString()) {
  const c=s.cycle;
  must(actor && s.users.some(u=>u.id===actor.id),'Sessão inválida.',401);
  must(cmd.cycleId===c.id,'O ciclo mudou. Atualize a página antes de continuar.',409);
  const admin=()=>must(actor.admin,'Esta ação é exclusiva do pesquisador.',403);
  const rater=()=>must(!actor.admin,'Use um acesso de avaliador para registrar treinamento e notas. O pesquisador atua separadamente.',403);
  const phase=(...phases)=>must(phases.includes(c.phase),`Esta ação não está disponível na fase ${c.phase}.`,409);
  switch(cmd.type) {
    case 'configure': {
      admin();phase('setup');
      const {threshold,sampleSize,fraction,seed}=cmd;
      must(typeof threshold==='number'&&threshold>=0&&threshold<=1,'Limiar inválido.');
      must(Number.isInteger(sampleSize)&&sampleSize>=1&&sampleSize<=500,'A amostra deve conter de 1 a 500 itens.');
      must(typeof fraction==='number'&&fraction>=1/3&&fraction<=1,'A fração individual deve ficar entre 1/3 e 1.');
      must(typeof seed==='string'&&seed.trim().length>0&&seed.length<=200,'Semente inválida.');
      c.config={threshold,sampleSize,fraction,seed:seed.trim()};break;
    }
    case 'updateThreshold': {
      admin();phase('training');
      must(typeof cmd.threshold==='number'&&Number.isFinite(cmd.threshold)&&cmd.threshold>=0&&cmd.threshold<=1,'Limiar inválido.');
      const reason=rationale(cmd.reason),previous=c.config.threshold;
      must(cmd.threshold!==previous,'O novo limiar é igual ao atual.');
      const change={at:now,actor:actor.id,previous,next:cmd.threshold,reason,afterRound:c.rounds.length};
      (c.thresholdChanges??=[]).push(change);c.config.threshold=cmd.threshold;
      addAudit(s,actor,'threshold_changed',{cycleId:c.id,...change},now);break;
    }
    case 'addUser':
      admin();phase('setup');must(raters(s).length<3,'Esta versão utiliza exatamente três avaliadores, além do pesquisador.');
      must(typeof cmd.name==='string'&&cmd.name.trim()&&cmd.name.length<=100,'Informe o nome do avaliador.');
      s.users.push({id:uid(),name:cmd.name.trim(),admin:false});break;
    case 'import': {
      admin();phase('setup','training','calibration_review');
      const items=normalizeItems(cmd.data);const existing=new Map(s.items.map(i=>[i.id,i]));let added=0;
      for(const item of items) {
        const old=existing.get(item.id);
        if(old) must(JSON.stringify(old)===JSON.stringify(item),`O ID ${item.id} já existe com outro conteúdo. A importação não sobrescreve evidências.`,409);
        else {s.items.push(item);existing.set(item.id,item);added++;}
      }
      must(s.items.length<=5000,'Limite desta versão: 5.000 itens.');
      addAudit(s,actor,'import_details',{added,source:typeof cmd.source==='string'?cmd.source.slice(0,300):'arquivo'},now);break;
    }
    case 'reference': {
      admin();phase('setup','training');must(s.items.some(i=>i.id===cmd.itemId),'Item inexistente.');
      must(!excluded(c,cmd.itemId),'Este item já foi marcado como inconclusivo. Importe uma versão corrigida com outro ID.');
      const decision=researcherDecision(cmd,actor,now);
      const changedReferences=decision.outcome!=='inconclusive'||Boolean(s.references[cmd.itemId]);
      if(decision.outcome==='inconclusive') {
        (c.inconclusives??={})[cmd.itemId]={...decision,phase:'reference'};
        delete s.references[cmd.itemId];
      } else {
        must(!excluded(c,cmd.itemId),'Este item foi marcado como inconclusivo. Importe uma versão corrigida com outro ID.');
        s.references[cmd.itemId]=decision;
      }
      if(changedReferences){s.referenceVersion++;c.trained={};rememberReferences(s,now);}break;
    }
    case 'startTraining':
      admin();phase('setup');must(raters(s).length===3,'Cadastre os três avaliadores antes de começar. O pesquisador não entra nessa contagem.');
      must(Object.keys(s.references).length>0,'Cadastre pelo menos um exemplo de referência.');
      must(s.items.filter(i=>!s.references[i.id]&&!excluded(c,i.id)).length>=c.config.sampleSize,'A base precisa conter referências e itens suficientes para a calibração.');
      c.phase='training';c.startedAt=now;rememberReferences(s,now);break;
    case 'acknowledge':
      rater();
      phase('training');must(cmd.version===s.referenceVersion,'O material de referência foi atualizado. Leia a nova versão.',409);
      c.trained[actor.id]={version:cmd.version,at:now};break;
    case 'startCalibration': {
      admin();phase('training');must(raters(s).every(u=>c.trained[u.id]?.version===s.referenceVersion),'Todos precisam concluir o treinamento vigente.');
      must(Object.keys(s.references).length>0,'Cadastre pelo menos um exemplo de referência válido antes da calibração.');
      const seen=new Set(c.rounds.flatMap(r=>r.itemIds));
      const pool=s.items.filter(i=>!s.references[i.id]&&!seen.has(i.id)&&!excluded(c,i.id));
      const r={number:c.rounds.length+1,itemIds:[],failed:[],decisions:{},createdAt:now,referenceVersion:s.referenceVersion};
      r.itemIds=stratifiedSample(pool,c.config.sampleSize,`${c.config.seed}:${c.id}:${r.number}`).map(i=>i.id);
      c.rounds.push(r);
      for(const itemId of r.itemIds) for(const u of raters(s))c.assignments.push(assignment(c,itemId,u.id,'calibration',r.number,s.referenceVersion));
      c.phase='calibration';break;
    }
    case 'submit': {
      rater();
      phase('calibration','evaluation');
      const a=c.assignments.find(a=>a.id===cmd.assignmentId&&a.userId===actor.id);
      must(a,'Atribuição não encontrada.',404);must(a.phase===c.phase,'Atribuição de uma fase encerrada.',409);
      must(!submitted(a),'Esta avaliação já foi enviada e não pode ser sobrescrita.',409);
      must(cmd.outcome==null||['scored','inconclusive'].includes(cmd.outcome),'Tipo de avaliação inválido.');
      const flagged=cmd.outcome==='inconclusive';
      must(flagged?cmd.score==null:validScore(cmd.score),'Escolha uma nota inteira de 0 a 2 ou Inconclusivo, sem nota numérica.');
      a.justification=flagged?rationale(cmd.justification):optionalObservation(cmd.justification);a.score=flagged?null:cmd.score;
      a.outcome=flagged?'inconclusive':'scored';a.submittedAt=now;
      if(c.phase==='calibration') {
        const r=c.rounds.at(-1), tasks=c.assignments.filter(a=>a.phase==='calibration'&&a.round===r.number);
        if(tasks.every(submitted)) {
          r.completedAt=now;
          r.failed=r.itemIds.filter(id=>needsReview(tasks.filter(a=>a.itemId===id),c.config.threshold));
          c.phase=r.failed.length?'calibration_review':'calibrated';
        }
      } else advanceEvaluation(s,a.itemId);
      break;
    }
    case 'adjudicate': {
      admin();phase('calibration_review','evaluation');
      const decision=researcherDecision(cmd,actor,now);
      if(c.phase==='calibration_review') {
        const r=c.rounds.at(-1);must(r.failed.includes(cmd.itemId),'O item não aguarda adjudicação nesta rodada.');
        must(!r.decisions[cmd.itemId],'Este item já foi adjudicado.',409);r.decisions[cmd.itemId]=decision;
        if(decision.outcome==='inconclusive')(c.inconclusives??={})[cmd.itemId]={...decision,phase:'calibration',round:r.number};
        if(r.failed.every(id=>r.decisions[id])) {
          const numeric=r.failed.filter(id=>r.decisions[id].outcome!=='inconclusive');
          for(const id of numeric)s.references[id]=r.decisions[id];
          if(numeric.length){s.referenceVersion++;rememberReferences(s,now);c.trained={};}
          c.phase='training';
        }
      } else {
        must(evaluationResult(s,cmd.itemId).status==='adjudication','O item não aguarda adjudicação.');
        c.adjudications[cmd.itemId]=decision;
        if(decision.outcome==='inconclusive')(c.inconclusives??={})[cmd.itemId]={...decision,phase:'evaluation'};
        advanceEvaluation(s,cmd.itemId);
      }
      break;
    }
    case 'startEvaluation': {
      admin();phase('calibrated');
      const seen=new Set(c.rounds.flatMap(r=>r.itemIds));
      c.evaluationIds=s.items.filter(i=>!s.references[i.id]&&!seen.has(i.id)&&!excluded(c,i.id)).map(i=>i.id);
      must(c.evaluationIds.length,'Não há itens reservados para avaliação. Reinicie o ciclo e importe mais dados.');
      for(const {itemId,userId} of distribute(c.evaluationIds,raters(s).map(u=>u.id),c.config.fraction,`${c.config.seed}:${c.id}:evaluation`)) c.assignments.push(assignment(c,itemId,userId,'evaluation',null,s.referenceVersion));
      c.phase='evaluation';break;
    }
    case 'restart': {
      admin();must(c.phase!=='setup','O ciclo já está em preparação.');
      // A full new cycle preserves all old ratings and assignments for audit/export.
      for(const [id,decision] of Object.entries(c.adjudications))if(cmd.promoteAdjudications&&decision.outcome!=='inconclusive') s.references[id]=decision;
      s.archives.push({...structuredClone(c),archivedAt:now,referenceVersion:s.referenceVersion});
      s.referenceVersion++;rememberReferences(s,now);s.cycle=newCycle(c.config);
      s.cycle.inconclusives=structuredClone(c.inconclusives??{});break;
    }
    default:throw new Problem('Comando desconhecido.');
  }
  addAudit(s,actor,cmd.type,{cycleId:c.id,itemId:cmd.itemId??null,assignmentId:cmd.assignmentId??null},now);
  return s;
}

function blindItem(s,itemId) {
  const i=s.items.find(x=>x.id===itemId);
  return {label:`Item ${String(s.items.indexOf(i)+1).padStart(3,'0')}`,objective:i.objective,prompt:i.prompt,response:i.response};
}
export function view(s,actor,adminMode=false) {
  const c=s.cycle, own=c.assignments.filter(a=>a.userId===actor.id);
  const active=own.filter(a=>a.phase===c.phase && (a.phase!=='calibration'||a.round===c.rounds.at(-1)?.number));
  const data={user:actor,title:s.title,cycleId:c.id,phase:c.phase,config:c.config,referenceVersion:s.referenceVersion,
    trained:c.trained[actor.id]?.version===s.referenceVersion,
    references:Object.entries(s.references).map(([id,r])=>({item:blindItem(s,id),score:r.score,justification:r.justification})),
    tasks:active.filter(a=>!submitted(a)).map(a=>({id:a.id,item:blindItem(s,a.itemId)})),
    progress:{completed:active.filter(submitted).length,total:active.length},round:c.rounds.at(-1)?.number??0};
  if(adminMode) {
    must(actor.admin,'Acesso restrito ao pesquisador.',403);
    const round=c.rounds.at(-1);
    data.admin={users:raters(s).map(u=>({...u,trained:c.trained[u.id]?.version===s.referenceVersion,
      completed:c.assignments.filter(a=>a.userId===u.id&&submitted(a)).length,assigned:c.assignments.filter(a=>a.userId===u.id).length})),
      items:s.items.map(i=>({...i,reference:s.references[i.id]??null,inconclusive:c.inconclusives?.[i.id]??null})),
      review:c.phase==='calibration_review'?round.failed.filter(id=>!round.decisions[id]).map(itemId=>({itemId,item:blindItem(s,itemId),flagged:c.assignments.filter(a=>a.itemId===itemId&&a.round===round.number&&a.phase==='calibration'&&a.outcome==='inconclusive').length,scores:c.assignments.filter(a=>a.itemId===itemId&&a.round===round.number&&a.phase==='calibration').map(a=>({userId:a.userId,score:a.score,outcome:a.outcome??'scored',justification:a.justification})),disagreement:disagreement(numericScores(c.assignments.filter(a=>a.itemId===itemId&&a.round===round.number&&a.phase==='calibration')))})):c.evaluationIds.map(id=>evaluationResult(s,id)).filter(r=>r.status==='adjudication').map(r=>({...r,item:blindItem(s,r.itemId),scores:c.assignments.filter(a=>a.itemId===r.itemId&&a.phase==='evaluation').map(a=>({userId:a.userId,score:a.score,outcome:a.outcome??'scored',justification:a.justification}))})),
      results:resultIds(c).map(id=>evaluationResult(s,id)),rounds:c.rounds,archives:s.archives.map(c=>({id:c.id,phase:c.phase,archivedAt:c.archivedAt})),
      audit:s.audit.slice(-40).reverse(),totalItems:s.items.length};
  }
  return data;
}

export function exportCSV(s,kind='results') {
  const cycles=[...s.archives,s.cycle];
  if(kind==='ratings') {
    const rows=[['cycle','phase','round','item_id','evaluator_id','evaluator','reference_version','score','justification','submitted_at','outcome']];
    for(const c of cycles)for(const a of c.assignments)if(submitted(a)) rows.push([c.id,a.phase,a.round,a.itemId,a.userId,s.users.find(u=>u.id===a.userId)?.name,a.version,a.score,a.justification,a.submittedAt,a.outcome??'scored']);
    return csv(rows);
  }
  const rows=[['cycle','item_id','method','target','language','status','n_ratings','disagreement','final_score','adjudicated','threshold','seed','author','previous_result','objective','prompt','response','source','decision_outcome','researcher_observation','decision_phase','n_inconclusive_reports']];
  for(const c of cycles) for(const id of resultIds(c)) {
    const i=s.items.find(i=>i.id===id),r=evaluationResult({...s,cycle:c},id);
    rows.push([c.id,id,i.method,i.target,i.language,r.status,r.ratings,r.disagreement,r.finalScore,Boolean(c.adjudications[id]),c.config.threshold,c.config.seed,i.author,i.previous,i.objective,i.prompt,i.response,i.source,r.decision?.outcome??(r.decision?'scored':''),r.decision?.justification??'',c.inconclusives?.[id]?.phase??'evaluation',r.flagged]);
  }
  return csv(rows);
}
