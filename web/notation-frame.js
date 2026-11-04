"use strict";
// Opaque sandbox: no parent DOM/cookies, no network, no audio. Parent sends only
// the shared score; render warnings remain visible instead of hiding bad input.
window.addEventListener('message',event=>{
 if(event.source!==parent||event.data?.type!=='som-score'||typeof event.data.abc!=='string'||event.data.abc.length>8000)return;
 const output=document.getElementById('score'),warnings=document.getElementById('warnings');output.replaceChildren();warnings.textContent='';
 try{
  const tunes=ABCJS.renderAbc(output,event.data.abc,{responsive:'resize',staffwidth:520,foregroundColor:'#eee',oneSvgPerLine:true});
  // Titles/annotations are untrusted text. Do not retain active SVG content or
  // links even inside the isolated frame.
  output.querySelectorAll('script,foreignObject,iframe,object,embed,a').forEach(el=>el.remove());
  output.querySelectorAll('*').forEach(el=>[...el.attributes].forEach(a=>{if(/^on/i.test(a.name)||/href$/i.test(a.name))el.removeAttribute(a.name);}));
  const messages=tunes.flatMap(t=>t.warnings||[]);
  if(!tunes.length||messages.length)warnings.textContent=(event.data.lang==='ru'?'Проверьте нотную запись ABC. ':'Check the ABC notation. ')+messages.join('\n');
 }catch(_){warnings.textContent=event.data.lang==='ru'?'Нотную запись не удалось показать.':'The notation could not be displayed.';}
});
