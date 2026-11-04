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
  const window = { P01: { state: { lang } }, addEventListener() {}, dispatchEvent() {} };
  const context = { window, document: { createElement: tag => new Element(tag) }, navigator: { mediaDevices: {
    enumerateDevices: async () => state.devices,
    getUserMedia: constraints => { state.mediaCalls++; state.mediaRequests.push(constraints); if (state.mediaCalls > 1) state.onNextMedia?.(); return state.mediaCalls === 1 ? media : state.nextMedia; }
  } },
    RTCPeerConnection: PC, MediaStream: class { constructor(t = []) { this.tracks = t; } addTrack(t) { this.tracks.push(t); } getTracks() { return this.tracks; } getAudioTracks() { return this.tracks.filter(t => t.kind === "audio"); } getVideoTracks() { return this.tracks.filter(t => t.kind === "video"); } },
    setTimeout: fn => { state.timers.push(fn); return state.timers.length; }, clearTimeout() {}, Event: class {}, console, URLSearchParams };
  vm.runInNewContext(fs.readFileSync(require.resolve("../web/conference-client.js"), "utf8"), context);
  const request = async (path, body) => {
    state.requests.push({ path, body });
    if (path.endsWith("/join")) return { self: "M", connection_id: "m-current", peers: state.peers, cursor: 0 };
    if (path.endsWith("/signal") && state.failSignal) throw new Error(state.failSignal);
    if (path.includes("/events?")) { const events = state.events; state.events = []; return { self: "M", peers: state.peers, events, cursor: events.at(-1)?.id || 0 }; }
    return { ok: true };
  };
  const root = new Element("div");
  return { conference: window.SomConference, state, root, request, release };
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
