const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

test("browser capture encodes mono 16kHz PCM WAV with correct clipping and byte order", () => {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(require.resolve("../web/audio-capture.js"), "utf8"), context);
  const bytes = context.window.SomAudio.wav(new Float32Array([-2, -1, 0, 1, 2]));
  const buffer = Buffer.from(bytes);
  assert.equal(buffer.toString("ascii", 0, 4), "RIFF");
  assert.equal(buffer.toString("ascii", 8, 12), "WAVE");
  assert.equal(buffer.readUInt32LE(24), 16000);
  assert.equal(buffer.readUInt16LE(22), 1);
  assert.equal(buffer.readUInt16LE(34), 16);
  assert.equal(buffer.readUInt32LE(40), 10);
  assert.deepEqual([0, 1, 2, 3, 4].map(i => buffer.readInt16LE(44 + i * 2)), [-32768, -32768, 0, 32767, 32767]);
});
