"use strict";
/* Souls of Muse Portal 2.0 (Claude Design, 3 Nov 2026).
   Home (#/, #/convention): the Golden Lyre route, the Convention card and two
   velvet doors (Leagues, My space); notes in a right-hand shutter.
   Leagues (#/leagues): seven Leagues turning around the Golden Lyre.
   The Convention wording comes from P01.CONV (approved text). The example
   signature animation and the sign button are driven by P01.bind(). */
(function () {
const T = {
  en: {
    promise: "Sign the Convention with your name, written as music.",
    cta: "Sign the Convention", launch: "Signing opens with the launch.",
    example: "Example: a member's musical signature", exampleData: "example data",
    listen: "Listen", pauseLabel: "Pause or play the writing",
    howTitle: "How a name becomes music", more: "Read more", less: "Less",
    howNote: "Cyrillic, Vietnamese and other scripts are read through Latin letters. For Chinese characters and kanji we ask you for the reading.",
    how: [["Latin letters — the French grid", "Composers have long signed music with names: B-A-C-H, D-S-C-H (Shostakovich), A-B-E-G-G (Schumann). We use the French grid of 1909.", "In 1909, for Haydn's centenary, a Paris music journal asked Debussy, Dukas, Hahn, d'Indy, Ravel and Widor to write pieces on his name. The alphabet was laid out in rows under the notes A to G. We use the same grid."],
      ["Japanese — iroha", "In Japanese, notes are named with kana from the iroha poem: イ ロ ハ ニ ホ ヘ ト are A B C D E F G.", "The whole iroha poem, laid out in rows of seven, gives every kana its note."],
      ["Korean — hangul", "In Korean, notes are named 가 나 다 라 마 바 사 — A B C D E F G. Each syllable sounds the note of its first consonant.", "ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ make the first row, then ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ the second."]],
    langName: "English", soon: "soon", language: "Language",
    leaguesTitle: "Seven Leagues", leaguesSub: "Families of instruments. Each League chooses its own emblem.",
    hideNotes: "Hide notes, open the scene", notesKicker: "Notes",
    tabHow: "How a name becomes music", tabWhat: "What is a League",
    route: ["Convention", "Leagues", "My space"], here: "You are here", routeLabel: "The Golden Lyre route",
    hubLabel: "Convention",
    doorL: { title: "Leagues", sub: "Seven families of instruments", enter: "Enter" },
    doorS: { title: "My space", sub: "Your sessions, practice plans and League", enter: "Enter" },
    hintTitle: "Choose a League", hint: "Drag to turn the circle, or pick from the list. Arrow keys turn it too.",
    mHint: "Swipe to turn · tap a League",
    graphLabel: "Seven Leagues around the Golden Lyre. Arrow keys turn the circle.",
    enterLeague: "Enter the League", prev: "Previous", next: "Next", close: "Close",
    whatTitle: "What is a League",
    what: ["A League brings together musicians who play instruments of one family.", "There are seven, by family: plucked strings, bowed strings, keys, winds, drums, electronic and vocal.", "Your instrument decides your League. Guitar is a plucked string, so a guitarist belongs to the League of the String.", "Each League chooses its own emblem."],
    whatRead: "How to read the circle",
    whatCircle: "In the centre is the Golden Lyre, the Convention. Gold threads link every League to it and to its neighbours.",
    about: "Souls of Muse is a free association of musicians keeping live music alive.",
  },
  ru: {
    promise: "Подпишите Конвенцию своим именем, записанным нотами.",
    cta: "Подписать Конвенцию", launch: "Подписание откроется с запуском.",
    example: "Образец: музыкальная подпись участника", exampleData: "пример данных",
    listen: "Слушать", pauseLabel: "Остановить или продолжить запись",
    howTitle: "Как имя становится музыкой", more: "Подробнее", less: "Свернуть",
    howNote: "Кириллица, вьетнамский и другие письменности читаются через латиницу. Для китайских иероглифов и кандзи мы спрашиваем у вас чтение.",
    how: [["Латиница — французская сетка", "Композиторы давно подписывают музыку именами: B-A-C-H, D-S-C-H (Шостакович), A-B-E-G-G (Шуман). Мы пользуемся французской сеткой 1909 года.", "В 1909 году, к столетию Гайдна, парижский музыкальный журнал попросил Дебюсси, Дюка, Ана, д’Энди, Равеля и Видора написать пьесы на его имя. Алфавит разложили рядами под нотами от A до G. Мы пользуемся той же сеткой."],
      ["Японский — ироха", "В японском ноты называют каной из стихотворения ироха: イ ロ ハ ニ ホ ヘ ト — это A B C D E F G.", "Всё стихотворение ироха, разложенное рядами по семь, даёт ноту каждому знаку каны."],
      ["Корейский — хангыль", "В корейском ноты называют 가 나 다 라 마 바 사 — A B C D E F G. Каждый слог звучит нотой своей первой согласной.", "ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ — первый ряд, ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ — второй."]],
    langName: "Русский", soon: "скоро", language: "Язык",
    leaguesTitle: "Семь Лиг", leaguesSub: "Семейства инструментов. Каждая Лига выбирает свою эмблему.",
    hideNotes: "Убрать записку, открыть сцену", notesKicker: "Записка",
    tabHow: "Как имя становится музыкой", tabWhat: "Что такое Лига",
    route: ["Конвенция", "Лиги", "Моё пространство"], here: "Вы здесь", routeLabel: "Маршрут «Золотая лира»",
    hubLabel: "Конвенция",
    doorL: { title: "Лиги", sub: "Семь семейств инструментов", enter: "Войти" },
    doorS: { title: "Моё пространство", sub: "Ваши встречи, планы практики и Лига", enter: "Войти" },
    hintTitle: "Выберите Лигу", hint: "Потяните, чтобы повернуть круг, или выберите из списка. Стрелки тоже поворачивают.",
    mHint: "Проведите, чтобы повернуть · нажмите на Лигу",
    graphLabel: "Семь Лиг вокруг Золотой лиры. Стрелки поворачивают круг.",
    enterLeague: "Войти в Лигу", prev: "Предыдущая", next: "Следующая", close: "Закрыть",
    whatTitle: "Что такое Лига",
    what: ["Лига объединяет музыкантов, играющих на инструментах одного семейства.", "Их семь, по семействам: щипковые и смычковые струнные, клавишные, духовые, ударные, электроника и вокал.", "Лигу определяет ваш инструмент. Гитара — щипковый струнный, поэтому гитарист — в Лиге струны.", "Каждая Лига выбирает свою эмблему."],
    whatRead: "Как читать круг",
    whatCircle: "В центре — Золотая лира, Конвенция. Золотые нити связывают с ней каждую Лигу и соседние Лиги между собой.",
    about: "Souls of Muse — свободное объединение музыкантов, хранящих живую музыку.",
  },
};
const LANGS = [["en", "English"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"], ["pt", "Português"], ["it", "Italiano"], ["ja", "日本語"], ["ko", "한국어"], ["zh", "中文"], ["hi", "हिन्दी"], ["vi", "Tiếng Việt"], ["kk", "Қазақша"], ["ru", "Русский"], ["tr", "Türkçe"], ["ar", "العربية"], ["id", "Bahasa Indonesia"]];
const GRIDS = [
  ["ABCDEFG", "HIJKLMN", "OPQRSTU", "VWXYZ"],
  ["イロハニホヘト", "チリヌルヲワカ", "ヨタレソツネナ", "ラムウヰノオク", "ヤマケフコエテ", "アサキユメミシ", "ヱヒモセス"],
  ["ㄱㄴㄷㄹㅁㅂㅅ", "ㅇㅈㅊㅋㅌㅍㅎ"]].map(rows => rows.flatMap(r => { const a = [...r]; while (a.length < 7) a.push(""); return a; }));
const NOTES = ["A", "B", "C", "D", "E", "F", "G"];
const IDS = ["string", "bow", "keys", "winds", "drums", "electronic", "vocal"];
const YS = [-70, 40, -30, 85, -55, 15, -95];
const TAU = Math.PI * 2;
const SIGS = [["latin", "assets/sig-latin.png"], ["korean", "assets/sig-korean.png"], ["japanese", "assets/sig-japanese.png"], ["cyrillic", "assets/sig-cyrillic.png"]];

const ss = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
};
const st = { menu: false, how: {}, sel: null, shut: ss.get("som_p20_shut", {}) };
let raf = null, offs = [];
const lang = () => (window.P01 && window.P01.state.lang === "ru") ? "ru" : "en";
const t = () => T[lang()];
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const reduced = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
const leagues7 = () => {
  const L = (window.P01Strings && window.P01Strings.LEAGUES) || [];
  const ru = lang() === "ru";
  return L.map((x, i) => ({ id: IDS[i], icon: x[0], name: ru ? x[2] : x[1], instr: ru ? x[4] : x[3], family: ru ? x[6] : x[5] }));
};

function sky(kind) {
  const clouds = [[-8, 18, 820, 220, .30, .05, 0], [40, 34, 900, 260, .34, .035, 2], [62, 58, 1000, 300, .40, .025, 4], [-12, 66, 900, 280, .36, .03, 1], [30, 80, 1300, 360, .46, .02, 3], [70, 12, 700, 200, .26, .045, 5]];
  const rings = [[1900, 646, 14, 3], [1560, 530, 18, 4], [1240, 422, 22, 5], [960, 326, 26, 6], [700, 238, 30, 7], [470, 160, 34, 8]];
  return `<div class="p20-sky p20-sky-${kind}" aria-hidden="true">
    <div class="p20-sun"></div>
    ${clouds.map(([l, tp, w, h, a, sp, off]) => `<div class="p20-cloud" data-cloud data-sp="${sp}" data-off="${off}" style="left:${l}%;top:${tp}%;width:${w}px;height:${h}px;--a:${Math.round(a * 100)}%"></div>`).join("")}
    ${rings.map(([w, h, a, f], i) => `<div class="p20-ring" style="width:${w}px;height:${h}px;bottom:${-Math.round(h * 0.47)}px;--a:${a}%;--f:${f}%"></div>`).join("")}
  </div>`;
}

function langMenu() {
  const tt = t(), cur = lang();
  return `<div class="p20-lang">
    <button class="p20-langbtn" data-p20-menu aria-haspopup="listbox" aria-expanded="${st.menu}"><i class="ph ph-globe-simple" aria-hidden="true"></i>${esc(tt.langName)}<i class="ph ph-caret-down" aria-hidden="true"></i></button>
    ${st.menu ? `<div class="p20-langlist" role="listbox" aria-label="${esc(tt.language)}">${LANGS.map(([code, label]) => {
      const avail = code === "en" || code === "ru", current = code === cur;
      return `<button role="option" aria-selected="${current}" aria-disabled="${!avail}" ${avail ? `data-p20-lang="${code}"` : "tabindex=\"-1\""} class="${avail ? "" : "soon"}"><span dir="auto">${esc(label)}</span>${avail ? "" : `<span class="p20-soon">${esc(tt.soon)}</span>`}${current ? '<i class="ph ph-check" aria-hidden="true"></i>' : ""}</button>`;
    }).join("")}</div>` : ""}
  </div>`;
}

function header() {
  return `<header class="p20-head">
    <a class="p20-brand" href="#/"><img src="assets/lyre.png" alt=""><span>Souls of Muse</span></a>
    <div class="p20-grow"></div>${langMenu()}
  </header>`;
}

function route(here) {
  const tt = t(), hrefs = ["#/convention", "#/leagues", "#/space"];
  return `<nav class="p20-route" aria-label="${esc(tt.routeLabel)}">
    <span class="p20-strings" aria-hidden="true"><i></i><i></i><i></i></span>
    <ol>${tt.route.map((label, i) => `<li><a href="${hrefs[i]}"${i === here ? ' aria-current="page"' : ""}>
      <span class="p20-dot"></span>
      <span class="p20-stop"><span class="p20-n">0${i + 1}</span>${esc(label)}</span>
      ${i === here ? `<span class="p20-here">${esc(tt.here)}</span>` : ""}</a></li>`).join("")}</ol>
  </nav>`;
}

function convCard() {
  const tt = t(), P = window.P01, cv = P.CONV[lang()], open = !!P.state.convOpen;
  return `<section class="p20-card p01-ent-card" aria-label="${esc(cv.title)}">
    <div class="p01-ent-cardhead"><img src="assets/lyre.png" alt="Golden Lyre"><h2>${esc(cv.title)}</h2></div>
    <p class="p01-ent-first">${esc(cv.first)}</p>
    ${open ? cv.rest.map(p => `<p class="p01-ent-rest">${esc(p)}</p>`).join("") : ""}
    <button class="p01-ent-toggle" data-conv aria-expanded="${open}"><i class="ph ${open ? "ph-caret-up" : "ph-caret-down"}"></i>${esc(open ? cv.collapse : cv.readAll)}</button>
    <div class="p20-signrow">
      <button class="p20-sign" id="entSign" type="button" aria-describedby="p20SignNote"><i class="ph ph-signature" aria-hidden="true"></i><span>${esc(tt.cta)}</span><span class="p20-social" aria-hidden="true"><i class="ph ph-facebook-logo"></i><i class="ph ph-instagram-logo"></i></span></button>
      <p id="p20SignNote" class="p20-signnote"><i class="ph ph-clock" aria-hidden="true"></i>${esc(tt.launch)}</p>
      <p id="entSignState" class="p20-sr" role="status"></p>
    </div>
    <div class="p01-ent-sig p20-example">
      <div class="p20-exlabel"><span>${esc(tt.example)}</span><span class="p20-exdata">${esc(tt.exampleData)}</span></div>
      <div class="p01-ent-sigline" data-sigline>
        ${SIGS.map(([k, f]) => `<div class="p01-ent-sigimg" data-k="${k}"><img src="${f}" alt=""></div>`).join("")}
        <span class="p01-ent-caret" data-caret></span>
      </div>
      <div class="p01-ent-sigbar"></div>
      <div class="p01-ent-sigrow">
        <span class="p01-ent-cap" data-cap>Lina Khairullina</span>
        <button class="p01-ent-iconbtn" data-sig-pause aria-label="${esc(tt.pauseLabel)}"><i class="ph ${P.state.sigPaused ? "ph-play-circle" : "ph-pause"}"></i></button>
        <button class="p01-play p01-ent-play" data-p01-play="entcur" aria-label="${esc(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button>
      </div>
    </div>
  </section>`;
}

function door(kind, n) {
  const tt = t(), d = kind === "leagues" ? tt.doorL : tt.doorS, href = kind === "leagues" ? "#/leagues" : "#/space";
  return `<a class="p20-door" href="${href}" data-door="${kind}">
    <span class="p20-stage" aria-hidden="true"></span><span class="p20-floor" aria-hidden="true"></span>
    <span class="p20-half l" aria-hidden="true"></span><span class="p20-half r" aria-hidden="true"></span>
    <span class="p20-pelmet" aria-hidden="true"></span><span class="p20-fringe" aria-hidden="true"></span><span class="p20-trim" aria-hidden="true"></span>
    <span class="p20-doorlabel"><span class="p20-n">${n}</span><span class="p20-doortitle">${esc(d.title)}</span><span class="p20-doorsub">${esc(d.sub)}</span><span class="p20-enter">${esc(d.enter)}<i class="ph ph-arrow-right" aria-hidden="true"></i></span></span>
  </a>`;
}

function howBody() {
  const tt = t();
  return `${tt.how.map(([title, short, full], i) => {
    const open = !!st.how[i];
    return `<div class="p20-howitem">
      <div class="p20-howhead"><span class="p20-n">0${i + 1}</span><h3>${esc(title)}</h3></div>
      <p>${esc(short)}</p>
      ${open ? `<p>${esc(full)}</p><div class="p20-grid" aria-hidden="true">${NOTES.map(n => `<span class="h">${n}</span>`).join("")}${GRIDS[i].map(c => `<span>${esc(c)}</span>`).join("")}</div>` : ""}
      <button class="p20-more" data-how="${i}" aria-expanded="${open}"><i class="ph ${open ? "ph-caret-up" : "ph-caret-down"}" aria-hidden="true"></i>${esc(open ? tt.less : tt.more)}</button>
    </div>`;
  }).join("")}<p class="p20-hownote">${esc(tt.howNote)}</p>`;
}

function whatBody() {
  const tt = t();
  return `${tt.what.map(p => `<p class="p20-what">${esc(p)}</p>`).join("")}
    <div class="p20-howitem"><h3>${esc(tt.whatRead)}</h3><p>${esc(tt.whatCircle)}</p></div>`;
}

function shutter(kind) {
  const tt = t(), closed = !!st.shut[kind], title = kind === "how" ? tt.howTitle : tt.whatTitle;
  return `<aside class="p20-shutter${closed ? " closed" : ""}" aria-label="${esc(kind === "how" ? tt.tabHow : tt.tabWhat)}"${closed ? " hidden" : ""}>
      <div class="p20-shuthead"><span class="p20-kicker">${esc(tt.notesKicker)}</span><button class="p20-hide" data-shut="${kind}" type="button">${esc(tt.hideNotes)}<i class="ph ph-arrow-right" aria-hidden="true"></i></button></div>
      <div class="p20-shutbody"><h2>${esc(title)}</h2>${kind === "how" ? howBody() : whatBody()}</div>
    </aside>
    ${closed ? `<button class="p20-tab" data-unshut="${kind}" type="button"><i class="ph ph-arrow-left" aria-hidden="true"></i><span>${esc(kind === "how" ? tt.tabHow : tt.tabWhat)}</span></button>` : ""}`;
}

function home() {
  const tt = t();
  return `<div class="p20 p20-home${st.shut.how ? " shut" : ""}">${sky("home")}${header()}
    <main id="main" tabindex="-1" class="p20-main">
      ${route(0)}
      <div class="p20-homegrid">
        <div class="p20-left"><h1 class="p20-promise">${esc(tt.promise)}</h1>${convCard()}</div>
        <div class="p20-doors">${door("leagues", "02")}${door("space", "03")}</div>
      </div>
      <details class="p20-mnotes"><summary>${esc(tt.howTitle)}<i class="ph ph-caret-down" aria-hidden="true"></i></summary><div class="p20-shutbody">${howBody()}</div></details>
      <p class="p20-about">${esc(tt.about)}</p>
    </main>
    ${shutter("how")}
    <div class="p20-veil" aria-hidden="true"></div>
  </div>`;
}

function leagues() {
  const tt = t(), L = leagues7(), sel = st.sel;
  const card = sel == null ? `<div class="p20-hint"><i class="ph ph-hand-grabbing" aria-hidden="true"></i><div><strong>${esc(tt.hintTitle)}</strong><span class="p20-hintfull">${esc(tt.hint)}</span><span class="p20-hintm">${esc(tt.mHint)}</span></div></div>`
    : `<section class="p20-lcard" aria-live="polite" aria-label="${esc(L[sel].name)}">
      <div class="p20-lcardhead"><span>${esc(L[sel].family)}</span><span class="p20-n">0${sel + 1}</span><button class="p20-x" data-lsel="none" aria-label="${esc(tt.close)}"><i class="ph ph-x"></i></button></div>
      <h2>${esc(L[sel].name)}</h2><p>${esc(L[sel].instr)}</p>
      <div class="p20-lcardnav"><button class="p20-sq" data-lstep="-1" aria-label="${esc(tt.prev)}"><i class="ph ph-caret-left"></i></button>
        <a class="p20-gold" href="#/league/${L[sel].id}">${esc(tt.enterLeague)}<i class="ph ph-arrow-right" aria-hidden="true"></i></a>
        <button class="p20-sq" data-lstep="1" aria-label="${esc(tt.next)}"><i class="ph ph-caret-right"></i></button></div>
    </section>`;
  return `<div class="p20 p20-leagues${st.shut.what ? " shut" : ""}">${sky("leagues")}${header()}
    <main id="main" tabindex="-1" class="p20-main">
      ${route(1)}
      <div class="p20-lside p20-lhead"><h1>${esc(tt.leaguesTitle)}</h1><p>${esc(tt.leaguesSub)}</p></div>
      <details class="p20-mnotes"><summary>${esc(tt.whatTitle)}<i class="ph ph-caret-down" aria-hidden="true"></i></summary><div class="p20-shutbody">${whatBody()}</div></details>
      <div class="p20-graph" data-graph tabindex="0" role="group" aria-label="${esc(tt.graphLabel)}">
        ${[0, 1, 2, 3, 4, 5, 6].flatMap(i => [`<div class="p20-edge" data-edge data-a="h" data-b="${i}"></div>`, `<div class="p20-edge" data-edge data-a="${i}" data-b="${(i + 1) % 7}"></div>`]).join("")}
        <div class="p20-hub" data-hub><span><img src="assets/lyre.png" alt=""></span><em>${esc(tt.hubLabel)}</em></div>
        ${L.map((x, i) => `<button class="p20-node${sel === i ? " on" : ""}" data-node="${i}" tabindex="-1" aria-hidden="true"><span class="p20-orb"><i class="ph ${x.icon}"></i></span><span class="p20-nname">${esc(x.name)}</span><span class="p20-nfam">${esc(x.family)}</span></button>`).join("")}
      </div>
      <div class="p20-lside p20-llist">
        <ul aria-label="${esc(tt.leaguesTitle)}">${L.map((x, i) => `<li><button data-lsel="${i}" aria-pressed="${sel === i}"><span class="p20-n">0${i + 1}</span><span class="p20-lname">${esc(x.name)}</span><i class="ph ${x.icon}" aria-hidden="true"></i></button></li>`).join("")}</ul>
      </div>
      <div class="p20-lfoot">${card}</div>
    </main>
    ${shutter("what")}
  </div>`;
}

/* ---------- behaviour ---------- */
function rerender() { if (typeof window.render === "function") window.render(); }
function on(el, ev, fn, opt) { el.addEventListener(ev, fn, opt); offs.push(() => el.removeEventListener(ev, fn, opt)); }

function bind() {
  stop();
  document.querySelectorAll("[data-p20-menu]").forEach(b => b.onclick = e => { e.stopPropagation(); st.menu = !st.menu; rerender(); const nb = document.querySelector("[data-p20-menu]"); if (nb) nb.focus(); });
  document.querySelectorAll("[data-p20-lang]").forEach(b => b.onclick = () => {
    st.menu = false;
    if (window.P01) { window.P01.state.lang = b.dataset.p20Lang; try { localStorage.setItem("som_p01_lang", b.dataset.p20Lang); } catch (e) {} }
    document.documentElement.lang = b.dataset.p20Lang;
    rerender();
  });
  if (st.menu) on(document, "click", e => { if (!e.target.closest(".p20-lang")) { st.menu = false; rerender(); } });
  on(document, "keydown", e => { if (e.key === "Escape" && st.menu) { st.menu = false; rerender(); } });
  document.querySelectorAll("[data-how]").forEach(b => b.onclick = () => { const i = +b.dataset.how; st.how[i] = !st.how[i]; keepScroll(rerender); });
  document.querySelectorAll("[data-shut]").forEach(b => b.onclick = () => { st.shut[b.dataset.shut] = true; ss.set("som_p20_shut", st.shut); rerender(); const tab = document.querySelector("[data-unshut]"); if (tab) tab.focus(); });
  document.querySelectorAll("[data-unshut]").forEach(b => b.onclick = () => { st.shut[b.dataset.unshut] = false; ss.set("som_p20_shut", st.shut); rerender(); const h = document.querySelector("[data-shut]"); if (h) h.focus(); });
  document.querySelectorAll("[data-door]").forEach(a => a.onclick = e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1 || reduced()) return;
    e.preventDefault();
    const root = document.querySelector(".p20"); a.classList.add("go"); if (root) root.classList.add("leaving");
    setTimeout(() => { location.hash = a.getAttribute("href"); }, 760);
  });
  document.querySelectorAll("[data-lsel]").forEach(b => b.onclick = () => { const v = b.dataset.lsel; select(v === "none" ? null : +v, true); });
  document.querySelectorAll("[data-lstep]").forEach(b => b.onclick = () => select(((st.sel == null ? 0 : st.sel) + +b.dataset.lstep + 7) % 7, true));
  document.documentElement.lang = lang();
  startLoop();
}
function keepScroll(fn) { const y = window.scrollY; fn(); window.scrollTo(0, y); }
const g = { th: 0.5, v: 0, pend: 0, snap: false, drag: false, lx: 0, moved: 0, hover: false };
function select(i, snap) {
  st.sel = i; g.snap = snap && i != null;
  const y = window.scrollY; rerender(); window.scrollTo(0, y);
  if (i != null) { const b = document.querySelector(`[data-lsel="${i}"]`); if (b) b.focus({ preventScroll: true }); }
}

function startLoop() {
  const graph = document.querySelector("[data-graph]");
  const clouds = [...document.querySelectorAll("[data-cloud]")];
  if (!graph && !clouds.length) return;
  if (graph) {
    on(graph, "pointerdown", e => { g.drag = true; g.lx = e.clientX; g.moved = 0; g.snap = false; try { graph.setPointerCapture(e.pointerId); } catch (x) {} });
    on(graph, "pointermove", e => { if (!g.drag) return; const dx = e.clientX - g.lx; g.lx = e.clientX; g.moved += Math.abs(dx); g.th += dx * 0.006; g.v = reduced() ? 0 : dx * 0.0036; });
    const up = e => { if (!g.drag) return; g.drag = false;
      if (g.moved < 6) { const n = document.elementsFromPoint(e.clientX, e.clientY).find(x => x.dataset && x.dataset.node != null); if (n) select(+n.dataset.node, true); } };
    on(graph, "pointerup", up); on(graph, "pointercancel", () => { g.drag = false; });
    on(graph, "mouseenter", () => { g.hover = true; }); on(graph, "mouseleave", () => { g.hover = false; });
    on(graph, "keydown", e => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); g.snap = false; g.pend += (e.key === "ArrowRight" ? 1 : -1) * TAU / 7; }
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(frontIndex(), true); }
    });
  }
  let last = performance.now(), stT = 0;
  const tick = now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now; const R = reduced();
    if (!document.hidden) {
      if (!R) stT += dt;
      clouds.forEach(el => { el.style.transform = `translateX(${(Math.sin(stT * +el.dataset.sp + +el.dataset.off) * 140).toFixed(1)}px)`; });
      if (graph) paintGraph(graph, dt, R);
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
}
let lastPts = null;
function frontIndex() { if (!lastPts) return 0; let b = 0; lastPts.forEach((p, i) => { if (p.k > lastPts[b].k) b = i; }); return b; }
function paintGraph(el, dt, R) {
  const sel = st.sel, narrow = el.clientWidth < 700;
  const W = el.clientWidth, side = narrow ? 0 : 330;
  const r = narrow ? Math.min(150, W * 0.36) : Math.max(150, Math.min(250, (W - side) / 2 - 110)), F = 900;
  const cx = narrow ? W / 2 : (side + W) / 2, cy = el.clientHeight * 0.47, ys = narrow ? 0.7 : 1;
  const cp = Math.cos(-0.36), sp = Math.sin(-0.36);
  if (!g.drag) {
    if (g.snap && sel != null) { const target = Math.PI - sel * TAU / 7; const d = (((target - g.th) % TAU) + TAU * 1.5) % TAU - Math.PI; g.th += R ? d : d * Math.min(1, dt * 5); g.v = 0; if (Math.abs(d) < 0.0005) g.snap = false; }
    else {
      if (g.pend) { const s = R ? g.pend : g.pend * Math.min(1, dt * 6); g.th += s; g.pend -= s; if (Math.abs(g.pend) < 1e-4) g.pend = 0; }
      g.th += g.v; g.v *= 0.92; if (Math.abs(g.v) < 1e-5) g.v = 0;
      if (!R && sel == null && !g.hover) g.th += dt * TAU / 90;
    }
  }
  const c = Math.cos(g.th), s = Math.sin(g.th);
  const P = (x, y, z) => { const x1 = x * c + z * s, z1 = -x * s + z * c, y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp, k = F / (F + z2); return { x: cx + x1 * k, y: cy + y2 * k, k, z: z2 }; };
  const pts = YS.map((y, i) => { const a = i * TAU / 7; return P(r * Math.sin(a), y * ys, r * Math.cos(a)); });
  lastPts = pts;
  const hub = P(0, 0, 0), kmin = F / (F + r), kmax = F / (F - r);
  const dep = p => Math.max(0, Math.min(1, (p.k - kmin) / (kmax - kmin)));
  const sc = narrow ? 0.72 : 1;
  el.querySelectorAll("[data-node]").forEach(n => { const i = +n.dataset.node, p = pts[i], dim = sel != null && sel !== i;
    n.style.transform = `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) translate(-50%,-34%) scale(${(p.k * sc).toFixed(3)})`;
    n.style.zIndex = String(Math.round(1000 - p.z)); n.style.opacity = (dim ? 0.3 : 0.5 + 0.5 * dep(p)).toFixed(2); });
  const h = el.querySelector("[data-hub]"); if (h) { h.style.transform = `translate(${hub.x.toFixed(1)}px,${hub.y.toFixed(1)}px) translate(-50%,-40%) scale(${sc})`; h.style.zIndex = String(Math.round(1000 - hub.z)); }
  el.querySelectorAll("[data-edge]").forEach(e => { const a = e.dataset.a, b = +e.dataset.b, p = a === "h" ? hub : pts[+a], q = pts[b];
    const dx = q.x - p.x, dy = q.y - p.y, hot = sel != null && a === "h" && b === sel, dimE = sel != null && !hot;
    e.style.width = Math.hypot(dx, dy).toFixed(1) + "px";
    e.style.transform = `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) rotate(${Math.atan2(dy, dx).toFixed(4)}rad)`;
    const d = (dep(q) + (a === "h" ? 0.6 : dep(p))) / 2;
    e.style.opacity = (hot ? 1 : dimE ? 0.12 : (a === "h" ? 0.28 : 0.2) + 0.45 * d).toFixed(2);
    e.classList.toggle("hot", hot); });
}
function stop() {
  if (raf) { cancelAnimationFrame(raf); raf = null; }
  offs.forEach(f => f()); offs = [];
}
function reset() { st.menu = false; }
window.Portal20 = { home, leagues, bind, stop, reset, T };
})();
