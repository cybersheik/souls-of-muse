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
    hintTitle: "Choose a League", hint: "Drag in any direction to turn the circle, or pick from the list. Arrow keys turn it too.",
    mHint: "Swipe any way to turn · tap a League",
    graphLabel: "Seven Leagues around the Golden Lyre. Arrow keys turn the circle in any direction.",
    enterLeague: "Enter the League", prev: "Previous", next: "Next", close: "Close",
    whatTitle: "What is a League",
    what: ["A League brings together musicians who play instruments of one family.", "There are seven, by family: plucked strings, bowed strings, keys, winds, drums, electronic and vocal.", "Your instrument decides your League. Guitar is a plucked string, so a guitarist belongs to the League of the String.", "Each League chooses its own emblem."],
    whatRead: "How to read the circle",
    whatCircle: "In the centre is the Golden Lyre, the Convention. Gold threads link every League to it and to its neighbours.",
    about: "Souls of Muse is a free association of musicians keeping live music alive.",
    nameLabel: "Your name", namePh: "Type your name", cancel: "Cancel",
    thanks: "Signed.", sub: "Your musical signature", savedHere: "Saved on this device.", signAgain: "Sign with another name",
    noNotes: "Type your name in letters — it will be written as music.",
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
    hintTitle: "Выберите Лигу", hint: "Тяните в любую сторону, чтобы вращать круг, или выберите из списка. Стрелки тоже вращают.",
    mHint: "Вращайте пальцем в любую сторону · нажмите на Лигу",
    graphLabel: "Семь Лиг вокруг Золотой лиры. Стрелки поворачивают круг в любую сторону.",
    enterLeague: "Войти в Лигу", prev: "Предыдущая", next: "Следующая", close: "Закрыть",
    whatTitle: "Что такое Лига",
    what: ["Лига объединяет музыкантов, играющих на инструментах одного семейства.", "Их семь, по семействам: щипковые и смычковые струнные, клавишные, духовые, ударные, электроника и вокал.", "Лигу определяет ваш инструмент. Гитара — щипковый струнный, поэтому гитарист — в Лиге струны.", "Каждая Лига выбирает свою эмблему."],
    whatRead: "Как читать круг",
    whatCircle: "В центре — Золотая лира, Конвенция. Золотые нити связывают с ней каждую Лигу и соседние Лиги между собой.",
    about: "Souls of Muse — свободное объединение музыкантов, хранящих живую музыку.",
    nameLabel: "Ваше имя", namePh: "Введите имя", cancel: "Отмена",
    thanks: "Подписано.", sub: "Ваша музыкальная подпись", savedHere: "Сохранено на этом устройстве.", signAgain: "Подписать другим именем",
    noNotes: "Введите имя буквами — оно будет записано нотами.",
  },
};
const LANGS = [["en", "English"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"], ["pt", "Português"], ["it", "Italiano"], ["ja", "日本語"], ["ko", "한국어"], ["zh", "中文"], ["hi", "हिन्दी"], ["vi", "Tiếng Việt"], ["kk", "Қазақша"], ["ru", "Русский"], ["uk", "Українська"], ["pl", "Polski"], ["tr", "Türkçe"], ["ar", "العربية"], ["id", "Bahasa Indonesia"], ["th", "ไทย"]];
const I18N = () => window.CONV_I18N || {};

/* Portal 2.1 (Claude Design, 4 Nov 2026): Nocturne night sky in layers, Muse on
   every screen, stone arches, seven coloured League spheres. */
Object.assign(T.en, {
  museName: "Muse", museIdle: "Sign with your name — I'll write it as music.",
  museForm: "Type it as you sign. Latin, Cyrillic, kana and hangul all work.",
  museDone: "Signed! Listen — this is your name in notes. ▶ plays it again.",
  museDoorL: "Seven Leagues behind this arch. Find yours by your instrument.",
  museDoorS: "Your space: sessions, practice plan, your League.",
  museLeagues: "Each colour is a League. Turn the circle, or pick one from the list.",
  legend: "Leagues by colour", autoRotate: "Rotate",
  whatCircle: "In the centre is the Golden Lyre, the Convention. Each League has its own colour; glowing threads link every League to the Lyre and to its neighbours.",
});
Object.assign(T.ru, {
  museName: "Muse", museIdle: "Подпишите своим именем — я запишу его нотами.",
  museForm: "Пишите, как подписываетесь. Латиница, кириллица, кана и хангыль — всё подходит.",
  museDone: "Подписано! Слушайте — это ваше имя нотами. ▶ сыграет ещё раз.",
  museDoorL: "За этой аркой семь Лиг. Найдите свою по инструменту.",
  museDoorS: "Ваше пространство: встречи, план практики, ваша Лига.",
  museLeagues: "Каждый цвет — Лига. Поверните круг или выберите из списка.",
  legend: "Лиги по цветам", autoRotate: "Вращение",
  whatCircle: "В центре — Золотая лира, Конвенция. У каждой Лиги свой цвет; светящиеся нити связывают каждую Лигу с лирой и с соседними Лигами.",
});
/* League colours (Portal 2.1 legend): Teal, Orchid, Sky, Mint, Apricot, Violet, Lime. */
const LCOL = ["#3ED0C8", "#DF86D7", "#86C5FA", "#6FDEA7", "#F6AB6B", "#AD8DFD", "#CCE170"];
const SAY = {
  en: ["Anything you pluck lives here: guitar, dombra, koto, ukulele.", "Strings that sing under a bow, from violin to kyl-kobyz.", "Piano, organ and synth share one keyboard and one League.", "Breath becomes sound here: flute, sax, brass, duduk.", "The pulse of every session: kit, hand drums, percussion.", "Producers and live-set players. A laptop is an instrument too.", "Your voice is the instrument, solo or in a choir."],
  ru: ["Всё, что щиплют, живёт здесь: гитара, домбра, кото, укулеле.", "Струны, которые поют под смычком, — от скрипки до кыл-кобыза.", "Фортепиано, орган и синтезатор: одна клавиатура, одна Лига.", "Здесь дыхание становится звуком: флейта, саксофон, медь, дудук.", "Пульс каждой встречи: установка, ручные барабаны, перкуссия.", "Продюсеры и лайв-сеты. Ноутбук — тоже инструмент.", "Ваш голос и есть инструмент — соло или в хоре."],
};
const MUSE = "assets/muse-cut.png";
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
const st = { menu: false, how: {}, sel: null, shut: ss.get("som_p20_shut", {}), signing: false, signMsg: "", draft: "", draftReading: "", conv: ss.get("som_conv_lang", null) };
const signedRec = () => { const r = ss.get("som_signed", null); return r && r.name && Array.isArray(r.notes) && r.notes.length ? r : null; };
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

/* Night sky in layers (stars, moon with thin gold rays, four cloud banks, floor
   grid or horizon rings, gold sparks). Each layer carries data-par = depth;
   startLoop() drifts it and leans it after the pointer. Sizes in vw keep the
   1440 composition on every width. */
const SKY = {};
function sky(kind) {
  if (SKY[kind]) return SKY[kind];
  let seed = kind === "home" ? 7 : 11;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  const vw = px => (px / 14.4).toFixed(2) + "vw";
  const stars = (d, size, count, tile, op) => {
    const g = []; for (let i = 0; i < count; i++) g.push(`radial-gradient(${size}px ${size}px at ${Math.round(rnd() * 100)}% ${Math.round(rnd() * 100)}%, var(--color-neutral-100), transparent)`);
    return `<div class="p21-stars" data-par="${d}" style="background-image:${g.join(",")};background-size:${tile};opacity:${op}"></div>`;
  };
  const C = (arr, k) => arr.map(([x, y, w, h]) => `<div class="p21-cloud ${k}" style="left:${x}%;top:${y}%;width:${vw(w)};height:${vw(h)}"></div>`).join("");
  const bank = (d, sp, off, inner) => `<div class="p21-bank" data-par="${d}" data-sp="${sp}" data-off="${off}">${inner}</div>`;
  const home = kind === "home", lx = home ? 80 : 82, ly = home ? 26 : 20;
  const sparks = (home ? [[62, 22, 3], [71, 14, 2], [84, 34, 2], [58, 40, 2], [90, 20, 3], [76, 44, 2], [66, 52, 2], [48, 30, 2], [94, 48, 2], [80, 8, 2]]
    : [[30, 20, 2], [62, 16, 3], [70, 30, 2], [38, 34, 2], [54, 8, 2], [22, 40, 2], [76, 12, 2]])
    .map(([x, y, z], i) => `<span class="p21-spark" style="left:${x}%;top:${y}%;--z:${z}px;animation-delay:${(-i * 0.73).toFixed(2)}s;animation-duration:${(2.6 + (i % 5) * 0.7).toFixed(1)}s"><i></i></span>`).join("");
  const rays = [-44, -26, -12, 2, 16, 34].map((a, i) => `<span class="p21-ray" style="height:${vw(380 + i * 60)};transform:rotate(${a}deg);opacity:${(0.22 + 0.06 * (i % 3)).toFixed(2)}"></span>`).join("");
  const rings = home ? [0, 1, 2, 3].map(i => `<div class="p21-hring" style="--w:${vw(1900 - i * 340)};--a:${10 + i * 5}%;--f:${6 + i * 3}%"></div>`).join("") : "";
  return (SKY[kind] = `<div class="p20-sky p21-sky p20-sky-${kind}" aria-hidden="true" data-sky>
    ${stars(0.04, 1.2, 14, "380px 280px", 0.5)}${stars(0.1, 1.8, 8, "620px 420px", 0.7)}
    <div class="p21-moon" data-par="0.12" style="left:${lx}%;top:${ly}%"><span class="p21-moonglow"></span>${rays}<span class="p21-moondisc"></span></div>
    ${bank(0.15, 0.03, 1, C([[4, 16, 900, 70], [52, 10, 760, 60], [30, 26, 600, 50]], "wisp"))}
    ${bank(0.28, 0.022, 2, C([[0, 52, 620, 150], [18, 49, 720, 170], [38, 53, 560, 140], [54, 48, 760, 180], [72, 51, 640, 150], [86, 47, 560, 140]], "far"))}
    ${home ? "" : `<div class="p21-bank" data-par="0.3"><div class="p21-floor"></div></div>`}${rings}
    ${bank(0.55, 0.016, 4, C([[-6, 62, 900, 230], [22, 64, 980, 250], [48, 60, 860, 230], [70, 63, 1000, 250]], "mid"))}
    ${bank(1, 0.012, 0, C([[-14, 78, 1200, 340], [20, 82, 1300, 360], [56, 79, 1200, 340], [84, 81, 1100, 330]], "near"))}
    ${sparks}
    <div class="p21-vignette"></div>
  </div>`);
}

/* Muse in the beret: the agent's image, never redrawn. Speech goes in a bubble. */
function museBox(text, cls) {
  return `<div class="p21-musebox ${cls || ""}">
    <img class="p21-muse" data-muse src="${MUSE}" alt="Muse" width="120" height="150">
    <div class="p21-bubble" role="note"><span class="p21-bk">${esc(t().museName)}</span><span class="p21-bt" data-muse-say aria-live="polite">${esc(text)}</span></div>
  </div>`;
}
function museIdleText() { return signedRec() ? t().museDone : st.signing ? t().museForm : t().museIdle; }

function convLang() { return st.conv && I18N()[st.conv] ? st.conv : null; }
function langMenu() {
  const tt = t(), cur = lang(), cl = convLang();
  return `<div class="p20-lang">
    <button class="p20-langbtn" data-p20-menu aria-haspopup="listbox" aria-expanded="${st.menu}"><i class="ph ph-globe-simple" aria-hidden="true"></i>${esc(cl ? I18N()[cl].name : tt.langName)}<i class="ph ph-caret-down" aria-hidden="true"></i></button>
    ${st.menu ? `<div class="p20-langlist" role="listbox" aria-label="${esc(tt.language)}">${LANGS.map(([code, label]) => {
      const avail = code === "en" || code === "ru" || !!I18N()[code], current = cl ? code === cl : code === cur;
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
  const tt = t(), P = window.P01, cl = convLang(), tr = cl ? I18N()[cl] : null, cv = tr || P.CONV[lang()], open = !!P.state.convOpen;
  const da = tr ? ` lang="${cl}" dir="${tr.dir}"` : "";
  return `<section class="p20-card p01-ent-card" aria-label="${esc(cv.title)}">
    <div class="p01-ent-cardhead"><img src="assets/lyre.png" alt="Golden Lyre"><h2${da}>${esc(cv.title)}</h2></div>
    ${tr ? `<p class="p20-trnote"${da}>${esc(tr.note)}</p>` : ""}
    <p class="p01-ent-first"${da}>${esc(cv.first)}</p>
    ${open ? cv.rest.map(p => `<p class="p01-ent-rest"${da}>${esc(p)}</p>`).join("") : ""}
    <button class="p01-ent-toggle" data-conv aria-expanded="${open}"><i class="ph ${open ? "ph-caret-up" : "ph-caret-down"}"></i>${esc(open ? cv.collapse : cv.readAll)}</button>
    ${signBlock()}
    ${signedRec() ? "" : `<div class="p01-ent-sig p20-example">
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
    </div>`}
  </section>`;
}

/* Signing: the personal musical signature exists only after the Convention is signed.
   Until sign-in with Meta and server storage are connected, the record stays on this device. */
function signBlock() {
  const tt = t(), rec = signedRec();
  if (rec) {
    const svg = window.SoulScoreSVG ? window.SoulScoreSVG(rec.notes) : "";
    return `<div class="p20-signed" role="status">
      <div class="p20-signedhead"><i class="ph ph-seal-check" aria-hidden="true"></i><span class="p20-thanks">${esc(tt.thanks)}</span></div>
      <span class="p20-sublabel">${esc(tt.sub)}</span>
      <div class="p20-score">${svg}</div>
      <div class="p01-ent-sigbar"></div>
      <div class="p01-ent-sigrow"><span class="p01-ent-cap">${esc(rec.name)}</span>
        <button class="p01-play p01-ent-play" data-p20-listen aria-label="${esc(tt.listen)}" aria-pressed="false"><i class="ph-fill ph-play"></i></button></div>
      <p class="p20-signnote"><i class="ph ph-device-mobile" aria-hidden="true"></i>${esc(tt.savedHere)} <button class="p20-link" data-p20-resign type="button">${esc(tt.signAgain)}</button></p>
    </div>`;
  }
  if (st.signing) {
    const P = (window.P01Strings && window.P01Strings.T && window.P01Strings.T[lang()]) || {};
    const needR = window.SoulSignature && window.SoulSignature.previewSignature(st.draft, "").has_han;
    return `<form class="p20-signform" data-p20-signform novalidate>
      <label class="p20-field"><span>${esc(tt.nameLabel)}</span><input id="p20Name" name="name" autocomplete="name" maxlength="80" placeholder="${esc(tt.namePh)}" value="${esc(st.draft)}" required></label>
      <label class="p20-field" id="p20ReadingWrap"${needR ? "" : " hidden"}><span>${esc(P.readingLabel || "")}</span><input id="p20Reading" name="reading" autocomplete="off" placeholder="${esc(P.readingPh || "")}" value="${esc(st.draftReading)}"></label>
      <p class="p20-signmsg" id="p20SignMsg" aria-live="polite">${esc(st.signMsg)}</p>
      <div class="p20-signrow"><button class="p20-sign" type="submit"><i class="ph ph-signature" aria-hidden="true"></i><span>${esc(tt.cta)}</span></button>
        <button class="p20-link" type="button" data-p20-cancel>${esc(tt.cancel)}</button></div>
    </form>`;
  }
  return `<div class="p20-signrow"><button class="p20-sign" id="p20Sign" type="button"><i class="ph ph-signature" aria-hidden="true"></i><span>${esc(tt.cta)}</span></button></div>`;
}

function door(kind, n) {
  const tt = t(), d = kind === "leagues" ? tt.doorL : tt.doorS, href = kind === "leagues" ? "#/leagues" : "#/space";
  /* Stone arch in depth: side walls, light inside, two leaves that swing open.
     The medal on the seam splits when the leaves open: seven League colours on
     the Leagues arch, a stave with a note on My space. Gold and red stay lines. */
  const medal = kind === "leagues"
    ? LCOL.map((c, i) => `<i class="p21-mdot" style="background:${c};transform:rotate(${Math.round(i * 360 / 7)}deg) translateY(calc(var(--w) * -.13))"></i>`).join("")
    : `<i class="p21-staff"></i><i class="p21-nhead"></i><i class="p21-stem"></i>`;
  const leaf = s => `<span class="p21-leaf ${s}"><span class="p21-leafline"></span><span class="p21-medal">${medal}</span></span>`;
  return `<a class="p20-door p21-arch" href="${href}" data-door="${kind}">
    <span class="p21-spill" aria-hidden="true"></span><span class="p21-shadow" aria-hidden="true"></span>
    <span class="p21-body" aria-hidden="true">
      <span class="p21-side l"></span><span class="p21-side r"></span>
      <span class="p21-frame"></span>
      <span class="p21-inner"><span class="p21-glow"></span><span class="p21-nest"></span><span class="p21-nest"></span><span class="p21-nest"></span></span>
      ${leaf("l")}${leaf("r")}
      <span class="p21-redline"></span>
    </span>
    <span class="p20-doorlabel"><span class="p21-lt"><span class="p20-n">${n}</span><span class="p20-doortitle">${esc(d.title)}</span></span><span class="p20-doorsub">${esc(d.sub)}</span><span class="p20-enter">${esc(d.enter)}<i class="ph ph-arrow-right" aria-hidden="true"></i></span></span>
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
  const anim = st.shutAnim === kind; if (anim) st.shutAnim = null;
  return `<aside class="p20-shutter${closed ? " closed" : ""}${anim ? " p20-anim" : ""}" aria-label="${esc(kind === "how" ? tt.tabHow : tt.tabWhat)}"${closed ? " hidden" : ""}>
      <div class="p20-shuthead"><span class="p20-kicker">${esc(tt.notesKicker)}</span><button class="p20-hide" data-shut="${kind}" type="button">${esc(tt.hideNotes)}<i class="ph ph-arrow-right" aria-hidden="true"></i></button></div>
      <div class="p20-shutbody"><h2>${esc(title)}</h2>${kind === "how" ? howBody() : whatBody()}</div>
    </aside>
    ${closed ? `<button class="p20-tab" data-unshut="${kind}" type="button"><i class="ph ph-arrow-left" aria-hidden="true"></i><span>${esc(kind === "how" ? tt.tabHow : tt.tabWhat)}</span></button>` : ""}`;
}

function home() {
  const tt = t();
  /* Portal 2.2: the promise runs across the top; the card and the two small arches
     share the left column (the arches always show in full, the card scrolls inside
     itself on short screens); Muse stands in the scene on the right. */
  return `<div class="p20 p21 p22 p20-home${st.shut.how ? " shut" : ""}">${sky("home")}${header()}
    <main id="main" tabindex="-1" class="p20-main">
      ${route(0)}
      <h1 class="p20-promise">${esc(tt.promise)}</h1>
      <div class="p20-homegrid">
        <div class="p20-left">${convCard()}
          <div class="p21-stagewrap"><span class="p21-plinth" aria-hidden="true"></span>
            <div class="p20-doors p21-doors">${door("leagues", "02")}${door("space", "03")}</div></div>
        </div>
        <div class="p21-right">${museBox(museIdleText(), "home")}</div>
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
  const ink = c => `color-mix(in oklch, ${c}, var(--color-bg) 78%)`;
  const card = sel == null ? "" : `<section class="p20-lcard" aria-live="polite" aria-label="${esc(L[sel].name)}" style="--c:${LCOL[sel]}">
      <div class="p20-lcardhead"><span class="p21-cardorb" aria-hidden="true"><i class="ph-fill ${L[sel].icon}" style="color:${ink(LCOL[sel])}"></i></span><span>${esc(L[sel].family)}</span><span class="p20-n">0${sel + 1} / 07</span><button class="p20-x" data-lsel="none" aria-label="${esc(tt.close)}"><i class="ph ph-x"></i></button></div>
      <h2>${esc(L[sel].name)}</h2><p>${esc(L[sel].instr)}</p>
      <div class="p21-cardmuse"><img class="p21-muse" data-muse src="${MUSE}" alt="Muse" width="48" height="60"><p><span class="p21-bk">${esc(tt.museName)}</span><span class="p21-bt" data-muse-say>${esc(SAY[lang()][sel])}</span></p></div>
      <div class="p20-lcardnav"><button class="p20-sq" data-lstep="-1" aria-label="${esc(tt.prev)}"><i class="ph ph-caret-left"></i></button>
        <a class="p20-gold" href="#/league/${L[sel].id}">${esc(tt.enterLeague)}<i class="ph ph-arrow-right" aria-hidden="true"></i></a>
        <button class="p20-sq" data-lstep="1" aria-label="${esc(tt.next)}"><i class="ph ph-caret-right"></i></button></div>
    </section>`;
  return `<div class="p20 p21 p20-leagues${st.shut.what ? " shut" : ""}">${sky("leagues")}${header()}
    <main id="main" tabindex="-1" class="p20-main">
      ${route(1)}
      <div class="p20-lside p20-lhead"><h1>${esc(tt.leaguesTitle)}</h1><p>${esc(tt.leaguesSub)}</p></div>
      <div class="p20-graph" data-graph tabindex="0" role="group" aria-label="${esc(tt.graphLabel)}">
        <svg class="p21-orbits" data-orbits aria-hidden="true"><path/><path/><path class="dash"/></svg>
        <button class="p21-auto${st.auto ? " on" : ""}" type="button" data-auto aria-pressed="${!!st.auto}"><i class="ph ph-arrows-clockwise" aria-hidden="true"></i><span>${esc(tt.autoRotate)}</span></button>
        ${[0, 1, 2, 3, 4, 5, 6].flatMap(i => [`<div class="p20-edge" data-edge data-a="h" data-b="${i}"></div>`, `<div class="p20-edge" data-edge data-a="${i}" data-b="${(i + 1) % 7}"></div>`]).join("")}
        <div class="p20-hub" data-hub><span><img src="assets/lyre.png" alt=""></span><em>${esc(tt.hubLabel)}</em></div>
        ${L.map((x, i) => `<button class="p20-node${sel === i ? " on" : ""}" data-node="${i}" tabindex="-1" aria-hidden="true" style="--c:${LCOL[i]}"><span class="p20-orb"><i class="ph-fill ${x.icon}" style="color:${ink(LCOL[i])}"></i></span><span class="p20-nname">${esc(x.name)}</span><span class="p20-nfam">${esc(x.family)}</span></button>`).join("")}
      </div>
      <div class="p20-lside p20-llist">
        <span class="p21-legend">${esc(tt.legend)}</span>
        <ul aria-label="${esc(tt.leaguesTitle)}">${L.map((x, i) => `<li><button data-lsel="${i}" aria-pressed="${sel === i}" style="--c:${LCOL[i]}"><span class="p20-n">0${i + 1}</span><span class="p21-ldot" aria-hidden="true"></span><span class="p20-lname">${esc(x.name)}</span><i class="ph ${x.icon}" aria-hidden="true"></i></button></li>`).join("")}</ul>
        ${sel == null ? `<p class="p21-ghint"><i class="ph ph-hand-grabbing" aria-hidden="true"></i><span class="p20-hintfull">${esc(tt.hint)}</span><span class="p20-hintm">${esc(tt.mHint)}</span></p>` : ""}
      </div>
      <div class="p20-lfoot">${sel == null ? museBox(tt.museLeagues, "leagues") : card}</div>
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
    const code = b.dataset.p20Lang;
    if (code === "en" || code === "ru") {
      st.conv = null;
      if (window.P01) { window.P01.state.lang = code; try { localStorage.setItem("som_p01_lang", code); } catch (e) {} }
    } else st.conv = code;
    ss.set("som_conv_lang", st.conv);
    keepScroll(rerender);
  });
  if (st.menu) on(document, "click", e => { if (!e.target.closest(".p20-lang")) { st.menu = false; rerender(); } });
  on(document, "keydown", e => { if (e.key === "Escape" && st.menu) { st.menu = false; rerender(); } });
  document.querySelectorAll("[data-how]").forEach(b => b.onclick = () => { const i = +b.dataset.how; st.how[i] = !st.how[i]; keepScroll(rerender); });
  document.querySelectorAll("[data-shut]").forEach(b => b.onclick = () => { st.shut[b.dataset.shut] = true; ss.set("som_p20_shut", st.shut); rerender(); const tab = document.querySelector("[data-unshut]"); if (tab) tab.focus(); });
  document.querySelectorAll("[data-unshut]").forEach(b => b.onclick = () => { st.shut[b.dataset.unshut] = false; st.shutAnim = b.dataset.unshut; ss.set("som_p20_shut", st.shut); rerender(); const h = document.querySelector("[data-shut]"); if (h) h.focus(); });
  document.querySelectorAll("[data-door]").forEach(a => a.onclick = e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1 || reduced()) return;
    e.preventDefault();
    const root = document.querySelector(".p20"); a.classList.add("go"); if (root) root.classList.add("leaving");
    setTimeout(() => { location.hash = a.getAttribute("href"); }, 760);
  });
  document.querySelectorAll("[data-door]").forEach(a => {
    const say = () => document.querySelector("[data-muse-say]");
    const inn = () => { const s = say(); if (s) s.textContent = a.dataset.door === "leagues" ? t().museDoorL : t().museDoorS; mz.lean = a.dataset.door === "leagues" ? -1 : -0.6; };
    const out = () => { const s = say(); if (s) s.textContent = museIdleText(); mz.lean = 0; };
    on(a, "mouseenter", inn); on(a, "focus", inn); on(a, "mouseleave", out); on(a, "blur", out);
  });
  document.querySelectorAll("[data-muse]").forEach(m => on(m, "click", () => { mz.joy = performance.now() / 1000; }));
  const sb = document.getElementById("p20Sign");
  if (sb) { on(sb, "mouseenter", () => { mz.lean = -0.8; }); on(sb, "mouseleave", () => { mz.lean = 0; }); }
  document.querySelectorAll("[data-lsel]").forEach(b => b.onclick = () => { const v = b.dataset.lsel; select(v === "none" ? null : +v, true); });
  document.querySelectorAll("[data-auto]").forEach(b => b.onclick = e => { e.stopPropagation(); st.auto = !st.auto; ss.set("som_p21_auto", st.auto);
    b.setAttribute("aria-pressed", String(st.auto)); b.classList.toggle("on", st.auto); });
  document.querySelectorAll("[data-lstep]").forEach(b => b.onclick = () => select(((st.sel == null ? 0 : st.sel) + +b.dataset.lstep + 7) % 7, true));
  bindSign();
  document.documentElement.lang = lang();
  startLoop();
}
function bindSign() {
  const tt = t();
  const open = document.getElementById("p20Sign");
  if (open) open.onclick = () => { st.signing = true; st.signMsg = ""; keepScroll(rerender); const n = document.getElementById("p20Name"); if (n) n.focus(); };
  const cancel = document.querySelector("[data-p20-cancel]");
  if (cancel) cancel.onclick = () => { st.signing = false; st.signMsg = ""; keepScroll(rerender); const b = document.getElementById("p20Sign"); if (b) b.focus(); };
  const name = document.getElementById("p20Name"), reading = document.getElementById("p20Reading");
  if (name) name.oninput = () => { st.draft = name.value; const w = document.getElementById("p20ReadingWrap");
    if (w && window.SoulSignature) w.hidden = !window.SoulSignature.previewSignature(name.value, "").has_han; };
  if (reading) reading.oninput = () => { st.draftReading = reading.value; };
  const form = document.querySelector("[data-p20-signform]");
  if (form) form.onsubmit = e => {
    e.preventDefault();
    const SS = window.SoulSignature, nm = (name && name.value || "").trim(), rd = (reading && !reading.closest("[hidden]") ? reading.value : "").trim();
    const P = (window.P01Strings && window.P01Strings.T && window.P01Strings.T[lang()]) || {};
    if (!SS || !nm) { st.signMsg = tt.noNotes; keepScroll(rerender); const n = document.getElementById("p20Name"); if (n) n.focus(); return; }
    const sig = SS.previewSignature(nm, rd);
    if (sig.need_reading) { st.draft = nm; st.signMsg = P.needReading || ""; keepScroll(rerender); const r = document.getElementById("p20Reading"); if (r) r.focus(); return; }
    if (!sig.notes.length) { st.draft = nm; st.signMsg = tt.noNotes; keepScroll(rerender); return; }
    ss.set("som_signed", { name: nm, reading: sig.reading, notes: sig.notes, algo: sig.algo_version, at: new Date().toISOString() });
    st.signing = false; st.signMsg = ""; st.draft = ""; st.draftReading = "";
    mz.joy = performance.now() / 1000;
    keepScroll(rerender);
    const l = document.querySelector("[data-p20-listen]"); if (l) l.focus();
  };
  const resign = document.querySelector("[data-p20-resign]");
  if (resign) resign.onclick = () => { try { localStorage.removeItem("som_signed"); } catch (x) {} st.signing = true; keepScroll(rerender); const n = document.getElementById("p20Name"); if (n) n.focus(); };
  const listen = document.querySelector("[data-p20-listen]");
  if (listen) listen.onclick = () => { const rec = signedRec(); if (rec) playNotes(rec.notes, listen); };
}
let actx = null, voices = [], playT = null;
function stopNotes() { voices.forEach(o => { try { o.stop(); } catch (e) {} }); voices = []; if (playT) { clearTimeout(playT); playT = null; }
  document.querySelectorAll("[data-p20-listen]").forEach(b => { b.setAttribute("aria-pressed", "false"); b.innerHTML = '<i class="ph-fill ph-play"></i>'; }); }
function playNotes(notes, btn) {
  if (voices.length) { stopNotes(); return; }
  const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
  actx = actx || new AC(); if (actx.state === "suspended") actx.resume();
  const beat = 60 / 92; let when = actx.currentTime + 0.05;
  const master = actx.createGain(); master.gain.value = 0.22; master.connect(actx.destination);
  notes.forEach(n => {
    const d = n.dur * beat, f = 440 * Math.pow(2, (n.midi - 69) / 12);
    [["triangle", 1], ["sine", .5]].forEach(([type, amp], k) => {
      const o = actx.createOscillator(), g = actx.createGain();
      o.type = type; o.frequency.value = f * (k ? 2 : 1);
      g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(amp * (k ? .25 : 1), when + .015);
      g.gain.exponentialRampToValueAtTime(0.001, when + Math.max(d * .95, .18));
      o.connect(g); g.connect(master); o.start(when); o.stop(when + d + .05); voices.push(o);
    });
    when += d;
  });
  if (btn) { btn.setAttribute("aria-pressed", "true"); btn.innerHTML = '<i class="ph-fill ph-stop"></i>'; }
  playT = setTimeout(stopNotes, (when - actx.currentTime) * 1000 + 150);
}
function keepScroll(fn) { const y = window.scrollY; fn(); window.scrollTo(0, y); }
/* Orbit state: yaw (th), pitch (ph), roll (ro), with inertia (v, vp). The circle turns
   in any direction: drag sideways, up/down or diagonally; on its own it drifts in a
   slow, changing pattern (yaw with a breathing pitch and a light roll). */
const g = { th: 0.5, ph: -0.36, ro: 0, v: 0, vp: 0, pend: 0, pendP: 0, snap: false, drag: false, lx: 0, ly: 0, moved: 0, hover: false, hi: null };
st.auto = ss.get("som_p21_auto", true);
const mz = { lean: 0, joy: -9, px: 0, py: 0, mx: null, my: null, r: 0 };
function select(i, snap) {
  st.sel = i; g.snap = snap && i != null;
  if (i != null) mz.joy = performance.now() / 1000;
  const y = window.scrollY; rerender(); window.scrollTo(0, y);
  if (i != null) { const b = document.querySelector(`[data-lsel="${i}"]`); if (b) b.focus({ preventScroll: true }); }
}

/* one clock for the whole visit: re-renders (language, signing, notes) must not
   make the clouds or the circle jump back to their starting positions */
let skyT = 0;
function startLoop() {
  const graph = document.querySelector("[data-graph]");
  const layers = [...document.querySelectorAll("[data-sky] [data-par]")];
  const muses = [...document.querySelectorAll("[data-muse]")];
  if (!graph && !layers.length) return;
  on(window, "pointermove", e => { mz.mx = e.clientX; mz.my = e.clientY; }, { passive: true });
  on(document, "pointerleave", () => { mz.mx = null; });
  if (graph) {
    on(graph, "pointerdown", e => { if (e.target.closest("[data-auto]")) return; g.drag = true; g.lx = e.clientX; g.ly = e.clientY; g.moved = 0; g.snap = false; try { graph.setPointerCapture(e.pointerId); } catch (x) {} });
    on(graph, "pointermove", e => { if (!g.drag) return; const dx = e.clientX - g.lx, dy = e.clientY - g.ly; g.lx = e.clientX; g.ly = e.clientY; g.moved += Math.abs(dx) + Math.abs(dy);
      g.th += dx * 0.006; g.ph -= dy * 0.006; g.v = reduced() ? 0 : dx * 0.0036; g.vp = reduced() ? 0 : -dy * 0.0036; });
    const up = e => { if (!g.drag) return; g.drag = false;
      if (g.moved < 6) { const n = document.elementsFromPoint(e.clientX, e.clientY).find(x => x.dataset && x.dataset.node != null); if (n) select(+n.dataset.node, true); } };
    on(graph, "pointerup", up); on(graph, "pointercancel", () => { g.drag = false; });
    on(graph, "mouseenter", () => { g.hover = true; }); on(graph, "mouseleave", () => { g.hover = false; g.hi = null; });
    on(graph, "pointerover", e => { const n = e.target.closest && e.target.closest("[data-node]"); g.hi = n ? +n.dataset.node : null; });
    on(graph, "keydown", e => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); g.snap = false; g.pend += (e.key === "ArrowRight" ? 1 : -1) * TAU / 7; }
      if (e.key === "ArrowUp" || e.key === "ArrowDown") { e.preventDefault(); g.snap = false; g.pendP += (e.key === "ArrowUp" ? -1 : 1) * 0.45; }
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(frontIndex(), true); }
    });
  }
  let last = performance.now();
  const tick = now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now; const R = reduced();
    if (!document.hidden) {
      if (!R) skyT += dt;
      paintSky(layers, muses, skyT, R);
      if (graph) paintGraph(graph, dt, R, skyT);
    }
    raf = requestAnimationFrame(tick);
  };
  paintSky(layers, muses, skyT, reduced());
  raf = requestAnimationFrame(tick);
}
/* Depth: each layer drifts on its own and leans away from the pointer by its depth.
   Phones get half the movement; reduced motion keeps the sky still. */
function paintSky(layers, muses, t, R) {
  const W = innerWidth, H = innerHeight, calm = W < 900 ? 0.5 : 1;
  const tx = R || mz.mx == null ? 0 : (mz.mx / W - 0.5) * 2, ty = R || mz.my == null ? 0 : (mz.my / H - 0.5) * 2;
  mz.px += (tx - mz.px) * 0.06; mz.py += (ty - mz.py) * 0.06;
  layers.forEach(el => { const d = +el.dataset.par, sp = +(el.dataset.sp || 0), off = +(el.dataset.off || 0);
    const dx = R ? 0 : Math.sin(t * sp + off) * 70 * d * calm;
    el.style.transform = `translate3d(${(dx - mz.px * 36 * d * calm).toFixed(1)}px,${(-mz.py * 16 * d * calm).toFixed(1)}px,0)`; });
  const now = performance.now() / 1000;
  muses.forEach(el => {
    if (R) { el.style.transform = "none"; return; }
    const target = mz.lean || mz.px * 0.5;
    mz.r += (target - mz.r) * 0.1;
    const j = now - mz.joy < 1.6 ? 1 - (now - mz.joy) / 1.6 : 0;
    const y = Math.sin(t * 1.2) * 5 * calm - Math.abs(Math.sin(t * 9)) * 16 * j;
    const rot = mz.r * 7 + Math.sin(t * 13) * 9 * j;
    el.style.transform = `perspective(500px) translateY(${y.toFixed(1)}px) rotateY(${(mz.r * 22).toFixed(1)}deg) rotate(${rot.toFixed(1)}deg) scale(${(1 + 0.06 * j).toFixed(3)})`;
  });
}
let lastPts = null;
function frontIndex() { if (!lastPts) return 0; let b = 0; lastPts.forEach((p, i) => { if (p.k > lastPts[b].k) b = i; }); return b; }
/* Seven Leagues on a sphere around the Golden Lyre: longitude by order,
   latitude from YS, so the ring of neighbours stays readable from any side. */
const BASE = YS.map((y, i) => { const lon = i * TAU / 7, lat = (y / 100) * 0.9; return [Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon)]; });
const wrapA = d => ((d % TAU) + TAU * 1.5) % TAU - Math.PI;
function paintGraph(el, dt, R, t) {
  const sel = st.sel, narrow = el.clientWidth < 700;
  const W = el.clientWidth, side = narrow ? 0 : 330;
  const r = narrow ? Math.min(150, W * 0.36) : Math.max(150, Math.min(260, (W - side) / 2 - 110)), F = 900;
  const cx = narrow ? W / 2 : (side + W) / 2, cy = el.clientHeight * 0.47;
  if (!g.drag) {
    if (g.snap && sel != null) {
      /* bring the chosen League to the front, a little above the Lyre */
      const [x, y, z] = BASE[sel], tt = Math.atan2(x, -z), tp = Math.atan2(-y, Math.hypot(x, z)) - 0.42;
      const d1 = wrapA(tt - g.th), d2 = wrapA(tp - g.ph), d3 = wrapA(-g.ro), f = R ? 1 : Math.min(1, dt * 5);
      g.th += d1 * f; g.ph += d2 * f; g.ro += d3 * f; g.v = g.vp = 0;
      if (Math.abs(d1) + Math.abs(d2) + Math.abs(d3) < 0.001) g.snap = false;
    } else {
      if (g.pend) { const s = R ? g.pend : g.pend * Math.min(1, dt * 6); g.th += s; g.pend -= s; if (Math.abs(g.pend) < 1e-4) g.pend = 0; }
      if (g.pendP) { const s = R ? g.pendP : g.pendP * Math.min(1, dt * 6); g.ph += s; g.pendP -= s; if (Math.abs(g.pendP) < 1e-4) g.pendP = 0; }
      g.th += g.v; g.ph += g.vp; g.v *= 0.94; g.vp *= 0.94; if (Math.abs(g.v) < 1e-5) g.v = 0; if (Math.abs(g.vp) < 1e-5) g.vp = 0;
      if (!R && sel == null && st.auto) {
        /* drift: steady yaw that speeds and slows, pitch that swings past the poles and back, light roll */
        const k = g.hover ? 0.25 : 1;
        g.th += dt * k * (0.17 + 0.09 * Math.sin(t * 0.13));
        g.ph += dt * k * 0.11 * Math.sin(t * 0.071 + 0.7);
        g.ro += dt * k * (0.24 * Math.sin(t * 0.05) - g.ro) * 0.5;
      }
    }
  }
  const c = Math.cos(g.th), s = Math.sin(g.th), cp = Math.cos(g.ph), sp = Math.sin(g.ph), cr = Math.cos(g.ro), sr = Math.sin(g.ro);
  const P = (x, y, z) => { const x1 = x * c + z * s, z1 = -x * s + z * c, y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    const x3 = x1 * cr - y2 * sr, y3 = x1 * sr + y2 * cr, k = F / (F + z2); return { x: cx + x3 * k, y: cy + y3 * k, k, z: z2 }; };
  /* spheres float: each bobs on its own phase */
  const pts = BASE.map(([x, y, z], i) => { const b = R ? 0 : Math.sin(t * 0.9 + i * 1.3) * 9; return P(x * r, y * r + b, z * r); });
  lastPts = pts;
  const hub = P(0, 0, 0), kmin = F / (F + r), kmax = F / (F - r);
  const dep = p => Math.max(0, Math.min(1, (p.k - kmin) / (kmax - kmin)));
  const sc = narrow ? 0.72 : 1;
  /* orbit lines: equator, one meridian and an inner ring, re-projected every frame */
  const orb = el.querySelector("[data-orbits]");
  if (orb) {
    orb.setAttribute("viewBox", `0 0 ${W} ${el.clientHeight}`);
    const ring = (f, fn) => { let d = ""; for (let j = 0; j <= 64; j++) { const a = j * TAU / 64, q = fn(Math.cos(a) * r * f, Math.sin(a) * r * f); d += (j ? "L" : "M") + q.x.toFixed(1) + " " + q.y.toFixed(1); } return d; };
    const paths = orb.querySelectorAll("path");
    paths[0].setAttribute("d", ring(1, (a, b) => P(a, 0, b)));
    paths[1].setAttribute("d", ring(1, (a, b) => P(0, a, b)));
    paths[2].setAttribute("d", ring(0.55, (a, b) => P(a, 0, b)));
  }
  el.querySelectorAll("[data-node]").forEach(n => { const i = +n.dataset.node, p = pts[i], dim = sel != null && sel !== i;
    n._h = (n._h || 0) + ((g.hi === i ? 1 : 0) - (n._h || 0)) * (R ? 1 : 0.18);
    n.style.transform = `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) translate(-50%,-32%) scale(${(p.k * sc * (1 + 0.16 * n._h)).toFixed(3)})`;
    n.style.zIndex = String(Math.round(1000 - p.z)); n.style.opacity = (dim && g.hi !== i ? 0.38 : 0.62 + 0.38 * Math.max(dep(p), n._h)).toFixed(2); });
  const h = el.querySelector("[data-hub]"); if (h) { h.style.transform = `translate(${hub.x.toFixed(1)}px,${hub.y.toFixed(1)}px) translate(-50%,-40%) scale(${sc})`; h.style.zIndex = String(Math.round(1000 - hub.z)); }
  el.querySelectorAll("[data-edge]").forEach(e => { const a = e.dataset.a, b = +e.dataset.b, p = a === "h" ? hub : pts[+a], q = pts[b];
    const dx = q.x - p.x, dy = q.y - p.y, hot = sel != null && (b === sel || (a !== "h" && +a === sel)), dimE = sel != null && !hot;
    if (e.dataset.c !== "1") { const ca = a === "h" ? "var(--color-gold-400)" : LCOL[+a]; e.style.background = `linear-gradient(90deg,${ca},${LCOL[b]})`; e.dataset.c = "1"; }
    e.style.width = Math.hypot(dx, dy).toFixed(1) + "px";
    e.style.transform = `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) rotate(${Math.atan2(dy, dx).toFixed(4)}rad)`;
    const d = (dep(q) + (a === "h" ? 0.6 : dep(p))) / 2;
    e.style.opacity = (hot ? 1 : dimE ? 0.14 : (a === "h" ? 0.34 : 0.22) + 0.46 * d).toFixed(2);
    e.style.height = hot ? "2px" : "1px";
    e.style.boxShadow = hot ? `0 0 10px ${LCOL[b]}` : `0 0 5px color-mix(in oklch, ${LCOL[b]} 50%, transparent)`;
    e.style.zIndex = String(Math.round(1000 - Math.max(p.z, q.z)) - 2); });
}
function stop() {
  stopNotes();
  if (raf) { cancelAnimationFrame(raf); raf = null; }
  offs.forEach(f => f()); offs = [];
}
function reset() { st.menu = false; }
window.Portal20 = { home, leagues, bind, stop, reset, T };
})();
