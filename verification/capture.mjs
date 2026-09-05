import { writeFile, mkdir } from 'node:fs/promises';

const [base = 'https://docs.replit.com', label = 'production'] = process.argv.slice(2);
const targets = await fetch('http://127.0.0.1:9230/json/list').then(r => r.json());
const page = targets.find(t => t.type === 'page');
const socket = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve,reject) => {socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let id=0;const pending=new Map();
socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(!m.id)return;const p=pending.get(m.id);if(!p)return;pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);});
function send(method,params={}) {const requestId=++id;socket.send(JSON.stringify({id:requestId,method,params}));return new Promise((resolve,reject)=>pending.set(requestId,{resolve,reject}));}
const sleep = ms=>new Promise(r=>setTimeout(r,ms));
await mkdir('verification/screenshots',{recursive:true});
await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
const routes = [['welcome','/'],['agent','/replitai/agent'],['deployments','/cloud-services/deployments/about-deployments']];
const observations=[];
for(const [name,path] of routes){
 for(const viewport of [{name:'desktop',width:1440,height:1000,mobile:false},{name:'mobile',width:390,height:844,mobile:true}]){
  await send('Emulation.setDeviceMetricsOverride',{...viewport,name:undefined,deviceScaleFactor:1});
  for(const theme of ['light','dark']){
   await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
   await send('Page.navigate',{url:base+path});await sleep(4000);
   await send('Runtime.evaluate',{expression:`localStorage.setItem('theme','${theme}');document.documentElement.classList.toggle('dark',${theme==='dark'});document.documentElement.classList.toggle('light',${theme==='light'});window.scrollTo(0,0)`});
   await sleep(900);
   const data=await send('Runtime.evaluate',{expression:`JSON.stringify({url:location.href,title:document.title,theme:document.documentElement.className,body:{font:getComputedStyle(document.body).fontFamily,background:getComputedStyle(document.body).backgroundColor},h1:[...document.querySelectorAll('h1')].map(e=>({text:e.innerText,box:e.getBoundingClientRect().toJSON(),font:getComputedStyle(e).fontFamily,size:getComputedStyle(e).fontSize})),links:[...document.querySelectorAll('header a')].map(e=>({text:e.innerText,href:e.getAttribute('href')})),buttons:[...document.querySelectorAll('button')].map(e=>({text:e.innerText,label:e.getAttribute('aria-label')})).slice(0,25),errors:[...document.images].filter(e=>!e.complete||e.naturalWidth===0).map(e=>e.src)})`,returnByValue:true});
   observations.push({name,viewport:viewport.name,theme,...JSON.parse(data.result.value)});
   const screenshot=await send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});
   await writeFile(`verification/screenshots/${label}-${name}-${viewport.name}-${theme}.png`,screenshot.data,'base64');
   console.log(`${label} ${name} ${viewport.name} ${theme}`);
  }
 }
}
await writeFile(`verification/${label}-observations.json`,JSON.stringify(observations,null,2)+'\n');
socket.close();
