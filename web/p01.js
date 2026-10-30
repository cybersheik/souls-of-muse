"use strict";
/* Portal P0.1 views: 02 Welcome, 03 Personal space, 04 Components.
   All user text comes from web/strings.js (window.P01Strings).
   Demo member is the mock's Lina Khairullina; no backend success is claimed:
   votes are "not open yet", session entry points at the preserved lesson page
   only where the mock does, everything else stays a local UI state. */
const PS = window.P01Strings;
const ROLE_HASH = { artist: "student", maestro: "teacher", admirer: "listener" };
const ROLE_KEY = { student: "artist", teacher: "maestro", listener: "admirer" };
const state = {
  lang: "en", medal: "playful", originOpen: false, mode: "group", playing: null,
};
try { const l = localStorage.getItem("som_p01_lang"); if (l === "ru" || l === "en") state.lang = l; } catch (e) {}
const escP = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const t = () => PS.T[state.lang];

/* --- audio: only on explicit click, copied note sequences from P0.1 --- */
let p01actx = null, p01voices = [], p01timer = null;
function stopAudio() {
  p01voices.forEach(v => { try { v.stop(); } catch (e) {} });
  p01voices = []; clearTimeout(p01timer);
  if (state.playing) { state.playing = null; document.querySelectorAll("[data-p01-play]").forEach(b => { b.innerHTML = '<i class="ph-fill ph-play"></i>'; b.setAttribute("aria-pressed", "false"); }); }
}
function playSeq(id, sig) {
  if (state.playing === id) { stopAudio(); return; }
  stopAudio();
  const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
  p01actx = p01actx || new AC(); if (p01actx.state === "suspended") p01actx.resume();
  const beat = 60 / sig.bpm; let when = p01actx.currentTime + 0.05;
  const master = p01actx.createGain(); master.gain.value = 0.22; master.connect(p01actx.destination);
  sig.seq.forEach(([m, b], i) => {
    let d = b * beat; if (sig.swing && b === .5) d = beat * (i % 2 ? .34 : .66);
    const f = 440 * Math.pow(2, (m - 69) / 12);
    [["triangle", 1], ["sine", .5]].forEach(([type, amp], k) => {
      const o = p01actx.createOscillator(), g = p01actx.createGain();
      o.type = type; o.frequency.value = f * (k ? 2 : 1);
      g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(amp * (k ? .25 : 1), when + .015);
      g.gain.exponentialRampToValueAtTime(0.001, when + Math.max(d * .95, .18));
      o.connect(g); g.connect(master); o.start(when); o.stop(when + d + .05); p01voices.push(o);
    });
    when += d;
  });
  state.playing = id;
  const btn = document.querySelector(`[data-p01-play="${id}"]`);
  if (btn) { btn.innerHTML = '<i class="ph-fill ph-pause"></i>'; btn.setAttribute("aria-pressed", "true"); }
  p01timer = setTimeout(stopAudio, (when - p01actx.currentTime) * 1000 + 150);
}

