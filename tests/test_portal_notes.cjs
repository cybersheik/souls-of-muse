"use strict";
/* Real CSS-cascade regression, isolated from participant/browser sessions.
   Run with an installed Playwright module, for example:
   SOM_PLAYWRIGHT_MODULE=/path/to/playwright node --test tests/test_portal_notes.cjs
   Fixture directories under /private/tmp/cx1-* are intentionally retained. */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
let chromium;
try { ({ chromium } = require(process.env.SOM_PLAYWRIGHT_MODULE || "playwright")); }
catch (error) { if (error.code !== "MODULE_NOT_FOUND") throw error; }
const web = path.resolve(__dirname, "../web");
const read = name => fs.readFileSync(path.join(web, name), "utf8");

async function fixture(browser, width, view, lang) {
  const context = await browser.newContext({ viewport: { width, height: 960 }, reducedMotion: "reduce" });
  // Fulfil only this synthetic origin; fonts/images and all external requests
  // are aborted. No public site, Harness, account cookie or provider is used.
  await context.route("**/*", route => route.request().url() === "http://portal-notes.test/"
    ? route.fulfill({ contentType: "text/html", body: '<!doctype html><html><body><div id="fixture"></div></body></html>' })
    : route.abort());
  const page = await context.newPage();
  await page.goto("http://portal-notes.test/");
  for (const name of ["styles.css", "portal20.css", "portal21.css"]) await page.addStyleTag({ content: read(name) });
  await page.addScriptTag({ content: read("strings.js") });
  await page.evaluate(({ lang, view }) => {
    window.P01 = { state: { lang, convOpen: false, sigPaused: false }, CONV: {
      en: { title: "Convention fixture", first: "Fixture", rest: [], readAll: "Read", collapse: "Collapse" },
      ru: { title: "Конвенция: тест", first: "Тест", rest: [], readAll: "Читать", collapse: "Свернуть" },
    } };
    window.notesView = view;
    window.notesRenders = 0;
  }, { lang, view });
  await page.addScriptTag({ content: read("portal20.js") });
  await page.evaluate(() => {
    window.render = () => {
      window.notesRenders++;
      document.getElementById("fixture").innerHTML = window.Portal20[window.notesView]();
      window.Portal20.bind();
    };
    window.render();
  });
  return { context, page };
}

async function state(locator) {
  return locator.evaluate(element => ({ hidden: element.hidden, display: getComputedStyle(element).display,
    width: element.getBoundingClientRect().width, boxes: element.getClientRects().length }));
}

test("Portal Notes honour hidden and reveal once at desktop and mobile widths", {
  skip: chromium ? false : "Install Playwright or set SOM_PLAYWRIGHT_MODULE to run computed-style acceptance",
}, async t => {
  const artifacts = fs.mkdtempSync("/private/tmp/cx1-portal-notes-");
  const previousTmpdir = process.env.TMPDIR;
  process.env.TMPDIR = artifacts;
  let browser;
  try {
    browser = await chromium.launch({ channel: "chrome", headless: true, artifactsDir: artifacts });
    for (const lang of ["en", "ru"]) for (const view of ["home", "leagues"]) {
      const kind = view === "home" ? "how" : "what";
      await t.test(`desktop ${view} ${lang}: hide removes layout and one reveal restores it`, async () => {
        const { context, page } = await fixture(browser, 1440, view, lang);
        try {
          const shutter = page.locator(".p20-shutter");
          assert.equal((await state(shutter)).display, "flex");
          assert.equal(await page.locator(".p20-tab").count(), 0);
          for (let cycle = 0; cycle < 2; cycle++) {
            await page.locator(`[data-shut="${kind}"]`).click();
            const hidden = await state(shutter);
            assert.equal(hidden.hidden, true, "the actual Hide notes handler sets hidden");
            assert.equal(hidden.display, "none", "author flex must not override hidden");
            assert.equal(hidden.width, 0);
            assert.equal(hidden.boxes, 0);
            assert.equal(await page.locator(`[data-unshut="${kind}"]`).count(), 1);
            await page.evaluate(() => { window.render(); window.render(); });
            assert.equal(await page.locator(`[data-unshut="${kind}"]`).count(), 1, "rerender cannot stack reveal controls");
            const before = await page.evaluate(() => window.notesRenders);
            await page.locator(`[data-unshut="${kind}"]`).click();
            assert.equal(await page.evaluate(() => window.notesRenders), before + 1, "one click triggers exactly one reveal");
            assert.equal((await state(shutter)).hidden, false);
            assert.equal((await state(shutter)).display, "flex");
            assert.equal(await page.locator(".p20-tab").count(), 0);
          }
          await page.evaluate(() => {
            const tab = document.createElement("button"); tab.className = "p20-tab"; tab.hidden = true;
            tab.dataset.fixtureHiddenTab = ""; document.body.append(tab);
          });
          assert.equal((await state(page.locator("[data-fixture-hidden-tab]"))).display, "none", "a hidden reveal control also honours hidden");
        } finally { await context.close(); }
      });
      for (const width of [1179, 390]) await t.test(`narrow ${width} ${view} ${lang}: native Notes disclosure and hidden remain distinct`, async () => {
        const { context, page } = await fixture(browser, width, view, lang);
        try {
          const notes = page.locator(".p20-mnotes");
          assert.equal((await state(page.locator(".p20-shutter"))).display, "none");
          assert.equal((await state(notes)).display, "block");
          assert.equal(await page.locator(".p20-tab:visible").count(), 0);
          await notes.locator("summary").click();
          assert.equal(await notes.evaluate(element => element.open), true);
          assert.equal(await notes.locator(".p20-shutbody").isVisible(), true);
          await notes.locator("summary").click();
          assert.equal(await notes.evaluate(element => element.open), false);
          assert.equal(await notes.locator(".p20-shutbody").isVisible(), false);
          await notes.evaluate(element => { element.hidden = true; });
          assert.equal((await state(notes)).display, "none", "mobile author block must not override hidden");
          assert.equal((await state(notes)).boxes, 0);
          await notes.evaluate(element => { element.hidden = false; });
          assert.equal((await state(notes)).display, "block");
        } finally { await context.close(); }
      });
    }
  } finally {
    if (browser) await browser.close();
    if (previousTmpdir === undefined) delete process.env.TMPDIR;
    else process.env.TMPDIR = previousTmpdir;
  }
});
