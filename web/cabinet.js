"use strict";
/* Muse Cabinet 1.4 views: home on #/space and session
   screens built on the approved session layout preserved in
   web/lesson.html (plan in the centre, notebook as a drawer on the right).
   All user text comes from web/strings.js (P01Strings.CAB + T role words).
   Example people and data only; no live connection is claimed, and sound
   (the metronome) starts only on a press. */
const CabPS = window.P01Strings;
const cabEsc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const cabState = {
  step: 3, focus: "london", chords: ["Am", "F", "C", "G"],
  drawer: { maestro: false, artist: true, admirer: false },
  tab: "chords", hand: false, rec: false, nNote: 0,
  extraChat: [], extraNotes: [], soon: "",
};
let cabMetro = { timer: null, ctx: null, beat: -1, bpm: 72, on: false };
function cabLang() { return (window.P01 && P01.state.lang) || "en"; }
function cabT() { return CabPS.CAB[cabLang()]; }
function cabRoles() {
  const tt = CabPS.T[cabLang()];
  return [["maestro", tt.roleT, "baton"], ["artist", tt.roleS, "ph-music-notes"], ["admirer", tt.roleL, "ph-headphones"]];
}
function cabLangSwitch() {
  const lang = cabLang();
  return `<div class="cab-lang" role="group" aria-label="Language">
    <button data-cab-lang="en" aria-pressed="${lang === "en"}">EN</button>
    <button data-cab-lang="ru" aria-pressed="${lang === "ru"}">RU</button></div>`;
}
function cabHead(role, sessTitle, sessSub) {
  const C = cabT();
  const [who, soul] = window.CabinetHarness?.state.user ? [CabinetHarness.state.user.name, CabinetHarness.state.user.id] : (CabPS.CAB.people[role] || CabPS.CAB.people.artist);
  return `<header class="cab-head">
    <a class="cab-brand" href="#/space/${role}"><img src="assets/lyre.png" alt="Golden Lyre"><span>${cabEsc(C.brand)}</span></a>
    ${sessTitle ? `<span class="cab-sess-title">${cabEsc(sessTitle)} <span>${cabEsc(sessSub || "")}</span></span>` : ""}
    <div class="cab-head-right">
      <span class="cab-tag cab-tag-neutral">${cabEsc(window.CabinetHarness?.state.meeting ? (cabLang() === "ru" ? "Музыкальная встреча" : "Music meeting") : C.exampleData)}</span>
      ${role === "admirer" && sessTitle ? `<span class="cab-tag cab-tag-outline">${cabEsc(C.proposal)}</span>` : ""}
      <span class="cab-who"><span>${cabEsc(who)}</span><span aria-hidden="true">·</span><span class="soul text-gold">${cabEsc(soul)}</span></span>
      ${cabLangSwitch()}
    </div></header>`;
}
function roleButtons(active) {
  return cabRoles().map(([id, label, ic]) => {
    const on = id === active;
    const icon = ic === "baton" ? '<span class="cab-baton" aria-hidden="true"></span>' : `<i class="ph ${ic}" aria-hidden="true"></i>`;
    return `<button type="button" class="cab-role${on ? " frame-gold" : ""}" data-cab-role="${id}" aria-pressed="${on}">${icon}${cabEsc(label)}</button>`;
  }).join("");
}
function museRowsHTML(C) {
  return C.museRows.map(([tag, kind, text]) =>
    `<div class="cab-muse-row"><span class="cab-tag cab-tag-${kind === "red" ? "red" : kind === "outline" ? "outline" : "neutral"}">${cabEsc(tag)}</span><span>${cabEsc(text)}</span></div>`).join("");
}
function home(role) {
  const C = cabT();
  const isA = role === "artist", isM = role === "maestro", isAd = role === "admirer";
  const enterHref = isAd ? "#/session/admirer/circle" : `#/session/${role}/circle`;
  const oneHref = `#/session/${role}/one-to-one`;
  const sessionBody = isA ? `
      <div><div class="cab-next-label">${cabEsc(C.nextSession)}</div>
      <div class="cab-next-time underline-gold">${cabEsc(C.today1830)}</div>
      <div class="cab-next-with">${cabEsc(C.artistWith)}</div></div>
      <div class="cab-lines">
        <span class="cab-line"><i class="ph ph-metronome"></i>${cabEsc(C.artistLine1)}</span>
        <span class="cab-line"><i class="ph ph-question"></i>${cabEsc(C.artistLine2)}</span>
        <span class="cab-line muse"><i class="ph ph-sparkle"></i>${cabEsc(C.artistLine3)}</span>
      </div>` : isM ? `
      <div><div class="cab-next-label">${cabEsc(C.nextSession)}</div>
      <div class="cab-next-time underline-gold">${cabEsc(C.today1830)}</div>
      <div class="cab-next-with">${cabEsc(C.maestroWith)}</div></div>
      <div class="cab-musebox bar-muse">
        <div class="cab-musebox-head"><i class="ph ph-sparkle"></i>${cabEsc(C.museWeek)}</div>
        ${museRowsHTML(C)}
      </div>` : `
      <div><div class="cab-next-label">${cabEsc(C.openListen)}</div>
      <div class="cab-next-time underline-gold">${cabEsc(C.today1830)}</div>
      <div class="cab-next-with">${cabEsc(C.admirerWith)}</div></div>
      <div class="cab-lines">
        <span class="cab-line"><i class="ph ph-headphones"></i>${cabEsc(C.admirerLine1)}</span>
        <span class="cab-line muse"><i class="ph ph-sparkle"></i>${cabEsc(C.admirerLine2)}</span>
      </div>`;
  const tile = (num, name, title, body, sub) => `<section class="cab-tile" aria-disabled="true">
      <div class="cab-tile-head"><span class="cab-tile-num dim"><span class="num-gold">${num}</span> · ${cabEsc(name)}</span><span style="flex:1"></span><span class="cab-tag cab-tag-neutral">${cabEsc(C.opensNext)}</span></div>
      <div class="cab-tile-title">${cabEsc(title)}</div>${sub ? `<div class="cab-tile-sub">${cabEsc(sub)}</div>` : ""}<div class="cab-tile-body">${cabEsc(body)}</div></section>`;
  return `<div class="cab" data-cab-screen="home-${role}">${cabHead(role)}
  <div class="cab-home">
    <aside class="cab-side">
      <div><span class="rule-gold">${cabEsc(C.myLeague)}</span><div class="cab-league-name">${cabEsc(C.leagueName)}</div><div class="cab-league-fam">${cabEsc(C.leagueFamily)}</div></div>
      <div class="divider-fade"></div>
      <div><span class="rule-gold">${cabEsc(C.myRole)}</span><div class="cab-roles" role="group" aria-label="${cabEsc(C.myRole)}">${roleButtons(role)}</div></div>
      <div class="divider-fade"></div>
      <nav class="cab-sidenav" aria-label="${cabEsc(C.brand)}">
        <a href="#/convention"><i class="ph ph-signature"></i>${cabEsc(C.myConvention)}</a>
        <a href="#/space/${role}" data-cab-soon="${cabEsc(C.history)}"><i class="ph ph-clock-counter-clockwise"></i>${cabEsc(C.history)}</a>
        <a href="#/space/${role}" data-private-notes-index><i class="ph ph-note-pencil"></i>${cabEsc(C.myNotes)}</a>
      </nav>
      <p class="cab-status" role="status" data-cab-soon-out>${cabEsc(cabState.soon)}</p>
      <p class="cab-side-note">${cabEsc(C.notesPrivate)}</p>
    </aside>
    <main id="main" tabindex="-1" class="cab-main">
      <div><h1>${cabEsc(C.playToday)}</h1><p class="cab-sub">${cabEsc(isA ? C.subArtist : isM ? C.subMaestro : C.subAdmirer)}</p></div>
      ${window.CabinetHarness ? CabinetHarness.panel() : ""}
      ${window.SomPrivateNotes ? SomPrivateNotes.indexHTML() : ""}
      <div class="cab-tiles">
        <section class="cab-tile-session" aria-label="${cabEsc(C.session)}">
          <div class="cab-tile-head"><span class="cab-tile-num"><span class="num-gold">01</span> · ${cabEsc(C.session)}</span><span style="flex:1"></span>
            <span class="cab-tag cab-tag-outline">${cabEsc(C.oneToOne)}</span><span class="cab-tag cab-tag-outline">${cabEsc(C.inCircle)}</span></div>
          ${sessionBody}
          <div class="cab-enter-row"><a class="btn-gold" href="${enterHref}">${cabEsc(C.enter)}<i class="ph ph-arrow-right"></i></a><span class="cab-sound-note">${cabEsc(C.soundPress)}</span></div>
          ${isAd ? "" : `<a class="cab-second" href="${oneHref}"><i class="ph ph-user"></i>${cabEsc(isA ? C.secondArtist : C.secondMaestro)}<i class="ph ph-caret-right"></i></a>`}
        </section>
        ${tile("02", C.tile2, C.tile2Title, C.tile2Body)}
        ${tile("03", C.tile3, C.tile3Title, C.tile3Body)}
        ${tile("04", C.tile4, C.tile4Title, C.tile4Body, C.tile4Sub)}
      </div>
      <p class="cab-home-foot">${cabEsc(C.homeFoot)}</p>
    </main>
  </div></div>`;
}