function langSwitch() {
  return `<div class="p01-lang" role="group" aria-label="Language">
    <button data-lang="en" aria-pressed="${state.lang === "en"}">EN</button>
    <button data-lang="ru" aria-pressed="${state.lang === "ru"}">RU</button></div>`;
}
function head(mode, current) {
  const tt = t();
  const nav = [["#/convention", tt.navConv], ["#/leagues", tt.navLeagues], ["#/space", tt.navSpace]];
  return `<header class="p01-head">
    <a class="p01-brand" href="#/"><img src="assets/lyre.png" alt="Golden Lyre"><span class="serif">Souls of Muse</span></a>
    <nav class="p01-nav" aria-label="Souls of Muse">${nav.map(([h, l]) => `<a href="${h}"${l === current ? ' aria-current="page"' : ""}>${escP(l)}</a>`).join("")}</nav>
    <div class="p01-spacer"></div>${langSwitch()}
    ${mode === "workshop" ? '<div class="p01-avatar" aria-label="Lina Khairullina">LK</div>' : ""}
  </header>`;
}
function memberCard(compact) {
  const tt = t();
  return `<div class="${compact ? "p01-minicard" : "p01-membercard"}">
    <div style="display:flex;gap:14px;align-items:center">
      <div class="p01-seal"><img src="assets/lyre.png" alt=""></div>
      <div style="display:flex;flex-direction:column;gap:2px;min-width:0">
        <span class="p01-kicker">${escP(tt.cardKicker)}</span>
        <span class="serif" style="font-size:${compact ? 22 : 28}px;font-weight:500;line-height:1.05">Lina Khairullina</span>
        <span class="mono" style="font-size:12px">SOUL 000127</span>
      </div>
      ${compact ? `<div class="p01-spacer"></div><img src="assets/medal-${state.medal}.png" alt="${escP(tt.medalName)}" style="height:58px">` : ""}
    </div>
    <div class="p01-sigstrip"><img src="assets/sig-latin.png" alt="Note signature of Lina Khairullina"></div>
    ${compact ? "" : `<div class="p01-cardmeta"><span>${escP(tt.cardSigned)}</span><span>${escP(tt.cardLeague)}</span></div>`}
  </div>`;
}
function medalCard() {
  const tt = t();
  return `<div class="p01-plaincard center">
    <img class="medal" src="assets/medal-${state.medal}.png" alt="${escP(tt.medalName)}">
    <span class="serif" style="font-size:22px;font-weight:500">${escP(tt.medalName)}</span>
    <span style="font-size:13px;color:var(--p01-muted)">${escP(tt.medalFor)}</span>
    <span style="font-size:12px;color:var(--p01-muted)">${escP(tt.styleLabel)}</span>
    <div class="p01-seg" role="group" aria-label="${escP(tt.styleLabel)}">
      <button data-medal="playful" aria-pressed="${state.medal === "playful"}">${escP(tt.playful)}</button>
      <button data-medal="classic" aria-pressed="${state.medal === "classic"}">${escP(tt.classic)}</button>
    </div></div>`;
}
function roleTabs(activeKey) {
  const tt = t();
  const defs = [["teacher", tt.roleT, "baton"], ["student", tt.roleS, "ph-microphone"], ["listener", tt.roleL, "ph-headphones"]];
  return `<div class="p01-roles" role="tablist" aria-label="${escP(tt.navSpace)}">${defs.map(([k, label, ic]) =>
    `<button role="tab" data-role="${k}" aria-selected="${k === activeKey}">${ic === "baton" ? '<span class="p01-baton" aria-hidden="true"></span>' : `<i class="ph ${ic}"></i>`}${escP(label)}</button>`).join("")}</div>`;
}

function welcome() {
  const tt = t();
  return `<div class="p01 p01-ceremony">${head("ceremony", tt.navSpace)}
  <main id="main" tabindex="-1" class="p01-wrap">
    <div class="p01-welcome-hero">
      <span class="p01-kicker">${escP(tt.wKicker)}</span>
      <h1>${escP(tt.wTitle)}</h1>
    </div>
    <div style="padding-top:22px">
      <div class="p01-sigframe">
        <img src="assets/sig-latin.png" alt="Note signature of Lina Khairullina">
        <div class="p01-playrow">
          <button class="p01-play" data-p01-play="lina" aria-label="${escP(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
          <div><div style="font-size:15px;font-weight:500">${escP(tt.listenYours)}</div>
          <div class="mono" style="font-size:11.5px;color:var(--p01-faint)">Hip-hop · 88 bpm · 0:07</div></div>
        </div>
      </div>
      <p class="p01-sub" style="margin:14px 4px 0">${escP(tt.wSub)}</p>
    </div>
    <div class="p01-gifts">
      <div><div class="p01-giftlabel">${escP(tt.gCard)}</div>${memberCard(false)}</div>
      <div><div class="p01-giftlabel">${escP(tt.gMedal)}</div>${medalCard()}</div>
      <div><div class="p01-giftlabel">${escP(tt.gVoice)}</div>
        <div class="p01-plaincard" style="height:calc(100% - 26px)">
          <i class="ph ph-scroll" style="font-size:32px;color:var(--p01-gold-ink)"></i>
          <span class="serif" style="font-size:26px;font-weight:500;line-height:1.1">${escP(tt.voiceTitle)}</span>
          <span style="font-size:14px;line-height:1.5;color:var(--p01-muted)">${escP(tt.voiceBody)}</span>
          <div class="p01-spacer"></div>
          <span class="p01-chip"><i class="ph ph-clock"></i>${escP(tt.chipNotOpen)}</span>
        </div></div>
    </div>
    <div style="padding:34px 0 0"><a class="p01-cta" href="#/space">${escP(tt.cta)} <i class="ph ph-arrow-right"></i> ${escP(tt.ctaTail)}</a></div>
    <div class="p01-accordion">
      <button data-origin aria-expanded="${state.originOpen}"><i class="ph ph-music-notes-simple" style="color:var(--p01-gold-ink)"></i><span style="flex:1">${escP(tt.originQ)}</span><i class="ph ${state.originOpen ? "ph-caret-up" : "ph-caret-down"}"></i></button>
      ${state.originOpen ? `<div class="p01-origin">${PS.ORIGIN[state.lang].map(([title, body], i) =>
        `<div><div class="n">${["I", "II", "III"][i]}</div><div style="font-size:14px;font-weight:500">${escP(title)}</div><div style="font-size:13.5px;line-height:1.5;color:var(--p01-muted)">${escP(body)}</div></div>`).join("")}</div>` : ""}
    </div>
  </main></div>`;
}

