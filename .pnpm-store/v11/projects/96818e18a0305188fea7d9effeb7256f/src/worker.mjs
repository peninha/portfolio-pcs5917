import { Problem, command, view, exportCSV, addAudit } from './domain.mjs';
import { readState, mutate } from './storage.mjs';

export const token=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
export const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');
const fail=(message,status=400)=>{throw new Problem(message,status);};
const json=(data,status=200,extra={})=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...extra}});
function cookie(request,value,maxAge=60*60*24*30) {
  return `hepic_session=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${new URL(request.url).protocol==='https:'?'; Secure':''}`;
}
async function body(request) {
  if(!request.headers.get('content-type')?.includes('application/json'))fail('Envie JSON.',415);
  const reader=request.body?.getReader();if(!reader)fail('Corpo vazio.');
  const chunks=[];let size=0;
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>5*1024*1024){await reader.cancel();fail('Envie no máximo 5 MB por importação.',413);}chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.byteLength;}
  try{return JSON.parse(new TextDecoder().decode(bytes));}catch{fail('JSON inválido.');}
}
async function authenticate(request,db,state) {
  const raw=request.headers.get('cookie')?.match(/(?:^|;\s*)hepic_session=([a-f0-9]{64})(?:;|$)/)?.[1];
  if(!raw)fail('Entre com seu convite ou acesso de pesquisador.',401);
  const session=await db.prepare("SELECT user_id FROM tokens WHERE hash=? AND kind='session' AND expires_at>?").bind(await digest(raw),Date.now()).first();
  const user=session&&state.users.find(u=>u.id===session.user_id);if(!user)fail('Sessão expirada. Solicite um novo convite ao pesquisador.',401);return user;
}
async function newSession(db,userId) {
  const raw=token();await db.prepare("INSERT INTO tokens(hash,user_id,kind,expires_at) VALUES (?,?,'session',?)").bind(await digest(raw),userId,Date.now()+30*24*3600000).run();return raw;
}
async function limitAuth(request,db) {
  const ip=request.headers.get('CF-Connecting-IP')||'local';
  const bucket=`${Math.floor(Date.now()/900000)}:${await digest(ip)}`;
  const r=await db.prepare('INSERT INTO auth_limits(bucket,count) VALUES (?,1) ON CONFLICT(bucket) DO UPDATE SET count=count+1 RETURNING count').bind(bucket).first();
  if(r.count>30)fail('Muitas tentativas. Aguarde até 15 minutos.',429);
  // Keep auth metadata bounded without recording IPs or plaintext tokens.
  await db.batch([db.prepare('DELETE FROM auth_limits WHERE CAST(substr(bucket,1,instr(bucket,\':\')-1) AS INTEGER) < ?').bind(Math.floor(Date.now()/900000)-2),db.prepare('DELETE FROM tokens WHERE expires_at<?').bind(Date.now())]);
}