/* ---- session screens (frames 1-5) ---- */
function chordSVG(name) {
  const sh = CabPS.CAB.shapes[name] || "xxxxxx";
  let marks = "", dots = "";
  [...sh].forEach((ch, i) => {
    const x = 6 + i * 9.6;
    marks += `<text x="${x}" y="5" text-anchor="middle" font-size="7" fill="var(--color-neutral-500)">${ch === "x" ? "×" : ch === "0" ? "○" : ""}</text>`;
    const f = parseInt(ch, 10);
    if (f > 0) dots += `<circle cx="${x}" cy="${10 + (f - 0.5) * 14}" r="4" fill="var(--color-accent)"></circle>`;
  });
  return `<svg viewBox="-2 -4 64 74" style="width:100%;max-width:100px" aria-hidden="true">
    <line x1="6" y1="10" x2="54" y2="10" stroke="var(--color-neutral-300)" stroke-width="2.5"></line>
    ${[24, 38, 52, 66].map(y => `<line x1="6" y1="${y}" x2="54" y2="${y}" stroke="var(--color-neutral-700)"></line>`).join("")}
    ${[6, 15.6, 25.2, 34.8, 44.4, 54].map(x => `<line x1="${x}" y1="10" x2="${x}" y2="66" stroke="var(--color-neutral-600)"></line>`).join("")}
    ${marks}${dots}</svg>`;
}
function notationSVG() {
  const ys = [45, 35, 25, 35, 55, 45, 35, 45, 35, 25, 15, 25, 50, 40, 30, 40];
  const notes = ys.map((y, i) => { const x = 100 + i * 44; const up = y >= 40; return `<line x1="${up ? x + 5.6 : x - 5.6}" y1="${y}" x2="${up ? x + 5.6 : x - 5.6}" y2="${up ? y - 30 : y + 30}" stroke="var(--color-neutral-200)" stroke-width="1.2"></line><ellipse cx="${x}" cy="${y}" rx="6" ry="4.4" transform="rotate(-20 ${x} ${y})" fill="var(--color-neutral-200)"></ellipse>`; }).join("");
  return `<svg viewBox="0 0 840 90" style="width:100%" role="img" aria-label="Am F C G">
    ${[20, 30, 40, 50, 60].map(y => `<line x1="0" y1="${y}" x2="840" y2="${y}" stroke="var(--color-neutral-600)"></line>`).join("")}
    ${[250, 445, 640].map(x => `<line x1="${x}" y1="20" x2="${x}" y2="60" stroke="var(--color-neutral-600)"></line>`).join("")}
    <line x1="836" y1="20" x2="836" y2="60" stroke="var(--color-neutral-400)" stroke-width="3"></line>
    <text x="6" y="62" font-size="54" fill="var(--color-neutral-300)">𝄞</text><text x="44" y="38" font-size="18" fill="var(--color-neutral-300)">4</text><text x="44" y="58" font-size="18" fill="var(--color-neutral-300)">4</text>
    ${notes}
    ${["Am", "F", "C", "G"].map((n, i) => `<text x="${100 + i * 195}" y="84" font-size="13" fill="var(--color-neutral-400)">${n}</text>`).join("")}</svg>`;
}
const CAB_TABS = `  Am          F           C           G
e|-0-----0---|-0-----0---|-0-----0---|-3-----3---|
B|---1-----1-|---1-----1-|---1-----1-|---0-----0-|
G|-----2-----|-----2-----|-----0-----|-----0-----|
D|-2---------|-3---------|-2---------|-0---------|
A|-0---------|-----------|-3---------|-2---------|
E|-----------|-----------|-----------|-3---------|`;
function drawerHTML(role, mode, C) {
  if (window.CabinetHarness?.state.meeting && window.SomLesson) return SomLesson.drawerHTML(role);
  const open = !!cabState.drawer[role];
  const editable = role === "maestro";
  const tab = cabState.tab;
  const body = tab === "chords" ? `<div class="cab-chords">${cabState.chords.map((c, i) => {
    const inner = `<span class="bar-n">${cabEsc(C.bar)} ${i + 1}</span><span class="ch">${cabEsc(c)}</span>${chordSVG(c)}`;
    return editable ? `<button type="button" class="cab-chord" data-cab-bar="${i}">${inner}</button>` : `<div class="cab-chord">${inner}</div>`;
  }).join("")}</div><p class="cab-drawer-note">${cabEsc(editable ? (mode === "one" ? C.clickBarOne : C.clickBar) : C.museChordTip)}</p>`
    : tab === "notes" ? notationSVG() : `<pre class="cab-tabtext">${cabEsc(CAB_TABS)}</pre>`;
  return `<div class="cab-drawer">
    <button type="button" class="cab-drawer-tab" data-cab-drawer aria-expanded="${open}"><i class="ph ${open ? "ph-caret-right" : "ph-caret-left"}"></i><span>${cabEsc(C.notebook)}</span><i class="ph ph-dots-six-vertical"></i></button>
    ${open ? `<div class="cab-drawer-panel">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><div class="cab-ntabs" role="tablist" aria-label="${cabEsc(C.notebook)}">
        ${[["chords", C.chords], ["notes", C.notation], ["tabs", C.tabs]].map(([k, l]) => `<button type="button" role="tab" data-cab-tab="${k}" aria-selected="${tab === k}">${cabEsc(l)}</button>`).join("")}
      </div><span style="flex:1"></span><span class="cab-drawer-note">${cabEsc(mode === "one" ? C.artistSees : role === "artist" || role === "admirer" ? C.ledBy : C.allSee)}</span></div>
      ${body}
    </div>` : ""}
  </div>`;
}
function rosterHTML(role, mode, C) {
  if (role !== "maestro") return "";
  const list = mode === "one" ? C.roster.filter(r => r.id === "london") : C.roster;
  const everyone = mode === "one" ? "" : `<button type="button" class="cab-roster-card everyone${cabState.focus === "all" ? " focus" : ""}" data-cab-focus="all">
      <span class="cab-roster-top"><i class="ph ph-users-three" style="color:var(--color-accent)"></i>${cabEsc(C.everyone)}</span>
      <span style="font-size:12px;line-height:1.35;color:var(--color-neutral-400)">${cabEsc(C.talkCircle)}</span>
      <span class="cab-roster-meta" style="margin-top:auto">${cabEsc(C.readyNeed)}</span></button>`;
  const cards = list.map(r => `<button type="button" class="cab-roster-card${cabState.focus === r.id || mode === "one" ? " focus" : ""}${r.alert ? " bar-live" : ""}" data-cab-focus="${r.id}">
      <span class="cab-roster-top"><span class="nm">${cabEsc(r.name)}</span><span class="cab-roster-lang">${cabEsc(r.lang)}</span><span style="flex:1"></span>
      ${r.hand ? '<i class="ph-fill ph-hand-waving cab-hand" aria-hidden="true"></i>' : ""}${r.alert ? `<span class="cab-tag cab-tag-red" style="font-size:10px">${cabEsc(C.needsHelp)}</span>` : ""}</span>
      <span class="cab-roster-status"><i class="ph ph-sparkle"></i>${cabEsc(r.status)}</span>
      <span class="cab-bar"><i class="${r.alert ? "help" : ""}" style="width:${r.pct}%"></i></span>
      <span class="cab-roster-meta"><span>${cabEsc(r.metrics)}</span><span>${r.pct}%</span></span></button>`).join("");
  return `<div class="cab-roster">${everyone}${cards}</div>`;
}
function chatHTML(role, mode, C) {
  if (window.CabinetHarness?.state.user) return CabinetHarness.messages();
  const F = role === "maestro" ? (mode === "one" ? "london" : cabState.focus) : "london";
  let msgs;
  if (role === "admirer") msgs = C.chat.filter(m => m.to === "all");
  else if (role === "maestro") msgs = C.chat.filter(m => F === "all" ? m.to === "all" : (m.to === "all" || m.to === F));
  else msgs = C.chat.filter(m => m.to === "all" || m.to === "london");
  msgs = msgs.concat(cabState.extraChat.filter(m => role !== "admirer"));
  const who = m => {
    if (m.from === "muse") return m.to === "all" ? C.museToAll : "Muse";
    const mine = (role === "maestro" && m.from === "maestro") || (role === "artist" && m.from === "london");
    if (mine) return m.to === "all" ? C.youToAll : C.you;
    if (m.from === "maestro") return m.to === "all" ? C.maestroToAll : C.maestroToYou;
    const p = C.roster.find(r => r.id === m.from);
    return p ? p.name : m.from;
  };
  return msgs.map(m => {
    const mine = (role === "maestro" && m.from === "maestro") || (role === "artist" && m.from === "london");
    const muse = m.from === "muse";
    return `<div class="cab-msg${mine ? " mine" : ""}${muse ? " muse" : ""}">
      <span class="cab-msg-who${muse ? " muse" : ""}"><i class="ph ${muse ? "ph-sparkle" : "ph-user-circle"}"></i>${cabEsc(who(m))}</span>
      <span class="cab-msg-text">${cabEsc(m.text)}</span>
      ${m.orig && !mine && !muse ? `<span class="cab-msg-orig">${cabEsc(C.original)} · ${cabEsc(m.orig)}</span>` : mine ? `<span class="cab-msg-orig">→ ${cabEsc(C.delivered)}</span>` : ""}
    </div>`;
  }).join("");
}
function notesFor(role, mode, C) {
  if (window.CabinetHarness?.state.meeting) return [];
  const base = role === "maestro" ? (mode === "one" ? [C.sessionGoalNote, ...C.notesMaestroOne] : [C.sessionGoalNote, ...C.notesMaestro])
    : role === "admirer" ? C.notesAdmirer : C.notesArtist;
  return base.concat(cabState.extraNotes);
}
function liveMetronome(role, C) {
  if (role !== "maestro") return "";
  return `<div class="cab-metro"><button type="button" class="btn-gold" data-cab-metro aria-pressed="${cabMetro.on}">${cabEsc(cabMetro.on ? C.stop : C.metronome)}</button>
    <span class="cab-beats" data-cab-beats>${[0,1,2,3].map(k=>`<i class="${cabMetro.on && cabMetro.beat===k ? "on" : ""}"></i>`).join("")}</span>
    <button type="button" class="cab-btn cab-icon-btn" data-cab-bpm="-1" aria-label="−">−</button><span class="cab-bpm"><b data-cab-bpm-val>${cabMetro.bpm}</b><span>BPM</span></span>
    <button type="button" class="cab-btn cab-icon-btn" data-cab-bpm="1" aria-label="+">+</button><small>${cabLang()==="ru"?"Локальный метроном":"Local metronome"}</small></div>`;
}
function session(role, mode) {
  const C = cabT();
  const isM = role === "maestro", isA = role === "artist", isAd = role === "admirer";
  if (isM && mode === "one") cabState.focus = "london";
  const F = isM ? cabState.focus : "london";
  const live = window.CabinetHarness?.state.meeting;
  const focusName = live ? (isM ? live.artist_alias : live.maestro_alias) : (C.roster.find(r => r.id === F) || {}).name || "";
  const sub = live ? `${live.maestro_alias} · ${live.artist_alias}` : isM ? (mode === "one" ? C.sessSubMaestroOne : C.sessSubMaestroCircle)
    : isA ? (mode === "one" ? C.sessSubArtistOne : C.sessSubArtistCircle) : C.sessSubAdmirer;
  const plan = C.plan, step = plan[cabState.step];
  const centre = isM ? `
      <div class="cab-plan-head"><span class="cab-plan-title">${cabEsc(C.sessionPlan)}</span>
        <span class="cab-tag cab-tag-outline">${cabEsc(C.stepOf(cabState.step + 1, plan.length))}</span>
        <span class="cab-plan-note">${cabEsc(mode === "one" ? C.stepOne : C.stepAll)}</span></div>
      <div class="cab-plan">${plan.map((p, i) => {
        const cur = i === cabState.step, done = i < cabState.step;
        return `<div class="cab-step${cur ? " cur frame-gold-step" : ""}">
          <button type="button" class="cab-step-btn" data-cab-step="${i}" aria-pressed="${cur}">
            <i class="ph ${done ? "ph-check-circle" : cur ? "ph-play-circle" : "ph-circle"}" style="color:${cur ? "var(--color-gold)" : "var(--color-neutral-600)"}"></i>
            <span style="flex:1;${cur ? "font-weight:500" : ""}">${cabEsc(p.t)}</span><span class="d">${cur ? `<span class="text-gold">${cabEsc(C.now)} · </span>` : ""}${cabEsc(p.d)}</span></button>
          ${cur ? `<p class="cab-step-goal">${cabEsc(p.goal)}</p>${p.tips.map(t => `<span class="cab-tip"><i class="ph ph-check"></i>${cabEsc(t)}</span>`).join("")}
          <span class="cab-tip" style="color:var(--color-accent-300)"><i class="ph ph-sparkle"></i>${cabEsc(C.museChecks)}</span>` : ""}
        </div>`; }).join("")}
      </div>
      <div class="cab-metro">
        <button type="button" class="btn-gold" data-cab-metro aria-pressed="${cabMetro.on}"><i class="ph ${cabMetro.on ? "ph-stop" : "ph-metronome"}"></i>${cabEsc(cabMetro.on ? C.stop : C.metronome)}</button>
        <span class="cab-beats" data-cab-beats>${[0, 1, 2, 3].map(k => `<i class="${cabMetro.on && cabMetro.beat === k ? "on" : ""}"></i>`).join("")}</span>
        <button type="button" class="cab-btn cab-btn-ghost cab-icon-btn" data-cab-bpm="-1" aria-label="−"><i class="ph ph-minus"></i></button>
        <span class="cab-bpm"><b data-cab-bpm-val>${cabMetro.bpm}</b><span>BPM</span></span>
        <button type="button" class="cab-btn cab-btn-ghost cab-icon-btn" data-cab-bpm="1" aria-label="+"><i class="ph ph-plus"></i></button>
        <span style="flex:1"></span><span style="font-size:12px;color:var(--color-neutral-500)">${cabEsc(live ? (cabLang() === "ru" ? "Локальный метроном" : "Local metronome") : mode === "one" ? C.inSync : C.forCircle)}</span>
      </div>` : `
      <div class="cab-plan-head"><span class="cab-plan-title">${cabEsc(isAd ? C.sessionPlan : C.practicePlan)}</span>
        <span class="cab-tag cab-tag-outline">${cabEsc(C.stepOf(cabState.step + 1, plan.length))}</span>
        <span class="cab-plan-note">${cabEsc(C.ledBy)}</span></div>
      <div class="cab-plan">
        <div><div class="cab-step-now text-gold">${cabEsc(C.now)} · ${cabEsc(step.d)}</div>
        <div class="cab-step-big">${cabEsc(step.t)}</div>
        <p class="cab-step-goal" style="padding-left:0">${cabEsc(step.goal)}</p></div>
        ${isA && !live ? `<div class="cab-muse-status"><span style="display:flex;gap:8px;align-items:center;font-size:13px;color:var(--color-accent-200)"><i class="ph ph-sparkle"></i><span style="flex:1">Muse: ${cabEsc(C.roster[0].status)}</span><span class="mono" style="font-size:12px">55%</span></span>
        <span class="cab-bar"><i style="width:55%"></i></span><span class="cab-mono-lines">${cabEsc(C.museStatusArtist)}</span></div>` : ""}
        <div>${step.tips.map(t => `<span class="cab-tip" style="padding-left:0;font-size:13px;color:var(--color-neutral-200)"><i class="ph ph-check"></i>${cabEsc(t)}</span>`).join("")}</div>
        <div class="cab-plan-mini">${plan.map((p, i) => {
          const cur = i === cabState.step, done = i < cabState.step;
          return `<span class="cab-plan-mini-row${cur ? " cur" : ""}"><i class="ph ${done ? "ph-check-circle" : cur ? "ph-play-circle" : "ph-circle"}" style="color:${cur ? "var(--color-gold)" : "var(--color-neutral-600)"}"></i><span style="flex:1">${cabEsc(p.t)}</span><span class="d">${cabEsc(p.d)}</span></span>`; }).join("")}
        </div>
      </div>
      <div class="cab-metro"><i class="ph ph-metronome" style="font-size:18px;color:var(--color-neutral-400)"></i>
        <span class="cab-beats">${[0, 1, 2, 3].map(() => "<i></i>").join("")}</span>
        <span class="cab-bpm"><b>72</b><span>BPM</span></span><span style="flex:1"></span>
        <span style="font-size:12px;color:var(--color-neutral-500)">${cabEsc(C.metroOff)}</span></div>`;
  const left = live ? `<div class="cab-label">${cabLang() === "ru" ? "Встреча EN ↔ VI" : "EN ↔ VI meeting"}</div><p>${CabinetHarness.state.tts ? (cabLang() === "ru" ? "Одобренный перевод можно прослушать в чате Muse. Видео ожидает подключения." : "Listen to approved translations in the Muse chat. Video is awaiting connection.") : (cabLang() === "ru" ? "Сообщения и одобрение перевода работают в чате Muse. Видео ожидает подключения." : "Use the Muse chat for messages and translation approval. Video is awaiting connection.")}</p>` : `
      <div style="display:flex;flex-direction:column;gap:11px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px"><span class="cab-label">${cabEsc(isM ? (F === "all" ? C.soundAll : C.soundPrivate) : isAd ? C.soundAdmirer : C.soundArtist)}</span><span class="cab-tag cab-tag-neutral">${cabEsc(C.exampleTag)}</span></div>
        <div class="cab-sound" aria-hidden="true"><i></i></div>
        ${isAd ? `<span class="cab-presence off"><i class="ph ph-microphone-slash"></i>${cabEsc(C.micOff)}</span>` : isA ? `<span class="cab-presence"><i class="ph ph-headphones"></i>${cabEsc(C.presenceArtist)}</span>` : ""}
        <div class="cab-mono-lines"><span>${cabEsc(isM ? (F === "all" ? C.museListensAll : `${focusName} · 38 ${cabLang() === "ru" ? "мс" : "ms"}`) : C.latency)}</span><span>${cabEsc(isM ? (F === "all" ? C.voiceMuseAll : C.voiceTrans) : C.voiceTrans)}</span></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:11px">
        <span class="cab-label">${cabEsc(C.video)}</span>
        <div class="cab-video-box"><span><i class="ph ph-video-camera-slash" style="font-size:22px"></i><br>${cabEsc(isM ? (mode === "circle" && F === "all" ? C.videoChoose : C.videoWait + (focusName ? ` · ${focusName}` : "")) : isAd ? C.videoAdmirer : C.videoMaestro)}</span></div>
        ${isAd ? "" : isM ? `<button type="button" class="cab-btn" data-cab-video><i class="ph ph-video-camera"></i>${cabEsc(C.videoCheck)}</button><button type="button" class="cab-btn" data-cab-video><i class="ph ph-monitor-play"></i>${cabEsc(C.videoDemo)}</button>` : `<button type="button" class="cab-btn" data-cab-video><i class="ph ph-monitor-play"></i>${cabEsc(C.videoDemo)}</button>`}
        <p class="cab-status" role="status" data-cab-video-out></p>
      </div>`;
  const chatLabel = live ? (cabLang() === "ru" ? "Личный чат Muse" : "Private Muse chat") : isAd ? C.circleChatRO : isM ? (F === "all" ? C.circleChat : C.privateChat(focusName)) : C.circleChat;
  const right = `
      <div style="display:flex;align-items:center;gap:8px"><span class="cab-btn cab-btn-primary" style="cursor:default"><i class="ph ph-sparkle"></i>Muse</span><span style="flex:1"></span>
        <span class="cab-tag cab-tag-neutral"><i class="ph ph-translate"></i>${live ? (isM ? "EN → VI" : "VI → EN") : isM && F === "all" ? "PT → 4" : "PT → RU"}</span></div>
      ${live ? "" : `<span class="cab-dictating"><i class="ph ph-waveform"></i>${cabEsc(isM ? C.dictatingM : C.dictatingA)}</span>`}
      <span class="cab-label">${cabEsc(chatLabel)}</span>
      ${live?`<button type="button" class="cab-btn cab-btn-ghost" data-cab-rec ${!CabinetHarness.state.asr||CabinetHarness.state.busy||live.state!=='active'?'disabled':''} aria-pressed="${CabinetHarness.state.recording}"><i class="ph ph-microphone"></i>${cabEsc(CabinetHarness.state.recording?C.done:(cabLang()==='ru'?'Надиктовать сообщение':'Dictate a message'))}</button>`:''}
      <div class="cab-chat">${chatHTML(role, mode, C)}</div>
      ${isAd ? "" : `<form class="cab-chat-form" data-cab-chat-form><input data-cab-chat-input autocomplete="off" placeholder="${cabEsc(live ? C.writeTo(focusName) : isM ? (F === "all" ? C.writeAll : C.writeTo(focusName)) : C.writeMaestro)}"><button type="submit" class="cab-btn cab-btn-primary cab-icon-btn" aria-label="→"><i class="ph ph-paper-plane-right"></i></button></form>`}
      <div class="cab-notes">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span class="cab-label" style="flex:1">${cabEsc(isA ? C.notesQuestions : C.myNotes)}</span>
        ${isA ? `<button type="button" class="cab-btn cab-btn-ghost" data-cab-hand ${window.CabinetHarness?.state.meeting ? "disabled" : ""} aria-pressed="${cabState.hand}" style="font-size:12px"><i class="ph ${cabState.hand ? "ph-fill ph-hand-waving" : "ph-hand-waving"}"></i>${cabEsc(cabState.hand ? C.handRaised : C.raiseHand)}</button>` : ""}
        ${!live?`<button type="button" class="cab-btn cab-btn-ghost" data-cab-rec aria-pressed="${cabState.rec}" style="font-size:12px"><i class="ph ph-microphone"></i>${cabEsc(cabState.rec?C.done:C.dictate)}</button>`:''}</div>
        ${cabState.rec ? `<span class="cab-dictating"><i class="ph ph-waveform"></i>${cabEsc(C.museListening)}</span>` : ""}
        ${notesFor(role, mode, C).map(n => `<span class="cab-note"><i class="ph ph-note-pencil"></i><span>${cabEsc(n)}</span></span>`).join("")}
        ${live&&window.SomPrivateNotes?SomPrivateNotes.HTML():''}
      </div>`;
  return `<div class="cab" data-cab-screen="session-${role}-${mode}">${cabHead(role, live ? (cabLang() === "ru" ? "Музыкальная встреча" : "Music meeting") : C.session3, sub)}
  <div class="cab-session">
    <div class="cab-sess-bar">
      <a class="cab-btn" href="#/space/${role}"><i class="ph ph-arrow-left"></i>${cabEsc(C.backCabinet)}</a>
      <span class="cab-elapsed"><i></i>${cabEsc(window.CabinetHarness?.state.meeting ? CabinetHarness.state.meeting.state : "12:34")}</span><span style="flex:1"></span>
      <a class="cab-btn" ${live ? "data-harness-end" : ""} href="#/space/${role}"><i class="ph ph-sign-out"></i>${cabEsc(isM ? C.endSession : C.leave)}</a>
    </div>
    <p class="cab-notlive bar-muse" role="note">${cabEsc(window.CabinetHarness?.state.meeting ? (cabLang() === "ru" ? "Встречу ведёт Маэстро. План и нотная тетрадь — общие для участников." : "The Maestro leads the meeting. The plan and notebook are shared with participants.") : C.notLive)}</p>
    ${window.CabinetHarness?.state.meeting ? `<div class="cab-live"><b>${cabEsc(CabinetHarness.state.meeting.maestro_alias)} · ${cabEsc(CabinetHarness.state.meeting.artist_alias)}</b></div>` : rosterHTML(role, mode, C)}
    ${window.CabinetHarness ? CabinetHarness.panel() : ""}
    <main id="main" tabindex="-1" class="cab-grid">
      <div class="cab-col">${left}</div>
      <div class="cab-col">${live && window.SomLesson ? SomLesson.planHTML() + liveMetronome(role, C) : centre}</div>
      <div class="cab-chat-col">${right}</div>
    </main>
    ${drawerHTML(role, mode, C)}
  </div></div>`;
}

