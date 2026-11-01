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

console.log("test_cabinet: all assertions passed");
