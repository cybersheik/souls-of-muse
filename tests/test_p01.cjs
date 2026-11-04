"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const web = path.join(__dirname, "..", "web");
const read = f => fs.readFileSync(path.join(web, f), "utf8");

// strings.js loads in Node (UMD export)
const S = require(path.join(web, "strings.js"));
assert.equal(S.T.en.roleT, "Maestro");
assert.equal(S.T.en.roleS, "Artist");
assert.equal(S.T.en.roleL, "Admirer");
assert.equal(S.T.ru.roleT, "Маэстро");
assert.equal(S.T.ru.roleS, "Артист");
assert.equal(S.T.ru.roleL, "Ценитель");
assert.match(S.T.en.cta, /Choose your League and role/);
assert.match(S.ROLE.teacher.en.today.title, /Breath and the first phrase/);
assert.match(S.ROLE.listener.ru.today.title, /домбра/);
assert.equal(S.LEAGUES.length, 7);

// P0.1 vocabulary: no superseded role/lesson words in the strings file user text
const strings = read("strings.js");
for (const bad of ["Teacher", "Student", "Listener", "Lesson", "Учитель", "Ученик", "Слушатель", "Урок"]) {
  assert.ok(!strings.includes(bad), `superseded word leaked into strings.js: ${bad}`);
}

// files wired
const index = read("index.html"), app = read("app.js"), p01 = read("p01.js");
for (const f of ["strings.js", "p01.js", "p01.css"]) assert.ok(index.includes(f), `index loads ${f}`);
assert.match(app, /#\/space/);
assert.match(app, /#\/components/);
assert.match(app, /P01\.welcome\(\)/);

// assets from the P0.1 archive exist
for (const a of ["lyre.png", "medal-playful.png", "medal-classic.png", "frame-classic.png", "muse-badge.png", "baton.svg", "baton-v2.svg",
  "sig-latin.png", "sig-cyrillic.png", "sig-viet.png", "sig-korean.png", "sig-japanese.png", "sig-short.png"]) {
  assert.ok(fs.existsSync(path.join(web, "assets", a)), `asset ${a}`);
}

// honest states: audio only behind a click handler; vote never presented as open
assert.match(p01, /data-p01-play/);
assert.ok(!/AudioContext\(\)[^]*autoplay/.test(p01));
assert.match(S.T.en.chipNotOpen, /not open yet/);
assert.match(S.T.ru.chipVote, /ещё не открыто/);
// Entrance v4 home + DW1 corrections (navigation / roles / inline CTA)
assert.match(p01, /P01 = \{ entrance/, "entrance view exported");
assert.match(app, /P01\.entrance\(\)/, "root and convention route to Entrance v4");
assert.match(app, /navConv/, "chrome nav uses Convention · Leagues · My space");
assert.ok(!app.includes("Student/Teacher") && !app.includes('data-role='), "no global Student/Teacher/Listener switch");
assert.match(p01, /ph-music-notes/, "Artist role uses paired music notes");
assert.ok(!p01.includes('"student", tt.roleS, "ph-microphone"'), "Artist is not a microphone (reserved for Vocal League)");
assert.match(read("p01.css"), /baton-v2\.svg/, "Maestro uses the Cabinet 1.4 baton-v2 asset (mask over assets/baton-v2.svg)");
assert.ok(!strings.includes("ph-feather") && !p01.includes("ph-feather"), "no feather/leaf emblem");
// Cabinet 1.4: the Folk League and its dombra emblem were intentionally removed;
// folk instruments join their family (dombra/kobza/koto -> plucked strings).
assert.ok(!p01.includes("DOMBRA_SVG"), "Folk dombra emblem removed with the Folk League in 1.4");
const p01css = read("p01.css");
assert.match(p01css, /\.p01-cta\{[^}]*height:60px/, "Welcome desktop CTA is 60px, content width, left aligned");
// Cabinet 1.3/1.4: the P0.1 Personal-space grid (incl. the 360px Artist Today
// right column) was intentionally replaced by the Cabinet home; p01.css now
// keeps the two-column space grid at 8fr/4fr.
assert.match(p01css, /\.p01-grid\{grid-template-columns:minmax\(0,8fr\) minmax\(0,4fr\)/, "space grid is 8fr/4fr after the Cabinet replacement");
assert.match(p01css, /1px solid var\(--p01-line\)/, "Ceremony divider #E3D8C2 line present");
console.log("test_p01: all assertions passed");
