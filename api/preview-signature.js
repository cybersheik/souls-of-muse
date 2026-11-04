"use strict";
/* Vercel serverless: NON-authoritative signature preview.
   Recomputes DW1 v2 notes with the same pure module the browser uses.
   It does NOT sign, store, authenticate or confirm anything: signing requires
   the future backend (DB record + server timestamp + convention text hash). */
const sig = require("../web/signature.js");

function preview(body) {
  const name = typeof body?.name === "string" ? body.name : "";
  const reading = typeof body?.reading === "string" ? body.reading : "";
  if (!name.trim()) return { status: 400, json: { error: "name_required", message: "Укажите имя или псевдоним." } };
  if (Array.from(name).length > 200) return { status: 400, json: { error: "name_too_long" } };
  const p = sig.previewSignature(name, reading);
  return { status: 200, json: { authoritative: false, kind: "preview_only",
    message: "Предпросмотр: это не подпись и не подтверждение подписания.",
    algo_version: p.algo_version, original_name: p.original_name, reading: p.reading,
    need_reading: p.need_reading, latin: p.latin, truncated: p.truncated,
    notes: p.notes.map(n => ({ note: n.note, octave: n.octave, dur: n.dur, ch: n.ch, midi: n.midi })),
    note_names_ru: p.note_names_ru } };
}
function handler(req, res) {
  if (req.method !== "POST") { res.status(405).json({ error: "method_not_allowed" }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const out = preview(body || {});
  res.status(out.status).json(out.json);
}
module.exports = handler;
module.exports.preview = preview;
