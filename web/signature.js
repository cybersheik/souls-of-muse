/* Souls of Muse — DW1 musical signature v2, canonical core extracted verbatim from
   references/signature-v2.html (SHA-256 175e3e908f6babab84edd2c4b363b18fe39d43276960a4b74dfdc7227cc3c237).
   Pure functions: normalizeName, buildMelody, layoutScore. UMD: browser global SoulSignature + Node module. */
"use strict";
const ALGO_VERSION = "dw1-signature-v2";

const MAX_LEN = 40;
const TRANSLIT = {
  "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
  "ә":"a","ғ":"g","қ":"q","ң":"ng","ө":"o","ұ":"u","ү":"u","һ":"h","і":"i",
  "є":"ye","ї":"yi","ґ":"g","ў":"u",
  "đ":"d","ß":"ss","æ":"ae","œ":"oe","ø":"o","ł":"l","þ":"th","ð":"d","ı":"i"
};
const CYR = /[Ѐ-ӿ]/;
const SEPS = new Set([" ", "_", ".", "-", " ", "–", "—", "　", "・"]);
const NOTE_COLS = ["A","B","C","D","E","F","G"];
const NAT = { C:0, D:1, E:2, F:3, G:4, A:5, B:6 };
const SEMI = [0, 2, 4, 5, 7, 9, 11];
const RU = { C:"до", D:"ре", E:"ми", F:"фа", G:"соль", A:"ля", B:"си" };
const DIGIT_NOTE = { "1":"C","2":"D","3":"E","4":"F","5":"G","6":"A","7":"B","8":"C","9":"D","0":"E" };
const LOW = 28, HIGH = 40, MID = 34; // C4 .. A5, centre B4 (diatonic step = octave*7 + NAT)

/* Korean note names 가 나 다 라 마 바 사 = A..G: the 14 basic consonants in dictionary order, two rows of seven */
const KO_GRID = ["ㄱㄴㄷㄹㅁㅂㅅ", "ㅇㅈㅊㅋㅌㅍㅎ"];
const KO_NOTE_NAMES = ["가","나","다","라","마","바","사"];
const KO_INI = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"];
const KO_TENSE = { "ㄲ":"ㄱ", "ㄸ":"ㄷ", "ㅃ":"ㅂ", "ㅆ":"ㅅ", "ㅉ":"ㅈ" };
const RR_INI = ["g","kk","n","d","tt","r","m","b","pp","s","ss","","j","jj","ch","k","t","p","h"];
const RR_VOW = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"];
const RR_FIN = ["","k","k","k","n","n","n","t","l","k","m","l","l","l","p","l","m","p","p","t","t","ng","t","t","k","t","p","t"];

/* Japanese note names イ ロ ハ ニ ホ ヘ ト = A..G: the iroha poem in rows of seven */
const IROHA = ["いろはにほへと", "ちりぬるをわか", "よたれそつねな", "らむうゐのおく", "やまけふこえて", "あさきゆめみし", "ゑひもせすん"];
const JA_NOTE_NAMES = ["イ","ロ","ハ","ニ","ホ","ヘ","ト"];
const SMALL_JOIN = "ゃゅょぁぃぅぇぉゎ";
const SMALL_BIG = { "ゃ":"や","ゅ":"ゆ","ょ":"よ","ぁ":"あ","ぃ":"い","ぅ":"う","ぇ":"え","ぉ":"お","ゎ":"わ","ゕ":"か","ゖ":"け" };
const ROMA = {
  "あ":"a","い":"i","う":"u","え":"e","お":"o","か":"ka","き":"ki","く":"ku","け":"ke","こ":"ko",
  "さ":"sa","し":"shi","す":"su","せ":"se","そ":"so","た":"ta","ち":"chi","つ":"tsu","て":"te","と":"to",
  "な":"na","に":"ni","ぬ":"nu","ね":"ne","の":"no","は":"ha","ひ":"hi","ふ":"fu","へ":"he","ほ":"ho",
  "ま":"ma","み":"mi","む":"mu","め":"me","も":"mo","や":"ya","ゆ":"yu","よ":"yo",
  "ら":"ra","り":"ri","る":"ru","れ":"re","ろ":"ro","わ":"wa","ゐ":"i","ゑ":"e","を":"o","ん":"n",
  "が":"ga","ぎ":"gi","ぐ":"gu","げ":"ge","ご":"go","ざ":"za","じ":"ji","ず":"zu","ぜ":"ze","ぞ":"zo",
  "だ":"da","ぢ":"ji","づ":"zu","で":"de","ど":"do","ば":"ba","び":"bi","ぶ":"bu","べ":"be","ぼ":"bo",
  "ぱ":"pa","ぴ":"pi","ぷ":"pu","ぺ":"pe","ぽ":"po","ゔ":"vu",
  "ぁ":"a","ぃ":"i","ぅ":"u","ぇ":"e","ぉ":"o","ゃ":"ya","ゅ":"yu","ょ":"yo","ゎ":"wa","ゕ":"ka","ゖ":"ke"
};

