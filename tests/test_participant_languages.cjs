"use strict";
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(storage=new Map()){
 const calls=[],select={value:'vi',addEventListener(t,fn){this[t]=fn;}};let api;
 const input={value:'',focus(){},addEventListener(){}};
 const c={window:null,document:{visibilityState:'visible',querySelector:s=>s==='[data-cab-chat-input]'?input:null,querySelectorAll:s=>s==='[data-harness-language]'?[select]:[]},location:{hash:'#/session/maestro/circle'},
  sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},crypto:{randomUUID:()=>String(calls.length)+'-nonce'},
  fetch:async(url,options)=>{if(url.endsWith('auth/me'))return new Promise(()=>{});calls.push({url,options});let data={};
   if(url.endsWith('/transcriptions'))data={text:'Reviewed source text'};
   else if(url.endsWith('/sessions'))data={sessions:[]};
   else if(url.endsWith('/heart'))data={counters:{}};
   else if(url.endsWith('/lesson'))data={revision:0,steps:[]};
   else if(/\/sessions\/one$/.test(url))data={id:'one',state:'active',deliveries:[]};
   return{ok:true,status:200,json:async()=>data,headers:{get:()=>api.state.user.id}};},
  SomAudio:{start:async()=>({result:Promise.resolve('wav-fixture'),stop(){}})},
  setInterval(){},addEventListener(){},render(){},scrollX:0,scrollY:0,scrollTo(){},AbortController,P01:{state:{lang:'en'}}};
 c.window=c;vm.createContext(c);vm.runInContext(fs.readFileSync(require.resolve('../web/harness-client.js'),'utf8'),c);api=c.CabinetHarness;
 Object.assign(api.state,{user:{id:'M',role:'maestro'},meeting:{id:'one',state:'active',deliveries:[]},asr:true});api.bind();return{api,c,calls,select,input,storage};
}
test('speaking language is independently selectable for a Maestro and persists per account',()=>{
 const f=fixture();assert.equal(typeof f.api.languagePair,'function');assert.match(f.api.languageControls(),/data-harness-language/);
 assert.equal(f.api.languagePair().source,'en');f.select.change({currentTarget:f.select});assert.equal(f.api.languagePair().source,'vi');assert.equal(f.calls.length,0);
 f.api.state.user={id:'A',role:'artist'};assert.equal(f.api.languagePair().source,'vi');f.select.value='en';f.select.change({currentTarget:f.select});assert.equal(f.api.languagePair().source,'en');
 f.api.state.user={id:'M',role:'maestro'};assert.equal(f.api.languagePair().source,'vi');const second=fixture(f.storage);assert.equal(second.api.languagePair().source,'vi');
});
test('explicit send uses the chosen language while keeping the real role and account marker',async()=>{
 const f=fixture();f.select.change({currentTarget:f.select});await f.api.send('Play slowly.','maestro');
 const request=f.calls.find(x=>x.url.endsWith('/messages'));const data=JSON.parse(request.options.body);
 assert.equal(data.source_lang,'vi');assert.equal(data.target_lang,'en');assert.equal(data.speaker,'maestro');assert.equal(request.options.headers['X-SOM-Participant'],'M');
});
test('ASR uses participant language and leaves the transcription editable without sending',async()=>{
 const f=fixture();f.select.change({currentTarget:f.select});await f.api.record();
 const r=f.calls.find(x=>x.url.endsWith('/transcriptions'));assert.equal(JSON.parse(r.options.body).language,'vi');assert.equal(f.input.value,'Reviewed source text');assert.ok(!f.calls.some(x=>x.url.endsWith('/messages')));
});
test('private RTC transport cannot override the explicitly selected dictation language',async()=>{
 const f=fixture();f.select.change({currentTarget:f.select});let legacyCalled=false;
 f.c.SomMedia={connected:()=>true,record:async()=>{legacyCalled=true;throw Error('role-fixed RTC transcription must not be used');},mount(){}};
 await f.api.record();assert.equal(legacyCalled,false);
 const r=f.calls.find(x=>x.url.endsWith('/transcriptions'));assert.equal(JSON.parse(r.options.body).language,'vi');
});
test('selected speaking language still applies when browser storage is blocked',()=>{
 const f=fixture();f.c.sessionStorage.getItem=()=>{throw Error('SecurityError')};f.c.sessionStorage.setItem=()=>{throw Error('SecurityError')};
 f.select.change({currentTarget:f.select});assert.equal(f.api.languagePair().source,'vi');
 f.api.state.user={id:'A',role:'artist'};f.select.value='en';f.select.change({currentTarget:f.select});assert.equal(f.api.languagePair().source,'en');
 f.api.state.user={id:'M',role:'maestro'};assert.equal(f.api.languagePair().source,'vi');
});
