const { test } = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

function client() {
  let release;
  const delayed = new Promise(resolve => { release = resolve; });
  const state = { block: false, rooms: 0, instances: [], calls: [] };
  class Room {
    constructor() { this.index = state.rooms++; this.state = "disconnected"; this.handlers = {}; state.instances.push(this); }
    on(event, callback) { this.handlers[event] = callback; }
    async connect() { this.state = "connected"; }
    async startAudio() {}
    async disconnect() { if (state.block && this.index < 2) await delayed; this.state = "disconnected"; }
  }
  const window = { LivekitClient: { Room, RoomEvent: { Disconnected: "disconnected" } }, dispatchEvent() {}, addEventListener() {} };
  const context = { window, document: { querySelector: () => null }, Event, DOMException,
    setInterval: () => 1, clearInterval() {}, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      const verb = url.split("/").at(-1);
      state.calls.push({ verb, body: JSON.parse(options.body || "{}"), keepalive: options.keepalive });
      if (verb === "join" && state.waitJoin) { const wait=state.waitJoin; state.waitJoin=null; await wait; }
      if (verb === "leave" && state.failLeave) { state.failLeave=false; return {ok:false,json:async()=>({detail:"cleanup_pending"})}; }
      return { ok: true, json: async () => verb === "join" ? {
        url: "ws://127.0.0.1", generation: "generation-" + state.calls.filter(x => x.verb === "join").length,
        ingress: { token: "ingress-capability" }, playback: { token: "playback-capability" },
      } : { state: "closed" } };
    } };
  vm.runInNewContext(fs.readFileSync(require.resolve("../web/media-client.js"), "utf8"), context);
  return { media: window.SomMedia, state, release };
}

test("reconnect waits for the previous disconnect and server cleanup", async () => {
  const { media, state, release } = client();
  await media.connect("meeting");
  state.block = true;
  const closing = media.disconnect(true), opening = media.connect("meeting");
  try {
    await new Promise(setImmediate);
    assert.equal(state.calls.filter(x => x.verb === "join").length, 1);
  } finally { release(); await Promise.allSettled([closing, opening]); }
  assert.deepEqual(state.calls.map(x => x.verb), ["join", "leave", "join"]);
  assert.equal(media.connected("meeting"), true);
});

test("page cleanup initiates generation-bound keepalive before waiting for RTC", async () => {
  const { media, state, release } = client();
  await media.connect("meeting");
  state.block = true;
  const closing = media.disconnect(true);
  try {
    const leave = state.calls.find(x => x.verb === "leave");
    assert.ok(leave, "server cleanup was not initiated before asynchronous disconnect");
    assert.equal(leave.keepalive, true);
    assert.equal(leave.body.generation, "generation-1");
  } finally { release(); await closing; }
});

test("cancelled provisioning finishes its cleanup before a later join", async () => {
  const { media, state } = client();
  let finishJoin;
  state.waitJoin = new Promise(resolve=>{finishJoin=resolve;});
  const old = media.connect("meeting"); old.catch(()=>{});
  await new Promise(setImmediate);
  const closing=media.disconnect(true), fresh=media.connect("meeting");
  finishJoin();
  const results=await Promise.allSettled([old,closing,fresh]);
  assert.equal(results[0].status,"rejected");
  assert.equal(results[0].reason.name,"AbortError");
  assert.equal(results[2].status,"fulfilled");
  assert.deepEqual(state.calls.map(x=>x.verb),["join","leave","join"]);
  assert.equal(state.calls[1].body.generation,"generation-1");
});

test("an explicit reconnect retries uncertain cleanup before creating rooms", async () => {
  const { media, state } = client();
  await media.connect("meeting"); state.failLeave=true;
  await assert.rejects(media.disconnect(true),/cleanup_pending/);
  assert.equal(state.calls.filter(x=>x.verb==="leave").length,1);
  await media.connect("meeting");
  assert.deepEqual(state.calls.map(x=>x.verb),["join","leave","leave","join"]);
  assert.equal(media.connected("meeting"),true);
});

test("a terminal RTC disconnect releases the server generation", async () => {
  const { media, state } = client();
  await media.connect("meeting");
  state.instances[0].handlers.disconnected();
  await new Promise(setImmediate);
  assert.equal(media.connected("meeting"), false);
  assert.deepEqual(state.calls.map(x => x.verb), ["join", "leave"]);
  assert.equal(state.calls[1].body.generation, "generation-1");
});