function gridPos(grid, key) {
  const rows = grid === "ko" ? KO_GRID : grid === "ja" ? IROHA : null;
  if (!rows) return null;
  for (let r = 0; r < rows.length; r++) { const c = Array.from(rows[r]).indexOf(key); if (c >= 0) return { row: r, col: c }; }
  return null;
}
const isHan = ch => /\p{Script=Han}/u.test(ch);
function toHira(ch) { const c = ch.codePointAt(0); return (c >= 0x30A1 && c <= 0x30F6) ? String.fromCodePoint(c - 0x60) : ch; }
function isKana(h) { const c = h.codePointAt(0); return (c >= 0x3041 && c <= 0x3096) || h === "ー"; }
function hangulParts(ch) { const i = ch.codePointAt(0) - 0xAC00; return { L: Math.floor(i / 588), V: Math.floor((i % 588) / 28), T: i % 28 }; }
function rrSyllable(ch) { const p = hangulParts(ch); return RR_INI[p.L] + RR_VOW[p.V] + RR_FIN[p.T]; }
function kanaToRomaji(s) {
  const a = Array.from(s); let out = "";
  for (let i = 0; i < a.length; i++) {
    const c = a[i], n = a[i + 1];
    if (c === "ー") continue;
    if (c === "っ") { const r = n ? (ROMA[n] || "") : ""; if (r) out += r.startsWith("ch") ? "t" : r[0]; continue; }
    let r = ROMA[c] || "";
    if (n && "ゃゅょ".includes(n) && r.length > 1 && r.endsWith("i")) {
      r = (["shi", "chi", "ji"].includes(r) ? r.slice(0, -1) : r.slice(0, -1) + "y") + ROMA[n].slice(1); i++;
    } else if (n && "ぁぃぅぇぉ".includes(n) && r.length > 1) { r = r.slice(0, -1) + ROMA[n]; i++; }
    out += r;
  }
  return out;
}
function latNote(c) {
  if (/[0-9]/.test(c)) return DIGIT_NOTE[c];
  if (c === "H") return "B";
  return NOTE_COLS[(c.charCodeAt(0) - 65) % 7];
}

/* Every token is one note: a Latin letter, a Hangul syllable, or a kana mora. */
function normalizeName(raw) {
  let chars = Array.from(String(raw).normalize("NFKC"));
  const truncated = chars.length > MAX_LEN ? chars.slice(MAX_LEN).join("") : "";
  chars = chars.slice(0, MAX_LEN);
  const trace = [], words = [], roms = [];
  let cur = [], rom = [], kanaBuf = "", hasHan = false;
  const flushKana = () => { if (kanaBuf) { rom.push(kanaToRomaji(kanaBuf)); kanaBuf = ""; } };
  const flush = () => { flushKana(); if (cur.length) { words.push(cur); roms.push(rom.join("")); } cur = []; rom = []; };
  for (const ch of chars) {
    if (SEPS.has(ch) || /\s/u.test(ch)) { trace.push({ src: ch, out: "", kind: "sep" }); flush(); continue; }
    const code = ch.codePointAt(0);
    if (code >= 0xAC00 && code <= 0xD7A3) {                       // Hangul syllable
      flushKana();
      const ini = KO_INI[hangulParts(ch).L], key = KO_TENSE[ini] || ini, pos = gridPos("ko", key), r = rrSyllable(ch);
      trace.push({ src: ch, out: ini, kind: "hangul", rom: r });
      cur.push({ label: ch, grid: "ko", key, note: NOTE_COLS[pos.col] });
      rom.push(r); continue;
    }
    if (code >= 0x3131 && code <= 0x314E) {                       // standalone Hangul consonant
      flushKana();
      const key = KO_TENSE[ch] || ch, pos = gridPos("ko", key);
      if (pos) { trace.push({ src: ch, out: key, kind: "hangul", rom: "" }); cur.push({ label: ch, grid: "ko", key, note: NOTE_COLS[pos.col] }); }
      else trace.push({ src: ch, out: "", kind: "drop" });
      continue;
    }
    const h = toHira(ch);
    if (isKana(h)) {                                               // kana: one mora, one note
      const last = cur[cur.length - 1], lastJa = last && last.grid === "ja";
      if (h === "ー") { if (lastJa) { last.long = true; last.label += ch; } trace.push({ src: ch, out: "", kind: "long" }); kanaBuf += h; continue; }
      if (h === "っ") { trace.push({ src: ch, out: "", kind: "pause" }); kanaBuf += h; continue; }
      if (SMALL_JOIN.includes(h) && lastJa) { last.label += ch; trace.push({ src: ch, out: "", kind: "join" }); kanaBuf += h; continue; }
      const key = (SMALL_BIG[h] || h).normalize("NFD").replace(/[゙゚]/g, "");
      const pos = gridPos("ja", key);
      if (!pos) { trace.push({ src: ch, out: "", kind: "drop" }); continue; }
      trace.push({ src: ch, out: key, kind: "kana", rom: ROMA[h] || "" });
      cur.push({ label: ch, grid: "ja", key, note: NOTE_COLS[pos.col] });
      kanaBuf += h; continue;
    }
    flushKana();
    if (isHan(ch)) { hasHan = true; trace.push({ src: ch, out: "", kind: "han" }); continue; }
    const lower = ch.toLowerCase();
    let out = "", kind;
    if (Object.prototype.hasOwnProperty.call(TRANSLIT, lower)) {
      out = TRANSLIT[lower].toUpperCase();
      kind = out ? (CYR.test(lower) ? "translit" : "diacritic") : "silent";
    } else if (/^[a-z]$/.test(lower)) { out = lower.toUpperCase(); kind = "kept"; }
    else if (/^[0-9]$/.test(ch)) { out = ch; kind = "digit"; }
    else {
      const base = lower.normalize("NFD").replace(/[̀-ͯ]/g, "");
      if (/^[a-z]+$/.test(base)) { out = base.toUpperCase(); kind = "diacritic"; }
      else kind = "drop";
    }
    trace.push({ src: ch, out, kind });
    for (const c of out) cur.push({ label: c, grid: /[0-9]/.test(c) ? "digit" : "lat", key: c, note: latNote(c) });
    if (out) rom.push(out.toLowerCase());
  }
  flush();
  const latin = roms.filter(Boolean).map(w => w[0].toUpperCase() + w.slice(1)).join(" ");
  return { trace, words, truncated, hasHan, latin };
}