/* ---- frame 9 · Seven Leagues catalogue (#/leagues) ---- */
const CAB_LEAGUE_IDS = ["string", "bow", "keys", "winds", "drums", "electronic", "vocal"];
function leagues() {
  const C = cabT();
  const en = cabLang() === "en";
  const cards = CabPS.LEAGUES.map((l, i) => {
    const [icon, enName, ruName, enInst, ruInst, enFam, ruFam] = l;
    const name = en ? enName : ruName;
    const mine = i === 0;
    const num = String(i + 1).padStart(2, "0");
    return `<section class="cab-league-card${mine ? " is-mine frame-gold" : ""}"${mine ? ' aria-pressed="true"' : ""} aria-label="${cabEsc(name)}">
      <div class="cab-lg-top"><span class="cab-lg-icon"><i class="ph ${cabEsc(icon)}" aria-hidden="true"></i></span><span class="cab-lg-num num-gold">${num}</span></div>
      <div><div class="cab-lg-name">${cabEsc(name)}</div><div class="cab-lg-fam">${cabEsc(en ? enFam : ruFam)}</div></div>
      <div class="cab-lg-inst">${cabEsc(en ? enInst : ruInst)}</div>
      ${mine
        ? `<div class="cab-lg-mine"><i class="ph ph-check" aria-hidden="true"></i>${cabEsc(C.myInstrument)}</div>`
        : `<button type="button" class="cab-btn" data-cab-join="${CAB_LEAGUE_IDS[i]}" aria-label="${cabEsc(C.joinLeague(name))}">${cabEsc(C.join)}</button>`}
    </section>`;
  }).join("");
  return `<div class="cab" data-cab-screen="leagues">${cabHead("artist")}
  <main id="main" tabindex="-1" class="cab-main cab-leagues-main">
    <div><span class="rule-gold">${cabEsc(C.leaguesKicker)}</span><h1>${cabEsc(C.chooseLeague)}</h1><p class="cab-leagues-sub">${cabEsc(C.leaguesSub)}</p></div>
    <div class="cab-league-grid">${cards}
      <div class="cab-league-cta">
        <div class="cab-lg-muse bar-muse"><i class="ph ph-sparkle" aria-hidden="true"></i><span>${cabEsc(C.museLeagueNote)}</span></div>
        <a class="btn-gold" href="#/space/artist">${cabEsc(C.joinMine)}<i class="ph ph-arrow-right" aria-hidden="true"></i></a>
      </div>
    </div>
  </main></div>`;
}

