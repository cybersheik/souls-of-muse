const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function client(lang='en') {
 const context = {window:null, location:{hash:'#/session/maestro/one-to-one'},
  document:{querySelector:()=>null}, sessionStorage:{getItem:()=>null},
  setInterval:()=>0, addEventListener:()=>{}, P01:{state:{lang}},
  fetch:async()=>({status:401,ok:false,json:async()=>({detail:'unauthorized'})})};
 context.window=context;vm.createContext(context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/harness-client.js'),'utf8'),context);
 const api=context.CabinetHarness;
 api.state.user={role:'maestro'};
 api.state.meeting={deliveries:[{id:'m1',speaker:'maestro',state:'flagged',text:'Chơi chậm.',validation_issues:['pitch changed']}]};
 return api;
}
test('failed second check disables approval and explains how to recover',()=>{
 const api=client();const message=api.state.meeting.deliveries[0];
 message.review={state:'failed'};message.approval_allowed=false;
 const html=api.messages();
 assert.match(html,/Translation check unavailable/);
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
 assert.doesNotMatch(api.messages(),/Private reviewer detail|data-harness-approve/);
});