function space(roleKey) {
  const tt = t();
  const R = PS.ROLE[roleKey], RL = R[state.lang];
  const iniName = Object.fromEntries(R.people.map(p => [p[0], p[1]]));
  const leagueIcon = roleKey === "teacher" ? "ph-microphone-stage" : roleKey === "listener" ? "ph-feather" : "ph-guitar";
  const recPlay = (kind, i) => `data-p01-rec="${kind}:${i}"`;
  return `<div class="p01 p01-workshop">${head("workshop", tt.navSpace)}
  <main id="main" tabindex="-1" class="p01-wrap">
    <div class="p01-space-top">
      <div><div class="mono" style="font-size:12.5px;color:var(--p01-n400)">${escP(tt.dateLine)}</div>
      <h1>${escP(tt.greet)}</h1></div>
      <div class="p01-spacer"></div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
        <span style="font-size:12px;color:var(--p01-n400)">${escP(tt.roleHint)}</span>${roleTabs(roleKey)}
      </div>
    </div>
    <div class="p01-grid">
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <section class="p01-panel" aria-label="${escP(tt.today)}">
          <div style="display:flex;gap:10px;align-items:center"><span class="p01-kicker">${escP(tt.today)}</span><span class="p01-tag"><i class="ph ${RL.today.chipIcon}"></i>${escP(RL.today.chip)}</span></div>
          <div><div style="font-size:13px;color:var(--p01-accent300)">${escP(RL.today.kicker)}</div>
          <div style="font-size:24px;font-weight:500;line-height:1.2">${escP(RL.today.title)}</div>
          <div class="mono" style="font-size:12.5px;color:var(--p01-n400)">${escP(RL.today.meta)}</div></div>
          <div class="p01-people">${R.todayPeople.map(i => `<span class="p01-ava" title="${escP(iniName[i] || "")}">${escP(i)}</span>`).join("")}<span style="font-size:12.5px;color:var(--p01-n400)">${escP(RL.today.peopleNote)}</span></div>
          ${R.lesson ? `<div style="display:flex;flex-direction:column;gap:8px"><span style="font-size:12.5px;color:var(--p01-n300)">${escP(tt.mode)}</span>
            ${[["indiv", tt.indiv, RL.modes.indiv], ["group", tt.group, RL.modes.group]].map(([k, label, sub]) =>
              `<button class="p01-mode" data-mode="${k}" role="radio" aria-checked="${state.mode === k}"><span class="p01-radio"><i></i></span><span><span style="display:block;font-size:14px;font-weight:500">${escP(label)}</span><span style="font-size:12px;color:var(--p01-n400)">${escP(sub)}</span></span></button>`).join("")}</div>` : ""}
          <a class="p01-btn primary" href="${R.lesson ? "lesson.html" : "#/space/admirer"}">${escP(RL.today.action)} <i class="ph ph-arrow-right"></i></a>
        </section>
        <section class="p01-panel p01-muse" aria-label="MUSE">
          <div style="display:flex;gap:10px;align-items:center"><img src="assets/muse-badge.png" alt="MUSE" style="width:34px"><span style="font-size:13.5px;font-weight:500">${escP(tt.museTitle)}</span><span style="font-size:12px;color:var(--p01-n400)">${escP(tt.museRule)}</span></div>
          <div style="font-size:14px;line-height:1.5;color:#d8d5e6">${escP(RL.muse.intro)}</div>
          <div class="p01-quote">${escP(RL.muse.quote)}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><button class="p01-btn primary">${escP(RL.muse.a1)}</button><button class="p01-btn ghost">${escP(RL.muse.a2)}</button><div class="p01-spacer"></div><span class="mono" style="font-size:12px;color:var(--p01-n400)">${escP(RL.muse.meta)}</span></div>
        </section>
        <section class="p01-panel" aria-label="${escP(RL.recsTitle)}">
          <span class="p01-kicker">${escP(RL.recsTitle)}</span>
          ${RL.recs.map(([kind, title, meta, chip], i) => `<div class="p01-rec">
            <button class="p01-play sm" ${recPlay(kind, i)} aria-label="${escP(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
            <div style="flex:1;min-width:0"><div style="font-size:14px">${escP(title)}</div><div class="mono" style="font-size:12px;color:var(--p01-n400)">${escP(meta)}</div>
            ${chip ? `<span class="p01-tag" style="margin-top:4px"><i class="ph ph-seal-question"></i>${escP(chip)}</span>` : ""}</div></div>`).join("")}
        </section>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <section class="p01-panel" aria-label="${escP(tt.league)}">
          <div style="display:flex;gap:12px;align-items:center"><span class="p01-emblem"><img src="assets/frame-classic.png" alt=""><i class="ph ${leagueIcon}"></i></span>
          <div><div class="p01-kicker">${escP(tt.league)}</div><div style="font-size:18px;font-weight:500">${escP(RL.league.name)}</div></div></div>
          <div class="p01-place"><i class="ph ph-user-circle" style="color:var(--p01-accent300);font-size:16px"></i>${escP(RL.place)}</div>
          <div style="font-size:12px;color:var(--p01-n400)">${escP(tt.people)}</div>
          ${R.people.map(([ini, nm, re, rr, langs]) => `<div style="display:flex;gap:10px;align-items:center"><span class="p01-ava">${escP(ini)}</span><div><div style="font-size:14px">${escP(nm)}</div><div style="font-size:12px;color:var(--p01-n400)">${escP(state.lang === "en" ? re : rr)} · ${escP(langs)}</div></div></div>`).join("")}
          <div style="font-size:12px;color:var(--p01-n400)">${escP(tt.events)}</div>
          ${RL.league.events.map(([mon, day, title, meta]) => `<div class="p01-event"><span class="p01-datebox"><span style="font-size:10.5px;color:var(--p01-n400);text-transform:uppercase">${escP(mon)}</span><span style="font-size:17px;font-weight:500">${escP(day)}</span></span><div><div style="font-size:14px">${escP(title)}</div><div class="mono" style="font-size:12px;color:var(--p01-n400)">${escP(meta)}</div></div></div>`).join("")}
          <span class="p01-chip" style="background:var(--p01-n900);border-color:var(--p01-n800);color:var(--p01-n300)"><i class="ph ph-clock"></i>${escP(tt.chipVote)}</span>
        </section>
        ${memberCard(true)}
      </div>
    </div>
  </main></div>`;
}

