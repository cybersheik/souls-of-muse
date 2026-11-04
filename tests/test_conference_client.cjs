"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function fixture({ deferMedia = false, lang = "en" } = {}) {
  const state = { requests: [], tracks: [], pcs: [], timers: [], mediaCalls: 0, answer: null, events: [], peers: [], devices: [{ kind: "videoinput", deviceId: "front", label: "Front" }, { kind: "videoinput", deviceId: "back", label: "Back" }], mediaRequests: [] };
  class Element {
    constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.listeners = {}; this.textContent = ""; }
    appendChild(child) { child.parentNode?.removeChild(child); this.children.push(child); child.parentNode = this; return child; }
    removeChild(child) { this.children = this.children.filter(x => x !== child); child.parentNode = null; }
    replaceChildren(...children) { for (const child of this.children) child.parentNode = null; this.children = []; children.forEach(child => this.appendChild(child)); }
    setAttribute(key, value) { this[key] = value; }
    addEventListener(key, handler) { this.listeners[key] = handler; }
    remove() { this.parentNode?.removeChild(this); }
    play() { return Promise.resolve(); }
    pause() {}
  }
  class PC {
    constructor() { this.signalingState = "stable"; this.connectionState = "new"; this.remoteDescription = null; this.candidates = []; state.pcs.push(this); }
    addTrack(track) {
      (this.tracks ||= []).push(track);
      const sender = { track, replaceTrack: async value => { if (this.failReplace) throw new Error("replace failed"); sender.track = value; } };
      (this.senders ||= []).push(sender);
    }
    getSenders() { return this.senders || []; }
    async setLocalDescription(description) {
      this.localDescription = description || { type: this.signalingState === "have-remote-offer" ? "answer" : "offer", sdp: "local" };
      this.signalingState = this.localDescription.type === "offer" ? "have-local-offer" : "stable";
    }
    async setRemoteDescription(description) { this.remoteDescription = description; this.signalingState = description.type === "offer" ? "have-remote-offer" : "stable"; }
    async addIceCandidate(candidate) { assert.ok(this.remoteDescription, "ICE applied before description"); this.candidates.push(candidate); }
    close() { this.closed = true; this.connectionState = "closed"; }
  }
  const tracks = ["audio", "video"].map(kind => ({ kind, enabled: true, getSettings: () => ({ deviceId: "front" }), stop() { this.stopped = true; } }));
  state.tracks = tracks;
  const stream = { getTracks: () => tracks, getAudioTracks: () => tracks.filter(t => t.kind === "audio"), getVideoTracks: () => tracks.filter(t => t.kind === "video") };
  let release;
  const media = deferMedia ? new Promise(resolve => { release = () => resolve(stream); }) : Promise.resolve(stream);
  state.windowEvents = {};
  const window = { P01: { state: { lang } }, addEventListener: (name, handler) => { state.windowEvents[name] = handler; }, dispatchEvent() {} };
  const context = { window, document: { createElement: tag => new Element(tag) }, navigator: { mediaDevices: {
    enumerateDevices: async () => state.devices,
    getUserMedia: constraints => { state.mediaCalls++; state.mediaRequests.push(constraints); if (state.mediaCalls > 1) state.onNextMedia?.(); return state.mediaCalls === 1 ? media : state.nextMedia; }
  } },
    RTCPeerConnection: PC, MediaStream: class { constructor(t = []) { this.tracks = t; } addTrack(t) { this.tracks.push(t); } getTracks() { return this.tracks; } getAudioTracks() { return this.tracks.filter(t => t.kind === "audio"); } getVideoTracks() { return this.tracks.filter(t => t.kind === "video"); } },
    setTimeout: (fn, delay) => { fn.delay = delay; state.timers.push(fn); return fn; }, clearTimeout: fn => { state.timers = state.timers.filter(timer => timer !== fn); }, Event: class {}, console, URLSearchParams, AbortController };
  vm.runInNewContext(fs.readFileSync(require.resolve("../web/conference-client.js"), "utf8"), context);
  const request = async (path, body, options) => {
    state.requests.push({ path, body, options });
    if (path.endsWith("/join")) { state.onJoin?.(); if (state.joinReply) return state.joinReply; return { self: "M", connection_id: "m-current", peers: state.peers, cursor: 0 }; }
    if (path.endsWith("/signal") && state.failSignal) throw new Error(state.failSignal);
    if (path.includes("/events?")) { const events = state.events; state.events = []; return { self: "M", peers: state.peers, events, cursor: events.at(-1)?.id || 0 }; }
    return { ok: true };
  };
  const root = new Element("div");
  return { conference: window.SomConference, state, root, request, release, context };
}

