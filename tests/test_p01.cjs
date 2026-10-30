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
for (const a of ["lyre.png", "medal-playful.png", "medal-classic.png", "frame-classic.png", "muse-badge.png", "baton.svg",
  "sig-latin.png", "sig-cyrillic.png", "sig-viet.png", "sig-korean.png", "sig-japanese.png", "sig-short.png"]) {
  assert.ok(fs.existsSync(path.join(web, "assets", a)), `asset ${a}`);
}

// honest states: audio only behind a click handler; vote never presented as open
assert.match(p01, /data-p01-play/);
assert.ok(!/AudioContext\(\)[^]*autoplay/.test(p01));
assert.match(S.T.en.chipNotOpen, /not open yet/);
assert.match(S.T.ru.chipVote, /ещё не открыто/);
console.log("test_p01: all assertions passed");
