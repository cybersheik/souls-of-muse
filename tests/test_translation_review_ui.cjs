const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function client(lang='en') {
 const context = {window:null, location:{hash:'#/session/maestro/one-to-one'},
  document:{querySelector:()=>null,querySelectorAll:()=>[]}, sessionStorage:{getItem:()=>null,setItem:()=>{}},
  crypto:{randomUUID:()=>require('node:crypto').randomUUID()},
  setInterval:()=>0, addEventListener:()=>{}, P01:{state:{lang}},
  fetch:async()=>({status:401,ok:false,json:async()=>({detail:'unauthorized'})})};
 Object.assign(context,{AbortController,setTimeout,clearTimeout});context.window=context;vm.createContext(context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/harness-client.js'),'utf8'),context);
 const api=context.CabinetHarness;
 api.state.user={id:'M',role:'maestro'};
 api.state.meeting={id:'one',state:'active',deliveries:[{id:'m1',speaker:'maestro',state:'flagged',text:'Chơi chậm.',validation_issues:['pitch changed']}]};
 api.testContext=context;
 return api;
}
test('failed second check disables approval and explains how to recover',()=>{
 const api=client();const message=api.state.meeting.deliveries[0];
 message.review={state:'failed'};message.approval_allowed=false;
 const html=api.messages();
 assert.match(html,/Translation check unavailable/);
 assert.match(html,/data-harness-review="m1"/);
 assert.doesNotMatch(html,/Send the message again/);
 assert.match(html,/<button[^>]*data-harness-approve="m1"[^>]*disabled/);
 assert.doesNotMatch(html,/data-harness-speak/);
});
test('completed second check shows escaped reason while retaining explicit approval',()=>{
 const api=client();const message=api.state.meeting.deliveries[0];
 message.review={state:'complete',verdict:'unfaithful',reason:'Lost F-sharp <img src=x onerror=alert(1)>'};
 message.approval_allowed=true;
 const html=api.messages();
 assert.match(html,/Meaning changed/);assert.match(html,/Lost F-sharp &lt;img/);
 assert.doesNotMatch(html,/<img/);assert.match(html,/data-harness-approve="m1"/);
 assert.doesNotMatch(html,/<button[^>]*data-harness-approve="m1"[^>]*disabled/);
});
test('Russian locale explains the check and no review detail is rendered for Artist',()=>{
 const api=client('ru');const message=api.state.meeting.deliveries[0];
 message.review={state:'complete',verdict:'uncertain',reason:'Private reviewer detail'};
 message.approval_allowed=true;
 assert.match(api.messages(),/Нужна проверка смысла/);
 api.state.user={role:'artist'};message.state='approved';
 assert.doesNotMatch(api.messages(),/Private reviewer detail|data-harness-approve|data-harness-review/);
});

function transport(api,onReview){
 api.testContext.fetch=async(url,options={})=>{
  let data={};
  if(options.method==='POST'){assert.match(url,/sessions\/one\/messages\/m[12]\/review$/);data=await onReview(JSON.parse(options.body),options);}
  else if(url.endsWith('/sessions'))data={sessions:[]};
  else if(url.endsWith('/sessions/one'))data=api.state.meeting;
  else if(url.endsWith('/lesson'))data={revision:0};
  return {ok:true,status:200,headers:{get:()=> 'M'},json:async()=>data};
 };
}
test('ambiguous retry response retains the intent and never resends the message',async()=>{
 const api=client(),message=api.state.meeting.deliveries[0],seen=[];
 message.review={state:'failed'};
 transport(api,async(body,options)=>{seen.push(body);assert.equal(options.headers['X-SOM-Participant'],'M');if(seen.length===1)throw Error('network interrupted');return {};});
 await api.retryTranslationReview('m1');await api.retryTranslationReview('m1');
 assert.equal(seen.length,2);assert.equal(seen[0].client_event_id,seen[1].client_event_id);
 assert.deepEqual(Object.keys(seen[0]),['client_event_id']);
});
test('observed terminal attempt gives a deliberate retry a fresh intent',async()=>{
 const api=client(),message=api.state.meeting.deliveries[0],seen=[];
 message.review={state:'failed'};
 transport(api,async body=>{seen.push(body);message.review={state:'failed',retry_event_id:body.client_event_id};throw Error('response lost after commit');});
 await api.retryTranslationReview('m1');await api.retryTranslationReview('m1');
 assert.equal(seen.length,2);assert.notEqual(seen[0].client_event_id,seen[1].client_event_id);
});
test('switching A to B and back retains each ambiguous review intent independently',async()=>{
 const api=client(),first=api.state.meeting.deliveries[0],seen=[];
 first.review={state:'failed'};
 api.state.meeting.deliveries.push({...first,id:'m2'});
 transport(api,async body=>{seen.push(body.client_event_id);throw Error('ambiguous response');});
 await api.retryTranslationReview('m1');await api.retryTranslationReview('m2');await api.retryTranslationReview('m1');
 assert.equal(seen.length,3);assert.equal(seen[0],seen[2]);assert.notEqual(seen[0],seen[1]);
});
test('retry action and control are restricted to an active Maestro draft',async()=>{
 for(const mode of ['artist','completed','processing','complete','busy']){
  const api=client(),message=api.state.meeting.deliveries[0];message.review={state:'failed'};let calls=0;
  transport(api,async()=>{calls++;return {};});
  if(mode==='artist')api.state.user.role='artist';else if(mode==='completed')api.state.meeting.state='completed';else if(mode==='busy')api.state.busy=true;else message.review.state=mode;
  await api.retryTranslationReview('m1');assert.equal(calls,0,mode);
  if(mode==='busy')assert.match(api.messages(),/data-harness-review="m1"[^>]*disabled/);
  else assert.doesNotMatch(api.messages(),/data-harness-review/);
 }
});