test("mount never requests devices; start adds both tracks and stop releases every resource", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a-current" }, { id: "B", connection_id: "b-current" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request });
  assert.equal(f.state.mediaCalls, 0);
  await f.conference.start();
  assert.equal(f.state.mediaCalls, 1);
  assert.equal(f.state.pcs.length, 2);
  for (const pc of f.state.pcs) assert.deepEqual(pc.tracks.map(t => t.kind), ["audio", "video"]);
  await f.conference.stop();
  assert.equal(f.state.requests.find(r => r.path.endsWith("/join")).options.signal.aborted, true);
  assert.ok(f.state.tracks.every(t => t.stopped));
  assert.ok(f.state.pcs.every(pc => pc.closed));
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/leave")).length, 1);
});

const walk = element => [element, ...element.children.flatMap(walk)];
function switchButton(f) { return walk(f.root).find(e => e.textContent === "Switch camera"); }
function nextCamera(f) {
  const track = { kind: "video", enabled: true, getSettings: () => ({ deviceId: "back" }), stop() { this.stopped = true; } };
  const stream = { getTracks: () => [track], getVideoTracks: () => [track], getAudioTracks: () => [] };
  f.state.nextMedia = Promise.resolve(stream); return { track, stream };
}
test("switch camera replaces only video at two peers and preserves audio, mute and camera-off", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a" }, { id: "B", connection_id: "b" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  walk(f.root).find(e => e.textContent === "Mute").listeners.click();
  walk(f.root).find(e => e.textContent === "Camera off").listeners.click();
  const next = nextCamera(f); assert.ok(switchButton(f), "Switch camera control is missing");
  await switchButton(f).listeners.click();
  assert.equal(f.state.mediaRequests[1].audio, false);
  assert.equal(f.state.mediaRequests[1].video.deviceId.exact, "back");
  for (const pc of f.state.pcs) {
    assert.equal(pc.getSenders().find(s => s.track.kind === "audio").track, f.state.tracks[0]);
    assert.equal(pc.getSenders().find(s => s.track.kind === "video").track, next.track);
  }
  assert.equal(f.state.tracks[0].stopped, undefined); assert.equal(f.state.tracks[0].enabled, false);
  assert.equal(f.state.tracks[1].stopped, true); assert.equal(next.track.enabled, false);
  const preview = walk(f.root).find(e => e.tagName === "video" && e.muted);
  assert.equal(preview.srcObject.getVideoTracks()[0], next.track);
  await f.conference.stop();
});

test("hangup while camera permission is pending stops late new camera and does not rejoin", async () => {
  const f = fixture(); f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  const next = nextCamera(f); let release; f.state.nextMedia = new Promise(resolve => { release = () => resolve(next.stream); });
  const requested = new Promise(resolve => { f.state.onNextMedia = resolve; });
  assert.ok(switchButton(f), "Switch camera control is missing");
  const changing = switchButton(f).listeners.click(); await requested;
  await f.conference.stop(); release(); await changing;
  assert.equal(next.track.stopped, true);
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/join")).length, 1);
});

test("one camera reports unavailable without opening another capture", async () => {
  const f = fixture(); f.state.devices = [f.state.devices[0]];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  assert.ok(switchButton(f), "Switch camera control is missing"); await switchButton(f).listeners.click();
  assert.equal(f.state.mediaCalls, 1); assert.ok(f.state.tracks.every(t => !t.stopped));
  assert.ok(walk(f.root).some(e => /No other camera/i.test(e.textContent)));
  await f.conference.stop();
});

test("a late camera grant after account and meeting change is discarded", async () => {
  const f = fixture(); f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  const next = nextCamera(f); let release;
  f.state.nextMedia = new Promise(resolve => { release = () => resolve(next.stream); });
  const requested = new Promise(resolve => { f.state.onNextMedia = resolve; });
  const changing = switchButton(f).listeners.click(); await requested;
  f.conference.mount(f.root, { sid: "another", userId: "B", request: f.request });
  release(); await changing;
  assert.equal(next.track.stopped, true);
  assert.equal(f.conference.connected(), false);
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/join")).length, 1);
  assert.ok(!walk(f.root).some(e => /Camera selected:/.test(e.textContent)));
});

