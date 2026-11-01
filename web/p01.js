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
  convOpen: false, sigPaused: false,
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
function head(mode, current, navRow) {
  const tt = t();
  const nav = [["#/convention", tt.navConv], ["#/leagues", tt.navLeagues], ["#/space", tt.navSpace]];
  return `<header class="p01-head">
    <a class="p01-brand" href="#/"><img src="assets/lyre.png" alt="Golden Lyre"><span class="serif">Souls of Muse</span></a>
    <nav class="p01-nav" aria-label="Souls of Muse">${nav.map(([h, l]) => `<a href="${h}"${l === current ? ' aria-current="page"' : ""}>${escP(l)}</a>`).join("")}</nav>
    <div class="p01-spacer"></div>${langSwitch()}
    ${mode === "workshop" ? '<div class="p01-avatar" aria-label="Lina Khairullina">LK</div>' : ""}
  </header>${navRow ? `<nav class="p01-navrow" aria-label="Souls of Muse">${nav.map(([h, l]) => `<a href="${h}"${l === current ? ' aria-current="page"' : ""}>${escP(l)}</a>`).join("")}</nav>` : ""}`;
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
/* Dombra contour (triangular body, long neck) — Folk emblem, not a feather/leaf. */
const DOMBRA_SVG = `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="width:1.35em;height:1.35em"><path d="M30 4l4 4-13 13"/><path d="M34 8l6-2-2 6"/><circle cx="15" cy="33" r="2.2" fill="currentColor" stroke="none"/><path d="M21 21L8 34a5 5 0 0 0 7 7l13-13a5 5 0 0 0-7-7z"/><path d="M13 36l6-6"/></svg>`;
function leagueGlyph(icon) {
  return icon === "dombra" ? DOMBRA_SVG : `<i class="ph ${icon}"></i>`;
}
function roleTabs(activeKey) {
  const tt = t();
  const defs = [["teacher", tt.roleT, "baton"], ["student", tt.roleS, "ph-music-notes"], ["listener", tt.roleL, "ph-headphones"]];
  return `<div class="p01-roles" role="tablist" aria-label="${escP(tt.navSpace)}">${defs.map(([k, label, ic]) =>
    `<button role="tab" data-role="${k}" aria-selected="${k === activeKey}">${ic === "baton" ? '<span class="p01-baton" aria-hidden="true"></span>' : `<i class="ph ${ic}"></i>`}${escP(label)}</button>`).join("")}</div>`;
}

/* Approved Convention text (verbatim, bilingual) + Entrance v4 first screen. */
const CONV = {
  en: { title: 'Convention of the Keepers of Live Music',
    first: 'I, the undersigned, honour music as one of humanity’s greatest gifts by pledging to preserve and develop people’s ability to compose, perform and pass musical works on to others.',
    rest: [
      'Many generations of musicians before us have built, generation after generation, the great musical universe in which we live today. I am ready to carry this tradition forward by sharing with other participants in this Convention—or gratefully learning from them—instrumental and vocal skills, knowledge of music theory, the practice of making music together, and the shared experience of listening to live music.',
      'As a participant in this Convention, I will respect and uphold the copyright of those who create musical works, and help preserve musical knowledge.',
      'I will strive to play live music more often than I do now, so that as many people around me as possible may experience music performed live, directly by a musician.',
      'In taking part in the Convention’s community, I pledge to follow all its adopted rules for communication between participants, while retaining my right to freedom of artistic expression in the musical direction I choose.'],
    readAll: 'Read the full Convention', collapse: 'Collapse' },
  ru: { title: 'Конвенция хранителей живой музыки',
    first: 'Я, нижеподписавшийся, отдаю дань уважения такому великому дару человечества, как музыка, и обязуюсь сохранять и развивать умение людей сочинять, исполнять и передавать другим людям музыкальные произведения.',
    rest: [
      'Множество предыдущих поколений музыкантов последовательно создали великую музыкальную вселенную, в которой мы сейчас живём. Я готов поддерживать эту традицию: делиться с другими участниками Конвенции или с благодарностью принимать от них умение играть на музыкальных инструментах, владение вокалом, знания по теории музыки, практику коллективного исполнения музыки и совместного прослушивания живой музыки.',
      'Как участник Конвенции, я буду всячески поддерживать авторские права создателей музыкальных произведений и заботиться о сохранении музыкальных знаний.',
      'Я постараюсь играть живую музыку чаще, чем делаю это сейчас, чтобы подарить опыт прослушивания музыки, создаваемой непосредственно играющим музыкантом, как можно большему количеству окружающих меня людей.',
      'Принимая участие в деятельности сообщества Конвенции, обязуюсь соблюдать все принятые в нём правила общения между участниками, но оставляю за собой право на свободу художественного самовыражения в выбранном мною направлении музыкального творчества!'],
    readAll: 'Читать Конвенцию целиком', collapse: 'Свернуть' },
};
const ENT_SIGS = [["latin", "assets/sig-latin.png"], ["korean", "assets/sig-korean.png"], ["japanese", "assets/sig-japanese.png"], ["cyrillic", "assets/sig-cyrillic.png"]];
function entrance() {
  const tt = t(), cv = CONV[state.lang];
  return `<div class="p01 p01-ceremony">${head("ceremony", tt.navConv, true)}
  <main id="main" tabindex="-1" class="p01-wrap p01-ent">
    <h1 class="p01-ent-promise">${escP(tt.promise)}</h1>
    <div class="p01-ent-grid">
      <section class="p01-ent-card" aria-label="${escP(cv.title)}">
        <div class="p01-ent-cardhead"><img src="assets/lyre.png" alt="Golden Lyre"><h2>${escP(cv.title)}</h2></div>
        <p class="p01-ent-first">${escP(cv.first)}</p>
        ${state.convOpen ? cv.rest.map(p => `<p class="p01-ent-rest">${escP(p)}</p>`).join("") : ""}
        <button class="p01-ent-toggle" data-conv aria-expanded="${state.convOpen}"><i class="ph ${state.convOpen ? "ph-caret-up" : "ph-caret-down"}"></i>${escP(state.convOpen ? cv.collapse : cv.readAll)}</button>
        <div class="p01-ent-sig">
          <div class="p01-ent-sigline" data-sigline>
            ${ENT_SIGS.map(([k, f]) => `<div class="p01-ent-sigimg" data-k="${k}"><img src="${f}" alt=""></div>`).join("")}
            <span class="p01-ent-caret" data-caret></span>
          </div>
          <div class="p01-ent-sigbar"></div>
          <div class="p01-ent-sigrow">
            <span class="p01-kicker">${escP(tt.signedWord)}</span>
            <span class="p01-ent-cap serif" data-cap>Lina Khairullina</span>
            <button class="p01-ent-iconbtn" data-sig-pause aria-label="${escP(tt.pauseLabel)}"><i class="ph ${state.sigPaused ? "ph-play-circle" : "ph-pause"}"></i></button>
            <button class="p01-play p01-ent-play" data-ent-play data-p01-play="entcur" aria-label="${escP(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
          </div>
          <span class="p01-chip">${escP(tt.signPreview)}</span>
        </div>
        <div class="p01-ent-preview">
          <label>${escP(tt.yourName)} <input id="entName" autocomplete="off" placeholder="${escP(tt.yourNamePh)}"></label>
          <label id="entReadingWrap" hidden>${escP(tt.readingLabel)} <input id="entReading" autocomplete="off" placeholder="${escP(tt.readingPh)}"></label>
          <p id="entNotes" class="p01-ent-notes" aria-live="polite">${escP(tt.notesEmpty)}</p>
          <div class="p01-ent-score" id="entScore"></div>
          <p><button class="p01-btn p01-ent-listen" id="entPlayBtn" type="button"><i class="ph-fill ph-play"></i> ${escP(tt.listenYours)}</button></p>
        </div>
      </section>
      <div class="p01-ent-side">
        <button class="p01-ent-cta" id="entSign" type="button"><i class="ph ph-signature"></i> ${escP(tt.signCta)}</button>
        <p class="p01-ent-note"><span class="p01-ent-social"><i class="ph ph-facebook-logo"></i><i class="ph ph-instagram-logo"></i></span><span>${escP(tt.signNote)}</span></p>
        <p id="entSignState" class="p01-ent-state" role="status"></p>
      </div>
    </div>
    <p class="p01-ent-about">${escP(tt.about)}</p>
    <div class="p01-ent-leagueshead"><h2 class="serif">${escP(tt.leaguesTitle)}</h2><span>${escP(tt.leaguesNote)}</span></div>
    <div class="p01-ent-leagues">${PS.LEAGUES.map(([ic, e, r]) => `<div class="p01-ent-league"><span class="p01-emblem p01-emblem-lg"><img src="assets/frame-classic.png" alt="">${leagueGlyph(ic)}</span><span>${escP(state.lang === "en" ? e : r)}</span></div>`).join("")}</div>
  </main>
  <footer class="p01-foot">${escP(tt.footer)}</footer></div>`;
}

function welcome() {
  const tt = t();
  return `<div class="p01 p01-ceremony">${head("ceremony", tt.navSpace, true)}
  <main id="main" tabindex="-1" class="p01-wrap">
    <div class="p01-welcome-hero">
      <span class="p01-kicker">${escP(tt.wKicker)}</span>
      <h1>${escP(tt.wTitle)}</h1>
      <p class="p01-example-note" role="note">${escP(tt.exampleProfileNote)}</p>
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
    <div class="p01-cta-wrap"><a class="p01-cta" href="#/space"><span class="p01-cta-text">${escP(tt.cta)} <i class="ph ph-arrow-right"></i> ${escP(tt.ctaTail)}</span></a></div>
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
  const leagueIcon = roleKey === "teacher" ? "ph-microphone-stage" : roleKey === "listener" ? "dombra" : "ph-guitar";
  const recPlay = (kind, i) => `data-p01-rec="${kind}:${i}"`;
  return `<div class="p01 p01-workshop">${head("workshop", tt.navSpace, true)}
  <main id="main" tabindex="-1" class="p01-wrap">
    <div class="p01-space-top">
      <div><div class="mono" style="font-size:12.5px;color:var(--p01-n400)">${escP(tt.dateLine)}</div>
      <h1>${escP(tt.greet)}</h1>
      <p class="p01-example-note" role="note">${escP(tt.exampleProfileNote)}</p></div>
      <div class="p01-spacer"></div>
      <div class="p01-roles-wrap">
        <span class="p01-rolehint">${escP(tt.roleHint)}</span>${roleTabs(roleKey)}
      </div>
    </div>
    <div class="p01-grid">
      <div class="p01-col p01-col-left">
        <section class="p01-panel p01-panel-today" aria-label="${escP(tt.today)}">
          <div class="p01-today-grid">
            <div class="p01-today-left">
              <div style="display:flex;gap:10px;align-items:center"><span class="p01-kicker">${escP(tt.today)}</span><span class="p01-tag"><i class="ph ${RL.today.chipIcon}"></i>${escP(RL.today.chip)}</span></div>
              <div><div style="font-size:13px;color:var(--p01-accent300)">${escP(RL.today.kicker)}</div>
              <div style="font-size:24px;font-weight:500;line-height:1.2">${escP(RL.today.title)}</div>
              <div class="mono" style="font-size:12.5px;color:var(--p01-n400)">${escP(RL.today.meta)}</div></div>
              <div class="p01-people">${R.todayPeople.map(i => `<span class="p01-ava" title="${escP(iniName[i] || "")}">${escP(i)}</span>`).join("")}<span style="font-size:12.5px;color:var(--p01-n400)">${escP(RL.today.peopleNote)}</span></div>
            </div>
            <div class="p01-today-right">
              ${R.lesson ? `<span style="font-size:12.5px;color:var(--p01-n300)">${escP(tt.mode)}</span>
                ${[["indiv", tt.indiv, RL.modes.indiv], ["group", tt.group, RL.modes.group]].map(([k, label, sub]) =>
                  `<button class="p01-mode" data-mode="${k}" role="radio" aria-checked="${state.mode === k}"><span class="p01-radio"><i></i></span><span><span style="display:block;font-size:14px;font-weight:500">${escP(label)}</span><span style="font-size:12px;color:var(--p01-n400)">${escP(sub)}</span></span></button>`).join("")}` : ""}
              <a class="p01-btn primary" href="${R.lesson ? "lesson.html" : "#/space/admirer"}">${escP(RL.today.action)} <i class="ph ph-arrow-right"></i></a>
            </div>
          </div>
        </section>
        <section class="p01-panel p01-muse p01-panel-muse" aria-label="MUSE">
          <div style="display:flex;gap:10px;align-items:center"><img src="assets/muse-badge.png" alt="MUSE" style="width:34px"><span style="font-size:13.5px;font-weight:500">${escP(tt.museTitle)}</span><span class="p01-muserule" style="font-size:12px;color:var(--p01-n400)">${escP(tt.museRule)}</span></div>
          <div style="font-size:14px;line-height:1.5;color:#d8d5e6">${escP(RL.muse.intro)}</div>
          <div class="p01-quote">${escP(RL.muse.quote)}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><button class="p01-btn primary">${escP(RL.muse.a1)}</button><button class="p01-btn ghost">${escP(RL.muse.a2)}</button><div class="p01-spacer"></div><span class="mono" style="font-size:12px;color:var(--p01-n400)">${escP(RL.muse.meta)}</span></div>
        </section>
        <section class="p01-panel p01-panel-recs" aria-label="${escP(RL.recsTitle)}">
          <span class="p01-kicker">${escP(RL.recsTitle)}</span>
          ${RL.recs.map(([kind, title, meta, chip], i) => `<div class="p01-rec">
            <button class="p01-play sm" ${recPlay(kind, i)} aria-label="${escP(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
            <div style="flex:1;min-width:0"><div style="font-size:14px">${escP(title)}</div><div class="mono" style="font-size:12px;color:var(--p01-n400)">${escP(meta)}</div>
            ${chip ? `<span class="p01-tag" style="margin-top:4px"><i class="ph ph-seal-question"></i>${escP(chip)}</span>` : ""}</div></div>`).join("")}
        </section>
      </div>
      <div class="p01-col p01-col-right">
        <section class="p01-panel p01-panel-league" aria-label="${escP(tt.league)}">
          <div style="display:flex;gap:12px;align-items:center"><span class="p01-emblem"><img src="assets/frame-classic.png" alt="">${leagueGlyph(leagueIcon)}</span>
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
        <div class="p01-leagues" style="margin-top:12px">${PS.LEAGUES.map(([ic, e, r]) => `<span class="p01-league"><span class="p01-emblem"><img src="assets/frame-classic.png" alt="">${leagueGlyph(ic)}</span>${escP(en ? e : r)}</span>`).join("")}</div></div>
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

/* --- Entrance signature-line animation (Entrance v4 storyboard) --- */
let entRaf = null, entCur = "latin";
const ENT_DUR = { latin: 3.6, korean: 3.0, japanese: 3.0, cyrillic: 4.0 };
const ENT_ORDER = ["latin", "korean", "japanese", "cyrillic"];
function bindEntrance() {
  const line = document.querySelector("[data-sigline]"); if (!line) return;
  const tt = t();
  const convBtn = document.querySelector("[data-conv]");
  if (convBtn) convBtn.onclick = () => { state.convOpen = !state.convOpen; render(); };
  const signBtn = document.getElementById("entSign");
  if (signBtn) signBtn.onclick = () => { const el = document.getElementById("entSignState"); if (el) el.textContent = tt.signState; };
  const pauseBtn = document.querySelector("[data-sig-pause]");
  /* typed-name inspectable preview via the shared signature engine (AI3-916) */
  const SS = window.SoulSignature;
  let preview = null;
  const updPreview = () => {
    if (!SS) return;
    const nm = document.getElementById("entName"), rd = document.getElementById("entReading");
    if (!nm) return;
    preview = SS.previewSignature(nm.value, rd ? rd.value : "");
    const wrap = document.getElementById("entReadingWrap"); if (wrap) wrap.hidden = !preview.has_han;
    const notesEl = document.getElementById("entNotes");
    if (notesEl) notesEl.textContent = preview.need_reading ? tt.needReading : (preview.notes.length ? tt.yourNotes + ": " + preview.note_names_ru.join(" – ") : tt.notesEmpty);
    const score = document.getElementById("entScore");
    if (score) score.innerHTML = preview.notes.length && window.SoulScoreSVG ? window.SoulScoreSVG(preview.notes) : "";
  };
  const nmEl = document.getElementById("entName"), rdEl = document.getElementById("entReading");
  if (nmEl) nmEl.addEventListener("input", updPreview);
  if (rdEl) rdEl.addEventListener("input", updPreview);
  const playBtn = document.getElementById("entPlayBtn");
  if (playBtn) playBtn.onclick = () => {
    if (!preview || !preview.notes.length) return;
    if (state.playing === "enttyped") { stopAudio(); return; }
    stopAudio();
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    p01actx = p01actx || new AC(); if (p01actx.state === "suspended") p01actx.resume();
    const beat = 60 / 92; let when = p01actx.currentTime + 0.05;
    const master = p01actx.createGain(); master.gain.value = 0.22; master.connect(p01actx.destination);
    preview.notes.forEach(n => {
      const d = n.dur * beat, f = 440 * Math.pow(2, (n.midi - 69) / 12);
      [["triangle", 1], ["sine", .5]].forEach(([type, amp], k) => {
        const o = p01actx.createOscillator(), g = p01actx.createGain();
        o.type = type; o.frequency.value = f * (k ? 2 : 1);
        g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(amp * (k ? .25 : 1), when + .015);
        g.gain.exponentialRampToValueAtTime(0.001, when + Math.max(d * .95, .18));
        o.connect(g); g.connect(master); o.start(when); o.stop(when + d + .05); p01voices.push(o);
      });
      when += d;
    });
    state.playing = "enttyped";
    p01timer = setTimeout(stopAudio, (when - p01actx.currentTime) * 1000 + 150);
  };
  updPreview();
  /* writing loop: pen reveal -> hold -> fade, four scripts, reduced-motion static */
  const reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const HOLD = 1.4, FADE = .35, GAP = .15;
  const slots = []; { let acc = 0; ENT_ORDER.forEach(k => { const len = ENT_DUR[k] + HOLD + FADE + GAP; slots.push({ k, start: acc, len }); acc += len; }); }
  const LOOP = slots.reduce((a, s) => a + s.len, 0);
  const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  const imgs = [...line.querySelectorAll("[data-k]")], caret = line.querySelector("[data-caret]");
  const cap = document.querySelector("[data-cap]");
  const paint = (k, p, op, capOp, writing) => {
    entCur = k;
    imgs.forEach(el => { const on = el.dataset.k === k; el.style.opacity = on ? op : 0; if (on) el.style.clipPath = `inset(0 ${(100 - p * 100).toFixed(2)}% 0 0)`; });
    if (caret) { caret.style.left = (p * 100) + "%"; caret.style.opacity = writing && !state.sigPaused ? 1 : 0; }
    if (cap) { const nm = PS.SIGS[k].name; if (cap.textContent !== nm) cap.textContent = nm; cap.style.opacity = Math.max(0, capOp); }
  };
  if (pauseBtn) pauseBtn.onclick = () => { state.sigPaused = !state.sigPaused; pauseBtn.innerHTML = `<i class="ph ${state.sigPaused ? "ph-play-circle" : "ph-pause"}"></i>`; };
  if (reduced) { state.sigPaused = true; paint("latin", 1, 1, 1, false); return; }
  let tAcc = 0, last = performance.now();
  const tick = now => {
    const dt = Math.min(.1, (now - last) / 1000); last = now;
    if (!state.sigPaused && !document.hidden) tAcc = (tAcc + dt) % LOOP;
    const s = slots.find(x => tAcc >= x.start && tAcc < x.start + x.len) || slots[0];
    const local = tAcc - s.start, dur = ENT_DUR[s.k];
    const p = local < dur ? ease(local / dur) : 1;
    const op = local < dur + HOLD ? 1 : local < dur + HOLD + FADE ? 1 - (local - dur - HOLD) / FADE : 0;
    const capOp = local < dur ? Math.max(0, (local - dur + .6) / .6) : op;
    paint(s.k, p, op, capOp, local < dur);
    entRaf = requestAnimationFrame(tick);
  };
  entRaf = requestAnimationFrame(tick);
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
    if (id === "entcur") { playSeq(id, PS.SIGS[entCur] || PS.SIGS.latin); return; }
    playSeq(id, id === "comp" ? PS.SIGS.korean : PS.SIGS.latin);
  });
  bindEntrance();
  document.querySelectorAll("[data-p01-rec]").forEach(b => b.onclick = () => {
    const [kind, i] = b.dataset.p01Rec.split(":");
    const sig = kind === "sig" ? PS.SIGS.latin : PS.SIGS.short;
    b.dataset.p01Play = "rec" + i;
    playSeq("rec" + i, sig);
  });
}
function stopAll() { stopAudio(); if (entRaf) { cancelAnimationFrame(entRaf); entRaf = null; } }
window.P01 = { entrance, welcome, space, components, bind, stop: stopAll, state };
