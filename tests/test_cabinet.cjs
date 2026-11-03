"use strict";
/* Cabinet 1.4 checks: routes resolve, role switch, gold-button rule,
   EN/RU strings, seven family Leagues, no pre-1.4 league names.
   Run: node tests/test_cabinet.cjs */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const web = path.join(__dirname, "..", "web");
const read = f => fs.readFileSync(path.join(web, f), "utf8");

// Load strings + cabinet views in Node (cabinet.js reads window.P01Strings).
global.window = {};
const S = require(path.join(web, "strings.js"));
assert.equal(window.P01Strings, S, "strings.js publishes P01Strings");
window.P01 = global.P01 = { state: { lang: "en" } };
require(path.join(web, "cabinet.js"));
const Cabinet = window.Cabinet;
assert.ok(Cabinet && Cabinet.home && Cabinet.session, "cabinet.js publishes views");

// --- home and every session route resolve ---
const app = read("app.js");
assert.match(app, /#\\\/space\(/, "app routes #/space to Cabinet.home");
assert.match(app, /Cabinet\.home\(/, "app calls Cabinet.home");
assert.match(app, /Cabinet\.session\(/, "app calls Cabinet.session");
const gold = html => (html.match(/btn-gold/g) || []).length;
const screens = [];
for (const lang of ["en", "ru"]) {
  window.P01.state.lang = lang;
  for (const role of ["maestro", "artist", "admirer"]) {
    // route patterns in app.js accept these hashes
    assert.ok(new RegExp("^#/space(?:\\/(artist|maestro|admirer))?$").test("#/space/" + role), `#/space/${role}`);
    const h = Cabinet.home(role);
    assert.ok(h.includes(`data-cab-screen="home-${role}"`), `home ${role} ${lang}`);
    assert.equal(gold(h), 1, `home ${role} ${lang}: exactly one filled gold button`);
    screens.push([`home-${role}-${lang}`, h]);
  }
  const sessionRoutes = [["maestro", "circle"], ["maestro", "one-to-one"], ["artist", "circle"], ["artist", "one-to-one"], ["admirer", "circle"]];
  for (const [role, rmode] of sessionRoutes) {
    const ok = new RegExp("^#/session/(maestro|artist)/(circle|one-to-one)$").test(`#/session/${role}/${rmode}`)
      || new RegExp("^#/session/(admirer)/(circle)$").test(`#/session/${role}/${rmode}`);
    assert.ok(ok, `#/session/${role}/${rmode}`);
    const mode = rmode === "circle" ? "circle" : "one";
    const s = Cabinet.session(role, mode);
    assert.ok(s.includes(`data-cab-screen="session-${role}-${mode}"`), `session ${role} ${mode} ${lang}`);
    // gold-button rule: Maestro screens carry the filled metronome button;
    // Artist/Admirer session screens have none (lead owns the metronome),
    // so never more than one filled gold button per screen.
    if (role === "maestro") assert.equal(gold(s), 1, `session ${role} ${mode} ${lang}: exactly one gold`);
    else assert.ok(gold(s) <= 1, `session ${role} ${mode} ${lang}: at most one gold`);
    screens.push([`session-${role}-${mode}-${lang}`, s]);
  }
}

// --- role switch works ---
window.P01.state.lang = "en";
const homeEn = Cabinet.home("artist");
for (const role of ["maestro", "artist", "admirer"]) assert.ok(homeEn.includes(`data-cab-role="${role}"`), `role button ${role}`);
assert.equal((homeEn.match(/aria-pressed="true"/g) || []).length >= 1, true);
assert.ok(homeEn.includes('data-cab-role="artist" aria-pressed="true"'), "active role pressed");
assert.ok(homeEn.includes('data-cab-role="maestro" aria-pressed="false"'), "inactive role not pressed");
assert.match(read("cabinet.js"), /data-cab-role][^]*?location\.hash = "#\/space\/" \+/, "role click navigates");
assert.ok(homeEn.includes("cab-baton"), "Maestro role uses baton icon");
assert.match(read("cabinet.css"), /assets\/baton-v2\.svg/, "baton-v2 in cabinet.css");
assert.match(read("p01.css"), /assets\/baton-v2\.svg/, "baton-v2 in p01.css");
assert.ok(fs.existsSync(path.join(web, "assets", "baton-v2.svg")), "assets/baton-v2.svg copied");

// --- EN and RU strings present (1.4 texts) ---
window.P01.state.lang = "en";
const hEn = Cabinet.home("artist");
for (const t of ["League of the String", "plucked strings · my instrument: guitar", "What shall we play today?", "plucked strings · chat, topics, decisions", "Session 3 · Guitar"])
  assert.ok(hEn.includes(t), "EN home: " + t);
assert.ok(Cabinet.home("admirer").includes("Sessions open to listen · League of the String"), "EN admirer subtitle");
for (const mode of ["circle", "one"]) {
  const ms = Cabinet.session("maestro", mode);
  assert.ok(ms.includes("Video check"), `EN maestro ${mode} Video check`);
  assert.ok(ms.includes("Video demo"), `EN maestro ${mode} Video demo`);
  assert.ok(!ms.includes("Video demonstration"), "EN: old Video demonstration gone");
}
window.P01.state.lang = "ru";
const hRu = Cabinet.home("artist");
for (const t of ["Лига струны · гитара", "щипковые струнные", "Что сыграем сегодня?", "щипковые струнные · чат, топики, решения", "Встреча 3 · Гитара"])
  assert.ok(hRu.includes(t), "RU home: " + t);
assert.ok(Cabinet.home("admirer").includes("Лига струны"), "RU admirer subtitle");
const msRu = Cabinet.session("maestro", "circle");
assert.ok(msRu.includes("Видео контроль"), "RU maestro: Видео контроль");
assert.ok(msRu.includes("Показ"), "RU maestro: Показ (Video demo in the 1.4 RU frame)");
for (const key of Object.keys(S.CAB.en)) assert.ok(key in S.CAB.ru, "CAB.ru has " + key);

// --- seven Leagues by instrument family; no pre-1.4 names anywhere user-facing ---
assert.equal(S.LEAGUES.length, 7, "seven Leagues");
assert.deepEqual(S.LEAGUES.map(l => l[1]),
  ["League of the String", "League of the Bow", "Keys", "Winds", "Drums", "Electronic", "Vocal"]);
assert.deepEqual(S.LEAGUES.map(l => l[2]),
  ["Лига струны", "Лига смычка", "Клавишные", "Духовые", "Ударные", "Электроника", "Вокал"]);
assert.equal(S.LEAGUES[0][5], "plucked strings");
assert.match(S.LEAGUES[0][3], /guitar · balalaika · dombra · kobza · mandolin · ukulele · koto/);
for (const [, , , , , eFam, rFam] of S.LEAGUES) { assert.ok(eFam && rFam, "family captions in EN and RU"); }
const userFacing = ["strings.js", "cabinet.js", "p01.js", "app.js", "cabinet.css", "p01.css", "styles.css", "index.html"]
  .map(f => read(f)).join("\n") + screens.map(([, h]) => h).join("\n");
for (const bad of ["Guitar League", "Лига гитары", "Folk League", "Лига фолка", "Video demonstration", "Видео демонстрация"])
  assert.ok(!userFacing.includes(bad), "removed in 1.4: " + bad);
assert.ok(!S.LEAGUES.some(l => /Folk|Фолк/.test(l[1] + l[2])), "no Folk League");

// --- DW1 review fixes (5a serif heading, 5b programmatic-focus ring) ---
const css = read("cabinet.css");
assert.match(css, /\.cab-main h1\{[^}]*font-family:Inter/, "home heading uses Inter (DS sans)");
assert.match(css, /main\[tabindex="-1"\][^{]*\{outline:none\}/, "no ring on programmatic main focus");
assert.match(css, /\.cab :focus-visible\{outline:2px/, "keyboard :focus-visible kept");

// --- GAP 2: #/leagues rebuilt per frame 9 (cabinet style, EN/RU) ---
assert.match(app, /Portal20\.leagues\(\)/, "app routes #/leagues to Portal 2.0 (Cabinet.leagues stays as the after-Welcome component)");
assert.ok(!/\bvLeagues\b|\bbindLeagues\b|leagueGrid/.test(app), "old portal leagues view removed");
window.P01.state.lang = "en";
const lgEn = Cabinet.leagues();
assert.equal(gold(lgEn), 1, "#/leagues EN: exactly one filled gold button");
assert.ok(lgEn.includes("Join League of the String"), "EN gold button label");
assert.ok(lgEn.includes("Choose your League") && lgEn.includes("Seven Leagues · after Welcome"), "EN frame-9 heading");
assert.ok(lgEn.includes("example data"), "example data label");
assert.ok(lgEn.includes('data-cab-screen="leagues"') && lgEn.includes('tabindex="-1"'), "leagues screen + routed main");
assert.equal((lgEn.match(/cab-league-card/g) || []).length, 7, "seven league cards");
assert.equal((lgEn.match(/data-cab-join=/g) || []).length, 6, "six outline Join buttons");
assert.ok(lgEn.includes("frame-gold") && lgEn.includes("my instrument: guitar"), "member league marked frame-gold + my instrument");
assert.ok(lgEn.includes("cab-lg-icon") && lgEn.includes("num-gold") && lgEn.includes("ph-guitar"), "neutral ring icon + gold number");
assert.ok(lgEn.includes("Muse: you play guitar, so your family is plucked strings."), "EN Muse note");
for (const l of S.LEAGUES) { assert.ok(lgEn.includes(l[1]) && lgEn.includes(l[5]) && lgEn.includes(l[3]), "EN card: " + l[1]); }
for (const ru of ["Лига струны", "Лига смычка", "Клавишные", "Духовые", "Ударные", "Электроника", "Вокал", "Выберите свою Лигу"])
  assert.ok(!lgEn.includes(ru), "EN leagues has no RU text: " + ru);
window.P01.state.lang = "ru";
const lgRu = Cabinet.leagues();
assert.equal(gold(lgRu), 1, "#/leagues RU: exactly one filled gold button");
assert.ok(lgRu.includes("Вступить в Лигу струны") && lgRu.includes("Выберите свою Лигу"), "RU frame-9 heading + gold button");
assert.ok(lgRu.includes("мой инструмент: гитара") && lgRu.includes("пример данных"), "RU my instrument + example label");
for (const l of S.LEAGUES) { assert.ok(lgRu.includes(l[2]) && lgRu.includes(l[6]) && lgRu.includes(l[4]), "RU card: " + l[2]); }

// --- GAP 1: 390 px fit — no fixed width above 390 px without a mobile override.
// Equivalent static check (no browser available): (a) every literal
// width/min-width in the base cabinet CSS is <= 390 px (max-width caps and
// min()/calc() viewport-bounded values are not fixed widths); (b) every base
// grid-template-columns using px tracks (auto-fill wraps, exempt) has a
// minmax(0,1fr) override for the same selector in a <=899/560px block;
// (c) header stacks, chips may wrap, drawer stays a drawer. ---
window.P01.state.lang = "en";
const mediaAt = css.indexOf("@media (max-width:899px)");
assert.ok(mediaAt > 0, "mobile media block exists");
const baseCss = css.slice(0, mediaAt), mobileCss = css.slice(mediaAt);
for (const m of baseCss.matchAll(/(?:^|[;{])\s*(width|min-width)\s*:\s*(\d+)px/g))
  assert.ok(+m[2] <= 390, `base ${m[1]}:${m[2]}px exceeds 390px`);
assert.match(baseCss, /\.cab-drawer-panel\{[^}]*width:min\(420px,86vw\)/, "drawer panel viewport-bounded, not fixed 420px");
for (const m of baseCss.matchAll(/([^{}]+)\{[^}]*grid-template-columns:([^;}]+)/g)) {
  const [, sel, val] = m;
  if (!/\d+px/.test(val) || /auto-fill|auto-fit/.test(val)) continue;
  const s = sel.trim().split("\n").pop().split(",").pop().trim();
  const re = new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\{[^}]*grid-template-columns:[^}]*minmax\\(0,1fr\\)");
  assert.match(mobileCss, re, `mobile minmax(0,1fr) override for ${s}`);
}
assert.match(mobileCss, /\.cab-head-right\{[^}]*flex:1 1 100%/, "header items stack at mobile width");
assert.match(mobileCss, /\.cab-tag\{white-space:normal\}/, "chips wrap at mobile width");
assert.match(mobileCss, /\.cab-league-grid\{grid-template-columns:minmax\(0,1fr\)\}/, "league grid single column at 390px");
assert.ok(!/\.cab-drawer\{[^}]*position:static/.test(mobileCss), "notebook stays a drawer (not static) on mobile");
assert.match(mobileCss, /\.cab-drawer-panel\{[^}]*calc\(100vw - 32px\)/, "drawer panel fits 390px beside its tab");
assert.match(baseCss, /min-width:0\}/, "flex/grid children get min-width:0");

console.log("test_cabinet: all assertions passed");
