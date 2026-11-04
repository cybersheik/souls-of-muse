"use strict";

// Direct browser mesh. HTTP carries bounded SDP/ICE only; it never carries media.
// No STUN/TURN is configured by default: this is suitable for a common LAN.
// The host may supply standard STUN servers. A TURN relay is not provided here.
window.SomConference = (() => {
  let binding = null, active = null, panel = null, view = null, message = "";
  const word = (en, ru) => window.P01?.state.lang === "ru" ? ru : en;
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }
  function button(text, action) {
    const element = node("button", "som-conference-button", text);
    element.type = "button";
    element.addEventListener("click", () => Promise.resolve(action()).catch(error => status(error.message)));
    return element;
  }
  function status(text) { message = text || ""; if (view) view.status.textContent = message; }
  function alive(session) { return active === session && !session.closed; }
  function tile(label, local = false) {
    const card = node("figure", "som-conference-tile");
    const video = node("video", "som-conference-video");
    video.autoplay = true; video.playsInline = true; video.muted = local;
    video.setAttribute("playsinline", "");
    video.setAttribute("aria-label", label);
    const caption = node("figcaption", "som-conference-caption", label);
    card.appendChild(video); card.appendChild(caption);
    return { card, video, caption };
  }
  function play(video) { const result = video.play(); if (result?.catch) result.catch(() => status(word("Press Enable sound to hear the lesson.", "Нажмите «Включить звук», чтобы слышать урок."))); }
  function controls() {
    if (!view) return;
    const busy = active && ["capturing", "joining"].includes(active.phase);
    const created = (active?.config || binding)?.state === "created";
    view.start.disabled = !!busy || !!active?.connectionId || (!!active?.stream && created);
    view.start.textContent = active?.stream && !active.connectionId && !created
      ? word("Connect to lesson", "Подключиться к уроку")
      : created ? word("Check camera & microphone", "Проверить камеру и микрофон") : word("Connect camera & microphone", "Подключить камеру и микрофон");
    view.hangup.disabled = !active;
    view.mute.disabled = !active?.stream;
    view.camera.disabled = !active?.stream;
    view.switchCamera.disabled = !active?.stream || !!active?.switching;
    view.mute.textContent = active?.muted ? word("Unmute", "Включить микрофон") : word("Mute", "Выключить микрофон");
    view.camera.textContent = active?.cameraOff ? word("Camera on", "Включить камеру") : word("Camera off", "Выключить камеру");
    view.mute.setAttribute("aria-label", view.mute.textContent);
    view.camera.setAttribute("aria-label", view.camera.textContent);
    view.mute.setAttribute("aria-pressed", active?.muted ? "true" : "false");
    view.camera.setAttribute("aria-pressed", active?.cameraOff ? "true" : "false");
  }
  function mount(element, options) {
    if (!element) return;
    if (options) {
      if (!options.sid || !options.userId || typeof options.request !== "function") throw new Error("conference_context_required");
      if (binding && (binding.sid !== options.sid || binding.userId !== options.userId)) stop();
      binding = { ...options, state: options.state === undefined ? "active" : options.state };
      if (!["created", "active"].includes(binding.state)) { stop(); throw new Error("conference_state_invalid"); }
      if (active) active.config = { ...binding };
    }
    if (!binding) return;
    if (!panel) {
      panel = node("section", "som-conference");
      panel.setAttribute("aria-label", word("Live lesson video", "Видео урока"));
      panel.appendChild(node("h3", "som-conference-title", word("Live lesson", "Живой урок")));
      const grid = node("div", "som-conference-grid");
      const toolbar = node("div", "som-conference-controls");
      const startButton = button(word("Connect camera & microphone", "Подключить камеру и микрофон"), start);
      const hangup = button(word("Hang up", "Завершить звонок"), stop);
      const mute = button(word("Mute", "Выключить микрофон"), () => {
        if (!active?.stream) return;
        active.muted = !active.muted;
        active.stream.getAudioTracks().forEach(track => { track.enabled = !active.muted; }); controls();
      });
      const camera = button(word("Camera off", "Выключить камеру"), () => {
        if (!active?.stream) return;
        active.cameraOff = !active.cameraOff;
        active.stream.getVideoTracks().forEach(track => { track.enabled = !active.cameraOff; }); controls();
      });
      const switchCameraButton = button(word("Switch camera", "Сменить камеру"), switchCamera);
      const speaker = button(word("Test speaker", "Проверить динамик"), testSpeaker);
      const sound = button(word("Enable sound", "Включить звук"), () => {
        if (active) for (const peer of active.peers.values()) play(peer.tile.video);
      });
      [startButton, mute, camera, switchCameraButton, speaker, sound, hangup].forEach(child => toolbar.appendChild(child));
      const micCheck = node("label", "som-conference-mic-check", word("Microphone input · local only ", "Уровень микрофона · локально "));
      const micMeter = node("meter", "som-conference-mic-meter"); micMeter.min = 0; micMeter.max = 1; micMeter.value = 0;
      micMeter.setAttribute("aria-label", word("Local microphone input level", "Локальный уровень микрофона"));
      const micNote = node("span", "som-conference-mic-note", word("Connect local devices to check input.", "Подключите локальные устройства для проверки."));
      micCheck.appendChild(micMeter); micCheck.appendChild(micNote);
      const statusNode = node("p", "som-conference-status"); statusNode.setAttribute("role", "status");
      const note = node("p", "som-conference-note", word(
        "Direct connection for up to three participants. Use headphones. Some networks cannot connect without a relay.",
        "Прямой звонок до трёх участников. Используйте наушники. В некоторых сетях без ретранслятора соединение невозможно."));
      panel.appendChild(grid); panel.appendChild(toolbar); panel.appendChild(micCheck); panel.appendChild(statusNode); panel.appendChild(note);
      view = { grid, start: startButton, hangup, mute, camera, speaker, micMeter, micNote, switchCamera: switchCameraButton, status: statusNode };
    }
    element.appendChild(panel); controls(); status(message);
  }
  function request(session, path, body, options) {
    return session.config.request(`sessions/${encodeURIComponent(session.config.sid)}/conference/${path}`, body, options);
  }
  function closePeer(session, id) {
    const peer = session.peers.get(id);
    if (!peer) return;
    peer.closed = true; peer.pc.close();
    peer.tile.video.pause(); peer.tile.video.srcObject = null; peer.tile.card.remove();
    session.peers.delete(id);
  }
  async function stop() {
    const session = active;
    if (!session) return;
    active = null; session.closed = true; clearTimeout(session.timer);
    session.joinController?.abort();
    closeChecks(session);
    for (const cancel of session.pending || []) cancel();
    if (session.stream) session.stream.getTracks().forEach(track => track.stop());
    if (session.cameraCapture) session.cameraCapture.getTracks().forEach(track => track.stop());
    for (const id of Array.from(session.peers.keys())) closePeer(session, id);
    if (session.local) { session.local.video.pause(); session.local.video.srcObject = null; session.local.card.remove(); }
    controls(); status(word("Call ended. Camera and microphone are off.", "Звонок завершён. Камера и микрофон выключены."));
    if (session.connectionId) {
      try { await request(session, "leave", { connection_id: session.connectionId }); }
      catch (_) { /* The server's short lease expires even if the page was lost. */ }
    }
  }
  function closeChecks(session) {
    clearTimeout(session.meterTimer);
    try { session.speakerTone?.stop(); } catch (_) {}
    try { session.micSource?.disconnect(); session.micAnalyser?.disconnect(); } catch (_) {}
    if (session.audioContext) session.audioContext.close().catch(() => {});
    session.audioContext = null;
    if (view) { view.micMeter.value = 0; view.micNote.textContent = word("Local input check stopped.", "Локальная проверка остановлена."); }
  }
  function localChecks(session) {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) { view.micNote.textContent = word("Input meter unavailable in this browser.", "Измеритель недоступен в этом браузере."); return; }
    try {
      const context = new Context(); session.audioContext = context;
      const analyser = context.createAnalyser(); analyser.fftSize = 1024; session.micAnalyser = analyser;
      const source = context.createMediaStreamSource(session.stream); session.micSource = source;
      source.connect(analyser); // Intentionally never connected to an audio destination.
      if (context.state === "suspended") context.resume().catch(() => {});
      const values = new Uint8Array(analyser.fftSize);
      const sample = () => {
        if (!alive(session)) return;
        analyser.getByteTimeDomainData(values);
        const mean = values.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / values.length;
        view.micMeter.value = session.muted ? 0 : Math.min(1, Math.sqrt(mean) * 4);
        view.micNote.textContent = context.state === "suspended"
          ? word("Audio check paused. Click Test speaker.", "Проверка приостановлена. Нажмите «Проверить динамик».")
          : session.muted ? word("Microphone muted.", "Микрофон выключен.") : session.phase === "connected"
            ? word("Lesson microphone input level.", "Уровень микрофона урока.") : word("Local input only; not sent.", "Только локальный вход; не передаётся.");
        session.meterTimer = setTimeout(sample, 100);
      };
      sample();
    } catch (_) { closeChecks(session); view.micNote.textContent = word("Input meter unavailable in this browser.", "Измеритель недоступен в этом браузере."); }
  }
  async function testSpeaker() {
    const session = active;
    if (!session?.stream) { status(word("Check local camera and microphone first, then test the speaker.", "Сначала проверьте локальные камеру и микрофон, затем динамик.")); return; }
    const context = session.audioContext;
    if (!context) { status(word("Speaker check unavailable in this browser.", "Проверка динамика недоступна в этом браузере.")); return; }
    try {
      if (context.state === "suspended") await bounded(session, context.resume(), "speaker_timeout");
      if (!alive(session)) return;
      try { session.speakerTone?.stop(); } catch (_) {}
      const tone = context.createOscillator(), gain = context.createGain();
      tone.frequency.value = 440; gain.gain.setValueAtTime(0.05, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.25);
      tone.connect(gain); gain.connect(context.destination);
      session.speakerTone = tone;
      tone.onended = () => { tone.disconnect(); gain.disconnect(); };
      tone.start(); tone.stop(context.currentTime + 0.3);
      status(word("Short local test tone. If silent, check device volume and output.", "Короткий локальный тестовый сигнал. Если его не слышно, проверьте громкость и устройство вывода."));
    } catch (_) { if (alive(session)) status(word("Speaker check failed. Check browser audio permissions and output.", "Проверка динамика не удалась. Проверьте разрешения браузера и вывод звука.")); }
  }
  function bounded(session, promise, code, expired = () => {}) {
    let timer, cancel;
    const deadline = new Promise((_, reject) => {
      cancel = () => reject(new Error("media_operation_cancelled"));
      session.pending.add(cancel);
      timer = setTimeout(() => { expired(); reject(new Error(code)); }, 20000);
    });
    return Promise.race([promise, deadline]).finally(() => { clearTimeout(timer); session.pending.delete(cancel); });
  }
  function mediaError(error) {
    if (error?.message === "capture_timeout") return word("Camera/microphone permission timed out. Check the browser permission prompt and retry.", "Ожидание разрешения камеры и микрофона истекло. Проверьте запрос браузера и повторите.");
    if (error?.message === "join_timeout") return word("Lesson connection timed out. Camera and microphone were stopped. Retry the connection.", "Подключение к уроку не завершилось вовремя. Камера и микрофон выключены. Повторите подключение.");
    if (["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(error?.name)) return word("Camera/microphone permission denied. Allow both for this site in browser settings, then retry.", "Нет разрешения камеры или микрофона. Разрешите оба устройства для этого сайта в настройках браузера и повторите.");
    if (["NotFoundError", "DevicesNotFoundError"].includes(error?.name)) return word("Camera or microphone was not found. Connect both devices and retry.", "Камера или микрофон не найдены. Подключите оба устройства и повторите.");
    if (["NotReadableError", "TrackStartError"].includes(error?.name)) return word("Camera or microphone is unavailable or used by another app. Close that app and retry.", "Камера или микрофон недоступны либо заняты другим приложением. Закройте его и повторите.");
    if (error?.name === "OverconstrainedError") return word("The selected camera cannot provide the requested video. Choose another camera and retry.", "Камера не поддерживает выбранные параметры. Выберите другую камеру и повторите.");
    if (["AbortError", "InvalidStateError"].includes(error?.name)) return word("Device access was interrupted. Keep this page active and retry the camera/microphone check.", "Доступ к устройствам прерван. Оставьте страницу активной и повторите проверку камеры и микрофона.");
    return error?.message || "connection_failed";
  }
  async function switchCamera() {
    const session = active;
    if (!session?.stream || session.switching) return;
    const oldVideo = session.stream.getVideoTracks()[0];
    if (!oldVideo) return;
    let capture = null, newVideo = null, accepted = false;
    session.switching = true; controls();
    const videoSenders = () => Array.from(session.peers.values()).flatMap(peer => peer.pc.getSenders())
      .filter(sender => sender.track?.kind === "video");
    try {
      if (!navigator.mediaDevices?.enumerateDevices) throw new Error("camera_selection_unavailable");
      const devices = (await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === "videoinput" && device.deviceId);
      if (!alive(session)) return;
      if (devices.length < 2) { status(word("No other camera is available.", "Другой камеры нет.")); return; }
      const currentId = oldVideo.getSettings?.().deviceId || session.cameraDeviceId;
      let index = devices.findIndex(device => device.deviceId === currentId);
      if (index < 0 && oldVideo.label) index = devices.findIndex(device => device.label === oldVideo.label);
      const next = devices[(index + 1) % devices.length];
      capture = await navigator.mediaDevices.getUserMedia({ audio: false, video: { deviceId: { exact: next.deviceId } } });
      if (!alive(session)) return;
      session.cameraCapture = capture;
      newVideo = capture.getVideoTracks()[0];
      if (!newVideo) throw new Error("camera_capture_unavailable");
      capture.getTracks().filter(track => track !== newVideo).forEach(track => track.stop());
      newVideo.enabled = !session.cameraOff;
      // Recheck peers while replacing: a peer may join during a permission or
      // replaceTrack await. Audio senders and the old capture stay untouched.
      for (let round = 0; round < 3; round++) {
        const remaining = videoSenders().filter(sender => sender.track !== newVideo);
        if (!remaining.length) break;
        for (const sender of remaining) {
          await sender.replaceTrack(newVideo);
          if (!alive(session)) return;
        }
      }
      if (videoSenders().some(sender => sender.track !== newVideo)) throw new Error("camera_peers_changed");
      newVideo.enabled = !session.cameraOff;
      session.stream = new MediaStream([...session.stream.getAudioTracks(), newVideo]);
      session.local.video.srcObject = session.stream; play(session.local.video);
      session.cameraDeviceId = next.deviceId;
      accepted = true; oldVideo.stop();
      status(word("Camera selected: ", "Выбрана камера: ") + (next.label || word("next camera", "следующая камера")));
    } catch (_) {
      if (alive(session)) {
        let rollbackFailed = oldVideo.readyState === "ended";
        for (const sender of videoSenders().filter(sender => sender.track === newVideo)) {
          try { await sender.replaceTrack(oldVideo); } catch (_) { rollbackFailed = true; }
          if (!alive(session)) return;
        }
        status(rollbackFailed
          ? word("Camera change failed. Some video connections need reconnecting; audio remains connected.", "Смена камеры не удалась. Часть видео нужно переподключить; звук остаётся подключённым.")
          : word("Camera change failed. The current camera and call are retained.", "Смена камеры не удалась. Текущая камера и звонок сохранены."));
      }
    } finally {
      if (capture && !accepted) capture.getTracks().forEach(track => track.stop());
      if (session.cameraCapture === capture) session.cameraCapture = null;
      session.switching = false;
      if (alive(session)) controls();
    }
  }
  function fail(session, error) {
    if (!alive(session)) return;
    // Stop devices immediately; a failed HTTP leave must not keep them running.
    stop(); status(word("Call stopped: ", "Звонок остановлен: ") + mediaError(error));
  }
  function serial(session, peer, work) {
    const result = peer.operation.then(async () => {
      if (alive(session) && !peer.closed) return work();
    });
    peer.operation = result.catch(error => fail(session, error));
    return peer.operation;
  }
  async function signal(session, peer, payload) {
    if (!alive(session) || peer.closed) return;
    try {
      return await request(session, "signal", { connection_id: session.connectionId, to: peer.id,
        to_connection: peer.connectionId, ...payload });
    } catch (error) {
      if (/conference_recipient_reconnected|conference_recipient_not_found/.test(error.message)) {
        // A normal peer hangup/rejoin must not stop the other two people.
        if (session.peers.get(peer.id) === peer) closePeer(session, peer.id);
        return;
      }
      throw error;
    }
  }
  function addPeer(session, member) {
    const pc = new RTCPeerConnection({ iceServers: session.config.iceServers || [] });
    const remote = tile(member.id);
    const peer = { id: member.id, connectionId: member.connection_id, pc, tile: remote,
      polite: `${session.config.userId}/${session.connectionId}` > `${member.id}/${member.connection_id}`,
      makingOffer: false, ignoreOffer: false, settingAnswer: false, pendingIce: [], operation: Promise.resolve(), closed: false };
    session.peers.set(member.id, peer); view.grid.appendChild(remote.card);
    pc.ontrack = event => {
      if (!alive(session) || peer.closed) return;
      if (event.streams?.[0]) remote.video.srcObject = event.streams[0];
      else {
        if (!remote.video.srcObject) remote.video.srcObject = new MediaStream();
        if (!remote.video.srcObject.getTracks().includes(event.track)) remote.video.srcObject.addTrack(event.track);
      }
      play(remote.video);
    };
    pc.onconnectionstatechange = () => {
      if (!alive(session) || peer.closed) return;
      remote.caption.textContent = member.id + " · " + pc.connectionState;
      if (pc.connectionState === "failed") status(word(
        "A direct connection failed. Check that devices share a network, then hang up and reconnect.",
        "Прямое соединение не удалось. Проверьте общую сеть устройств, завершите звонок и подключитесь снова."));
    };
    pc.onicecandidate = event => {
      if (!alive(session) || peer.closed) return;
      const value = event.candidate;
      const candidate = value ? (value.toJSON ? value.toJSON() : {
        candidate: value.candidate, sdpMid: value.sdpMid, sdpMLineIndex: value.sdpMLineIndex, usernameFragment: value.usernameFragment }) : null;
      signal(session, peer, { candidate }).catch(error => fail(session, error));
    };
    pc.onnegotiationneeded = () => serial(session, peer, async () => {
      try {
        peer.makingOffer = true;
        await pc.setLocalDescription();
        if (!alive(session) || peer.closed) return;
        await signal(session, peer, { description: { type: pc.localDescription.type, sdp: pc.localDescription.sdp } });
      } finally { peer.makingOffer = false; }
    });
    session.stream.getTracks().forEach(track => pc.addTrack(track, session.stream));
    return peer;
  }
  function reconcile(session, peers) {
    if (!Array.isArray(peers) || peers.length > 2) throw new Error("invalid_conference_roster");
    const members = new Map();
    for (const member of peers) {
      if (typeof member.id !== "string" || member.id.length > 100 || typeof member.connection_id !== "string" || member.connection_id.length > 100 || member.id === session.config.userId) throw new Error("invalid_conference_roster");
      members.set(member.id, member);
    }
    for (const [id, peer] of session.peers) if (members.get(id)?.connection_id !== peer.connectionId) closePeer(session, id);
    for (const member of members.values()) if (!session.peers.has(member.id)) addPeer(session, member);
  }
  async function receive(session, event) {
    const peer = session.peers.get(event.from);
    if (!peer || peer.closed || event.from_connection !== peer.connectionId) return;
    return serial(session, peer, async () => {
      const pc = peer.pc;
      if (event.description) {
        const description = event.description;
        const ready = !peer.makingOffer && (pc.signalingState === "stable" || peer.settingAnswer);
        const collision = description.type === "offer" && !ready;
        peer.ignoreOffer = !peer.polite && collision;
        if (peer.ignoreOffer) { peer.pendingIce = []; return; }
        peer.settingAnswer = description.type === "answer";
        try { await pc.setRemoteDescription(description); }
        finally { peer.settingAnswer = false; }
        if (!alive(session) || peer.closed) return;
        for (const candidate of peer.pendingIce.splice(0)) await pc.addIceCandidate(candidate);
        if (description.type === "offer") {
          await pc.setLocalDescription();
          if (!alive(session) || peer.closed) return;
          await signal(session, peer, { description: { type: pc.localDescription.type, sdp: pc.localDescription.sdp } });
        }
      } else if (Object.prototype.hasOwnProperty.call(event, "candidate") && !peer.ignoreOffer) {
        if (!pc.remoteDescription) {
          if (peer.pendingIce.length >= 64) throw new Error("conference_ice_queue_full");
          peer.pendingIce.push(event.candidate);
        } else await pc.addIceCandidate(event.candidate);
      }
    });
  }
  async function poll(session) {
    if (!alive(session)) return;
    try {
      const result = await request(session, `events?connection_id=${encodeURIComponent(session.connectionId)}&after=${session.cursor}`);
      if (!alive(session)) return;
      if (result.self !== session.config.userId) throw new Error("participant_context_changed");
      reconcile(session, result.peers);
      if (!Array.isArray(result.events) || result.events.length > 128) throw new Error("invalid_conference_events");
      for (const event of result.events) {
        if (!alive(session)) return;
        await receive(session, event);
      }
      session.cursor = Math.max(session.cursor, result.cursor || 0); session.failures = 0;
    } catch (error) {
      if (!alive(session)) return;
      if (/unauthorized|participant_context|session_not|lesson_join|connection_expired/.test(error.message) || ++session.failures >= 8) {
        fail(session, error); return;
      }
      status(word("Reconnecting signalling…", "Восстанавливается связь…"));
    }
    if (alive(session)) session.timer = setTimeout(() => poll(session), 750);
  }
  async function start() {
    if (!binding || !view) throw new Error("conference_context_required");
    if (!navigator.mediaDevices?.getUserMedia) {
      status(word("Camera access requires HTTPS (or localhost) and a supported browser.", "Для камеры нужны HTTPS (или localhost) и поддерживаемый браузер.")); return;
    }
    if (active) {
      if (active.phase === "preview" && active.config.state === "active") return join(active);
      return;
    }
    const captureStartedCreated = binding.state === "created";
    const session = { config: { ...binding }, connectionId: null, stream: null, peers: new Map(), pending: new Set(), phase: "capturing", cursor: 0, failures: 0, closed: false };
    active = session; controls(); status(word("Allow camera and microphone…", "Разрешите камеру и микрофон…"));
    try {
      const capture = navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: { width: { ideal: 640 }, height: { ideal: 360 }, frameRate: { ideal: 15, max: 24 } } });
      capture.then(stream => { if (session.captureExpired || !alive(session)) stream.getTracks().forEach(track => track.stop()); }, () => {});
      const stream = await bounded(session, capture, "capture_timeout", () => { session.captureExpired = true; });
      if (!alive(session)) { stream.getTracks().forEach(track => track.stop()); return; }
      session.stream = stream;
      if (!stream.getVideoTracks().length || !stream.getAudioTracks().length) { const error = new Error("incomplete_capture"); error.name = "NotFoundError"; throw error; }
      session.local = tile(word("You · local preview", "Вы · локальная проверка"), true); session.local.video.srcObject = stream;
      view.grid.appendChild(session.local.card); play(session.local.video);
      localChecks(session);
      session.phase = "preview"; controls();
      if (captureStartedCreated) {
        status(word("Local preview only. Camera and microphone are not sent. When the lesson starts, click Connect to lesson.", "Только локальная проверка. Камера и микрофон никому не передаются. После начала урока нажмите «Подключиться к уроку»."));
        return;
      }
      await join(session);
    } catch (error) { if (alive(session)) fail(session, error); }
  }
  async function join(session) {
    if (!alive(session) || session.config.state !== "active" || session.phase !== "preview") return;
    session.phase = "joining"; controls(); status(word("Local devices ready. Connecting to lesson…", "Локальные устройства готовы. Подключаемся к уроку…"));
    const controller = new AbortController(); session.joinController = controller;
    const attempt = { expired: false, left: false };
    const cleanup = result => {
      if (!result?.connection_id || attempt.left) return;
      attempt.left = true;
      try { Promise.resolve(request(session, "leave", { connection_id: result.connection_id })).catch(() => {}); } catch (_) {}
    };
    try {
      if (typeof RTCPeerConnection !== "function") throw new Error(word("This browser can preview devices but cannot connect a WebRTC lesson.", "Браузер позволяет локальную проверку, но не поддерживает WebRTC-подключение урока."));
      const pending = request(session, "join", {}, { signal: controller.signal,
        isCurrent: () => alive(session) && !attempt.expired && !controller.signal.aborted });
      pending.then(result => { if (attempt.expired || !alive(session)) cleanup(result); }, () => {});
      const joined = await bounded(session, pending, "join_timeout", () => { attempt.expired = true; controller.abort(); });
      if (!alive(session)) { cleanup(joined); return; }
      session.connectionId = joined.connection_id;
      if (joined.self !== session.config.userId) throw new Error("participant_context_changed");
      session.cursor = joined.cursor || 0;
      session.phase = "connected";
      reconcile(session, joined.peers); controls();
      status(word("Connected to lesson. Waiting for peer video…", "Вы в уроке. Ожидание видео участников…"));
      session.timer = setTimeout(() => poll(session), 750);
    } catch (error) { if (alive(session)) fail(session, error); }
    finally { if (session.joinController === controller && !session.connectionId) session.joinController = null; }
  }
  window.addEventListener("pagehide", () => { stop(); });
  window.addEventListener("hashchange", () => { stop(); });
  window.addEventListener("som-logout", () => { stop(); });
  return { mount, start, stop, connected: () => !!active?.connectionId };
})();