test("replaceTrack failure rolls back changed peers and keeps the current call and camera", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a" }, { id: "B", connection_id: "b" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  const next = nextCamera(f); f.state.pcs[1].failReplace = true;
  assert.ok(switchButton(f), "Switch camera control is missing"); await switchButton(f).listeners.click();
  assert.equal(f.state.pcs[0].getSenders().find(s => s.track.kind === "video").track, f.state.tracks[1]);
  assert.ok(f.state.tracks.every(t => !t.stopped)); assert.equal(next.track.stopped, true);
  assert.ok(f.state.pcs.every(pc => !pc.closed));
  assert.ok(walk(f.root).some(e => /Camera change failed/i.test(e.textContent)));
  await f.conference.stop();
});

test("created meeting captures local preview without any HTTP, peer connection or send", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a" }];
  f.context.RTCPeerConnection = undefined; // Local checks do not need WebRTC signalling.
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request });
  assert.equal(f.state.mediaCalls, 0); await f.conference.start();
  assert.equal(f.state.requests.length, 0); assert.equal(f.state.pcs.length, 0);
  assert.ok(walk(f.root).some(e => e.tagName === "video" && e.srcObject));
  assert.ok(walk(f.root).some(e => /Local preview only/i.test(e.textContent)));
  assert.equal(f.conference.connected(), false); await f.conference.stop();
});

test("join deadline stops capture and cleans a late capability without creating peers", async () => {
  const f = fixture(); let resolveJoin;
  f.state.joinReply = new Promise(resolve => { resolveJoin = resolve; });
  const joining = new Promise(resolve => { f.state.onJoin = resolve; });
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); const starting = f.conference.start(); await joining;
  f.state.timers.find(fn => fn.delay >= 10000)(); await starting;
  assert.equal(f.state.requests.find(r => r.path.endsWith("/join")).options.signal.aborted, true);
  assert.ok(f.state.tracks.every(t => t.stopped)); assert.equal(f.state.pcs.length, 0);
  resolveJoin({ self: "M", connection_id: "late", peers: [{ id: "A", connection_id: "a" }], cursor: 0 });
  await Promise.resolve(); await Promise.resolve();
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/leave")).length, 1);
  assert.equal(f.state.requests.find(r => r.path.endsWith("/leave")).options, undefined);
  assert.equal(f.state.pcs.length, 0);
});

test("stop aborts a pending logical join before retry and never sends the stale conference POST", async () => {
  const f = fixture(); let releaseLogical, announceLogical, first = true;
  const logicalPending = new Promise(resolve => { releaseLogical = resolve; });
  const entered = new Promise(resolve => { announceLogical = resolve; });
  const conferencePosts = [], cancelledOptions = [];
  const adapter = async (path, body, options) => {
    if (path.endsWith("/join")) {
      if (first) {
        first = false; cancelledOptions.push(options); announceLogical(); await logicalPending;
        if (options?.signal?.aborted || !options?.isCurrent?.()) throw new Error("cancelled_logical_join");
      }
      conferencePosts.push(path);
      return { self: "M", connection_id: "new-connection", peers: [], cursor: 0 };
    }
    return { ok: true };
  };
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: adapter });
  const old = f.conference.start(); await entered;
  await f.conference.stop();
  assert.equal(cancelledOptions[0]?.signal?.aborted, true);
  assert.equal(cancelledOptions[0]?.isCurrent?.(), false);
  const fresh = ["audio", "video"].map(kind => ({ kind, enabled: true, stop() { this.stopped = true; } }));
  f.state.nextMedia = Promise.resolve({ getTracks: () => fresh, getVideoTracks: () => fresh.filter(t => t.kind === "video"), getAudioTracks: () => fresh.filter(t => t.kind === "audio") });
  await f.conference.start();
  releaseLogical(); await old;
  assert.equal(conferencePosts.length, 1);
  assert.equal(f.conference.connected(), true); await f.conference.stop();
});

