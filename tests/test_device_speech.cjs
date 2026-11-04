"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const reply = (data, status = 200, owner = "M") => ({ ok: status < 400, status, json: async () => data,
  headers: { get: name => name.toLowerCase() === "x-som-participant" ? owner : null } });
const canonical = (overrides = {}) => ({ id: "m1", state: "approved", target_lang: "vi", text: "Chơi chậm.", ...overrides });
function fixture({ lang = "en", voices = [{ name: "Linh", lang: "vi-VN", localService: true }, { name: "Daniel", lang: "en-GB", localService: true }] } = {}) {
  const calls = [], spoken = [], events = {}, buttons = {};
  let cancels = 0, handler;
  for (const key of ["speak", "stop-speech", "logout"]) buttons[key] = { dataset: { harnessSpeak: "m1" }, addEventListener(type, fn) { this[type] = fn; } };
  const c = { window: null, location: { hash: "#/session/maestro/one-to-one" },
    document: { visibilityState: "visible", querySelector: () => null,
      querySelectorAll: selector => {
        const match = selector.match(/^\[data-harness-(speak|stop-speech|logout)\]$/);
        return match ? [buttons[match[1]]] : [];
      } },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setInterval: fn => { c.poll = fn; }, addEventListener: (name, fn) => { events[name] = fn; },
    fetch: async (url, options) => {
      if (url.endsWith("auth/me")) return new Promise(() => {});
      calls.push({ url, options });
      return handler ? handler(url, options) : reply({ id: "one", state: "active", private_notes: { text: "" }, deliveries: [canonical()] });
    },
    speechSynthesis: { getVoices: () => voices, cancel: () => { cancels++; }, speak: utterance => { spoken.push(utterance); }, addEventListener() {} },
    SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
    AbortController, Uint8Array, Blob, atob: value => Buffer.from(value, "base64").toString("binary"),
    URL: { createObjectURL: () => "blob:fixture", revokeObjectURL() {} },
    Audio: class { constructor(url) { this.url = url; this.style = {}; } setAttribute() {} play() { return Promise.resolve(); } pause() {} removeAttribute() {} load() {} remove() {} },
    render() {}, scrollX: 0, scrollY: 0, scrollTo() {}, P01: { state: { lang } } };
  c.window = c; vm.createContext(c); vm.runInContext(fs.readFileSync(require.resolve("../web/harness-client.js"), "utf8"), c);
  const api = c.CabinetHarness;
  Object.assign(api.state, { user: { id: "M", role: "maestro" }, tts: false,
    meeting: { id: "one", state: "active", deliveries: [canonical({ text: "Browser replacement must not be spoken" })] } });
  api.bind();
  return { api, c, calls, spoken, events, buttons, voices, get cancels() { return cancels; }, setHandler(fn) { handler = fn; },
    click: () => buttons.speak.onclick() };
}

for (const lang of ["en", "ru"]) test(`device speech is opt-in, labelled, and uses fresh canonical translation (${lang})`, async () => {
  const f = fixture({ lang });
  assert.match(f.api.messages(), lang === "ru" ? /Голос устройства/ : /Device voice/);
  assert.equal(f.spoken.length, 0);
  await f.click();
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].url, "/api/harness/sessions/one");
  assert.equal(f.calls[0].options.headers["X-SOM-Participant"], "M");
  assert.equal(f.spoken.length, 1);
  assert.equal(f.spoken[0].text, "Chơi chậm.");
  assert.equal(f.spoken[0].lang, "vi-VN");
  assert.equal(f.spoken[0].voice.name, "Linh");
  f.buttons["stop-speech"].onclick();
  assert.ok(f.cancels > 0);
});

test("fresh draft, absent message and unsupported language never become device speech", async () => {
  for (const deliveries of [[canonical({ state: "draft" })], [], [canonical({ target_lang: "ru" })]]) {
    const f = fixture(); f.setHandler(() => reply({ id: "one", private_notes: {}, deliveries }));
    await f.click(); assert.equal(f.spoken.length, 0); assert.ok(f.api.state.status);
  }
});

