"use strict";
const { test } = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
const flush = () => new Promise(resolve => setImmediate(resolve));
function client() {
  let resolveAuth, rejectAuth, nextAuth, health;
  const initial = new Promise((resolve, reject) => { resolveAuth = resolve; rejectAuth = reject; });
  const timers = new Map(), requests = [], snapshots = [], retry = { addEventListener(type, handler) { this[type] = handler; } };
  const c = { window: null, location: { hash: "#/space" }, P01: { state: { lang: "en" } },
    document: { querySelector: () => null, querySelectorAll: selector => selector === "[data-harness-auth-retry]" ? [retry] : [] },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} }, AbortController,
    setTimeout: (fn, delay) => { const handle = { unref() {} }; timers.set(handle, { fn, delay }); return handle; },
    clearTimeout: handle => timers.delete(handle), setInterval() {}, addEventListener() {}, scrollX: 0, scrollY: 0, scrollTo() {},
    render: () => { if (c.CabinetHarness) snapshots.push(c.CabinetHarness.panel()); },
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (url.endsWith("auth/me")) return requests.filter(r => r.url.endsWith("auth/me")).length === 1 ? initial : nextAuth;
      if (url.endsWith("health")) return health || response({ capabilities: {} });
      if (url.endsWith("sessions")) return response({ sessions: [] });
      throw new Error("Unexpected fixture request");
    } };
  c.window = c; vm.createContext(c); vm.runInContext(fs.readFileSync("web/harness-client.js", "utf8"), c);
  return { c, api: c.CabinetHarness, timers, requests, snapshots, retry, resolveAuth, rejectAuth,
    setNextAuth: value => { nextAuth = value; }, setHealth: value => { health = value; } };
}

test("initial cookie check never exposes a sign-in form before its response", () => {
  const f = client();
  assert.match(f.api.panel(), /Checking sign-in/);
  assert.doesNotMatch(f.api.panel(), /data-harness-login|name="username"|name="password"/);
  assert.equal(f.api.state.authChecking, true);
});

test("anonymous401 immediately exposes the form without waiting for health or meeting restoration", async () => {
  const f = client(); f.resolveAuth(response({ detail: "unauthorized" }, 401)); await flush();
  assert.equal(f.api.state.authChecking, false); assert.match(f.api.panel(), /data-harness-login/);
  assert.equal(f.requests.length, 1); assert.equal(f.timers.size, 0);
});

test("successful existing cookie avoids form flash even while health is still loading", async () => {
  const f = client(); let finishHealth;
  f.setHealth(new Promise(resolve => { finishHealth = resolve; }));
  f.resolveAuth(response({ id: "M", name: "Maestro", role: "maestro" })); await flush();
  assert.equal(f.api.state.user.id, "M"); assert.equal(f.api.state.authChecking, false);
  assert.doesNotMatch(f.api.panel(), /data-harness-login/);
  assert.ok(f.snapshots.every(html => !html.includes("data-harness-login")));
  finishHealth(response({ capabilities: {} })); await flush();
});

test("network failure is honest and explicit retry can establish anonymous state", async () => {
  const f = client(); f.rejectAuth(new Error("network unavailable")); await flush();
  assert.equal(f.api.state.authChecking, false); assert.match(f.api.panel(), /Could not check sign-in/);
  assert.doesNotMatch(f.api.panel(), /data-harness-login/);
  f.setNextAuth(response({ detail: "unauthorized" }, 401)); f.api.bind(); await f.retry.click();
  assert.match(f.api.panel(), /data-harness-login/); assert.equal(f.api.state.authCheckFailed, false);
});

test("bounded timeout aborts the lookup and ignores a late authenticated response", async () => {
  const f = client(); assert.equal(f.timers.size, 1);
  const timer = [...f.timers.values()][0]; assert.ok(timer.delay > 8000 && timer.delay <= 30000);
  timer.fn(); await flush();
  assert.equal(f.requests[0].options.signal.aborted, true);
  assert.equal(f.api.state.authChecking, false); assert.match(f.api.panel(), /data-harness-auth-retry/);
  f.resolveAuth(response({ id: "OLD", role: "artist" })); await flush();
  assert.equal(f.api.state.user, null); assert.equal(f.api.state.authCheckFailed, true);
});

test("a late lookup cannot replace an explicit new account", async () => {
  const f = client(), current = { id: "NEW", role: "maestro" }; f.api.state.user = current;
  f.resolveAuth(response({ id: "OLD", role: "artist" })); await flush();
  assert.equal(f.api.state.user, current); assert.equal(f.api.state.authChecking, false);
});

test("timed-out initial response cannot replace the account established by explicit retry", async () => {
  const f = client(); [...f.timers.values()][0].fn(); await flush();
  f.setNextAuth(response({ id: "NEW", name: "Current Maestro", role: "maestro" }));
  f.api.bind(); await f.retry.click();
  const current = f.api.state.user; assert.equal(current.id, "NEW");
  f.resolveAuth(response({ id: "OLD", role: "artist" })); await flush();
  assert.equal(f.api.state.user, current); assert.equal(f.api.state.authChecking, false);
  assert.doesNotMatch(f.api.panel(), /data-harness-login/);
});

test("live home checking hint does not tell an authenticated-cookie visitor to sign in", () => {
  const f = client();
  for (const file of ["strings.js", "cabinet.js"]) vm.runInContext(fs.readFileSync(`web/${file}`, "utf8"), f.c);
  const html = f.c.Cabinet.home("artist");
  assert.match(html, /Checking sign-in/); assert.doesNotMatch(html, /Sign in to see your meetings/);
});