function buildMelody(words) {
  const notes = [];
  let prev = null;
  words.forEach((word, wi) => {
    word.forEach((T, li) => {
      const cands = [];
      for (let oct = 3; oct <= 6; oct++) {
        const s = oct * 7 + NAT[T.note];
        if (s >= LOW && s <= HIGH) cands.push(s);
      }
      let step;
      if (prev === null) step = cands.find(s => s >= 30 && s <= 36);
      else step = cands.reduce((best, s) => {
        const d = Math.abs(s - prev), bd = Math.abs(best - prev);
        if (d < bd) return s;
        if (d === bd && Math.abs(s - MID) < Math.abs(best - MID)) return s;
        return best;
      });
      prev = step;
      const oct = Math.floor(step / 7);
      notes.push({
        ch: T.label, grid: T.grid, key: T.key, note: T.note,
        step, octave: oct, midi: (oct + 1) * 12 + SEMI[NAT[T.note]],
        dur: (li === word.length - 1 || T.long) ? 2 : 1,
        wordStart: li === 0 && wi > 0, word: wi
      });
    });
  });
  return notes;
}

/* Score geometry shared by the SVG and the card canvas. Units: staff gap = 10. */
function layoutScore(notes, opts) {
  const o = Object.assign({ perRow: 16, q: 30, h: 46, wordGap: 14, clefW: 40, rowH: 112, padEnd: 22 }, opts || {});
  const rows = [];
  let row = [], count = 0;
  const words = [];
  notes.forEach(n => { if (!words[n.word]) words[n.word] = []; words[n.word].push(n); });
  for (const w of words) {
    if (count && count + w.length > o.perRow) { rows.push(row); row = []; count = 0; }
    for (const n of w) {
      if (count >= o.perRow) { rows.push(row); row = []; count = 0; }
      row.push(n); count++;
    }
  }
  if (row.length) rows.push(row);
  let width = 0;
  const out = rows.map((r, ri) => {
    const top = ri * o.rowH + 30;
    let x = o.clefW + 14;
    const items = r.map((n, k) => {
      if (k > 0 && n.wordStart) x += o.wordGap;
      const p = n.step - 30;
      const y = top + 40 - p * 5;
      const it = { n, x, y, p, stemUp: p < 4 };
      x += n.dur === 2 ? o.h : o.q;
      return it;
    });
    const end = x + o.padEnd - 18;
    width = Math.max(width, end + 4);
    return { top, items, end, last: ri === rows.length - 1 };
  });
  return { rows: out, width, height: rows.length * o.rowH + 22, o };
}

function previewSignature(rawName, reading) {
  const raw = String(rawName ?? "");
  const hasHan = /\p{Script=Han}/u.test(raw);
  const read = String(reading ?? "").trim();
  const needReading = hasHan && !read;
  const usingReading = hasHan && !!read;
  const norm = normalizeName(usingReading ? read : raw);
  const notes = needReading ? [] : buildMelody(norm.words);
  return { algo_version: ALGO_VERSION, original_name: raw, reading: usingReading ? read : null,
    using_reading: usingReading, need_reading: needReading, has_han: hasHan,
    latin: norm.latin, truncated: norm.truncated, notes,
    note_names_ru: notes.map(n => RU[n.note] + n.octave + (n.dur === 2 ? "½" : "")) };
}
const SoulSignature = { ALGO_VERSION, MAX_LEN, TRANSLIT, NOTE_COLS, RU, normalizeName, buildMelody, layoutScore, previewSignature };
if (typeof module !== "undefined" && module.exports) module.exports = SoulSignature;
if (typeof window !== "undefined") window.SoulSignature = SoulSignature;
