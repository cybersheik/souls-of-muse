"use strict";

const routes = [
  /^(health|auth\/(login|logout|me))$/,
  /^sessions(?:\/[a-zA-Z0-9_-]+(?:\/(?:start|complete|join|heart|events|lesson|transcriptions|audit\/verify|messages(?:\/[a-zA-Z0-9_-]+\/(?:approve|speech|review))?))?)?$/,
  /^sessions\/[a-zA-Z0-9_-]+\/media\/(?:status|join|leave|recordings(?:\/[a-zA-Z0-9_-]+\/(?:stop|cancel))?|speech\/[a-zA-Z0-9_-]+)$/,
  /^sessions\/[a-zA-Z0-9_-]+\/lesson\/translations(?:\/[a-zA-Z0-9_-]+\/approve)?$/,
  /^sessions\/[a-zA-Z0-9_-]+\/lesson\/proposals(?:\/[a-zA-Z0-9_-]+\/apply)?$/,
  /^notes$/,
  /^sessions\/[a-zA-Z0-9_-]+\/notes$/,
];

// The browser uses its host-only HttpOnly participant cookie. Global pilot
// credentials and model keys are never accepted from, or sent to, the browser.
module.exports = async function handler(req, res) {
  const base = process.env.SOM_HARNESS_URL;
  if (!base) return res.status(503).json({ detail: "harness_not_configured" });
  const parts = req.query.path;
  const path = Array.isArray(parts) ? parts.join("/") : String(parts || "");
  if (!routes.some(route => route.test(path))) {
    return res.status(404).json({ detail: "route_not_found" });
  }
  if (!["GET", "POST"].includes(req.method)) {
    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ detail: "method_not_allowed" });
  }
  const headers = { "Content-Type": "application/json" };
  if (req.headers.cookie) headers.Cookie = req.headers.cookie;
  if (req.headers.origin) headers.Origin = req.headers.origin;
  if (req.headers['x-som-participant']) headers['X-SOM-Participant'] = req.headers['x-som-participant'];
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 55000);
  try {
    const target = new URL(path, base.replace(/\/$/, "") + "/");
    if(path==='notes'&&req.method==='GET'&&typeof req.query.cursor==='string')target.searchParams.set('cursor',req.query.cursor);
    const upstream = await fetch(target, {
      method: req.method, headers, redirect: "error", signal: controller.signal,
      body: req.method === "POST" ? JSON.stringify(req.body || {}) : undefined,
    });
    res.setHeader("Cache-Control", "no-store");
    const cookie = upstream.headers.get("set-cookie");
    if (cookie) res.setHeader("Set-Cookie", cookie);
    const participant=upstream.headers.get('x-som-participant');
    if(participant)res.setHeader('X-SOM-Participant',participant);
    res.setHeader("Content-Type", "application/json");
    res.status(upstream.status).send(await upstream.text());
  } catch (_) {
    res.status(502).json({ detail: "harness_unavailable" });
  } finally {
    clearTimeout(timer);
  }
};
