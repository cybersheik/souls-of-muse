"use strict";

window.CabinetHarness = (() => {
  const state = { user: null, meeting: null, sessions: [], heart: null, busy: false, status: "", pending: null, recording: false, asr: false };
  let capture = null, captureAbort = null, composeText = "", focusCompose = false;
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
  async function call(path, body) {
    const response = await fetch("/api/harness/" + path, {
      method: body === undefined ? "GET" : "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json();
    if (response.status === 401) {
      Object.assign(state, { user: null, meeting: null, sessions: [], heart: null });
    }
    if (!response.ok) throw new Error(data.detail || "request_failed");
    return data;
  }
  async function refresh() {
    state.sessions = (await call("sessions")).sessions;
    if (state.meeting) {
      sessionStorage.setItem("som_meeting", state.meeting.id);
      state.meeting = await call("sessions/" + state.meeting.id);
      state.heart = await call("sessions/" + state.meeting.id + "/heart");
    }
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
  function panel() {
    const disabled = state.busy ? " disabled" : "";
    const home = !location.hash.startsWith("#/session/");
    if (!state.user) return `<section class="cab-live"><b>${word("Join your meeting", "Войти на встречу")}</b>
      <form data-harness-login><label>${word("Participant", "Участник")}<input name="username" autocomplete="username" required maxlength="100"></label>
      <label>${word("Password", "Пароль")}<input name="password" type="password" autocomplete="current-password" required maxlength="256"></label>
      <button class="cab-btn"${disabled}>${word("Sign in", "Войти")}</button></form><p role="status">${esc(state.status)}</p></section>`;
    return `<section class="cab-live"><b>${esc(state.user.name)} · ${esc(state.user.role)}</b>
      <button class="cab-btn" data-harness-refresh${disabled}>${word("Refresh", "Обновить")}</button>
      <button class="cab-btn" data-harness-logout${disabled}>${word("Sign out", "Выйти")}</button>
      ${home && state.user.role === "maestro" ? `<form data-harness-create><label>${word("Artist's participant ID", "ID участника-Артиста")}<input name="artist" required maxlength="100"></label>
        <button class="cab-btn"${disabled}>${word("Create meeting", "Создать встречу")}</button></form>` : ""}
      <div class="cab-live-meetings">${(home ? state.sessions : []).map(s => `<button class="cab-btn" data-harness-open="${esc(s.id)}"${disabled}>${esc(s.maestro_alias)} · ${esc(s.artist_alias)} · ${esc(s.state)}</button>`).join("")}</div>
      ${state.meeting ? `<p>${word("Meeting", "Встреча")} · ${esc(state.meeting.state)}</p>
        ${state.user.role === "maestro" && state.meeting.state === "created" ? `<button class="cab-btn" data-harness-start${disabled}>${word("Start", "Начать")}</button>` : ""}
        ${state.meeting.state === "active" ? `<button class="cab-btn" data-harness-join${disabled}>${word("Join", "Присоединиться")}</button>
          ${state.user.role === "maestro" ? `<button class="cab-btn" data-harness-complete${disabled}>${word("Complete", "Завершить")}</button>` : ""}` : ""}
        ${state.heart ? `<p>♥ ${word("Meetings", "Встречи")} ${state.heart.counters.happened} · ${word("Useful", "Полезно")} ${state.heart.counters.useful} · ${word("Progress", "Прогресс")} ${state.heart.counters.progress}</p>` : ""}` : ""}
      <p role="status">${esc(state.status)}</p></section>`;
  }
  function messages() {
    return (state.meeting?.deliveries || []).map(message => `<div class="cab-msg muse"><span class="cab-msg-who">Muse · ${esc(message.speaker)} · ${esc(message.state)}</span>
      ${message.source_text ? `<span class="cab-msg-orig">${esc(message.source_text)}</span>` : ""}<span class="cab-msg-text">${esc(message.text)}</span>
      ${message.validation_issues?.length ? `<strong>${esc(message.validation_issues.join(", "))}</strong>` : ""}
      ${state.user?.role === "maestro" && ["draft", "flagged"].includes(message.state) ? `<button class="cab-btn" data-harness-approve="${esc(message.id)}" data-flagged="${message.state === "flagged"}">${word("Approve translation", "Одобрить перевод")}</button>` : ""}</div>`).join("") || `<p>${word("Approved messages will appear here", "Здесь появятся одобренные сообщения")}</p>`;
  }
  async function send(text, role) {
    if (!state.user || !state.meeting || state.user.role !== role) {
      state.status = word("Sign in and join your meeting", "Войдите и присоединитесь к своей встрече");
      redraw();
      return;
    }
    if (!state.pending || state.pending.text !== text) state.pending = { text, id: crypto.randomUUID() };
    await action(async () => {
      await call(`sessions/${state.meeting.id}/messages`, {
        client_event_id: state.pending.id, text, speaker: state.user.role,
        source_lang: role === "maestro" ? "en" : "vi", target_lang: role === "maestro" ? "vi" : "en",
      });
      state.pending = null; composeText = "";
      await refresh();
    });
  }
  function bind() {
    const on = (selector, event, fn) => document.querySelectorAll(selector).forEach(el => el.addEventListener(event, fn));
    on("[data-harness-login]", "submit", event => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const username = data.get("username"), password = data.get("password");
      event.currentTarget.reset();
      action(async () => { state.user = await call("auth/login", { username, password }); state.asr = !!(await call("health")).capabilities.asr; await refresh(); location.hash = "#/space/" + state.user.role; });
    });
    on("[data-harness-create]", "submit", event => {
      event.preventDefault();
      const artist = new FormData(event.currentTarget).get("artist");
      action(async () => {
        state.meeting = await call("sessions", { kind: "individual", league: "string", maestro_alias: state.user.name,
          artist_alias: artist, artist_id: artist, source_lang: "en", target_lang: "vi" });
        await refresh();
      });
    });
    on("[data-harness-open]", "click", event => action(async () => {
      state.meeting = await call("sessions/" + event.currentTarget.dataset.harnessOpen);
      if (window.Cabinet) Cabinet.state.drawer[state.user.role] = false;
      await refresh(); location.hash = "#/session/" + state.user.role + "/one-to-one";
    }));
    on("[data-harness-refresh]", "click", () => action(refresh));
    on("[data-harness-logout]", "click", () => action(async () => { cancelCapture(); await call("auth/logout", {}); sessionStorage.removeItem("som_meeting"); Object.assign(state, { user: null, meeting: null, sessions: [], heart: null, pending: null }); }));
    for (const verb of ["start", "join", "complete"]) on(`[data-harness-${verb}]`, "click", () => action(async () => {
      await call(`sessions/${state.meeting.id}/${verb}`, {});
      if (verb === "start") await call(`sessions/${state.meeting.id}/join`, {});
      await refresh();
    }));
    on("[data-harness-end]", "click", event => {
      event.preventDefault();
      action(async () => {
        if (state.user.role === "maestro" && state.meeting.state === "active") await call(`sessions/${state.meeting.id}/complete`, {});
        await refresh(); location.hash = "#/space/" + state.user.role;
      });
    });
    const input = document.querySelector("[data-cab-chat-input]");
    if (input) input.addEventListener("input", () => { composeText = input.value; });
    bindApprovals();
  }
  function bindApprovals() {
    document.querySelectorAll("[data-harness-approve]").forEach(button => button.onclick = () => {
      const id = button.dataset.harnessApprove;
      const flagged = button.dataset.flagged === "true";
      if (flagged && !window.confirm(word("The validator flagged this translation. Have you reviewed it?", "Валидатор отметил ошибку. Вы проверили перевод?"))) return;
      action(async () => { await call(`sessions/${state.meeting.id}/messages/${id}/approve`, { confirm_flagged: flagged }); await refresh(); });
    });
  }
  call("auth/me").then(async user => {
    state.user = user;
    state.asr = !!(await call("health")).capabilities.asr;
    const saved = sessionStorage.getItem("som_meeting");
    if (saved) {
      try { state.meeting = await call("sessions/" + encodeURIComponent(saved)); if (window.Cabinet) Cabinet.state.drawer[user.role] = false; }
      catch (_) { sessionStorage.removeItem("som_meeting"); }
    }
    await refresh(); redraw();
  }).catch(() => {});
  setInterval(async () => {
    if (!state.user || !state.meeting || state.busy || document.visibilityState !== "visible" || !location.hash.startsWith("#/session/")) return;
    if (document.activeElement?.matches("input,textarea")) return;
    const before = JSON.stringify({ state: state.meeting.state, heart: state.heart });
    const messagesBefore = JSON.stringify(state.meeting.deliveries);
    try {
      await refresh();
      if (before !== JSON.stringify({ state: state.meeting.state, heart: state.heart })) redraw();
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
    if (!state.asr || state.busy || state.recording || !state.meeting || state.meeting.state !== "active") return;
    const controller = new AbortController();
    captureAbort = controller;
    state.recording = true; state.status = word("Recording · up to 10 seconds", "Запись · до 10 секунд"); redraw();
    try {
      capture = await SomAudio.start(controller.signal);
      const audio = await capture.result;
      const meeting = state.meeting.id;
      state.recording = false; capture = null;
      await action(async () => {
        const transcript = await call(`sessions/${meeting}/transcriptions`, {
          client_event_id: crypto.randomUUID(), language: state.user.role === "maestro" ? "en" : "vi", wav_base64: audio,
        });
        if (controller.signal.aborted) return;
        composeText = transcript.text; focusCompose = true;
        state.status = "";
        // The participant reviews the recognized words before sending them.
        redraw();
        const input = document.querySelector("[data-cab-chat-input]");
        if (input) { input.value = transcript.text; input.focus(); }
      });
    } catch (error) {
      if (!controller.signal.aborted) state.status = word("Recording could not be transcribed", "Запись не удалось распознать") + " · " + error.message;
    } finally {
      if (captureAbort === controller) { captureAbort = null; capture = null; state.recording = false; }
      redraw();
    }
  }
  window.addEventListener("hashchange", cancelCapture);
  return { state, panel, messages, send, bind, record };
})();