function components() {
  const tt = t();
  const en = state.lang === "en";
  const chipL = en ? ["Composing your melody", "No League chosen yet", "First vote not open yet", "Confirm from Instagram"]
                   : ["Сочиняем вашу мелодию", "Лига ещё не выбрана", "Первое голосование ещё не открыто", "Подтвердить из Instagram"];
  const chipD = en ? ["Loading session plan", "No recordings yet", "League vote not open yet", "Needs Maestro's OK"]
                   : ["Загружаем план встречи", "Записей пока нет", "Голосование Лиги ещё не открыто", "Нужно одобрение Маэстро"];
  return `<div class="p01">${head("workshop", "")}
  <main id="main" tabindex="-1" class="p01-comp">
    <section class="light">
      <span class="p01-kicker">Ceremony</span>
      <div><h2>${en ? "Note-signature frame" : "Рамка нотной подписи"}</h2>
        <div class="p01-sigframe" style="margin-top:12px">
          <div class="p01-playrow" style="padding-top:2px"><button class="p01-play" data-p01-play="comp" aria-label="${escP(tt.listen)}" aria-pressed="false" style="width:52px;height:52px;font-size:20px"><i class="ph-fill ph-play"></i></button>
          <div><div class="serif" style="font-size:24px;font-weight:500">김민지 · Kim Minji</div><div class="mono" style="font-size:12px;color:var(--p01-faint)">Waltz · 150 bpm · 3/4</div></div></div>
          <img src="assets/sig-korean.png" alt="Note signature of Kim Minji">
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px">
          <div class="p01-sigstrip"><img src="assets/sig-japanese.png" alt="さくら"></div>
          <div class="p01-sigstrip"><img src="assets/sig-short.png" alt="Haydn"></div>
          <div class="p01-sigstrip"><img src="assets/sig-viet.png" alt="Nguyễn Thị Mai"></div>
        </div></div>
      <div><h2>Card</h2><div style="margin-top:12px">${memberCard(false)}</div></div>
      <div><h2>${en ? "Medal · member's choice" : "Медаль · выбор участника"}</h2><div style="margin-top:12px">${medalCard()}</div></div>
      <div><h2>${en ? "League emblem frame" : "Рамка эмблемы Лиги"}</h2>
        <div class="p01-leagues" style="margin-top:12px">${PS.LEAGUES.map(([ic, e, r]) => `<span class="p01-league"><span class="p01-emblem"><img src="assets/frame-classic.png" alt=""><i class="ph ${ic}"></i></span>${escP(en ? e : r)}</span>`).join("")}</div></div>
      <div><h2>${en ? "Status chips" : "Чипы статусов"}</h2><div class="p01-chips" style="margin-top:12px">${chipL.map(c => `<span class="p01-chip">${escP(c)}</span>`).join("")}</div></div>
    </section>
    <section class="dark">
      <span class="p01-kicker" style="color:var(--p01-accent300)">Workshop</span>
      <div><h2>${en ? "Role switch · one space, three contexts" : "Переключатель роли · одно пространство, три контекста"}</h2><div style="margin-top:12px">${roleTabs("student")}</div></div>
      <div><h2>${en ? "Note-signature frame on Workshop ground" : "Рамка подписи на фоне Мастерской"}</h2>
        <div class="p01-darkframe" style="margin-top:12px"><button class="p01-play sm" data-p01-play="lina" aria-label="${escP(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
        <div class="p01-sigstrip" style="flex:1"><img src="assets/sig-latin.png" alt="Note signature of Lina Khairullina"></div></div></div>
      <div><h2>MUSE</h2><div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:12px">
        <span style="display:flex;gap:10px;align-items:center"><img src="assets/muse-badge.png" alt="MUSE" style="width:40px">MUSE · mediator</span>
        <span style="display:flex;gap:10px;align-items:center"><img src="assets/lyre.png" alt="Golden Lyre" style="height:40px">Souls of Muse · community</span></div></div>
      <div><h2>${en ? "League emblem frame · compact" : "Рамка эмблемы Лиги · компактно"}</h2>
        <div style="display:flex;gap:12px;align-items:center;margin-top:12px"><span class="p01-emblem"><img src="assets/frame-classic.png" alt=""><i class="ph ph-guitar"></i></span><div><div class="p01-kicker">${escP(tt.league)}</div><div style="font-size:18px;font-weight:500">${en ? "Guitar League" : "Лига гитары"}</div></div></div></div>
      <div><h2>${en ? "Status chips" : "Чипы статусов"}</h2><div class="p01-chips" style="margin-top:12px">${chipD.map(c => `<span class="p01-chip" style="background:var(--p01-n900);border-color:var(--p01-n800);color:var(--p01-n300)">${escP(c)}</span>`).join("")}</div></div>
    </section>
  </main></div>`;
}

