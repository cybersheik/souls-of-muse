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

for (const lang of ["en", "ru"]) test(`rejected native voices remain disabled even when installed (${lang})`, async () => {
  const f = fixture({ lang });
  assert.doesNotMatch(f.api.messages(), /data-harness-speak|Device voice|Голос устройства/);
  assert.match(f.api.messages(), lang === "ru" ? /Серверная озвучка/ : /Server voice/);
  await f.click();
  assert.equal(f.spoken.length, 0);
  assert.equal(f.calls.length, 0);
});

test("unapproved messages cannot expose server playback controls", () => {
  const f = fixture(); f.api.state.tts = true;
  f.api.state.meeting.deliveries = [canonical({ state: "draft" })];
  assert.doesNotMatch(f.api.messages(), /data-harness-speak/);
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