async function api(request,env) {
  if(!env.DB)fail('Banco de dados não configurado.',503);
  const db=env.DB.withSession?env.DB.withSession('first-primary'):env.DB;
  const url=new URL(request.url),path=url.pathname;
  if(!['GET','POST'].includes(request.method))fail('Método não permitido.',405);
  if(request.method==='POST') {
    if(request.headers.get('origin')!==url.origin)fail('Origem da solicitação não permitida.',403);
    if(request.headers.get('sec-fetch-site')==='cross-site')fail('Solicitação entre sites não permitida.',403);
  }
  if(path==='/api/status'&&request.method==='GET') {
    const {state}=await readState(db);return json({initialized:state.users.length>0,configured:Boolean(env.BOOTSTRAP_SECRET)});
  }
  if(path==='/api/bootstrap'&&request.method==='POST') {
    await limitAuth(request,db);const input=await body(request);
    if(!env.BOOTSTRAP_SECRET||env.BOOTSTRAP_SECRET.length<32)fail('Configure BOOTSTRAP_SECRET com pelo menos 32 caracteres.',503);
    if(typeof input.secret!=='string'||input.secret.length>500||await digest(input.secret)!==await digest(env.BOOTSTRAP_SECRET))fail('Chave do pesquisador inválida.',401);
    const user=await mutate(db,s=>{
      if(s.users.length)return s.users.find(u=>u.admin);
      const name=typeof input.name==='string'?input.name.trim().slice(0,100):'';
      if(!name)fail('Informe o nome do pesquisador.');
      const u={id:crypto.randomUUID(),name,admin:true};s.users.push(u);addAudit(s,u,'initialize',{},new Date().toISOString());return u;
    });
    return json({user},200,{'Set-Cookie':cookie(request,await newSession(db,user.id))});
  }
  if(path==='/api/invite'&&request.method==='POST') {
    await limitAuth(request,db);const {code}=await body(request);if(typeof code!=='string'||!/^[a-f0-9]{64}$/.test(code))fail('Convite inválido.',401);
    const raw=token(),hashed=await digest(raw);
    const results=await db.batch([
      db.prepare("INSERT INTO tokens(hash,user_id,kind,expires_at) SELECT ?,user_id,'session',? FROM tokens WHERE hash=? AND kind='invite' AND expires_at>?").bind(hashed,Date.now()+30*24*3600000,await digest(code),Date.now()),
      db.prepare("DELETE FROM tokens WHERE hash=? AND kind='invite'").bind(await digest(code))
    ]);
    if(!results[0].meta.changes)fail('O convite expirou ou já foi usado. Solicite outro ao pesquisador.',401);
    return json({ok:true},200,{'Set-Cookie':cookie(request,raw)});
  }
  const {state}=await readState(db),user=await authenticate(request,db,state);
  if(path==='/api/state'&&request.method==='GET')return json(view(state,user,user.admin||url.searchParams.get('mode')==='admin'));
  if(path==='/api/logout'&&request.method==='POST') {
    const raw=request.headers.get('cookie')?.match(/hepic_session=([a-f0-9]{64})/)?.[1];
    if(raw)await db.prepare('DELETE FROM tokens WHERE hash=?').bind(await digest(raw)).run();
    return json({ok:true},200,{'Set-Cookie':cookie(request,'',0)});
  }
  if(path==='/api/invitations'&&request.method==='POST') {
    if(!user.admin)fail('Acesso restrito ao pesquisador.',403);
    const {userId}=await body(request);if(!state.users.some(u=>u.id===userId&&!u.admin))fail('Avaliador inexistente.');
    const code=token();
    await db.batch([
      db.prepare('DELETE FROM tokens WHERE user_id=?').bind(userId),
      db.prepare("INSERT INTO tokens(hash,user_id,kind,expires_at) VALUES (?,?,'invite',?)").bind(await digest(code),userId,Date.now()+7*24*3600000)
    ]);
    return json({url:`${url.origin}/#invite=${code}`,expiresInDays:7});
  }
  if(path==='/api/command'&&request.method==='POST') {
    const input=await body(request);
    await mutate(db,s=>{const actor=s.users.find(u=>u.id===user.id);command(s,actor,input);});
    return json({ok:true});
  }
  if(path==='/api/export'&&request.method==='GET') {
    if(!user.admin)fail('Acesso restrito ao pesquisador.',403);
    const kind=url.searchParams.get('kind');
    if(!['results','ratings','backup'].includes(kind))fail('Exportação inválida.');
    return new Response(kind==='backup'?JSON.stringify(state,null,2):exportCSV(state,kind),{headers:{'Content-Type':kind==='backup'?'application/json; charset=utf-8':'text/csv; charset=utf-8','Content-Disposition':`attachment; filename="hepic-${kind}-${new Date().toISOString().slice(0,10)}.${kind==='backup'?'json':'csv'}"`,'Cache-Control':'no-store'}});
  }
  fail('Rota não encontrada.',404);
}
export default {
  async fetch(request,env) {
    try {
      const response=new URL(request.url).pathname.startsWith('/api/')?await api(request,env):await env.ASSETS.fetch(request);
      const secured=new Response(response.body,response);
      secured.headers.set('X-Content-Type-Options','nosniff');
      secured.headers.set('Referrer-Policy','no-referrer');
      secured.headers.set('X-Frame-Options','DENY');
      secured.headers.set('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
      return secured;
    } catch(error) {
      if(error instanceof Problem)return json({error:error.message},error.status);
      // Do not log dataset content, request bodies, session tokens, or invites.
      return json({error:'Não foi possível concluir a operação. Seus dados enviados anteriormente permanecem salvos. Verifique a configuração do banco ou tente novamente.'},500);
    }
  }
};
