"use strict";
const { test } = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
function fixture(phase) {
  const mounts = [], calls = [], host = {};
  const c = { window: null, document: { visibilityState: "visible", querySelector: s => s === "[data-live-conference]" ? host : null, querySelectorAll: () => [] },
    location: { hash: "#/session/maestro/circle" }, sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    SomConference: { mount: (element, config) => mounts.push({ element, config }), stop() {} },
    fetch: async (url, options) => { if (url.endsWith("auth/me")) return new Promise(() => {}); calls.push({ url, options }); return { ok: true, status: 200, headers: { get: () => "M" }, json: async () => ({ connection_id: "c" }) }; },
    setInterval() {}, addEventListener() {}, setTimeout: () => 1, clearTimeout() {}, AbortController, P01: { state: { lang: "en" } } };
  c.window = c; vm.createContext(c); vm.runInContext(fs.readFileSync("web/harness-client.js", "utf8"), c);
  Object.assign(c.CabinetHarness.state, { user: { id: "M", role: "maestro" }, meeting: { id: "one", state: phase } });
  c.CabinetHarness.bind(); return { c, mounts, calls, host };
}
for (const phase of ["created", "active"]) test(`equipment mount receives ${phase} without a render-time join`, async () => {
  const f = fixture(phase); assert.equal(f.mounts.length, 1);
  assert.equal(f.mounts[0].element, f.host); assert.equal(f.mounts[0].config.state, phase); assert.equal(f.calls.length, 0);
});
test("active equipment explicitly joins the lesson before joining AV signalling", async () => {
  const f = fixture("active"); await f.mounts[0].config.request("sessions/one/conference/join", {});
  assert.deepEqual(f.calls.map(r => r.url), ["/api/harness/sessions/one/join", "/api/harness/sessions/one/conference/join"]);
});
test("created equipment binding cannot transmit or join before the lesson starts", async () => {
  const f = fixture("created"); assert.equal(f.mounts.length, 1);
  await assert.rejects(f.mounts[0].config.request("sessions/one/conference/join", {}), /session_not_active/);
  assert.equal(f.calls.length, 0);
});
test("a stale equipment binding cannot issue requests for a different account or room", async () => {
  const f = fixture("active"); const config = f.mounts[0].config;
  f.c.CabinetHarness.state.user = { id: "B", role: "artist" };
  await assert.rejects(config.request("sessions/one/conference/join", {}), /participant_context_changed/);
  assert.equal(f.calls.length, 0);
});
test("cancelled pending logical join cannot replace a newer AV connection on retry", async () => {
  const f = fixture("active"), config = f.mounts[0].config, fetch = f.c.fetch;
  let release, first = true, current = true;
  const gate = new Promise(resolve => { release = resolve; });
  f.c.fetch = async (url, options) => {
    const reply = await fetch(url, options);
    if (url.endsWith("/sessions/one/join") && first) { first = false; await gate; }
    return reply;
  };
  const old = config.request("sessions/one/conference/join", {}, { isCurrent: () => current });
  const rejected = assert.rejects(old, /media_operation_cancelled/);
  await Promise.resolve(); await Promise.resolve(); current = false;
  await config.request("sessions/one/conference/join", {}, { isCurrent: () => true });
  release(); await rejected;
  assert.equal(f.calls.filter(r => r.url.endsWith("/conference/join")).length, 1);
});
test("AV join cancellation signal reaches both logical join and conference request", async () => {
  const f = fixture("active"), controller = new AbortController();
  await f.mounts[0].config.request("sessions/one/conference/join", {}, { signal: controller.signal, isCurrent: () => true });
  assert.ok(f.calls.every(r => r.options.signal === controller.signal));
  controller.abort(); const before = f.calls.length;
  await assert.rejects(f.mounts[0].config.request("sessions/one/conference/join", {}, { signal: controller.signal }), /media_operation_cancelled/);
  assert.equal(f.calls.length, before);
});
