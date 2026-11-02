import { DatabaseSync } from 'node:sqlite';
export class SQLiteD1 {
  constructor(path=':memory:'){this.sqlite=new DatabaseSync(path);this.sqlite.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;');}
  prepare(sql){return new Statement(this,sql);}
  async batch(statements){
    this.sqlite.exec('BEGIN');
    try{const results=statements.map(s=>s.execute());this.sqlite.exec('COMMIT');return results;}
    catch(e){this.sqlite.exec('ROLLBACK');throw e;}
  }
  close(){this.sqlite.close();}
}
class Statement {
  constructor(db,sql,params=[]){Object.assign(this,{db,sql,params});}
  bind(...params){return new Statement(this.db,this.sql,params);}
  execute(){
    const s=this.db.sqlite.prepare(this.sql);
    const read=/^\s*(SELECT|WITH|PRAGMA)/i.test(this.sql)||/\bRETURNING\b/i.test(this.sql);
    if(read){const results=s.all(...this.params);return {results,meta:{changes:/^\s*(SELECT|WITH|PRAGMA)/i.test(this.sql)?0:results.length}};}
    const r=s.run(...this.params);return {results:[],meta:{changes:Number(r.changes)}};
  }
  async first(){return this.execute().results[0]??null;}
  async run(){return this.execute();}
}