test("local mic meter has no destination route; explicit speaker tone is bounded and stop closes checks", async () => {
  const f = fixture(), edges = [], contexts = [];
  class AudioContext {
    constructor() { this.state = "running"; this.currentTime = 0; this.destination = { kind: "destination" }; contexts.push(this); }
    createMediaStreamSource() { this.source = { kind: "microphone", connect: target => edges.push(["microphone", target.kind]), disconnect() {} }; return this.source; }
    createAnalyser() { return { kind: "analyser", fftSize: 0, getByteTimeDomainData: values => values.fill(160), disconnect() {} }; }
    createGain() { return { kind: "gain", gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect: target => edges.push(["gain", target.kind]), disconnect() {} }; }
    createOscillator() { const oscillator = { kind: "tone", frequency: { value: 0 }, connect: target => edges.push(["tone", target.kind]), start: () => { oscillator.started = true; }, stop: when => { oscillator.stopAt = when; }, disconnect() {} }; this.oscillator = oscillator; return oscillator; }
    resume() { return Promise.resolve(); } close() { this.closed = true; return Promise.resolve(); }
  }
  f.context.window.AudioContext = AudioContext;
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request }); await f.conference.start();
  assert.deepEqual(edges, [["microphone", "analyser"]]);
  assert.ok(walk(f.root).find(e => e.tagName === "meter").value > 0);
  await walk(f.root).find(e => e.textContent === "Test speaker").listeners.click();
  assert.equal(contexts[0].oscillator.started, true);
  assert.ok(contexts[0].oscillator.stopAt > 0 && contexts[0].oscillator.stopAt <= 1);
  assert.ok(!edges.some(([from, to]) => from === "microphone" && to === "destination"));
  f.state.windowEvents.hashchange(); assert.equal(contexts[0].closed, true); assert.equal(f.state.timers.length, 0);
  assert.ok(f.state.tracks.every(track => track.stopped));
});

test("created to active mount never autojoins; explicit second click reuses capture", async () => {
  const f = fixture();
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request }); await f.conference.start();
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "active", request: f.request });
  assert.equal(f.state.requests.length, 0); assert.equal(f.state.mediaCalls, 1);
  await f.conference.start();
  assert.equal(f.state.mediaCalls, 1); assert.equal(f.state.requests.filter(r => r.path.endsWith("/join")).length, 1);
  assert.equal(f.conference.connected(), true); await f.conference.stop();
});

test("created capture intent stays local when lesson becomes active before permission grant", async () => {
  const f = fixture({ deferMedia: true }); f.state.peers = [{ id: "A", connection_id: "a" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request });
  const checking = f.conference.start();
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "active", request: f.request });
  f.release(); await checking;
  assert.equal(f.state.requests.length, 0); assert.equal(f.state.pcs.length, 0);
  assert.equal(f.conference.connected(), false); assert.equal(f.state.mediaCalls, 1);
  await f.conference.start();
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/join")).length, 1);
  assert.equal(f.state.pcs.length, 1); assert.equal(f.state.mediaCalls, 1);
  await f.conference.stop();
});

test("local preview is visible before a pending lesson join resolves", async () => {
  const f = fixture(); let resolveJoin;
  f.state.joinReply = new Promise(resolve => { resolveJoin = resolve; });
  const joining = new Promise(resolve => { f.state.onJoin = resolve; });
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); const starting = f.conference.start();
  await joining;
  assert.ok(walk(f.root).some(e => e.tagName === "video" && e.srcObject));
  resolveJoin({ self: "M", connection_id: "m-current", peers: [], cursor: 0 }); await starting; await f.conference.stop();
});

test("capture deadline ends waiting and a late permission grant is stopped", async () => {
  const f = fixture({ deferMedia: true });
  f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request }); const starting = f.conference.start();
  assert.ok(f.state.timers.some(fn => fn.delay >= 10000));
  f.state.timers.find(fn => fn.delay >= 10000)(); await starting;
  assert.ok(walk(f.root).some(e => /permission.*timed out/i.test(e.textContent)));
  f.release(); await Promise.resolve(); await Promise.resolve();
  assert.ok(f.state.tracks.every(t => t.stopped)); assert.equal(f.state.requests.length, 0);
});

test("device absence and denied permission have distinct actionable messages", async () => {
  for (const [name, expected] of [["NotFoundError", /camera or microphone.*not found/i], ["NotAllowedError", /permission.*denied/i]]) {
    const f = fixture(); f.context.navigator.mediaDevices.getUserMedia = async () => { const error = new Error(name); error.name = name; throw error; };
    f.conference.mount(f.root, { sid: "lesson", userId: "M", state: "created", request: f.request }); await f.conference.start();
    assert.ok(walk(f.root).some(e => expected.test(e.textContent))); assert.equal(f.state.requests.length, 0);
  }
});

