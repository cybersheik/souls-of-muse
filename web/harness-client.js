"use strict";

window.CabinetHarness = (() => {
  const state = { user: null, meeting: null, lesson: null, sessions: [], heart: null, busy: false, status: "", pending: null, recording: false, asr: false, tts: false, media: false, authChecking: true, authCheckFailed: false };
  let initialAuthAttempt = null;
  let capture = null, captureAbort = null, composeText = "", focusCompose = false;
  let materialPending = null, planningPending = null, planningRetry = null;
  const reviewPending = new WeakMap();
  let speechAudio = null, speechURL = null, speechAbort = null, speechMessage = null;
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ru = () => window.P01?.state.lang === "ru";
  const word = (en, local) => ru() ? local : en;
  const redraw = () => {
    if (typeof render !== "function") return;
    const x = scrollX, y = scrollY;
    render();
    window.scrollTo(x, y);
    const input = document.querySelector("[data-cab-chat-input]");
    if (input) { input.value = composeText; if (focusCompose) { input.focus(); focusCompose = false; } }
  };
  const speakingLanguages = new Map();
  function languagePair() {
    let source = speakingLanguages.get(state.user?.id);
    if (!source) try { source = sessionStorage.getItem("som_speaking_language:" + state.user?.id); } catch (_) {}
    if (!["en", "vi"].includes(source)) source = state.user?.role === "artist" ? "vi" : "en";
    return { source, target: source === "en" ? "vi" : "en" };
  }
  function languageControls() {
    if (!state.user) return "";
    const pair = languagePair();
    return `<label class="cab-language-controls">${word("I speak", "Я говорю")} <select data-harness-language ${state.busy || state.recording ? "disabled" : ""}><option value="en" ${pair.source === "en" ? "selected" : ""}>English</option><option value="vi" ${pair.source === "vi" ? "selected" : ""}>Tiếng Việt</option></select> → ${pair.target === "en" ? "English" : "Tiếng Việt"}</label>`;
  }
  async function call(path, body, options = {}) {
    const requestedUser = state.user;
    const response = await fetch("/api/harness/" + path, {
      method: body === undefined ? "GET" : "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(requestedUser?{'X-SOM-Participant':encodeURIComponent(requestedUser.id)}:{}) },
      body: body === undefined ? undefined : JSON.stringify(body), signal: options.signal,
    });
    const data = await response.json();
    const carriesPrivateNotes=data.private_notes||/^notes(?:\?|$)|^sessions\/[^/]+\/notes$/.test(path);
    let contextMismatch=data.detail==='participant_context_changed';
    if(response.ok&&requestedUser&&(carriesPrivateNotes||/^sessions\/[^/]+\/messages\/[^/]+\/speech$/.test(path))){
      try{contextMismatch=decodeURIComponent(response.headers?.get('X-SOM-Participant')||'')!==requestedUser.id;}
      catch(_){contextMismatch=true;}
    }
    if ((response.status === 401||contextMismatch) && state.user === requestedUser) {
      cancelCapture(); stopSpeech(); window.SomConference?.stop();
      window.SomMedia?.disconnect(true).catch(() => {});
      Object.assign(state, { user: null, meeting: null, lesson: null, sessions: [], heart: null });
      window.SomLesson?.reset();
      window.SomPrivateNotes?.reset();
      redraw();
    }
    if(contextMismatch)throw new Error(word('The account changed in another tab. Sign in again to open the correct private workspace.','Аккаунт изменён в другой вкладке. Войдите снова, чтобы открыть нужное личное пространство.'));
    if (!response.ok) throw new Error(data.detail || "request_failed");
    return data;
  }
  async function refresh() {
    const user = state.user, meetingId = state.meeting?.id;
    const sessions = (await call("sessions")).sessions;
    if (state.user !== user || state.meeting?.id !== meetingId) return false;
    let meeting, heart, lesson;
    if (meetingId) [meeting, heart, lesson] = await Promise.all([
      call("sessions/" + meetingId), call("sessions/" + meetingId + "/heart"), call("sessions/" + meetingId + "/lesson"),
    ]);
    // Old polls may finish after a different meeting/account has opened.
    // Apply one coherent snapshot only to the context that requested it.
    if (state.user !== user || state.meeting?.id !== meetingId) return false;
    state.sessions = sessions;
    if (meetingId) {
      // A poll may have read the old document before our acknowledged save.
      // Revisions are monotonic within this exact account/meeting context.
      const acknowledgedNotes=state.meeting?.private_notes;
      if(meeting.private_notes&&acknowledgedNotes&&meeting.private_notes.revision<acknowledgedNotes.revision)meeting.private_notes=acknowledgedNotes;
      sessionStorage.setItem("som_meeting", meetingId);
      Object.assign(state, { meeting, heart, lesson });
    }
    return true;
  }
  async function action(work) {
    if (state.busy) return;
    state.busy = true;
    state.status = word("Working…", "Выполняется…");
    redraw();
    try {
      await work();
      state.status = "";
    } catch (error) {
      state.status = word("Could not complete the action", "Действие не выполнено") + " · " + error.message;
    } finally {
      state.busy = false;
      redraw();
    }
  }
  function updateLesson(doc, saved) {
    if (state.user?.role !== "maestro" || !state.meeting) return;
    const user = state.user, meetingId = state.meeting.id;
    return action(async () => {
      try {
        const lesson = await call(`sessions/${meetingId}/lesson`, doc);
        if (state.user !== user || state.meeting?.id !== meetingId) return;
        state.lesson = lesson;
      }
      catch (error) {
        if (error.message === "lesson_revision_conflict") throw new Error(word(
          "The lesson changed in another tab. Your edit is retained. Cancel editing, refresh and reapply your changes.",
          "Урок изменён в другой вкладке. Ваши правки сохранены в форме. Отмените редактирование, обновите урок и внесите их снова."));
        throw error;
      }
      saved?.();
    });
  }
  function savePrivateNotes(doc,saved){
    if(!state.user||!state.meeting||state.busy)return;
    const user=state.user,meetingId=state.meeting.id;
    return action(async()=>{
      try{
        const notes=await call(`sessions/${meetingId}/notes`,doc);
        if(state.user!==user||state.meeting?.id!==meetingId)return;
        state.meeting.private_notes=notes;saved?.();
      }catch(error){
        if(error.message==='private_notes_revision_conflict'){
          if(state.user===user&&state.meeting?.id===meetingId)await refresh();
          throw new Error(word('Your notes changed in another tab. Your draft is retained. Copy it if needed, cancel editing, then review the saved version before editing again.','Заметки изменены в другой вкладке. Ваш черновик сохранён в форме. При необходимости скопируйте его, отмените правки и просмотрите сохранённую версию перед новым редактированием.'));
        }
        throw error;
      }
    });
  }
  async function privateNotesPage(cursor){
    const user=state.user;
    const page=await call('notes'+(cursor?'?cursor='+encodeURIComponent(cursor):''));
    return state.user===user?page:null;
  }
  function translateLessonStep(index, retry = false) {
    if (state.user?.role !== "maestro" || !state.meeting || !state.lesson || state.busy) return;
    const user = state.user, meetingId = state.meeting.id;
    const context = `${user.id}:${meetingId}:${state.lesson.revision}:${index}:${retry}`;
    const projection = state.meeting.lesson_translations;
    const previous = projection?.revision === state.lesson.revision ? projection.steps[index] : null;
    // Preserve the event ID after an ambiguous response. A later observed job
    // proves that request was processed; another deliberate attempt gets a new ID.
    if (!materialPending || materialPending.context !== context || (previous?.id && previous.id !== materialPending.baseId)) {
      materialPending = { context, baseId: previous?.id, body: { revision: state.lesson.revision, step: index, retry, client_event_id: crypto.randomUUID() } };
    }
    const pending = materialPending;
    return action(async () => {
      try {
        await call(`sessions/${meetingId}/lesson/translations`, pending.body);
        if (materialPending === pending) materialPending = null;
      } catch (error) {
        if (state.user === user && state.meeting?.id === meetingId) await refresh().catch(() => {});
        throw error;
      }
      if (state.user === user && state.meeting?.id === meetingId) await refresh();
    });
  }
  function requestLessonPlan(brief, retry = false) {
    if (state.user?.role !== 'maestro' || !state.meeting || !state.lesson || state.busy) return;
    const user=state.user, meetingId=state.meeting.id;
    const context=JSON.stringify([user.id,meetingId,state.lesson.revision,brief,retry]);
    const previous=state.meeting.lesson_planner?.revision===state.lesson.revision ? state.meeting.lesson_planner.proposal : null;
    if(!planningPending || planningPending.context!==context || (previous?.id && previous.id!==planningPending.baseId)) {
      planningPending={context,baseId:previous?.id,body:{revision:state.lesson.revision,brief,retry,client_event_id:crypto.randomUUID()}};
    }
    const pending=planningPending;
    return action(async()=>{
      try { await call(`sessions/${meetingId}/lesson/proposals`,pending.body); if(planningPending===pending)planningPending=null; planningRetry=null; }
      catch(error){
        if(error.message==='explicit_planning_retry_required' && state.user===user && state.meeting?.id===meetingId) {
          planningRetry={user,meetingId,revision:pending.body.revision,brief};
          throw new Error(word('An earlier attempt for this goal failed. Choose “Retry this goal” to request a new draft.','Предыдущая попытка для этой цели не удалась. Нажмите «Повторить для этой цели», чтобы запросить новый черновик.'));
        }
        throw error;
      }
      finally { if(state.user===user && state.meeting?.id===meetingId)await refresh(); }
    });
  }
  function planningRetryAllowed(brief){
    return !!planningRetry && state.user===planningRetry.user && state.meeting?.id===planningRetry.meetingId && state.lesson?.revision===planningRetry.revision && brief===planningRetry.brief;
  }
  function applyLessonPlan(id) {
    if(state.user?.role!=='maestro' || !state.meeting || state.busy)return;
    const user=state.user,meetingId=state.meeting.id;
    return action(async()=>{
      try { await call(`sessions/${meetingId}/lesson/proposals/${encodeURIComponent(id)}/apply`,{confirm:true}); }
      finally { if(state.user===user && state.meeting?.id===meetingId)await refresh(); }
    });
  }
  function retryTranslationReview(id) {
    const user=state.user,meetingId=state.meeting?.id;
    const message=state.meeting?.deliveries?.find(item=>item.id===id);
    if(user?.role!=='maestro'||!meetingId||state.meeting.state!=='active'||state.busy||
       message?.state!=='flagged'||['processing','complete'].includes(message.review?.state))return;
    // Preserve an ambiguous request's ID. A matching terminal server marker
    // proves that attempt finished; the next deliberate click is a new intent.
    let pendingMessages=reviewPending.get(user);
    if(!pendingMessages){pendingMessages=new Map();reviewPending.set(user,pendingMessages);}
    const key=JSON.stringify([meetingId,id]);
    let pending=pendingMessages.get(key);
    if(!pending||message.review?.retry_event_id===pending.body.client_event_id){
      pending={body:{client_event_id:crypto.randomUUID()}};
      pendingMessages.set(key,pending);
    }
    return action(async()=>{
      try{
        await call(`sessions/${meetingId}/messages/${id}/review`,pending.body);
        if(pendingMessages.get(key)===pending)pendingMessages.delete(key);
      }finally{
        if(state.user===user&&state.meeting?.id===meetingId)await refresh();
      }
    });
  }
  function approveLessonTranslation(id) {
    if (state.user?.role !== "maestro" || !state.meeting || state.busy) return;
    const user = state.user, meetingId = state.meeting.id;
    return action(async () => {
      try { await call(`sessions/${meetingId}/lesson/translations/${encodeURIComponent(id)}/approve`, { confirm_flagged: true }); }
      finally { if (state.user === user && state.meeting?.id === meetingId) await refresh(); }
    });
  }
  function panel() {
    const disabled = state.busy ? " disabled" : "";
    const home = !location.hash.startsWith("#/session/");
    if (!state.user && state.authChecking) return `<section class="cab-live" aria-busy="true"><p role="status">${word("Checking sign-in…", "Проверяем вход…")}</p></section>`;
    if (!state.user && state.authCheckFailed) return `<section class="cab-live"><p role="status">${word("Could not check sign-in. Please retry.", "Не удалось проверить вход. Повторите проверку.")}</p><button type="button" class="cab-btn" data-harness-auth-retry${disabled}>${word("Retry sign-in check", "Повторить проверку входа")}</button></section>`;
    if (!state.user) return `<section class="cab-live"><b>${word("Join your meeting", "Войти на встречу")}</b>
      <form data-harness-login><label>${word("Participant", "Участник")}<input name="username" autocomplete="username" required maxlength="100"></label>
      <label>${word("Password", "Пароль")}<input name="password" type="password" autocomplete="current-password" required maxlength="256"></label>
      <button class="cab-btn"${disabled}>${word("Sign in", "Войти")}</button></form><p role="status">${esc(state.status)}</p></section>`;
    return `<section class="cab-live"><b>${esc(state.user.name)} · ${esc(state.user.role)}</b>
      <button class="cab-btn" data-harness-refresh${disabled}>${word("Refresh", "Обновить")}</button>
      <button class="cab-btn" data-harness-logout${disabled}>${word("Sign out", "Выйти")}</button>
      ${home && state.user.role === "maestro" ? `<form data-harness-create><label>${word("Artist IDs (one or two, separated by a comma)", "ID Артистов (один или два, через запятую)")}<input name="artist" required maxlength="220"></label>
        <button class="cab-btn"${disabled}>${word("Create meeting", "Создать встречу")}</button></form>` : ""}
      <div class="cab-live-meetings">${(home ? state.sessions : []).map(s => `<button class="cab-btn" data-harness-open="${esc(s.id)}"${disabled}>${esc(s.maestro_alias)} · ${esc(s.artists?.map(a=>a.name).join(', ') || s.artist_alias)} · ${esc(s.state)}</button>`).join("")}</div>
      ${state.meeting ? `<p>${word("Meeting", "Встреча")} · ${esc(state.meeting.state)}</p>
        ${home && state.user.role === "maestro" && state.meeting.state === "created" ? `<button class="cab-btn" data-harness-start${disabled}>${word("Start", "Начать")}</button>` : ""}
        ${state.meeting.state === "active" ? `<button class="cab-btn" data-harness-join${disabled}>${word("Join", "Присоединиться")}</button>
          ${state.user.role === "maestro" ? `<button class="cab-btn" data-harness-complete${disabled}>${word("Complete", "Завершить")}</button>` : ""}` : ""}
        ${state.meeting.state === "closing" && state.user.role === "maestro" ? `<button class="cab-btn" data-harness-complete${disabled}>${word("Finish closing", "Завершить закрытие")}</button>` : ""}
        ${state.media && state.meeting.state === "active" && !home ? `<button class="cab-btn" data-harness-media${disabled}>${window.SomMedia?.connected(state.meeting.id) ? word("Disconnect voice", "Отключить голос") : word("Connect voice", "Подключить голос")}</button><div data-harness-media-audio></div>` : ""}
        ${state.heart ? `<p>♥ ${word("Meetings", "Встречи")} ${state.heart.counters.happened} · ${word("Useful", "Полезно")} ${state.heart.counters.useful} · ${word("Progress", "Прогресс")} ${state.heart.counters.progress}</p>` : ""}` : ""}
      ${state.heart?.accrual?.state === 'group_policy_pending' ? `<p>${word("Group heart accrual is awaiting an agreed rule.", "Правило начисления heart для группы ещё согласуется.")}</p>` : ''}
      <p role="status">${esc(state.status)}</p></section>`;
  }
  function reviewNote(message) {
    if (state.user?.role !== "maestro" || (!message.review && message.state !== "flagged")) return "";
    const review = message.review;
    let text;
    if (review?.state === "complete") {
      const verdict = review.verdict === "faithful" ? word("Meaning preserved", "Смысл сохранён")
        : review.verdict === "unfaithful" ? word("Meaning changed", "Смысл изменён")
        : word("Meaning needs review", "Нужна проверка смысла");
      text = verdict + " · " + review.reason;
    } else if (review?.state === "processing") {
      text = word("Checking translation…", "Проверяем перевод…");
    } else {
      text = word("Translation check unavailable. Retry the check when the service recovers.",
        "Проверка перевода недоступна. Повторите проверку после восстановления сервиса.");
    }
    return `<span class="cab-msg-check">${esc(text)}</span>`;
  }
  function lessonNote(message) {
    const note = message.lesson_note;
    if (!note) return "";
    const rows = [[word("Reported observation", "Наблюдение из реплики"), note.heard],
      [word("Measure", "Такт"), note.where?.measure], [word("Note", "Нота"), note.where?.note],
      [word("Change", "Что изменить"), note.change], [word("Try", "Как попробовать"), note.try]].filter(([, value]) => value);
    if (!rows.length) return "";
    const attribution = message.speaker === "maestro" ? word("From Maestro's words", "Из слов Маэстро") : word("From Artist's words", "Из слов Артиста");
    return `<section class="cab-lesson-note"><b>${word("Lesson note", "Замечание к уроку")}</b><small>${esc(attribution)}</small><dl>${rows.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl></section>`;
  }
  function messages() {
    return (state.meeting?.deliveries || []).map(message => `<div class="cab-msg muse"><span class="cab-msg-who">Muse · ${esc(message.participant_name || message.speaker)} · ${esc(message.state)}</span>
      ${message.source_text ? `<span class="cab-msg-orig">${esc(message.source_text)}</span>` : ""}<span class="cab-msg-text">${esc(message.text)}</span>
      ${lessonNote(message)}
      ${message.validation_issues?.length ? `<strong>${esc(message.validation_issues.join(", "))}</strong>` : ""}
      ${reviewNote(message)}
      ${state.user?.role === "maestro" && state.meeting.state === "active" && message.state === "flagged" && !["processing","complete"].includes(message.review?.state) ? `<button type="button" class="cab-btn" data-harness-review="${esc(message.id)}"${state.busy ? " disabled" : ""}>${word("Retry translation check", "Повторить проверку перевода")}</button>` : ""}
      ${state.user?.role === "maestro" && ["draft", "flagged"].includes(message.state) ? `<button class="cab-btn" data-harness-approve="${esc(message.id)}" data-flagged="${message.state === "flagged"}"${state.busy || message.approval_allowed === false || (message.state === "flagged" && message.review?.state !== "complete") ? " disabled" : ""}>${word("Approve translation", "Одобрить перевод")}</button>` : ""}
      ${speechControls(message)}</div>`).join("") || `<p>${word("Approved messages will appear here", "Здесь появятся одобренные сообщения")}</p>`;
  }
  function speechControls(message) {
    if (!state.user || message.state !== "approved") return "";
    if (!state.tts) return `<span class="cab-msg-check">${word("Server voice is not connected yet.", "Серверная озвучка пока не подключена.")}</span>`;
    return `<button class="cab-btn" data-harness-speak="${esc(message.id)}" ${state.busy ? "disabled" : ""}>${word("Listen to translation", "Прослушать перевод")}</button><span data-harness-audio="${esc(message.id)}"></span>`
      + (speechAudio && speechMessage === message.id ? `<button class="cab-btn" data-harness-stop-speech>${word("Stop playback", "Остановить воспроизведение")}</button>` : "");
  }
  async function send(text, role) {
    if (!state.user || !state.meeting || state.user.role !== role) {
      state.status = word("Sign in and join your meeting", "Войдите и присоединитесь к своей встрече");
      redraw();
      return;
    }
    if (state.busy) return;
    const user = state.user, meeting = state.meeting.id, pair = languagePair();
    if (!state.pending || state.pending.text !== text || state.pending.user !== user || state.pending.meeting !== meeting || state.pending.source !== pair.source)
      state.pending = { text, id: crypto.randomUUID(), user, meeting, source: pair.source };
    const pending = state.pending;
    await action(async () => {
      state.status = word("Translating and checking… Your message has not been delivered yet.", "Переводим и проверяем… Сообщение ещё не доставлено.");
      redraw();
      await call(`sessions/${meeting}/messages`, {
        client_event_id: pending.id, text, speaker: user.role,
        source_lang: pair.source, target_lang: pair.target,
      });
      if (state.user !== user || state.meeting?.id !== meeting) return;
      state.pending = null; composeText = "";
      await refresh();
    });
  }

  function bind() {
    const on = (selector, event, fn) => document.querySelectorAll(selector).forEach(el => el.addEventListener(event, fn));
    on("[data-harness-auth-retry]", "click", restoreInitialAuth);
    on("[data-harness-language]", "change", event => {
      const language = event.currentTarget.value;
      if (!state.user || state.busy || state.recording || !["en", "vi"].includes(language)) return;
      stopSpeech();
      speakingLanguages.set(state.user.id, language);
      try { sessionStorage.setItem("som_speaking_language:" + state.user.id, language); } catch (_) {}
      state.pending = null;
      redraw();
    });
    on("[data-harness-login]", "submit", event => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const username = data.get("username"), password = data.get("password");
      event.currentTarget.reset();
      action(async () => {
        const user = await call("auth/login", { username, password });
        Object.assign(state, { user, meeting: null, lesson: null, heart: null, sessions: [], pending: null });
        sessionStorage.removeItem("som_meeting"); window.SomLesson?.reset(); window.SomPrivateNotes?.reset();
        await capabilities(); await refresh(); location.hash = "#/space/" + state.user.role;
      });
    });
    on("[data-harness-create]", "submit", event => {
      event.preventDefault();
      const artists = [...new Set(String(new FormData(event.currentTarget).get("artist") || '').split(/[,\s]+/).filter(Boolean))];
      action(async () => {
        if(artists.length<1 || artists.length>2) throw new Error(word('Enter one or two registered Artist IDs.','Укажите один или два зарегистрированных ID Артистов.'));
        state.meeting = await call("sessions", { kind: artists.length>1?'group':'individual', league: "string", maestro_alias: state.user.name,
          artist_alias: artists.join(', '), ...(artists.length>1?{artist_ids:artists}:{artist_id:artists[0]}), source_lang: "en", target_lang: "vi" });
        await refresh();
      });
    });
    on("[data-harness-open]", "click", event => action(async () => {
      window.SomConference?.stop(); state.lesson = null; window.SomLesson?.reset(); window.SomPrivateNotes?.reset();
      state.meeting = await call("sessions/" + event.currentTarget.dataset.harnessOpen);
      if (window.Cabinet) Cabinet.state.drawer[state.user.role] = false;
      await refresh(); location.hash = "#/session/" + state.user.role + (state.meeting.kind==='group'?"/circle":"/one-to-one");
    }));
    on("[data-harness-refresh]", "click", () => action(refresh));
    on("[data-harness-logout]", "click", () => action(async () => {
      cancelCapture(); stopSpeech(); window.SomConference?.stop();
      await window.SomMedia?.disconnect(true).catch(() => {});
      try { await call("auth/logout", {}); }
      finally { sessionStorage.removeItem("som_meeting"); Object.assign(state, { user: null, meeting: null, lesson: null, sessions: [], heart: null, pending: null }); window.SomLesson?.reset(); window.SomPrivateNotes?.reset(); }
    }));
    on("[data-harness-media]", "click", () => action(async () => {
      if (SomMedia.connected(state.meeting.id)) await SomMedia.disconnect(true);
      else await SomMedia.connect(state.meeting.id);
    }));
    for (const verb of ["start", "join", "complete"]) on(`[data-harness-${verb}]`, "click", () => action(async () => {
      await call(`sessions/${state.meeting.id}/${verb}`, {});
      if (verb === "start") await call(`sessions/${state.meeting.id}/join`, {});
      if (verb === "complete") { window.SomConference?.stop(); await window.SomMedia?.disconnect(false); }
      await refresh();
    }));
    on("[data-harness-end]", "click", event => {
      event.preventDefault();
      action(async () => {
        window.SomConference?.stop();
        if (state.user.role === "maestro" && ["active","closing"].includes(state.meeting.state)) await call(`sessions/${state.meeting.id}/complete`, {});
        await refresh(); location.hash = "#/space/" + state.user.role;
      });
    });
    const input = document.querySelector("[data-cab-chat-input]");
    if (input) input.addEventListener("input", () => { composeText = input.value; });
    bindApprovals();
    window.SomMedia?.mount();
    const conferenceHost=document.querySelector('[data-live-conference]');
    if(conferenceHost && state.user && state.meeting?.state==='active' && window.SomConference) {
      const sid=state.meeting.id,conferenceUser=state.user;
      const sameConference=()=>state.user===conferenceUser&&state.meeting?.id===sid;
      SomConference.mount(conferenceHost,{sid,userId:state.user.id,request:async(path,body)=>{
        if(!sameConference()) throw new Error('participant_context_changed');
        if(path===`sessions/${sid}/conference/join`) {
          await call(`sessions/${sid}/join`,{});
          if(!sameConference()) throw new Error('participant_context_changed');
        }
        return call(path,body);
      }});
    } else if(state.meeting?.state==='completed') window.SomConference?.stop();
  }
  function bindApprovals() {
    document.querySelectorAll("[data-harness-review]").forEach(button => button.onclick = () => retryTranslationReview(button.dataset.harnessReview));
    document.querySelectorAll("[data-harness-approve]").forEach(button => button.onclick = () => {
      const id = button.dataset.harnessApprove;
      const flagged = button.dataset.flagged === "true";
      if (flagged && !window.confirm(word("The validator flagged this translation. Have you reviewed it?", "Валидатор отметил ошибку. Вы проверили перевод?"))) return;
      action(async () => { await call(`sessions/${state.meeting.id}/messages/${id}/approve`, { confirm_flagged: flagged }); await refresh(); });
    });
    document.querySelectorAll("[data-harness-speak]").forEach(button => button.onclick = () => playSpeech(button.dataset.harnessSpeak));
    document.querySelectorAll("[data-harness-stop-speech]").forEach(button => button.onclick = () => { stopSpeech(); redraw(); });
    if (speechAudio && speechMessage) {
      const slot = Array.from(document.querySelectorAll("[data-harness-audio]")).find(el => el.dataset.harnessAudio === speechMessage);
      if (slot) slot.appendChild(speechAudio);
    }
  }
  async function capabilities() {
    const user = state.user;
    const caps = (await call("health")).capabilities;
    if (state.user !== user) return;
    state.asr = !!caps.asr; state.tts = !!caps.tts; state.media = !!caps.private_media_transport;
  }
  function stopSpeech() {
    if (speechAbort) speechAbort.abort();
    if (speechAudio) { speechAudio.pause(); speechAudio.removeAttribute("src"); speechAudio.load(); speechAudio.remove(); }
    if (speechURL) URL.revokeObjectURL(speechURL);
    speechAudio = null; speechURL = null; speechAbort = null; speechMessage = null;
  }
  async function playSpeech(mid) {
    if (state.busy || !state.user || !state.meeting) return;
    stopSpeech();
    if (!state.tts) {
      state.status = word("Server voice is not connected yet.", "Серверная озвучка пока не подключена.");
      redraw(); return;
    }
    if (window.SomMedia?.connected(state.meeting.id)) {
      await action(() => SomMedia.say(mid));
      return;
    }
    const controller = new AbortController(); speechAbort = controller;
    const user = state.user, meeting = state.meeting.id;
    const current = () => !controller.signal.aborted && speechAbort === controller
      && state.user === user && state.meeting?.id === meeting;
    await action(async () => {
      let data;
      try {
        // Server resolves the approved canonical text; the browser sends no text.
        // call() checks both participant request and response markers.
        data = await call(`sessions/${encodeURIComponent(meeting)}/messages/${encodeURIComponent(mid)}/speech`, {}, {signal: controller.signal});
      } catch (error) { if (!current()) return; throw error; }
      if (!current()) return;
      if (!["en", "vi"].includes(data.language) || typeof data.wav_base64 !== "string"
          || !data.wav_base64 || data.wav_base64.length > 1_280_140) throw new Error("speech_unavailable");
      const bytes = Uint8Array.from(atob(data.wav_base64), char => char.charCodeAt(0));
      if (!current()) return;
      speechURL = URL.createObjectURL(new Blob([bytes], {type:"audio/wav"}));
      speechAudio = new Audio(speechURL); speechAudio.controls = true;
      speechAudio.setAttribute("aria-label", word("Approved translation", "Одобренный перевод"));
      speechAudio.style.maxWidth = "100%"; speechMessage = mid;
      // Explicit controls remain if a browser requires a second playback gesture.
      await speechAudio.play().catch(() => {});
    });
  }
  async function restoreInitialAuth() {
    if (state.user) return;
    if (initialAuthAttempt) initialAuthAttempt.controller.abort();
    const attempt = { controller: new AbortController() };
    initialAuthAttempt = attempt;
    state.authChecking = true; state.authCheckFailed = false; redraw();
    let timer = null;
    try {
      const deadline = new Promise((_, reject) => {
        timer = setTimeout(() => { attempt.controller.abort(); reject(new Error("auth_check_timeout")); }, 20000);
        timer?.unref?.();
      });
      const lookup = (async () => {
        const response = await fetch("/api/harness/auth/me", { credentials: "same-origin", signal: attempt.controller.signal });
        const data = await response.json();
        if (response.status === 401) return null;
        if (!response.ok || typeof data?.id !== "string" || !["maestro", "artist"].includes(data.role)) throw new Error("auth_check_failed");
        return data;
      })();
      const user = await Promise.race([lookup, deadline]);
      clearTimeout(timer); timer = null;
      if (initialAuthAttempt !== attempt || attempt.controller.signal.aborted || state.user) return;
      state.authChecking = false;
      if (!user) { redraw(); return; }
      state.user = user; redraw();
      const initialMeeting = state.meeting;
      const current = () => state.user === user && state.meeting === initialMeeting;
      await capabilities();
      if (!current()) return;
      const saved = sessionStorage.getItem("som_meeting");
      if (saved) {
        try {
          const meeting = await call("sessions/" + encodeURIComponent(saved));
          if (!current()) return;
          state.meeting = meeting;
          if (window.Cabinet) Cabinet.state.drawer[user.role] = false;
        }
        catch (_) { if (!current()) return; sessionStorage.removeItem("som_meeting"); }
      }
      if (await refresh()) redraw();
    } catch (_) {
      if (initialAuthAttempt === attempt && !state.user) {
        state.authChecking = false; state.authCheckFailed = true; redraw();
      }
    } finally {
      if (timer !== null) clearTimeout(timer);
      if (initialAuthAttempt === attempt) initialAuthAttempt = null;
      if (state.user) state.authChecking = false;
    }
  }
  restoreInitialAuth();
  setInterval(async () => {
    if (!state.user || !state.meeting || state.busy || document.visibilityState !== "visible" || !location.hash.startsWith("#/session/")) return;
    if (document.activeElement?.matches("input,textarea")) return;
    const before = JSON.stringify({ state: state.meeting.state, heart: state.heart, lesson: state.lesson?.revision, materials: state.meeting.lesson_translations, planner: state.meeting.lesson_planner, notes: state.meeting.private_notes });
    const messagesBefore = JSON.stringify(state.meeting.deliveries);
    try {
      if (!await refresh()) return;
      if (before !== JSON.stringify({ state: state.meeting.state, heart: state.heart, lesson: state.lesson?.revision, materials: state.meeting.lesson_translations, planner: state.meeting.lesson_planner, notes: state.meeting.private_notes })) redraw();
      else if (messagesBefore !== JSON.stringify(state.meeting.deliveries)) {
        const chat = document.querySelector(".cab-chat");
        if (chat) { chat.innerHTML = messages(); bindApprovals(); }
      }
    } catch (_) { /* The explicit refresh action displays errors. */ }
  }, 5000);
  function cancelCapture() {
    if (captureAbort) captureAbort.abort();
    capture = null; captureAbort = null; composeText = ""; focusCompose = false; state.recording = false;
  }
  async function record() {
    if (capture) { capture.stop(); return; }
    if (state.recording && captureAbort) { captureAbort.abort(); return; }
    if (!state.asr || state.busy || state.recording || !state.meeting || state.meeting.state !== "active") return;
    if (!state.user) return;
    const user = state.user, meeting = state.meeting.id, language = languagePair().source;
    const controller = new AbortController();
    const current = () => !controller.signal.aborted && captureAbort === controller
      && state.user === user && state.meeting?.id === meeting;
    captureAbort = controller;
    state.recording = true; state.status = word("Recording · up to 10 seconds", "Запись · до 10 секунд"); redraw();
    try {
      // Explicit dictation follows the participant language, independently of
      // role-fixed private RTC interpretation. Direct AV remains connected.
      capture = await SomAudio.start(controller.signal);
      const audio = await capture.result;
      if (!current()) return;
      state.recording = false; capture = null;
      await action(async () => {
        state.status = word("Recognizing speech… Review the text before sending.", "Распознаём речь… Проверьте текст перед отправкой.");
        redraw();
        const transcript = await call(`sessions/${meeting}/transcriptions`, {
          client_event_id: crypto.randomUUID(), language, wav_base64: audio,
        });
        if (!current()) return;
        composeText = transcript.text; focusCompose = true;
        state.status = "";
        // The participant reviews the recognized words before sending them.
        redraw();
        const input = document.querySelector("[data-cab-chat-input]");
        if (input) { input.value = transcript.text; input.focus(); }
      });
    } catch (error) {
      if (current()) state.status = word("Recording could not be transcribed", "Запись не удалось распознать") + " · " + error.message;
    } finally {
      if (captureAbort === controller) { captureAbort = null; capture = null; state.recording = false; }
      redraw();
    }
  }
  window.addEventListener("som-media-changed", redraw);
  window.addEventListener("pagehide", stopSpeech);
  window.addEventListener("hashchange", () => { cancelCapture(); stopSpeech(); window.SomConference?.stop(); window.SomMedia?.disconnect(true).catch(() => {}); });
  return { state, panel, messages, send, bind, record, languagePair, languageControls, updateLesson, translateLessonStep, approveLessonTranslation, requestLessonPlan, applyLessonPlan, planningRetryAllowed, retryTranslationReview, savePrivateNotes, privateNotesPage };
})();
