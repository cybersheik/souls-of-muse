"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
function fixture(){
  const calls=[],played=[],blobs=[],events={},buttons={};let handler;
  for(const key of ['speak','logout'])buttons[key]={dataset:{harnessSpeak:'m1'},addEventListener(t,fn){this[t]=fn;}};
  const c={window:null,location:{hash:'#/session/artist/circle'},document:{visibilityState:'visible',querySelector:()=>null,querySelectorAll:s=>s==='[data-harness-speak]'?[buttons.speak]:s==='[data-harness-logout]'?[buttons.logout]:[]},
    sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},setInterval(){},addEventListener:(k,v)=>events[k]=v,
    fetch:async(url,options)=>{if(url.endsWith('auth/me'))return new Promise(()=>{});calls.push({url,options});return handler(url,options);},
    URL:{createObjectURL:b=>{blobs.push(b);return'blob:approved';},revokeObjectURL(){}},
    Audio:class{constructor(){this.style={};}setAttribute(){}play(){played.push(this);return Promise.resolve();}pause(){}removeAttribute(){}load(){}remove(){}},
    speechSynthesis:{getVoices:()=>[{lang:'vi-VN',localService:true}],speak(){throw Error('native voice rejected by owner');},cancel(){},addEventListener(){}},SpeechSynthesisUtterance:class{},
    AbortController,setTimeout,clearTimeout,Uint8Array,Blob,atob:s=>Buffer.from(s,'base64').toString('binary'),render(){},scrollX:0,scrollY:0,scrollTo(){},P01:{state:{lang:'en'}}};
  c.window=c;vm.createContext(c);vm.runInContext(fs.readFileSync(require.resolve('../web/harness-client.js'),'utf8'),c);
  Object.assign(c.CabinetHarness.state,{tts:true,user:{id:'A',role:'artist'},meeting:{id:'one',state:'active',deliveries:[{id:'m1',state:'approved',text:'Chơi chậm.',target_lang:'vi'}]}});
  c.CabinetHarness.bind();
  return{api:c.CabinetHarness,c,calls,played,blobs,events,buttons,setHandler:f=>handler=f,click:()=>buttons.speak.onclick()};
}
const response=(status=200,owner='A')=>({status,ok:status<400,headers:{get:()=>owner},json:async()=>status===200?{wav_base64:'UklGRiQAAABXQVZF',language:'vi'}:{detail:'unauthorized'}});
test('server speech sends participant precondition and only canonical message id',async()=>{
 const f=fixture();f.setHandler(()=>response());await f.click();
 assert.equal(f.calls[0].options.headers['X-SOM-Participant'],'A');
 assert.equal(f.calls[0].options.body,'{}');assert.equal(f.played.length,1);
});
for(const owner of ['B',''])test('wrong or missing server audio owner never plays: '+owner,async()=>{
 const f=fixture();f.setHandler(()=>response(200,owner));await f.click();assert.equal(f.played.length,0);assert.equal(f.blobs.length,0);assert.equal(f.api.state.user,null);
});
for(const change of ['account','ABA','meeting','navigation','pagehide'])test('late server audio never plays after '+change,async()=>{
 const f=fixture();let done;f.setHandler(()=>new Promise(r=>done=r));const playing=f.click();
 if(change==='account')f.api.state.user={id:'B',role:'artist'};
 if(change==='ABA'){f.api.state.user={id:'B',role:'artist'};f.api.state.user={id:'A',role:'artist'};}
 if(change==='meeting')f.api.state.meeting={id:'two',state:'active'};
 if(change==='navigation')f.events.hashchange();
 if(change==='pagehide')f.events.pagehide();
 done(response());await playing;assert.equal(f.played.length,0);assert.equal(f.blobs.length,0);
 if(change==='account')assert.equal(f.api.state.user.id,'B');
});
test('old audio401 does not sign out a newer account',async()=>{
 const f=fixture();let done;f.setHandler(()=>new Promise(r=>done=r));const playing=f.click();f.api.state.user={id:'B',role:'artist'};done(response(401));await playing;assert.equal(f.api.state.user.id,'B');assert.equal(f.played.length,0);
});
test('unavailable server voice does not expose or trigger rejected native fallback',async()=>{
 const f=fixture();f.api.state.tts=false;f.setHandler(()=>response());assert.doesNotMatch(f.api.messages(),/data-harness-speak/);await f.click();assert.equal(f.calls.length,0);assert.equal(f.played.length,0);
});
