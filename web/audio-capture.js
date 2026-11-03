"use strict";

window.SomAudio = (() => {
  function wav(samples, rate = 16000) {
    const data = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(data);
    const text = (offset, value) => [...value].forEach((letter, i) => view.setUint8(offset + i, letter.charCodeAt(0)));
    text(0, "RIFF"); view.setUint32(4, data.byteLength - 8, true); text(8, "WAVE");
    text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    text(36, "data"); view.setUint32(40, samples.length * 2, true);
    samples.forEach((sample, index) => {
      const value = Math.max(-1, Math.min(1, sample));
      view.setInt16(44 + index * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
    });
    return new Uint8Array(data);
  }

  async function start(signal) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw Error("microphone_unavailable");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const closeTracks = () => stream.getTracks().forEach(track => track.stop());
    if (signal.aborted) { closeTracks(); throw Error("recording_cancelled"); }
    let recorder;
    try { recorder = new MediaRecorder(stream); }
    catch (error) { closeTracks(); throw error; }
    const chunks = [];
    const stop = () => { if (recorder.state !== "inactive") recorder.stop(); };
    const result = new Promise((resolve, reject) => {
      const timer = setTimeout(stop, 10000);
      signal.addEventListener("abort", stop, { once: true });
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onerror = () => { clearTimeout(timer); closeTracks(); reject(Error("recording_failed")); };
      recorder.onstop = async () => {
        clearTimeout(timer);
        signal.removeEventListener("abort", stop);
        closeTracks();
        if (signal.aborted) { reject(Error("recording_cancelled")); return; }
        const Context = window.AudioContext || window.webkitAudioContext;
        let context;
        try {
          context = new Context();
          const input = await context.decodeAudioData(await new Blob(chunks).arrayBuffer());
          if (input.duration <= 0 || input.duration > 11) throw Error("recording_too_long");
          const output = new OfflineAudioContext(1, Math.ceil(input.duration * 16000), 16000);
          const source = output.createBufferSource();
          source.buffer = input; source.connect(output.destination); source.start();
          const rendered = await output.startRendering();
          if (signal.aborted) throw Error("recording_cancelled");
          const bytes = wav(rendered.getChannelData(0));
          let binary = "";
          for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
          resolve(btoa(binary));
        } catch (error) { reject(error); }
        finally { if (context) await context.close(); }
      };
      try { recorder.start(); }
      catch (error) { clearTimeout(timer); closeTracks(); reject(error); }
    });
    return { stop, result };
  }
  return { start, wav };
})();
