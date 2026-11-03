"use strict";
window.SomPrivateNotes=(()=>{
  const state=()=>window.CabinetHarness.state;
  const word=(en,ru)=>window.P01?.state.lang==='ru'?ru:en;
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const redraw=()=>{if(typeof render==='function')render();};
  let owner=null,meeting=null,editor=null,index=null;
  function context(){
    if(owner!==state().user||meeting!==state().meeting?.id){owner=state().user;meeting=state().meeting?.id;editor=null;}
    if(index&&index.owner!==state().user)index=null;
    return state().meeting?.private_notes;
  }
  function HTML(){
    const doc=context();
    if(!state().user||!state().meeting)return '';
    if(!doc)return `<p role="status">${word('Private notes are unavailable.','Личные заметки недоступны.')}</p>`;
    const caption=`<p class="cab-drawer-note">${word('Only you can read these notes. They stay separate from the shared Notebook and Muse messages.','Эти заметки видны только вам. Они хранятся отдельно от общей тетради и сообщений Muse.')}</p>`;
    if(editor)return `${caption}<form class="cab-lesson-editor" data-private-notes-form><fieldset${state().busy?' disabled':''}><label>${word('Private note text','Текст личной заметки')}<textarea data-private-notes-text maxlength="8000" autocomplete="off">${esc(editor.text)}</textarea></label><div class="cab-lesson-actions"><button class="cab-btn">${word('Save notes','Сохранить заметки')}</button><button class="cab-btn" type="button" data-private-notes-cancel>${word('Cancel editing','Отменить правки')}</button></div></fieldset></form>`;
    return `${caption}${doc.text?`<div class="cab-private-text">${esc(doc.text)}</div>`:`<p>${word('No personal notes yet.','Личных заметок пока нет.')}</p>`}<button type="button" class="cab-btn" data-private-notes-edit${state().busy?' disabled':''}>${word('Edit my notes','Изменить мои заметки')}</button>`;
  }
  function indexHTML(){
    context();
    if(!index)return '';
    return `<section class="cab-live"><h2>${word('My notes','Мои заметки')}</h2><p>${word('Private notes from your meetings. Open a meeting to read or edit the full text.','Личные заметки по вашим встречам. Откройте встречу, чтобы прочитать или изменить полный текст.')}</p>
      <div class="cab-lesson-actions"><button class="cab-btn" data-private-notes-refresh${index.loading?' disabled':''}>${word('Refresh notes','Обновить заметки')}</button><button class="cab-btn" data-private-notes-close>${word('Close notes','Закрыть заметки')}</button></div>
      ${index.rows.map(row=>`<article class="cab-material-translation"><b>${esc(row.maestro_alias)} · ${esc(row.artist_alias)}</b><small>${esc(row.updated_at)}</small><p class="cab-private-text">${esc(row.preview)}</p><button class="cab-btn" data-harness-open="${esc(row.session_id)}"${state().busy?' disabled':''}>${word('Open meeting','Открыть встречу')}</button></article>`).join('')}
      ${!index.rows.length&&!index.loading&&!index.error?`<p>${word('No saved notes yet.','Сохранённых заметок пока нет.')}</p>`:''}
      ${index.loading?`<p role="status">${word('Loading notes…','Заметки загружаются…')}</p>`:''}${index.error?`<p role="status">${word('Could not load private notes. Try refreshing.','Не удалось загрузить личные заметки. Попробуйте обновить.')}</p>`:''}
      ${index.next?`<button class="cab-btn" data-private-notes-more${index.loading?' disabled':''}>${word('More notes','Ещё заметки')}</button>`:''}</section>`;
  }
  async function loadIndex(more=false){
    context();
    if(!state().user){state().status=word('Sign in to read your private notes.','Войдите, чтобы прочитать личные заметки.');redraw();return;}
    if(index?.loading)return;
    if(!more)index={owner:state().user,rows:[],next:null,loading:false,error:false};
    if(!index)return;
    const requested=index;requested.loading=true;requested.error=false;redraw();
    try{
      const page=await window.CabinetHarness.privateNotesPage(more?requested.next:null);
      if(index!==requested||state().user!==requested.owner||!page)return;
      const rows=more?[...requested.rows,...page.notes]:page.notes;
      requested.rows=[...new Map(rows.map(row=>[row.session_id,row])).values()];requested.next=page.next_cursor;
    }catch(_){if(index===requested&&state().user===requested.owner)requested.error=true;}
    finally{if(index===requested&&state().user===requested.owner){requested.loading=false;redraw();}}
  }
  function bind(){
    context();
    const on=(selector,event,fn)=>document.querySelectorAll(selector).forEach(el=>el.addEventListener(event,fn));
    on('[data-private-notes-edit]','click',()=>{const doc=context();if(!doc||state().busy)return;editor={revision:doc.revision,text:doc.text};redraw();});
    on('[data-private-notes-text]','input',event=>{if(editor)editor.text=event.currentTarget.value;});
    on('[data-private-notes-cancel]','click',()=>{editor=null;redraw();});
    on('[data-private-notes-form]','submit',event=>{event.preventDefault();context();if(!editor||state().busy)return;const draft={...editor},user=owner,sid=meeting;return window.CabinetHarness.savePrivateNotes(draft,()=>{if(state().user===user&&state().meeting?.id===sid)editor=null;});});
    on('[data-private-notes-index]','click',event=>{event.preventDefault();return loadIndex();});
    on('[data-private-notes-refresh]','click',()=>loadIndex());
    on('[data-private-notes-more]','click',()=>loadIndex(true));
    on('[data-private-notes-close]','click',()=>{index=null;redraw();});
  }
  return {HTML,indexHTML,bind,reset:()=>{owner=null;meeting=null;editor=null;index=null;}};
})();
