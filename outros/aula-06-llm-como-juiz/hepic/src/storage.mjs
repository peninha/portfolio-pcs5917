import { initialState, migrateState, Problem } from './domain.mjs';

export async function readState(db) {
  const r=await db.batch([
    db.prepare('SELECT COALESCE(MAX(revision), 0) AS revision FROM commits'),
    db.prepare('SELECT data FROM state_chunks ORDER BY part')
  ]);
  return {revision:r[0].results[0].revision,state:r[1].results.length?migrateState(JSON.parse(r[1].results.map(c=>c.data).join(''))):initialState()};
}
export async function mutate(db,change) {
  for(let attempt=0;attempt<5;attempt++) {
    const {revision,state}=await readState(db);
    const result=await change(state);
    const json=JSON.stringify(state);
    if(new TextEncoder().encode(json).byteLength>8*1024*1024) throw new Problem('O estudo excedeu 8 MB de estado. Exporte um backup e abra outro estudo antes de acrescentar dados.',413);
    const chunks=[];
    for(let i=0;i<json.length;) {
      let end=Math.min(i+250000,json.length);
      if(end<json.length&&/[\uD800-\uDBFF]/.test(json[end-1]))end--;
      chunks.push(json.slice(i,end));i=end;
    }
    try {
      // First statement is a compare-and-swap fence: only one writer can claim
      // revision+1. D1 batch rolls back every statement on any constraint failure.
      await db.batch([
        db.prepare('INSERT INTO commits(revision, created_at) VALUES (?, ?)').bind(revision+1,new Date().toISOString()),
        db.prepare('DELETE FROM state_chunks'),
        ...chunks.map((data,part)=>db.prepare('INSERT INTO state_chunks(part, data) VALUES (?, ?)').bind(part,data))
      ]);
      return result;
    } catch(error) {
      if(!String(error.message).includes('UNIQUE constraint failed: commits.revision'))throw error;
    }
  }
  throw new Problem('Outra avaliação foi salva simultaneamente. Tente novamente; sua nota ainda não foi enviada.',409);
}
