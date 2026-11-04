const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function load(){
 const handlers={},elements={},calls=[];const meeting={id:'group-one',kind:'group',state:'active',maestro_alias:'M',artist_alias:'A',artist_ids:['A','B'],deliveries:[]};
 const c={window:null,location:{hash:'#/space/maestro'},P01:{state:{lang:'en'}},scrollX:0,scrollY:0,scrollTo(){},render(){},setInterval(){},addEventListener(){},sessionStorage:{setItem(){},removeItem(){},getItem(){return null;}},crypto:{randomUUID(){return'event';}},FormData:class{constructor(form){this.form=form;}get(key){return this.form[key];}},document:{visibilityState:'visible',querySelector(){return null;},querySelectorAll(selector){return(elements[selector]||[]).map(el=>({...el,addEventListener:(event,fn)=>{handlers[selector+':'+event]=fn;}}));}},fetch:async(url,opt)=>{calls.push({url,opt});if(url.endsWith('/auth/me'))return{ok:false,status:401,json:async()=>({detail:'unauthorized'})};let result=url.endsWith('/sessions')?(opt.method==='POST'?meeting:{sessions:[meeting]}):url.endsWith('/heart')?{counters:{happened:0,useful:0,progress:0}}:url.endsWith('/lesson')?{revision:0,steps:[]}:meeting;return{ok:true,status:200,json:async()=>result,headers:{get:()=> 'M'}};}};
 Object.assign(c,{AbortController,setTimeout,clearTimeout});c.window=c;vm.createContext(c);vm.runInContext(fs.readFileSync('web/harness-client.js','utf8'),c);c.CabinetHarness.state.user={id:'M',name:'Maestro',role:'maestro'};return{c,handlers,elements,calls,meeting};
}
test('two explicit Artist IDs create a group rather than an individual containing a comma in its ID',async()=>{
 const {c,handlers,elements,calls}=load();elements['[data-harness-create]']=[{}];c.CabinetHarness.bind();
 handlers['[data-harness-create]:submit']({preventDefault(){},currentTarget:{artist:'A, B'}});
 while(c.CabinetHarness.state.busy)await new Promise(r=>setImmediate(r));
 const request=calls.find(x=>x.url.endsWith('/sessions')&&x.opt.method==='POST');assert.ok(request);const data=JSON.parse(request.opt.body);assert.equal(data.kind,'group');assert.deepEqual(data.artist_ids,['A','B']);assert.equal(data.artist_id,undefined);
});
test('a server-owned group opens the circle route for the logged-in role',async()=>{
 const {c,handlers,elements}=load();elements['[data-harness-open]']=[{dataset:{harnessOpen:'group-one'}}];c.CabinetHarness.bind();
 handlers['[data-harness-open]:click']({currentTarget:{dataset:{harnessOpen:'group-one'}}});
 while(c.CabinetHarness.state.busy)await new Promise(r=>setImmediate(r));assert.equal(c.location.hash,'#/session/maestro/circle');
});
test('group messages identify the server-owned sender, escaping an Artist name',()=>{
 const {c,meeting}=load();meeting.deliveries=[{id:'msg',state:'approved',speaker:'artist',participant_name:'Student <two>',text:'Hello'}];c.CabinetHarness.state.meeting=meeting;assert.ok(c.CabinetHarness.messages().includes('Student &lt;two&gt;'));
});