test("hangup during permission prompt stops late tracks and never joins", async () => {
  const f = fixture({ deferMedia: true }); f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request });
  const starting = f.conference.start(); await f.conference.stop(); f.release(); await starting;
  assert.ok(f.state.tracks.every(t => t.stopped));
  assert.equal(f.state.requests.filter(r => r.path.endsWith("/join")).length, 0);
});

test("ICE received before SDP waits; polite collision answers and stale generation is ignored", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a-current" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  const pc = f.state.pcs[0]; await pc.onnegotiationneeded();
  f.state.events = [
    { id: 1, from: "A", from_connection: "old", candidate: { candidate: "stale" } },
    { id: 2, from: "A", from_connection: "a-current", candidate: { candidate: "valid" } },
    { id: 3, from: "A", from_connection: "a-current", description: { type: "offer", sdp: "remote" } },
  ];
  await f.state.timers.shift()();
  assert.equal(pc.remoteDescription.sdp, "remote");
  assert.equal(pc.candidates.length, 1);
  assert.equal(pc.candidates[0].candidate, "valid");
  assert.ok(f.state.requests.some(r => r.body?.description?.type === "answer"));
  await f.conference.stop();
});

test("repeated mount keeps active capture and moving meeting closes it", async () => {
  const f = fixture(); f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request });
  assert.equal(f.state.mediaCalls, 1);
  f.conference.mount(f.root, { sid: "next", userId: "M", request: f.request });
  assert.ok(f.state.tracks.every(t => t.stopped));
});

test("a peer reconnect during negotiation does not hang up the remaining lesson", async () => {
  const f = fixture(); f.state.peers = [{ id: "A", connection_id: "a-current" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  f.state.failSignal = "conference_recipient_reconnected";
  await f.state.pcs[0].onnegotiationneeded();
  assert.ok(f.state.tracks.every(t => !t.stopped));
  assert.equal(f.state.pcs[0].closed, true);
  f.state.failSignal = null; f.state.peers = [{ id: "A", connection_id: "a-new" }];
  await f.state.timers.shift()();
  assert.equal(f.state.pcs.length, 2);
  await f.conference.stop();
});

for (const [lang, muteLabel, unmuteLabel, cameraOff, cameraOn] of [
  ["en", "Mute", "Unmute", "Camera off", "Camera on"],
  ["ru", "Выключить микрофон", "Включить микрофон", "Выключить камеру", "Включить камеру"],
]) test(`local mic and camera toggles preserve remote media and expose state (${lang})`, async () => {
  const f = fixture({ lang }); f.state.peers = [{ id: "A", connection_id: "a-current" }];
  f.conference.mount(f.root, { sid: "lesson", userId: "M", request: f.request }); await f.conference.start();
  const walk = element => [element, ...element.children.flatMap(walk)];
  const mute = walk(f.root).find(e => e.textContent === muteLabel);
  const camera = walk(f.root).find(e => e.textContent === cameraOff);
  const remoteTrack = { kind: "audio", enabled: true, stopped: false };
  const remoteStream = { getTracks: () => [remoteTrack] };
  f.state.pcs[0].ontrack({ streams: [remoteStream], track: remoteTrack });
  assert.equal(mute["aria-pressed"], "false");
  assert.equal(camera["aria-pressed"], "false");
  mute.listeners.click();
  assert.equal(f.state.tracks[0].enabled, false);
  assert.equal(f.state.tracks[1].enabled, true);
  assert.equal(mute.textContent, unmuteLabel);
  assert.equal(mute["aria-label"], unmuteLabel);
  assert.equal(mute["aria-pressed"], "true");
  camera.listeners.click();
  assert.equal(f.state.tracks[1].enabled, false);
  assert.equal(camera.textContent, cameraOn);
  assert.equal(camera["aria-label"], cameraOn);
  assert.equal(camera["aria-pressed"], "true");
  assert.equal(remoteTrack.enabled, true);
  assert.equal(remoteTrack.stopped, false);
  assert.ok(f.state.tracks.every(t => !t.stopped));
  assert.equal(f.state.pcs[0].closed, undefined);
  mute.listeners.click(); camera.listeners.click();
  assert.ok(f.state.tracks.every(t => t.enabled));
  assert.equal(mute.textContent, muteLabel);
  assert.equal(camera.textContent, cameraOff);
  await f.conference.stop();
});