function bind() {
  document.querySelectorAll("[data-lang]").forEach(b => b.onclick = () => {
    state.lang = b.dataset.lang;
    try { localStorage.setItem("som_p01_lang", state.lang); } catch (e) {}
    render();
  });
  document.querySelectorAll("[data-medal]").forEach(b => b.onclick = () => { state.medal = b.dataset.medal; render(); });
  const org = document.querySelector("[data-origin]");
  if (org) org.onclick = () => { state.originOpen = !state.originOpen; render(); };
  document.querySelectorAll("[data-role]").forEach(b => b.onclick = () => { location.hash = "#/space/" + ROLE_KEY[b.dataset.role]; });
  document.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => { state.mode = b.dataset.mode; render(); });
  document.querySelectorAll("[data-p01-play]").forEach(b => b.onclick = () => {
    const id = b.dataset.p01Play;
    playSeq(id, id === "comp" ? PS.SIGS.korean : PS.SIGS.latin);
  });
  document.querySelectorAll("[data-p01-rec]").forEach(b => b.onclick = () => {
    const [kind, i] = b.dataset.p01Rec.split(":");
    const sig = kind === "sig" ? PS.SIGS.latin : PS.SIGS.short;
    b.dataset.p01Play = "rec" + i;
    playSeq("rec" + i, sig);
  });
}
window.P01 = { welcome, space, components, bind, stop: stopAudio, state };
