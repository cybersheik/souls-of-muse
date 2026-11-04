import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const rootDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const publicDir = path.join(rootDir, 'public');
const serverPath = path.join(rootDir, 'server.mjs');

assert.ok(
  fs.existsSync(serverPath),
  'server.mjs is missing: expected server.mjs at package root exporting createAppServer({ publicDir })',
);

const { createAppServer } = await import(pathToFileURL(serverPath).href);
assert.equal(typeof createAppServer, 'function', 'server.mjs must export createAppServer({ publicDir })');

const indexBytes = fs.readFileSync(path.join(publicDir, 'index.html'));

const assets = [
  { requestPath: '/support.js', rel: 'support.js', type: 'text/javascript; charset=utf-8' },
  {
    requestPath: '/_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/styles.css',
    rel: '_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/styles.css',
    type: 'text/css; charset=utf-8',
  },
  { requestPath: '/_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/_ds_bundle.js', rel: '_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/_ds_bundle.js', type: 'text/javascript; charset=utf-8' },
  { requestPath: '/_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/_ds_manifest.json', rel: '_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834/_ds_manifest.json', type: 'application/json; charset=utf-8' },
];

function rawRequest(port, method, requestPath) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, method, path: requestPath }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
    });
    req.on('error', reject);
    req.end();
  });
}

async function withServer(fn) {
  const server = createAppServer({ publicDir });
  assert.ok(server instanceof http.Server, 'createAppServer({ publicDir }) must return a node:http Server');
  assert.equal(server.listening, false, 'createAppServer({ publicDir }) must return an unlistened server');
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  try {
    await fn(server.address().port);
  } finally {
    await new Promise((resolve, reject) => server.close((err) => (err ? reject(err) : resolve())));
  }
}

function it(name, fn) {
  test(name, async () => {
    await withServer(async (port) => {
      await fn(port);
    });
  });
}

for (const requestPath of ['/', '/index.html', '/souls.html']) {
  it(`GET ${requestPath} serves exact index.html bytes as text/html; charset=utf-8`, async (port) => {
    const res = await rawRequest(port, 'GET', requestPath);
    assert.equal(res.status, 200);
    assert.equal(res.headers['content-type'], 'text/html; charset=utf-8');
    assert.deepEqual(res.body, indexBytes);
  });
}

it('GET index routes with query strings serve exact index.html bytes', async (port) => {
  for (const requestPath of ['/?preview=1', '/index.html?preview=1', '/souls.html?preview=1']) {
    const res = await rawRequest(port, 'GET', requestPath);
    assert.equal(res.status, 200, requestPath);
    assert.equal(res.headers['content-type'], 'text/html; charset=utf-8', requestPath);
    assert.deepEqual(res.body, indexBytes, requestPath);
  }
});

for (const asset of assets) {
  it(`GET ${asset.requestPath} serves exact bytes with MIME ${asset.type}`, async (port) => {
    const expected = fs.readFileSync(path.join(publicDir, ...asset.rel.split('/')));
    const res = await rawRequest(port, 'GET', asset.requestPath);
    assert.equal(res.status, 200);
    assert.equal(res.headers['content-type'], asset.type);
    assert.deepEqual(res.body, expected);
  });
}

it('HEAD / returns no body with correct UTF-8 byte Content-Length', async (port) => {
  const res = await rawRequest(port, 'HEAD', '/');
  assert.equal(res.status, 200);
  assert.equal(res.headers['content-type'], 'text/html; charset=utf-8');
  assert.equal(res.headers['content-length'], String(indexBytes.length));
  assert.equal(res.body.length, 0);
});

it('GET / sends noindex header', async (port) => {
  const res = await rawRequest(port, 'GET', '/');
  assert.equal(res.status, 200);
  assert.match(res.headers['x-robots-tag'] ?? '', /noindex/);
});

it('GET / sends nosniff header', async (port) => {
  const res = await rawRequest(port, 'GET', '/');
  assert.equal(res.status, 200);
  assert.equal(res.headers['x-content-type-options'], 'nosniff');
});

it('POST / returns 405 with Allow: GET, HEAD', async (port) => {
  const res = await rawRequest(port, 'POST', '/');
  assert.equal(res.status, 405);
  assert.equal(res.headers.allow, 'GET, HEAD');
});

it('GET unknown path returns 404', async (port) => {
  const res = await rawRequest(port, 'GET', '/does-not-exist.txt');
  assert.equal(res.status, 404);
});

for (const requestPath of ['/server.mjs', '/package.json', '/.env', '/%2e%2e/server.mjs', '/_ds/../../server.mjs']) {
  it(`GET ${requestPath} never exposes code or secrets (400 or 404)`, async (port) => {
    const res = await rawRequest(port, 'GET', requestPath);
    assert.ok([400, 404].includes(res.status), `expected 400 or 404, got ${res.status}`);
    assert.equal(res.body.includes('createAppServer'), false);
  });
}

it('GET malformed percent-encoding returns 400', async (port) => {
  const res = await rawRequest(port, 'GET', '/%zz');
  assert.equal(res.status, 400);
});

it('GET /healthz returns 200 liveness JSON for design-preview with live features disabled', async (port) => {
  const res = await rawRequest(port, 'GET', '/healthz');
  assert.equal(res.status, 200);
  assert.match(res.headers['content-type'] ?? '', /^application\/json/);
  const body = JSON.parse(res.body.toString('utf8'));
  assert.equal(body.stage, 'design-preview');
  assert.equal(body.liveLessons, false);
  assert.equal(body.metaApiEnabled, false);
});

it('GET /api/lessons returns 503 live_lessons_unavailable with no fake live success', async (port) => {
  const res = await rawRequest(port, 'GET', '/api/lessons');
  assert.equal(res.status, 503);
  assert.match(res.headers['content-type'] ?? '', /^application\/json/);
  assert.deepEqual(JSON.parse(res.body.toString('utf8')), { error: 'live_lessons_unavailable' });
});

it('POST /api/lessons returns 503 live_lessons_unavailable with no fake live success', async (port) => {
  const res = await rawRequest(port, 'POST', '/api/lessons');
  assert.equal(res.status, 503);
  assert.match(res.headers['content-type'] ?? '', /^application\/json/);
  assert.deepEqual(JSON.parse(res.body.toString('utf8')), { error: 'live_lessons_unavailable' });
});
