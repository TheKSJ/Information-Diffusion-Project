/* Failure-mode tests execute the actual client code without a browser or extra packages. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../src/eventstudy/web/app.js'),'utf8').replace(/boot\(\);\s*$/, '');

function client() {
  const elements = new Map();
  function element(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      innerHTML:'', textContent:'', content:'old-token', hidden:false, disabled:false, clientWidth:380,
      scrollHeight:0, clientHeight:0, scrollTop:0, attributes:{}, classes:new Set(),
      setAttribute(key,value){this.attributes[key]=value;}, removeAttribute(key){delete this.attributes[key];},
      classList:{toggle(){}}, closest(){return element('table');}, insertAdjacentHTML(position,text){this.innerHTML=text+this.innerHTML;},
      addEventListener(){}, querySelector(){return null;}, scrollIntoView(){}, focus(){}
    });
    return elements.get(selector);
  }
  const tasks=[element('task-tests'),element('task-demo')];
  const context=vm.createContext({
    document:{querySelector:element,querySelectorAll:selector=>selector==='[data-task]'?tasks:[],addEventListener(){},createElement:()=>element('created')},
    window:{innerWidth:443,addEventListener(){},scrollTo(){},matchMedia:()=>({matches:true})},
    location:{hash:''},URL,URLSearchParams,AbortController,setTimeout:()=>1,clearTimeout(){},setInterval(){},
    fetch:async()=>{throw new TypeError('Failed to fetch');}, console
  });
  vm.runInContext(source, context);
  return {context,element,tasks,run:code=>vm.runInContext(code,context)};
}
const response=body=>({ok:true,status:200,json:async()=>body});
const overview={ready:false,revision:'new-data',summary:{},primary:{},universe:[],facets:{}};

test('missing financial values stay unavailable; zero and negative signs remain valid',()=>{
  const c=client();
  assert.equal(c.run('percent(null)'),'—');
  assert.equal(c.run('percent(0)'),'0.00%');
  assert.equal(c.run('percent(-0.0123)'),'−1.23%');
  assert.equal(c.run('pp(0.5010637)'),'+0.501');
});

test('a missing return breaks the plotted path instead of bridging the gap',()=>{
  const c=client();
  const html=c.run('lineChart([{offset:-5,value:1},{offset:-4,value:null},{offset:-3,value:2}],{value:"value"})');
  assert.equal((html.match(/class="chart-line"/g)||[]).length,2);
  const empty=c.run('lineChart([{offset:0,value:null}],{value:"value"})');
  assert.match(empty,/No return window/);
});

test('API network failure exposes disconnection and disables task controls',async()=>{
  const c=client();
  await assert.rejects(c.run('api("/api/jobs")'),/Open Research Desk.cmd/);
  assert.equal(c.element('#connection-banner').hidden,false);
  assert.equal(c.element('#connection-label').textContent,'Disconnected');
  assert.ok(c.tasks.every(button=>button.disabled));
});

test('initial connection failure can recover without reloading the page',async()=>{
  const c=client();
  await c.run('pollJobs()');
  assert.match(c.element('#main').innerHTML,/Start the local research desk/);
  c.context.fetch=async url=>response(url==='/api/overview'?overview:{jobs:[],active_id:null,instance_id:'new-server',data_revision:'new-data',session_token:'new-token'});
  await c.run('pollJobs()');
  assert.equal(c.element('#connection-label').textContent,'Connected');
  assert.equal(c.element('meta[name="research-token"]').content,'new-token');
  assert.ok(c.tasks.every(button=>!button.disabled));
});

test('server restart renews the token and refreshes the saved data',async()=>{
  const c=client();
  c.run('state.overview={ready:false};state.instance="old-server";state.dataRevision="old-data"');
  const calls=[];
  c.context.fetch=async url=>{calls.push(url);return response(url==='/api/overview'?overview:{jobs:[],active_id:null,instance_id:'new-server',data_revision:'new-data',session_token:'fresh-token'});};
  await c.run('pollJobs()');
  assert.deepEqual(calls,['/api/jobs','/api/overview']);
  assert.equal(c.run('state.instance'),'new-server');
  assert.equal(c.element('meta[name="research-token"]').content,'fresh-token');
});

test('rapid clicks submit one task with the current session token',async()=>{
  const c=client();c.run('state.connected=true');
  let release;const calls=[];
  c.context.fetch=async(url,options)=>{
    calls.push({url,options});
    if(url==='/api/session')return new Promise(resolve=>{release=()=>resolve(response({token:'current-token'}));});
    return response({id:'job-1',title:'Verification',status:'queued',lines:[]});
  };
  const first=c.run('startTask("tests")');
  const second=c.run('startTask("demo")');
  assert.equal(calls.length,1);
  release();await Promise.all([first,second]);
  assert.equal(calls.length,2);
  assert.equal(calls[1].options.headers['X-Research-Token'],'current-token');
  assert.equal(JSON.parse(calls[1].options.body).action,'tests');
  assert.equal(c.run('state.activeJob'),'job-1');
});

test('a lost POST response is never retried automatically',async()=>{
  const c=client();c.run('state.connected=true');let posts=0;
  c.context.fetch=async(url)=>{if(url==='/api/session')return response({token:'fresh'});posts++;throw new TypeError('Network failed');};
  await c.run('startTask("tests")');
  assert.equal(posts,1);
  assert.equal(c.run('state.starting'),false);
  assert.equal(c.run('state.connected'),false);
});

test('HTTP validation errors are reported without falsely declaring the server offline',async()=>{
  const c=client();c.run('state.connected=true');
  c.context.fetch=async()=>({ok:false,status:409,json:async()=>({error:'A task is already running'})});
  await assert.rejects(c.run('api("/api/jobs")'),/already running/);
  assert.equal(c.run('state.connected'),true);
});

test('a late event search response cannot replace the newly selected view',async()=>{
  const c=client();c.run('state.view="events"');let release;
  c.element('#events-body').innerHTML='original';
  c.context.fetch=async()=>new Promise(resolve=>{release=()=>resolve(response({total:0,page:1,limit:12,items:[]}));});
  const pending=c.run('loadEvents()');
  c.run('state.view="overview";state.request++');
  release();await pending;
  assert.equal(c.element('#events-body').innerHTML,'original');
});