/* ---- metronome: sound only after the press ---- */
function cabClick(accent) {
  const c = cabMetro.ctx; if (!c) return;
  try {
    const o = c.createOscillator(), g = c.createGain(), t = c.currentTime;
    o.frequency.value = accent ? 1600 : 1000;
    g.gain.setValueAtTime(0.22, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
    o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + 0.06);
  } catch (e) {}
}
function cabMetroPaint() {
  const dots = document.querySelector("[data-cab-beats]");
  if (dots) [...dots.children].forEach((d, k) => d.classList.toggle("on", cabMetro.on && cabMetro.beat === k));
}
function cabMetroStep() {
  cabMetro.beat = (cabMetro.beat + 1) % 4;
  cabClick(cabMetro.beat === 0); cabMetroPaint();
  cabMetro.timer = setTimeout(cabMetroStep, 60000 / cabMetro.bpm);
}
function cabMetroStop() {
  /* page cleanup: pause the timer only. Context and on-state survive the
     re-render; bind() resumes the loop on the new DOM. */
  if (cabMetro.timer) { clearTimeout(cabMetro.timer); cabMetro.timer = null; }
}
function cabMetroOff() {
  cabMetro.on = false; cabMetro.beat = -1; cabMetroStop();
  if (cabMetro.ctx) { try { cabMetro.ctx.close(); } catch (e) {} cabMetro.ctx = null; }
}
function cabRerender() { if (typeof render === "function") render(); }
function bind() {
  if (window.CabinetHarness) CabinetHarness.bind();
  if (window.SomLesson) SomLesson.bind();
  if (window.SomPrivateNotes) SomPrivateNotes.bind();
  document.querySelectorAll("[data-cab-lang]").forEach(b => b.onclick = () => {
    if (window.P01) { P01.state.lang = b.dataset.cabLang; try { localStorage.setItem("som_p01_lang", P01.state.lang); } catch (e) {} }
    cabRerender();
  });
  document.querySelectorAll("[data-cab-role]").forEach(b => b.onclick = () => { location.hash = "#/space/" + b.dataset.cabRole; });
  document.querySelectorAll("[data-cab-join]").forEach(b => b.onclick = () => { location.hash = "#/league/" + b.dataset.cabJoin; });
  document.querySelectorAll("[data-cab-soon]").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    cabState.soon = a.dataset.cabSoon + " · " + cabT().opensNext;
    const out = document.querySelector("[data-cab-soon-out]"); if (out) out.textContent = cabState.soon;
  }));
  document.querySelectorAll("[data-cab-focus]").forEach(b => b.onclick = () => { cabState.focus = b.dataset.cabFocus; cabRerender(); });
  document.querySelectorAll("[data-cab-step]").forEach(b => b.onclick = () => { cabState.step = +b.dataset.cabStep; cabRerender(); });
  const scr = document.querySelector("[data-cab-screen]");
  const role = scr ? (scr.dataset.cabScreen.split("-")[1] || "artist") : "artist";
  const dr = document.querySelector("[data-cab-drawer]");
  if (dr) dr.onclick = () => { cabState.drawer[role] = !cabState.drawer[role]; cabRerender(); };
  document.querySelectorAll("[data-cab-tab]").forEach(b => b.onclick = () => { cabState.tab = b.dataset.cabTab; cabRerender(); });
  document.querySelectorAll("[data-cab-bar]").forEach(b => b.onclick = () => {
    const i = +b.dataset.cabBar, lib = CabPS.CAB.lib;
    cabState.chords[i] = lib[(lib.indexOf(cabState.chords[i]) + 1) % lib.length];
    cabRerender();
  });
  document.querySelectorAll("[data-cab-video]").forEach(vid => vid.onclick = () => { const o = document.querySelector("[data-cab-video-out]"); if (o) o.textContent = cabT().videoNotConnected; });
  const hand = document.querySelector("[data-cab-hand]");
  if (hand) hand.onclick = () => { cabState.hand = !cabState.hand; cabRerender(); };
  const rec = document.querySelector("[data-cab-rec]");
  if (rec) rec.onclick = () => {
    if (window.CabinetHarness?.state.meeting) { CabinetHarness.record(); return; }
    if (cabState.rec) {
      cabState.rec = false;
      const pool = cabT().notesArtist;
      cabState.extraNotes.push(pool[cabState.nNote % pool.length]); cabState.nNote++;
    } else cabState.rec = true;
    cabRerender();
  };
  const form = document.querySelector("[data-cab-chat-form]");
  if (form) form.addEventListener("submit", e => {
    e.preventDefault();
    const inp = form.querySelector("[data-cab-chat-input]");
    const text = (inp.value || "").trim(); if (!text) return;
    if (window.CabinetHarness) { CabinetHarness.send(text, role); return; }
    const isM = role === "maestro";
    cabState.extraChat.push({ from: isM ? "maestro" : "london", to: isM ? cabState.focus : "london", text });
    cabRerender();
  });
  const metroBtn = document.querySelector("[data-cab-metro]");
  if (metroBtn && cabMetro.on && cabMetro.ctx && !cabMetro.timer) cabMetroStep();
  if (metroBtn) metroBtn.onclick = () => {
    if (cabMetro.on) { cabMetroOff(); cabRerender(); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    cabMetro.ctx = cabMetro.ctx || new AC();
    if (cabMetro.ctx.state === "suspended") cabMetro.ctx.resume();
    cabMetro.on = true; cabMetro.beat = -1;
    cabRerender();
    cabMetroStep();
  };
  document.querySelectorAll("[data-cab-bpm]").forEach(b => b.onclick = () => {
    cabMetro.bpm = Math.max(40, Math.min(180, cabMetro.bpm + (+b.dataset.cabBpm) * 4));
    const v = document.querySelector("[data-cab-bpm-val]"); if (v) v.textContent = cabMetro.bpm;
  });
}
function stop() { cabMetroStop(); cabState.rec = false; }
window.Cabinet = { home, session, leagues, bind, stop, state: cabState };
