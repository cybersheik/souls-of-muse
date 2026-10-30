"use strict";
/* Smoke / route / DW1 algorithm tests. Run: node --test tests/test_portal.cjs */
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const sig = require("../web/signature.js");
const api = require("../api/preview-signature.js");
const root = path.join(__dirname, "..");

const VECTORS = [
  ["HAYDN", "", ["си4","ля4","ре5","ре5","соль5½"]],
  ["Айдар Кожахметов", "", ["ля4","ре5","ре5","ля4","ре5½","ре5","ля4","ми4","си4","ля4","ре5","си4","фа4","ми4","фа4","ля4","ля4½"]],
  ["Әлия Нұрланқызы", "", ["ля4","ми4","си4","ре5","ля4½","соль4","соль4","ре4","ми4","ля4","соль4","до5","ре5","ми5","ре5½"]],
  ["Nguyễn Thị Mai", "", ["соль4","соль4","соль4","ре4","ми4","соль4½","фа4","си4","си4½","фа4","ля4","си4½"]],
  ["김민지", "", ["ля4","ми4","си4½"]],
  ["가나다라마바사", "", ["ля4","си4","до5","ре5","ми5","фа5","соль5½"]],
  ["イロハニホヘト", "", ["ля4","си4","до5","ре5","ми5","фа5","соль5½"]],
  ["キョーコ", "", ["до5½","ми5½"]],
  ["がっこう", "", ["соль4","ми4","до4½"]],
  ["たなか ゆき", "", ["си4","соль4","соль4½","ре4","до4½"]],
];
for (const [name, reading, expected] of VECTORS) {
  test("DW1 vector: " + name, () => {
    assert.deepStrictEqual(sig.previewSignature(name, reading).note_names_ru, expected);
  });
}
test("Han without reading requires explicit reading, no notes guessed", () => {
  const p = sig.previewSignature("田中由紀", "");
  assert.equal(p.need_reading, true);
  assert.deepStrictEqual(p.notes, []);
});
test("Han with owner-provided reading builds from reading, keeps original", () => {
  const p = sig.previewSignature("田中由紀", "たなか ゆき");
  assert.equal(p.original_name, "田中由紀");
  assert.equal(p.reading, "たなか ゆき");
  assert.ok(p.notes.length > 0);
});
test("API preview is explicitly non-authoritative", () => {
  const out = api.preview({ name: "HAYDN" });
  assert.equal(out.status, 200);
  assert.equal(out.json.authoritative, false);
  assert.equal(out.json.kind, "preview_only");
  assert.deepStrictEqual(out.json.note_names_ru, VECTORS[0][2]);
  assert.equal(api.preview({}).status, 400);
});
test("portal files and relative references exist", () => {
  for (const f of ["web/index.html","web/app.js","web/styles.css","web/signature.js","web/lesson.html","api/preview-signature.js"])
    assert.ok(fs.existsSync(path.join(root, f)), f);
  const html = fs.readFileSync(path.join(root, "web/index.html"), "utf8");
  for (const ref of ["styles.css","signature.js","app.js","lesson.html"])
    assert.ok(html.includes(ref), ref);
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  for (const route of ["#/convention","#/welcome","#/leagues","#/studio","lesson.html"])
    assert.ok(app.includes(route), route);
  assert.ok(!app.includes("подписано ·"), "no fake signed state");
});
test("canonical seven leagues, ceremony/workshop modes, no invented emblem", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  for (const name of ["Лига гитары","Лига клавишных","Лига духовых","Лига ударных","Лига электронных","Лига вокала","Лига народных"])
    assert.ok(app.includes(name), name);
  assert.ok(!app.includes("Лига струнных") && !app.includes("Лига голоса"), "invented leagues removed");
  assert.ok(app.includes('"ceremony"') && app.includes('"workshop"'), "two modes");
  assert.ok(app.includes("Эмблему каждая Лига выбирает сама"), "league emblem choice text");
  assert.ok(app.includes("Convention of the Keepers of Live Music"), "approved EN name");
  assert.ok(app.includes("Музыка живёт, пока её слушают"), "listener line");
});
test("no internal jargon or fake-confirmation text in user-facing app strings", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  for (const bad of ["DW1","CX1","backend","имитация юридического","я понимаю, что это предпросмотр","ALGO_VERSION"])
    assert.ok(!app.includes(bad), bad);
  assert.ok(!/подписал\(а\) Конвенцию/.test(app), "no signed claim on card");
});
test("stable item ids, single lifecycle, studio cleanup wiring", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  assert.ok(app.includes('data-open="${x.id}"') && app.includes("byId(tab"), "stable ids, not filtered indexes");
  assert.ok(app.includes("function cleanupStudio()") && app.includes('addEventListener("pagehide",cleanupPage)'), "pagehide cleanup");
  assert.ok(app.includes("studio.pending") && app.includes("studio.generation"), "pending lock + generation guard");
  assert.ok(!app.includes("pendingBind"), "no dead binder mechanism");
  assert.ok(app.includes("document.fonts.ready"), "card waits for fonts");
  assert.ok(app.includes("ceremony.preview") && !app.includes('localStorage.setItem("som_account'), "ceremony memory, no fake account");
});
test("deploy/vercel.json: owner-approved Permissions-Policy, everything else preserved", () => {
  const cfg = JSON.parse(fs.readFileSync(path.join(root, "deploy/vercel.json"), "utf8"));
  const all = Object.fromEntries(cfg.headers.flatMap(h => h.headers.map(x => [x.key + "@" + h.source, x.value])));
  assert.equal(all["Permissions-Policy@/(.*)"], "camera=(self), microphone=(self), geolocation=(), payment=()");
  assert.ok(!all["Permissions-Policy@/(.*)"].includes("*"), "no wildcard origin");
  assert.equal(all["X-Robots-Tag@/(.*)"], "noindex, nofollow");
  assert.equal(all["X-Content-Type-Options@/(.*)"], "nosniff");
  assert.equal(all["Cache-Control@/"], "no-cache, must-revalidate");
  assert.equal(all["Cache-Control@/index.html"], "no-cache, must-revalidate");
  assert.equal(cfg.outputDirectory, "dist");
});
test("recording starts only after explicit consent + click (no eager getUserMedia)", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  const gum = app.indexOf("getUserMedia(");
  assert.ok(gum > 0, "getUserMedia exists (in recorder)");
  const handlerStart = app.lastIndexOf('$("#recStart").onclick');
  assert.ok(handlerStart > 0 && gum > handlerStart, "every getUserMedia call sits inside the recStart click handler");
  assert.ok(app.slice(handlerStart).split("getUserMedia(").length - 1 >= 1, "audio/video branches present");
  const handler = app.slice(handlerStart, gum);
  assert.ok(handler.includes("recConsent"), "consent checked before getUserMedia");
  assert.ok(handler.includes("studio.pending"), "pending lock before getUserMedia");
  assert.ok(!/getUserMedia/.test(app.slice(0, app.indexOf("function bindStudio"))), "no getUserMedia outside studio binder");
});
test("league deep links: validated tab segment, cabinet links target intended tabs", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  assert.ok(app.includes('#/league/${l.id}/media'), "media deep link");
  assert.ok(app.includes('#/league/${l.id}/events'), "events deep link");
  assert.ok(app.includes("U.resolveLeague("), "shared resolver used");
  assert.ok(app.includes("location.hash=`#/league/${leagueId}/${btn.dataset.tab}`"), "tab clicks update hash for back/forward");
  assert.ok(app.includes('aria-controls="tabBody"') && app.includes('role="tabpanel"'), "tab/tabpanel wiring");
  assert.ok(app.includes('setAttribute("aria-current","page")'), "nav aria-current");
  assert.ok(app.includes('addEventListener("keydown"') && app.includes("U.tabIndexForKey"), "tab keyboard navigation");
});
test("resolveLeague/tabIndexForKey behavior (unit)", () => {
  const U = require("../web/portal-utils.js");
  const ids = ["guitar","keys","winds","drums","electronic","voice","folk"];
  assert.deepStrictEqual(U.resolveLeague("keys","events",ids,"guitar"), {id:"keys",tab:"events",idValid:true});
  assert.deepStrictEqual(U.resolveLeague("keys","Events",ids,"guitar"), {id:"keys",tab:"events",idValid:true}, "uppercase tab normalized");
  assert.deepStrictEqual(U.resolveLeague("keys","bogus",ids,"guitar"), {id:"keys",tab:"topics",idValid:true}, "unknown tab -> topics");
  assert.deepStrictEqual(U.resolveLeague("nope","media",ids,"keys"), {id:"keys",tab:"media",idValid:false}, "unknown league keeps saved, not guitar fallback");
  assert.deepStrictEqual(U.resolveLeague("keys/Events",undefined,ids,"keys"), {id:"keys",tab:"topics",idValid:false}, "swallowed segment is not a valid id");
  assert.equal(U.tabIndexForKey("ArrowRight",4,5),0);
  assert.equal(U.tabIndexForKey("ArrowLeft",0,5),4);
  assert.equal(U.tabIndexForKey("Home",3,5),0);
  assert.equal(U.tabIndexForKey("End",0,5),4);
  assert.equal(U.tabIndexForKey("x",2,5),2);
});
test("ceremony contrast tokens meet WCAG AA for preview note and eyebrow", () => {
  const css = fs.readFileSync(path.join(root, "web/styles.css"), "utf8");
  assert.ok(css.includes("body.ceremony .demo-banner{color:#3f3d8f;background:#ece8f7"), "violet ink banner");
  assert.ok(css.includes("body.ceremony .eyebrow{color:#4c3fc0}"), "violet eyebrow");
  const lum = h => { const [r,g,b]=[0,2,4].map(i=>parseInt(h.slice(1).substr(i,2),16)/255).map(c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)); return 0.2126*r+0.7152*g+0.0722*b; };
  const ratio = (a,b) => { const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  assert.ok(ratio("#3f3d8f","#ece8f7") >= 4.5, "banner contrast");
  assert.ok(ratio("#4c3fc0","#f1f2f6") >= 4.5, "eyebrow contrast");
  assert.ok(ratio("#7a5808","#f4f1ea") >= 4.5, "soft badge contrast");
});
test("canonical convention text verbatim, approved EN title, real brand assets", () => {
  const app = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
  assert.ok(app.includes("Я, нижеподписавшийся, отдаю дань уважения такому великому дару человечества, как музыка"), "RU p1");
  assert.ok(app.includes("оставляю за собой право на свободу художественного самовыражения"), "RU p5");
  assert.ok(app.includes("I, the undersigned, honour music as one of humanity’s greatest gifts"), "EN p1");
  assert.ok(app.includes("Convention of the Keepers of Live Music"), "approved EN title");
  assert.ok(!app.includes("Custodians of Living Music"), "old EN title replaced");
  assert.ok(!app.includes("Полный текст Конвенции в утверждённой редакции будет опубликован"), "placeholder removed");
  assert.ok(!app.includes("seal-a") && !app.includes("A.NOVA"), "demo seal never used as personal seal");
  for (const f of ["web/assets/logo-a.png","web/assets/honors-playful.png","web/assets/honors-formal.png","web/assets/muse-original.png"]){
    assert.ok(fs.existsSync(path.join(root, f)), f);
    assert.ok(fs.statSync(path.join(root, f)).size > 50000, f+" non-trivial");
    assert.ok(app.includes("assets/"+path.basename(f)), f+" referenced");
  }
});
test("lesson source preserved byte-identical (pinned SHA-256)", () => {
  const crypto = require("node:crypto");
  const lesson = fs.readFileSync(path.join(root, "web/lesson.html"));
  const sha = crypto.createHash("sha256").update(lesson).digest("hex");
  assert.equal(sha, "b50ccad858bbb79399a3da6be66a366036f1ba88481340fbe8275f5da492ae50");
});
