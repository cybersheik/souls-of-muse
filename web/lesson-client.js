"use strict";
window.SomLesson = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const word = (en,ru) => window.P01?.state.lang === 'ru' ? ru : en;
  let key='', editing=null, planningBrief='';
  const state = () => window.CabinetHarness.state;
  function context() {
    const next=(state().user?.id||'')+':'+(state().meeting?.id||'');
    if(key!==next){key=next;editing=null;planningBrief='';}
    return state().lesson;
  }
  const editable = () => state().user?.role === 'maestro' && ['created','active'].includes(state().meeting?.state) && !state().busy;
  const redraw = () => { if(typeof render==='function')render(); };
  const clone = value => JSON.parse(JSON.stringify(value));
  function material(index) {
    const doc=context(),translations=state().meeting?.lesson_translations;
    return translations?.revision===doc?.revision ? translations.steps[index] : null;
  }
  function materialLabel(index) {
    const translations=state().meeting?.lesson_translations,approved=material(index)?.state==='approved';
    return word(approved?'Approved translation':'Original',approved?'Одобренный перевод':'Оригинал')+' · '+String(approved?translations?.target_lang:translations?.source_lang||'en').toUpperCase();
  }
  function materialIssue(issue) {
    if(issue==='lesson step: full-context field alignment requires review')return word('Compare every translated field with its original.','Сверьте каждое переведённое поле с оригиналом.');
    return issue.replace(/^title:/,word('Title:','Название:')).replace(/^duration:/,word('Duration:','Длительность:')).replace(/^goal:/,word('Goal:','Цель:')).replace(/^tips\.(\d+):/,(_,i)=>word(`Tip ${+i+1}:`,`Подсказка ${+i+1}:`));
  }
  function translationPanel(index) {
    if(state().user?.role!=='maestro')return '';
    const job=material(index),target=job?.target,review=job?.review,can=editable()&&!editing;
    const pair=state().meeting?.lesson_translations;
    return `<section class="cab-material-translation"><b>${word('Step translation','Перевод этапа')} · ${esc((pair?.target_lang||'vi').toUpperCase())}</b>
      ${target?`<p>${esc(target.title)} · ${esc(target.duration)}</p><p>${esc(target.goal)}</p>${target.tips.map(t=>`<span class="cab-tip">${esc(t)}</span>`).join('')}`:''}
      ${review?`<p class="cab-review-note">${esc(review.state==='complete'?word(review.verdict==='faithful'?'Meaning preserved':review.verdict==='unfaithful'?'Meaning changed':'Needs review',review.verdict==='faithful'?'Смысл сохранён':review.verdict==='unfaithful'?'Смысл изменён':'Нужна проверка')+' · '+review.reason:word('Review unavailable. This translation is not shared.','Проверка недоступна. Перевод не опубликован.'))}</p>`:''}
      ${job?.issues?.length?`<small>${esc(job.issues.map(materialIssue).join('; '))}</small>`:''}
      ${['failed','superseded','unavailable'].includes(job?.state)?`<p role="status">${word('Translation is unavailable. You can request it again.','Перевод недоступен. Его можно запросить снова.')}</p>`:''}
      ${job?.state==='processing'?`<p role="status">${word('Preparing translation…','Перевод готовится…')}</p>`:''}
      ${can&&job?.state!=='processing'?`<button type="button" class="cab-btn" data-lesson-translate="${index}" data-retry="${!!job?.id}">${word(job?.id?'Translate again':'Translate step',job?.id?'Перевести заново':'Перевести этап')}</button>`:''}
      ${can&&job?.state==='flagged'&&review?.state==='complete'?`<button type="button" class="cab-btn" data-lesson-approve="${esc(job.id)}">${word('Approve step translation','Одобрить перевод этапа')}</button>`:''}</section>`;
  }
  function planHTML() {
    const doc=context();
    if(!doc)return `<p role="status">${word('Lesson is loading…','Урок загружается…')}</p>`;
    if(editing?.kind==='plan')return planEditor();
    const plan=doc.plan.map((source,i)=>state().user?.role==='artist'&&material(i)?.state==='approved'?material(i).target:source),teacher=editable()&&!editing,selected=doc.step;
    return `<div class="cab-plan-head"><span class="cab-plan-title">${word('Session plan','План встречи')}</span><span class="cab-tag cab-tag-outline">${plan.length?word(`Step ${selected+1} of ${plan.length}`,`Этап ${selected+1} из ${plan.length}`):word('No steps','Нет этапов')}</span></div>
      <div class="cab-plan">${plan.length?plan.map((p,i)=>`<section class="cab-step${i===selected?' cur frame-gold-step':''}">
        ${teacher?`<button type="button" class="cab-step-btn" data-lesson-step="${i}" aria-pressed="${i===selected}">${esc(p.title)}<span class="d">${esc(p.duration)}</span></button>`:`<h3 class="cab-step-btn">${esc(p.title)} <small>${esc(p.duration)}</small>${i===selected?` · ${word('Now','Сейчас')}`:''}</h3>`}
        ${state().user?.role==='artist'?`<small>${esc(materialLabel(i))}</small>`:''}
        ${i===selected?`<p class="cab-step-goal">${esc(p.goal)}</p>${p.tips.map(t=>`<span class="cab-tip">${esc(t)}</span>`).join('')}${translationPanel(i)}`:''}</section>`).join(''):`<p>${word('The Maestro has not added a plan yet.','Маэстро ещё не добавил план.')}</p>`}</div>
      ${teacher?`<button class="cab-btn" data-lesson-edit-plan>${word('Edit plan','Изменить план')}</button>`:''}${plannerHTML()}`;
  }
  function plannerHTML(){
    if(state().user?.role!=='maestro')return '';
    const doc=context(),projection=state().meeting?.lesson_planner;
    const job=projection?.revision===doc?.revision?projection.proposal:null,can=editable()&&!editing;
    return `<section class="cab-material-translation"><b>${word('Plan with Muse','План с Muse')}</b>
      <p>${word('Describe the lesson goal. Muse prepares a private draft; review every step before sharing it.','Опишите цель урока. Muse подготовит личный черновик; проверьте каждый этап перед публикацией.')}</p>
      <form data-lesson-planner-form><fieldset class="cab-lesson-edit-fields"${!can?' disabled':''}><label>${word('Lesson goal','Цель урока')}<textarea data-lesson-planning-brief maxlength="2000" required>${esc(planningBrief)}</textarea></label><button class="cab-btn" data-lesson-plan-submit${job?.state==='processing'?' disabled':''}>${planningButton(job)}</button></fieldset></form>
      ${job?`<p role="status">${esc(job.state==='processing'?word('Muse is preparing the plan…','Muse готовит план…'):job.state==='draft'?word('Private draft · not yet shared','Личный черновик · ещё не опубликован'):word('Draft unavailable. You can request another attempt.','Черновик недоступен. Можно запросить ещё одну попытку.'))}</p><p>${esc(job.brief)}</p>${job.state==='draft'&&job.plan?job.plan.map((s,i)=>`<div class="cab-step"><h3>${i+1}. ${esc(s.title)} · ${esc(s.duration)}</h3><p>${esc(s.goal)}</p>${s.tips.map(t=>`<span class="cab-tip">${esc(t)}</span>`).join('')}</div>`).join(''):''}${can&&job.state==='draft'?`<button class="cab-btn" data-lesson-apply-plan="${esc(job.id)}">${word('Use this plan','Использовать этот план')}</button>`:''}`:''}</section>`;
  }
  function planningButton(job){
    return window.CabinetHarness.planningRetryAllowed?.(planningBrief)||job?.state==='failed'&&job.brief===planningBrief
      ?word('Retry this goal','Повторить для этой цели'):word(job?.id?'Prepare another draft':'Prepare a draft',job?.id?'Подготовить ещё черновик':'Подготовить черновик');
  }
  function field(label,name,value,max,area=false){return `<label>${label}${area?`<textarea data-lesson-field="${name}" maxlength="${max}">${esc(value)}</textarea>`:`<input data-lesson-field="${name}" value="${esc(value)}" maxlength="${max}"${name==='title'?' required':''}>`}</label>`;}
  function planEditor(){return `<form class="cab-lesson-editor" data-lesson-plan-form><fieldset class="cab-lesson-edit-fields"${state().busy?' disabled':''}><b>${word('Session plan','План встречи')}</b>${editing.doc.plan.map((p,i)=>`<fieldset data-lesson-row="${i}"><legend>${word('Step','Этап')} ${i+1}</legend>${field(word('Title','Название'),'title',p.title,160)}${field(word('Duration','Длительность'),'duration',p.duration,40)}${field(word('Goal','Цель'),'goal',p.goal,1000,true)}${field(word('Tips · one per line','Подсказки · по одной на строку'),'tips',p.tips.join('\n'),4010,true)}<button type="button" class="cab-btn" data-lesson-remove-step="${i}">${word('Remove step','Убрать этап')}</button></fieldset>`).join('')}<div class="cab-lesson-actions"><button type="button" class="cab-btn" data-lesson-add-step${editing.doc.plan.length>=32?' disabled':''}>${word('Add step','Добавить этап')}</button><button class="cab-btn"${state().busy?' disabled':''}>${word('Save plan','Сохранить план')}</button><button type="button" class="cab-btn" data-lesson-cancel>${word('Cancel','Отмена')}</button></div></fieldset></form>`;}
  function drawerHTML(role){
    const doc=context(),C=window.Cabinet.state,open=!!C.drawer[role],tab=C.tab;
    const book=doc?.notebook;
    let body='';
    if(!book)body=`<p>${word('Notebook is loading…','Тетрадь загружается…')}</p>`;
    else if(editing?.kind==='book')body=bookEditor();
    else if(tab==='chords')body=book.chords.length?`<div class="cab-chords">${book.chords.map((c,i)=>`<div class="cab-chord"><span class="bar-n">${word('bar','такт')} ${i+1}</span><span class="ch">${esc(c)}</span></div>`).join('')}</div>`:`<p>${word('No chords added.','Аккорды не добавлены.')}</p>`;
    else if(tab==='notes')body=book.notation?`<iframe class="cab-score" title="${word('Sheet music','Ноты')}" sandbox="allow-scripts" src="notation.html" data-lesson-score></iframe>`:`<p>${word('No notation added.','Ноты не добавлены.')}</p>`;
    else body=book.tabs?`<pre class="cab-tabtext">${esc(book.tabs)}</pre>`:`<p>${word('No tablature added.','Табулатура не добавлена.')}</p>`;
    return `<div class="cab-drawer"><button type="button" class="cab-drawer-tab" data-cab-drawer aria-expanded="${open}"><span>${word('Notebook','Нотная тетрадь')}</span></button>${open?`<div class="cab-drawer-panel"><div class="cab-ntabs" role="tablist">${[['chords',word('Chords','Аккорды')],['notes',word('Notation','Ноты')],['tabs',word('Tabs','Табулатура')]].map(([id,label])=>`<button role="tab" type="button" data-cab-tab="${id}" aria-selected="${id===tab}">${label}</button>`).join('')}</div>${body}${editable()&&!editing?`<button class="cab-btn" data-lesson-edit-book>${word('Edit notebook','Изменить тетрадь')}</button>`:''}<p class="cab-drawer-note">${word('Shared material · led by the Maestro','Общий материал · ведёт Маэстро')}</p></div>`:''}</div>`;
  }
  function bookEditor(){const b=editing.doc.notebook;return `<form class="cab-lesson-editor" data-lesson-book-form><fieldset class="cab-lesson-edit-fields"${state().busy?' disabled':''}>${field(word('Chords · one bar per line','Аккорды · каждый такт на новой строке'),'chords',b.chords.join('\n'),2112,true)}${field(word('Notation · ABC format','Ноты · формат ABC'),'notation',b.notation,8000,true)}<small>${word('Paste ABC sheet music; the Notation tab displays the score.','Вставьте нотную запись ABC; вкладка «Ноты» покажет партитуру.')}</small>${field(word('Tablature','Табулатура'),'tabs',b.tabs,8000,true)}<div class="cab-lesson-actions"><button class="cab-btn"${state().busy?' disabled':''}>${word('Save notebook','Сохранить тетрадь')}</button><button type="button" class="cab-btn" data-lesson-cancel>${word('Cancel','Отмена')}</button></div></fieldset></form>`;}
  function bind(){
    if(!state().meeting)return;
    context();
    const on=(selector,event,fn)=>document.querySelectorAll(selector).forEach(el=>el.addEventListener(event,fn));
    on('[data-lesson-edit-plan]','click',()=>{if(!editable()||editing)return;editing={kind:'plan',doc:clone(context())};redraw();});
    on('[data-lesson-planning-brief]','input',event=>{planningBrief=event.currentTarget.value;const doc=context(),p=state().meeting?.lesson_planner,job=p?.revision===doc.revision?p.proposal:null,button=document.querySelector('[data-lesson-plan-submit]');if(button)button.textContent=planningButton(job);});
    on('[data-lesson-planner-form]','submit',event=>{event.preventDefault();if(!editable()||editing)return;const doc=context(),p=state().meeting?.lesson_planner,job=p?.revision===doc.revision?p.proposal:null;window.CabinetHarness.requestLessonPlan(planningBrief,!!job?.id&&job.brief===planningBrief||!!window.CabinetHarness.planningRetryAllowed?.(planningBrief));});
    on('[data-lesson-apply-plan]','click',event=>{if(editable()&&!editing&&window.confirm(word('Use this draft as the shared plan? You have reviewed every step.','Использовать этот черновик как общий план? Вы проверили каждый этап.')))window.CabinetHarness.applyLessonPlan(event.currentTarget.dataset.lessonApplyPlan);});
    on('[data-lesson-edit-book]','click',()=>{if(!editable()||editing)return;editing={kind:'book',doc:clone(context())};redraw();});
    on('[data-lesson-cancel]','click',()=>{editing=null;redraw();});
    on('[data-lesson-add-step]','click',()=>{editing.doc.plan.push({title:'',duration:'',goal:'',tips:[]});if(editing.doc.step===null)editing.doc.step=0;redraw();});
    on('[data-lesson-remove-step]','click',event=>{const i=+event.currentTarget.dataset.lessonRemoveStep,d=editing.doc;d.plan.splice(i,1);if(!d.plan.length)d.step=null;else if(i<d.step)d.step--;else d.step=Math.min(d.step,d.plan.length-1);redraw();});
    on('[data-lesson-row] [data-lesson-field]','input',event=>{const el=event.currentTarget,index=+el.closest('[data-lesson-row]').dataset.lessonRow;editing.doc.plan[index][el.dataset.lessonField]=el.dataset.lessonField==='tips'?el.value.split('\n').filter(x=>x.trim()):el.value;});
    on('[data-lesson-book-form] [data-lesson-field]','input',event=>{const el=event.currentTarget;editing.doc.notebook[el.dataset.lessonField]=el.dataset.lessonField==='chords'?el.value.split('\n').filter(x=>x.trim()):el.value;});
    on('[data-lesson-plan-form], [data-lesson-book-form]','submit',event=>{event.preventDefault();if(editable())window.CabinetHarness.updateLesson(clone(editing.doc),()=>{editing=null;});});
    on('[data-lesson-translate]','click',event=>{if(editable()&&!editing)window.CabinetHarness.translateLessonStep(+event.currentTarget.dataset.lessonTranslate,event.currentTarget.dataset.retry==='true');});
    on('[data-lesson-approve]','click',event=>{if(editable()&&!editing&&window.confirm(word('Have you compared these fields with the original and approved their meaning?','Вы сверили поля с оригиналом и одобряете их смысл?')))window.CabinetHarness.approveLessonTranslation(event.currentTarget.dataset.lessonApprove);});
    on('[data-lesson-step]','click',event=>{if(!editable()||editing)return;const d=clone(context());d.step=+event.currentTarget.dataset.lessonStep;window.CabinetHarness.updateLesson(d);});
    const frame=document.querySelector('[data-lesson-score]');
    if(frame)frame.addEventListener('load',()=>frame.contentWindow.postMessage({type:'som-score',abc:context()?.notebook.notation||'',lang:window.P01?.state.lang},'*'));
  }
  return {planHTML,drawerHTML,bind,reset:()=>{editing=null;key='';planningBrief='';}};
})();
