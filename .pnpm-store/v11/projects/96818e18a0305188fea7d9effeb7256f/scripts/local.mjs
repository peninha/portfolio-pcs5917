import http from 'node:http';
import { readFile, mkdir, writeFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';
import { Readable } from 'node:stream';
import worker, { token } from '../src/worker.mjs';
import { SQLiteD1 } from './sqlite-d1.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const local=resolve(root,process.env.DATA_DIR||'.local');await mkdir(local,{recursive:true});
const db=new SQLiteD1(resolve(local,'hepic.sqlite'));
db.sqlite.exec(await readFile(resolve(root,'migrations/0001_initial.sql'),'utf8'));
const keyFile=resolve(local,'bootstrap.key');let secret=process.env.BOOTSTRAP_SECRET;
if(!secret){try{secret=(await readFile(keyFile,'utf8')).trim();}catch{secret=token();await writeFile(keyFile,secret,{mode:0o600});}}
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml'};
const publicRoot=resolve(root,'public');
const assets={async fetch(request){
  let name;try{name=decodeURIComponent(new URL(request.url).pathname);}catch{return new Response('URL inválida',{status:400});}
  let path=resolve(publicRoot,'.'+(name==='/'?'/index.html':name));
  if(!path.startsWith(publicRoot+sep))return new Response('Não encontrado',{status:404});
  try{if(!(await stat(path)).isFile())throw Error();return new Response(await readFile(path),{headers:{'Content-Type':types[extname(path)]||'application/octet-stream'}});}catch{return new Response('Não encontrado',{status:404});}
}};
const server=http.createServer(async(req,res)=>{
  try{
    const port=server.address().port;
    const request=new Request(`http://127.0.0.1:${port}${req.url}`,{method:req.method,headers:req.headers,...(['GET','HEAD'].includes(req.method)?{}:{body:Readable.toWeb(req),duplex:'half'})});
    const response=await worker.fetch(request,{DB:db,ASSETS:assets,BOOTSTRAP_SECRET:secret});
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  }catch{res.writeHead(500);res.end('Erro no servidor local.');}
});
server.listen(Number(process.env.PORT||8787),'127.0.0.1',()=>{
  console.log(`HEPIC: http://127.0.0.1:${server.address().port}`);
  console.log(`Chave do pesquisador: leia o arquivo ${keyFile}`);
  console.log('Modo local: dados em .local/hepic.sqlite. Para acesso remoto, publique no Cloudflare.');
});
