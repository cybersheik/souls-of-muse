"use strict";
/* Portal 2.0 checks: Home (route, Convention card, two doors, notes shutter),
   Leagues (seven nodes + seven-item list), one filled gold button per screen,
   EN/RU, approved Convention text, launch wording. Run: node tests/test_portal20.cjs */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const web = path.join(__dirname, "..", "web");
const read = f => fs.readFileSync(path.join(web, f), "utf8");

global.window = {};
global.localStorage = { getItem: () => null, setItem: () => {} };
const S = require(path.join(web, "strings.js"));
const CONV = { en: { title: "Convention of the Keepers of Live Music", first: "EN-FIRST", rest: ["r1", "r2"], readAll: "Read the full Convention", collapse: "Collapse" },
  ru: { title: "Конвенция хранителей живой музыки", first: "RU-FIRST", rest: ["r1"], readAll: "Читать Конвенцию целиком", collapse: "Свернуть" } };
window.P01 = { state: { lang: "en", convOpen: false, sigPaused: false }, CONV };
require(path.join(web, "portal20.js"));
const P = window.Portal20;
assert.ok(P && P.home && P.leagues && P.bind && P.stop, "portal20.js publishes views");

const goldCount = h => (h.match(/class="p20-sign"|class="p20-gold"/g) || []).length;
for (const lang of ["en", "ru"]) {
  window.P01.state.lang = lang;
  const T = P.T[lang];
  const home = P.home();
  assert.ok(home.includes('class="p20-route"') && (home.match(/<li><a href=/g) || []).length === 3, `home route ${lang}`);
  assert.ok(home.includes('aria-current="page"') && home.includes(T.here), `home: You are here ${lang}`);
  assert.ok(home.includes('data-door="leagues"') && home.includes('data-door="space"'), `two doors ${lang}`);
  assert.ok(home.includes('href="#/leagues"') && home.includes('href="#/space"'), `door targets ${lang}`);
  assert.ok(home.includes('class="p20-shutter') && home.includes(T.howTitle), `notes shutter ${lang}`);
  assert.ok(home.includes(CONV[lang].title) && home.includes(CONV[lang].first), `Convention card uses the approved CONV text ${lang}`);
  assert.equal(goldCount(home), 1, `home ${lang}: exactly one filled gold button`);
  assert.ok(home.includes('id="p20Sign"') && home.includes(T.cta), `sign button ${lang}`);
  assert.ok(home.includes("data-sigline") && home.includes(T.exampleData), `example signature marked as example data ${lang}`);
  assert.ok(!home.includes("entName"), `no typed-name preview before signing ${lang}`);
  const lg = P.leagues();
  assert.equal((lg.match(/data-node="/g) || []).length, 7, `seven League nodes ${lang}`);
  assert.equal((lg.match(/data-lsel="\d"/g) || []).length, 7, `seven-item League list ${lang}`);
  assert.ok(lg.includes("data-graph") && lg.includes(T.graphLabel), `graph labelled ${lang}`);
  assert.ok(lg.includes(T.whatTitle), `What is a League shutter ${lang}`);
  assert.match(lg, /<details class="p20-mnotes">[\s\S]*?<summary>[\s\S]*?<\/summary>[\s\S]*?<\/details>/, `League explanation remains reachable when the desktop shutter is hidden ${lang}`);
  for (const L of S.LEAGUES) assert.ok(lg.includes(lang === "en" ? L[1] : L[2]), `League name ${L[1]} ${lang}`);
  assert.ok(goldCount(lg) <= 1, `leagues ${lang}: at most one filled gold button`);
  // Portal 2.1: Muse on both screens, seven League colours, arches with leaves
  assert.ok(home.includes("data-muse") && home.includes("data-muse-say") && home.includes(T.museIdle), `Muse greets on Home ${lang}`);
  assert.ok(lg.includes("data-muse") && lg.includes(T.museLeagues), `Muse on Leagues ${lang}`);
  assert.equal(new Set((lg.match(/data-node="\d" tabindex="-1" aria-hidden="true" style="--c:(#[0-9A-F]{6})/g) || [])).size, 7, `seven coloured spheres ${lang}`);
  assert.equal((home.match(/class="p21-leaf /g) || []).length, 4, `two arches with two leaves each ${lang}`);
}

// router wiring
const app = read("app.js");
assert.match(app, /\[\/\^#\?\\\/\?\$\/,\(\)=>Portal20\.home\(\)/, "#/ renders Portal 2.0 Home");
assert.match(app, /#\\\/convention\$\/,\(\)=>Portal20\.home\(\)/, "#/convention renders Portal 2.0 Home");
assert.match(app, /#\\\/leagues\$\/,\(\)=>Portal20\.leagues\(\)/, "#/leagues renders the League circle");
assert.match(read("index.html"), /portal20\.js/, "index.html loads portal20.js");
assert.match(read("index.html"), /portal20\.css[\s\S]*portal21\.css/, "Portal 2.1 styles load after 2.0");
assert.ok(fs.existsSync(path.join(web, "assets", "muse-cut.png")), "Muse image (background removed) is shipped");
assert.match(read("index.html"), /og:image" content="https:\/\/soulsofmuse\.app\/assets\/og-portal\.jpg"/, "link preview image");
assert.ok(fs.statSync(path.join(web, "assets", "og-portal.jpg")).size < 300 * 1024, "og image under 300 KB");

// launch wording
const userFacing = ["strings.js", "p01.js", "portal20.js", "app.js", "index.html", "portal20.css"].map(read).join("\n");
for (const bad of ["Muse Image", "I sign", "Подписываю", "These gifts are yours", "Эти подарки"])
  assert.ok(!userFacing.includes(bad), "removed for launch: " + bad);
assert.ok(!/soulsofmuse\.com/.test(read("portal20.js") + read("index.html") + read("strings.js")), "soulsofmuse.app only");
console.log("portal20: all checks passed");

// Convention translations (from the Russian original) and the language menu
const I = require(path.join(web, "convention-i18n.js"));
assert.ok(Object.keys(I).length >= 17, "Convention in at least 17 more languages");
for (const [k, c] of Object.entries(I)) {
  assert.ok(c.name && c.title && c.first && c.rest.length === 4 && c.readAll && c.collapse && c.note, "complete translation: " + k);
  assert.ok(c.dir === "ltr" || c.dir === "rtl", "text direction: " + k);
}
assert.equal(I.ar.dir, "rtl", "Arabic is right-to-left");
assert.match(read("index.html"), /convention-i18n\.js[\s\S]*portal20\.js/, "translations load before portal20.js");

// Cabinet header leads back to the site
const cab = read("cabinet.js");
assert.match(cab, /class="cab-brand" href="#\/"/, "cabinet wordmark goes to the site home");
assert.match(cab, /cabSiteNav\(role\)/, "cabinet header shows the site route");
console.log("portal20: translations and cabinet navigation checks passed");
