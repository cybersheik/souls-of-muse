"use strict";
const { test } = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
function client({ role = "maestro", narrow = false, hash = "#/space", signedIn = true } = {}) {
  const c = { window: null, P01: { state: { lang: "en" }, stop() {}, bind() {} }, location: { hash },
    localStorage: { getItem: () => null, setItem() {} }, matchMedia: () => ({ matches: narrow }),
    document: { body: { innerHTML: "", className: "" }, querySelector: () => null, querySelectorAll: () => [], addEventListener() {} },
    addEventListener() {}, scrollTo() {}, clearTimeout() {}, clearInterval() {}, Image: class {},
    Portal20: { stop() {}, bind() {}, home: () => "PUBLIC PORTAL", leagues: () => "PUBLIC LEAGUES" },
    CabinetHarness: { state: { user: signedIn ? { id: "real-user-id", name: "Real Maestro", role } : null,
      sessions: [{ id: "real-lesson", state: "created", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" }],
      meeting: null, lesson: { plan: [] }, busy: false, asr: false, tts: false, status: "" },
      panel: () => '<div class="cab-live"><button data-harness-start>Start</button><span>AUTHENTICATED CONTROLS</span></div>',
      messages: () => '<div class="cab-msg">CANONICAL MESSAGE</div>', bind() {} },
    SomLesson: { planHTML: () => '<div>REAL PLAN</div><form data-lesson-planner-form>PLAN WITH MUSE</form>', drawerHTML: () => '<div class="cab-drawer">REAL NOTEBOOK</div>', bind() {} } };
  c.window = c; vm.createContext(c);
  for (const file of ["strings.js", "cabinet.js"]) vm.runInContext(fs.readFileSync(`web/${file}`, "utf8"), c);
  return c;
}

test("authenticated home shows actual meetings and a next step without invented people, times or Muse scores", () => {
  const c = client(), html = c.Cabinet.home("artist");
  assert.match(html, /data-cab-screen="home-maestro"/);
  assert.match(html, /data-harness-open="real-lesson"/);
  assert.match(html, /Actual Artist/);
  assert.match(html, /Prepare meeting/);
  assert.doesNotMatch(html, /18:30|Amara|Kenji|Ramires|4 artists|Muse this week|55%|example data/i);
  assert.doesNotMatch(html, /data-cab-role="artist"|data-cab-role="admirer"/);
});

test("empty live home has a truthful next step rather than an example lesson", () => {
  const c = client(); c.CabinetHarness.state.sessions = [];
  const html = c.Cabinet.home("maestro");
  assert.match(html, /No meetings yet/);
  assert.match(html, /Create a meeting/);
  assert.doesNotMatch(html, /18:30|data-harness-open=|Amara|Kenji/);
});

test("generic My space and a conflicting role URL resolve from the authenticated account", () => {
  for (const hash of ["#/space", "#/space/artist"]) {
    const c = client({ hash }); vm.runInContext(fs.readFileSync("web/app.js", "utf8"), c);
    assert.match(c.document.body.innerHTML, /data-cab-screen="home-maestro"/);
    assert.doesNotMatch(c.document.body.innerHTML, /data-cab-role="artist"/);
  }
});

test("explicit demo remains separate from authenticated identity, meeting and protected controls", () => {
  const c = client(); c.CabinetHarness.state.meeting = { id: "live-id", state: "active", maestro_alias: "SECRET PERSON", artist_alias: "SECRET ARTIST" };
  const home = c.Cabinet.home("artist", { demo: true });
  const lesson = c.Cabinet.session("artist", "one", { demo: true });
  for (const html of [home, lesson]) {
    assert.match(html, /data-cab-demo="true"/);
    assert.match(html, /example data/i);
    assert.doesNotMatch(html, /Real Maestro|real-user-id|SECRET PERSON|SECRET ARTIST|AUTHENTICATED CONTROLS|CANONICAL MESSAGE|REAL NOTEBOOK/);
  }
  assert.match(home, /#\/demo\/session\/artist\//);
});

test("anonymous live entry offers sign-in and an explicit example choice instead of a scheduled example", () => {
  const c = client({ signedIn: false }); const html = c.Cabinet.home("artist");
  assert.match(html, /Sign in/);
  assert.match(html, /#\/demo\/space\/artist/);
  assert.doesNotMatch(html, /18:30|Amara|Kenji/);
});

test("signed-in session URL without a selected meeting cannot display a prototype lesson", () => {
  const c = client(); const html = c.Cabinet.session("artist", "circle");
  assert.match(html, /data-harness-open="real-lesson"/);
  assert.doesNotMatch(html, /Amara|Kenji|55%|12:34|Session 3/);
});

test("mobile conversation and named composer precede collapsed plan and planner; Notebook remains separate", () => {
  const c = client({ narrow: true }); c.CabinetHarness.state.meeting = { id: "one", state: "active", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" };
  const html = c.Cabinet.session("artist", "one");
  assert.match(html, /data-cab-screen="session-maestro-one"/);
  assert.ok(html.indexOf("data-cab-chat-input") < html.indexOf("REAL PLAN"));
  assert.ok(html.indexOf("data-cab-chat-input") < html.indexOf("CANONICAL MESSAGE"));
  assert.match(html, /<input[^>]*data-cab-chat-input[^>]*aria-label="Message for Muse"/);
  assert.match(html, /<button[^>]*type="submit"[^>]*aria-label="Send message"/);
  const disclosure = html.match(/<details[^>]*data-cab-live-plan[^>]*>/)?.[0];
  assert.ok(disclosure); assert.doesNotMatch(disclosure, /\bopen\b/);
  assert.match(html, /REAL NOTEBOOK/);
  assert.doesNotMatch(html, /class="cab-notlive/);
});

test("desktop retains open real plan and Maestro metronome alongside the real Notebook", () => {
  const c = client(); c.CabinetHarness.state.meeting = { id: "one", state: "active", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" };
  const html = c.Cabinet.session("maestro", "one");
  assert.match(html, /<details[^>]*data-cab-live-plan[^>]*\bopen\b/);
  assert.match(html, /REAL PLAN/); assert.match(html, /data-cab-metro/); assert.match(html, /REAL NOTEBOOK/);
});

test("prototype recording state cannot appear as live Muse listening or a live raised hand", () => {
  const c = client({ role: "artist" }); c.Cabinet.state.rec = true; c.Cabinet.state.hand = true;
  c.CabinetHarness.state.meeting = { id: "one", state: "active", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" };
  const html = c.Cabinet.session("artist", "one");
  assert.doesNotMatch(html, /cab-dictating|data-cab-hand|hand is raised/i);
});

test("demo binding never installs protected handlers or sends prototype chat through the live account", () => {
  const c = client(); let protectedBinds = 0, sends = 0, submit;
  c.CabinetHarness.bind = () => { protectedBinds++; }; c.CabinetHarness.send = () => { sends++; };
  c.SomLesson.bind = () => { protectedBinds++; };
  const form = { addEventListener: (type, handler) => { submit = handler; }, querySelector: () => ({ value: "Example-only message" }) };
  c.document.querySelector = selector => selector === "[data-cab-screen]" ? { dataset: { cabScreen: "session-artist-one", cabDemo: "true" } } : selector === "[data-cab-chat-form]" ? form : null;
  c.Cabinet.bind(); submit({ preventDefault() {} });
  assert.equal(protectedBinds, 0); assert.equal(sends, 0);
  assert.equal(c.Cabinet.state.extraChat.at(-1).text, "Example-only message");
});

test("live conversation uses the account language controls and pair instead of a role-fixed direction", () => {
  const c = client(); let calls = 0;
  c.CabinetHarness.state.meeting = { id: "one", state: "active", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" };
  c.CabinetHarness.languagePair = () => { calls++; return { source: "vi", target: "en" }; };
  c.CabinetHarness.languageControls = () => { calls++; return '<label class="cab-language-controls">I speak<select data-harness-language><option>Vietnamese</option></select></label>'; };
  const html = c.Cabinet.session("maestro", "one");
  assert.match(html, /data-harness-language/); assert.match(html, /VI → EN/);
  const liveCalls = calls;
  const demo = c.Cabinet.session("maestro", "one", { demo: true });
  assert.equal(calls, liveCalls); assert.doesNotMatch(demo, /data-harness-language/);
});

test("missing Harness module fails closed on real home and session routes", () => {
  const c = client(); delete c.CabinetHarness;
  for (const html of [c.Cabinet.home("maestro"), c.Cabinet.session("maestro", "circle")]) {
    assert.match(html, /Service unavailable/);
    assert.match(html, /data-cab-reload/);
    assert.doesNotMatch(html, /18:30|Amara|Kenji|55%|12:34|data-harness-|data-cab-demo="true"|example data/i);
  }
  let reloads = 0, protectedCalls = 0, click;
  c.location.reload = () => { reloads++; }; c.SomLesson.bind = () => { protectedCalls++; };
  c.document.querySelector = selector => selector === "[data-cab-reload]" ? { addEventListener: (type, handler) => { click = handler; } } : null;
  c.Cabinet.bind(); click({ preventDefault() {} });
  assert.equal(reloads, 1); assert.equal(protectedCalls, 0);
});

test("explicit demo still works when the Harness module is missing", () => {
  const c = client(); delete c.CabinetHarness;
  assert.match(c.Cabinet.home("artist", { demo: true }), /data-cab-demo="true"/);
  assert.match(c.Cabinet.session("artist", "one", { demo: true }), /data-cab-demo="true"/);
});

test("created lesson has one prominent Maestro start and an Artist waiting message, with no render-time calls", () => {
  for (const role of ["maestro", "artist"]) {
    const c = client({ role, hash: `#/session/${role}/circle` });
    const saved = c.CabinetHarness.state; let calls = 0;
    Object.assign(c, { AbortController, setTimeout, clearTimeout, sessionStorage: { getItem: () => null },
      fetch: () => { calls++; return new Promise(() => {}); }, setInterval() {} });
    vm.runInContext(fs.readFileSync("web/harness-client.js", "utf8"), c);
    Object.assign(c.CabinetHarness.state, saved, { authChecking: false,
      meeting: { id: "one", state: "created", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" } });
    const before = calls, html = c.Cabinet.session(role, "circle");
    assert.equal(calls, before);
    assert.equal((html.match(/data-harness-start/g) || []).length, role === "maestro" ? 1 : 0);
    if (role === "maestro") {
      assert.match(html, />Start lesson<\/button>/);
      assert.ok(html.indexOf("data-harness-start") < html.indexOf("data-cab-live-controls"));
    } else assert.match(html, /Waiting for your Maestro to start this lesson/);
    c.CabinetHarness.state.meeting.state = "active";
    const active = c.Cabinet.session(role, "circle");
    assert.doesNotMatch(active, /data-harness-start|Waiting for your Maestro/);
  }
});

test("created lesson exposes local equipment checks for both roles without starting the meeting", () => {
  for (const role of ["maestro", "artist"]) {
    const c = client({ role, narrow: true });
    c.CabinetHarness.state.meeting = { id: "one", state: "created", maestro_alias: "Real Maestro", artist_alias: "Actual Artist" };
    const html = c.Cabinet.session(role, "circle");
    assert.match(html, /data-cab-phase="created"/);
    assert.match(html, /data-live-conference/);
    assert.match(html, /Only you can see and hear this check/);
    assert.doesNotMatch(html.match(/<details[^>]*data-cab-live-controls[^>]*>/)[0], /\bopen\b/);
    assert.match(html, /data-cab-chat-input[^>]*disabled/);
  }
});
