"use strict";

// Participant capabilities stay in memory. There is no direct participant-to-
// participant audio route: ingress publishes only to the private server room.
window.SomMedia = (() => {
  let current = null, loading = null, intent = null, operation = Promise.resolve();
  const pendingCleanup = new Set();
  function enqueue(work) {
    const result = operation.then(work, work);
    operation = result.catch(() => {});
    return result;
  }
  const changed = () => window.dispatchEvent(new Event("som-media-changed"));
  const aborted = () => new DOMException("Media operation cancelled", "AbortError");
  function sdk() {
    if (window.LivekitClient) return Promise.resolve(window.LivekitClient);
    if (!loading) loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/vendor/livekit-client-2.23.0.umd.js";
      script.onload = () => resolve(window.LivekitClient);
      script.onerror = () => { loading = null; script.remove(); reject(new Error("media_client_unavailable")); };
      document.head.appendChild(script);
    });
    return loading;
  }
  async function request(sid, path, body = {}, keepalive = false) {
    const response = await fetch(`/api/harness/sessions/${encodeURIComponent(sid)}/media/${path}`, {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), keepalive,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "media_request_failed");
    return result;
  }
  function mount() {
    const slot = document.querySelector("[data-harness-media-audio]");
    if (slot && current) for (const element of current.audio) slot.appendChild(element);
  }
  function cleanup(session, leave) {
    if (!session) return Promise.resolve();
    if (current === session) current = null;
    clearInterval(session.heartbeat);
    if (!session.localClosing) {
      if (session.cancelRecording) session.cancelRecording();
      for (const element of session.audio) { element.pause(); element.srcObject = null; element.remove(); }
      session.audio.clear();
    }
    session.leaveWanted = session.leaveWanted || leave;
    // Start keepalive while the page still exists, before any SDK await.
    if (session.leaveWanted && !session.leaving) {
      const leaving = request(session.sid, "leave", { generation: session.generation }, true);
      session.leaving = leaving;
      leaving.catch(() => { if (session.leaving === leaving) session.leaving = null; });
    }
    if (!session.localClosing) session.localClosing = Promise.allSettled([session.ingress.disconnect(), session.playback.disconnect()]);
    pendingCleanup.add(session);
    const pending = Promise.all([session.localClosing, session.leaving || Promise.resolve()]);
    session.cleanupTask = pending;
    pending.then(() => { if (session.cleanupTask === pending) pendingCleanup.delete(session); }, () => {});
    changed();
    return pending;
  }
  async function drainCleanup() {
    await Promise.all(Array.from(pendingCleanup, session => cleanup(session, session.leaveWanted)));
  }
  function connect(sid) {
    if (current?.sid === sid && connected()) return;
    const attempt = {}; intent = attempt;
    return enqueue(async () => {
    await cleanup(current, true); await drainCleanup();
    if (intent !== attempt) throw aborted();
    const L = await sdk();
    if (intent !== attempt) throw aborted();
    const config = await request(sid, "join");
    const session = { sid, generation: config.generation, audio: new Set(), ingress: new L.Room(), playback: new L.Room(), cancelRecording: null };
    if (intent !== attempt) { await cleanup(session, true); throw aborted(); }
    current = session;
    session.playback.on(L.RoomEvent.TrackSubscribed, track => {
      if (track.kind !== L.Track.Kind.Audio || current !== session) return;
      const element = track.attach(); element.controls = true; element.style.maxWidth = "100%";
      element.setAttribute("aria-label", "Muse voice"); session.audio.add(element); mount();
    });
    session.playback.on(L.RoomEvent.TrackUnsubscribed, track => {
      for (const element of track.detach()) { session.audio.delete(element); element.remove(); }
    });
    const dropped = () => { if (current === session) cleanup(session, true).catch(() => {}); };
    session.ingress.on(L.RoomEvent.Disconnected, dropped);
    session.playback.on(L.RoomEvent.Disconnected, dropped);
    try {
      await Promise.all([
        session.ingress.connect(config.url, config.ingress.token, { autoSubscribe: false }),
        session.playback.connect(config.url, config.playback.token, { autoSubscribe: true }),
      ]);
      if (current !== session || intent !== attempt) throw aborted();
      await session.playback.startAudio();
      if (current !== session || intent !== attempt) throw aborted();
      session.heartbeat = setInterval(async () => {
        if (current !== session) return;
        try {
          const response = await fetch(`/api/harness/sessions/${encodeURIComponent(sid)}/media/status`, { credentials: "same-origin" });
          if (!response.ok || (await response.json()).state !== "active") await cleanup(session, true);
        } catch (_) { /* The RTC disconnect event handles a lost connection. */ }
      }, 15000);
      mount(); changed();
    } catch (error) {
      await cleanup(session, true).catch(() => {});
      throw error;
    }
    });
  }
  function connected(sid) {
    return !!current && (!sid || current.sid === sid) && current.ingress.state === "connected" && current.playback.state === "connected";
  }
  function disconnect(leave = true) {
    intent = null;
    const immediate = cleanup(current, leave);
    immediate.catch(() => {});
    return enqueue(async () => { await immediate; await cleanup(current, leave); await drainCleanup(); });
  }
  async function record(signal) {
    if (!connected()) throw new Error("media_not_connected");
    const session = current, L = await sdk(), id = crypto.randomUUID();
    if (signal.aborted || current !== session) throw aborted();
    let track = null, started = false, stopped = false, timer = null;
    let resolve, reject;
    const result = new Promise((ok, fail) => { resolve = ok; reject = fail; });
    result.catch(() => {}); // Abort may happen before the capture handle is returned.
    async function finish(cancel) {
      if (stopped) return;
      stopped = true; clearTimeout(timer); signal.removeEventListener("abort", cancelRecording);
      session.cancelRecording = null;
      try {
        if (track) { track.stop(); await session.ingress.localParticipant.unpublishTrack(track); }
        if (cancel) {
          if (started) await request(session.sid, `recordings/${id}/cancel`, {}, true);
          reject(aborted());
        } else resolve(await request(session.sid, `recordings/${id}/stop`));
      } catch (error) { if (track) track.stop(); reject(error); }
    }
    const cancelRecording = () => { finish(true).catch(() => {}); };
    signal.addEventListener("abort", cancelRecording, { once: true });
    session.cancelRecording = cancelRecording;
    try {
      track = await L.createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true, autoGainControl: true });
      if (signal.aborted || stopped || current !== session) { track.stop(); throw aborted(); }
      await request(session.sid, "recordings", { client_event_id: id }); started = true;
      if (signal.aborted || stopped || current !== session) throw aborted();
      await session.ingress.localParticipant.publishTrack(track, { source: L.Track.Source.Microphone });
      if (signal.aborted || stopped || current !== session) throw aborted();
      // The server enforces the ten-second bound independently of this timer.
      timer = setTimeout(() => finish(false), 10000);
      return { stop: () => finish(false), result };
    } catch (error) {
      clearTimeout(timer); signal.removeEventListener("abort", cancelRecording); session.cancelRecording = null;
      if (track) { track.stop(); await session.ingress.localParticipant.unpublishTrack(track).catch(() => {}); }
      if (started) await request(session.sid, `recordings/${id}/cancel`, {}, true).catch(() => {});
      // The handle was never returned, so no caller owns this promise yet.
      result.catch(() => {}); reject(error); throw error;
    }
  }
  async function say(mid) {
    if (!connected()) throw new Error("media_not_connected");
    return request(current.sid, "speech/" + encodeURIComponent(mid), { client_event_id: crypto.randomUUID() });
  }
  window.addEventListener("pagehide", () => { disconnect(true).catch(() => {}); });
  return { connect, disconnect, connected, record, say, mount };
})();