test("fresh canonical target language selects English even when the cached message was Vietnamese", async () => {
  const f = fixture();
  f.setHandler(() => reply({ id: "one", private_notes: {}, deliveries: [canonical({ target_lang: "en", text: "Play slowly." })] }));
  await f.click();
  assert.equal(f.spoken[0].text, "Play slowly.");
  assert.equal(f.spoken[0].voice.name, "Daniel");
  assert.equal(f.spoken[0].lang, "en-GB");
});

test("no matching installed voice gives an honest error without choosing another language or network voice", async () => {
  const f = fixture({ voices: [{ name: "English", lang: "en-US", localService: true }, { name: "Online VI", lang: "vi-VN", localService: false }] });
  assert.match(f.api.messages(), /Device voice unavailable/);
  assert.doesNotMatch(f.api.messages(), /data-harness-speak/);
  await f.click(); assert.equal(f.spoken.length, 0); assert.match(f.api.state.status, /voice.*unavailable/i);
});

for (const change of ["account", "meeting", "navigation"]) test(`late canonical reply cannot speak after ${change} changes`, async () => {
  const f = fixture(); let release;
  f.setHandler(() => new Promise(resolve => { release = resolve; }));
  const playing = f.click();
  if (change === "account") f.api.state.user = { id: "A", role: "artist" };
  if (change === "meeting") f.api.state.meeting = { id: "two", state: "active", deliveries: [] };
  if (change === "navigation") f.events.hashchange();
  release(reply({ id: "one", private_notes: {}, deliveries: [canonical()] })); await playing;
  assert.equal(f.spoken.length, 0);
  if (change === "account") assert.equal(f.api.state.user.id, "A");
  if (change === "meeting") assert.equal(f.api.state.meeting.id, "two");
});

test("wrong-owner response and current-account 401 cancel speech without exposing another account", async () => {
  const wrong = fixture(); wrong.setHandler(() => reply({ id: "one", private_notes: {}, deliveries: [canonical()] }, 200, "A"));
  await wrong.click(); assert.equal(wrong.spoken.length, 0); assert.equal(wrong.api.state.user, null);
  const f = fixture(); await f.click(); const before = f.cancels;
  f.setHandler(() => reply({ detail: "unauthorized" }, 401)); await f.c.poll();
  assert.ok(f.cancels > before); assert.equal(f.api.state.user, null);
});

test("navigation, pagehide and explicit logout cancel an already queued utterance", async () => {
  for (const kind of ["navigation", "pagehide", "logout"]) {
    const f = fixture(); await f.click(); const before = f.cancels;
    if (kind === "navigation") f.events.hashchange();
    else if (kind === "pagehide") f.events.pagehide();
    else { f.setHandler(() => reply({ signed_out: true })); await f.buttons.logout.click(); }
    assert.ok(f.cancels > before);
  }
});

test("server TTS capability keeps the server speech path without device fallback", async () => {
  const f = fixture(); f.api.state.tts = true;
  f.setHandler(url => { assert.match(url, /\/messages\/m1\/speech$/); return reply({ wav_base64: "AA==", language: "vi" }); });
  await f.click(); assert.equal(f.spoken.length, 0); assert.equal(f.calls.length, 1);
  assert.match(f.api.messages(), /Listen to translation/);
  assert.doesNotMatch(f.api.messages(), /Device voice/);
});

test("a configured server TTS error does not silently invoke device voice", async () => {
  const f = fixture(); f.api.state.tts = true;
  f.setHandler(() => reply({ detail: "speech_unavailable" }, 503));
  await f.click();
  assert.equal(f.spoken.length, 0);
  assert.match(f.api.state.status, /speech_unavailable/);
});
