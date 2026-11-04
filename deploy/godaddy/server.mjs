import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DS_DIR = '_ds/nocturne-cce07e63-bda7-479d-9318-f0cdcc3c2834';
const DEFAULT_PUBLIC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public');

const FILES = [
  { rel: 'index.html', type: 'text/html; charset=utf-8', cache: 'no-store' },
  { rel: 'support.js', type: 'text/javascript; charset=utf-8', cache: 'public, max-age=3600' },
  { rel: `${DS_DIR}/styles.css`, type: 'text/css; charset=utf-8', cache: 'public, max-age=3600' },
  { rel: `${DS_DIR}/_ds_bundle.js`, type: 'text/javascript; charset=utf-8', cache: 'public, max-age=3600' },
  { rel: `${DS_DIR}/_ds_manifest.json`, type: 'application/json; charset=utf-8', cache: 'public, max-age=3600' },
];

const ROUTES = new Map([
  ['/', 'index.html'],
  ['/index.html', 'index.html'],
  ['/souls.html', 'index.html'],
  ['/support.js', 'support.js'],
  [`/${DS_DIR}/styles.css`, `${DS_DIR}/styles.css`],
  [`/${DS_DIR}/_ds_bundle.js`, `${DS_DIR}/_ds_bundle.js`],
  [`/${DS_DIR}/_ds_manifest.json`, `${DS_DIR}/_ds_manifest.json`],
]);

const HEALTH_BODY = Buffer.from(JSON.stringify({ service: 'souls-of-muse', stage: 'design-preview', liveLessons: false, metaApiEnabled: false }));
const API_BODY = Buffer.from(JSON.stringify({ error: 'live_lessons_unavailable' }));

function loadPublicFiles(publicDir) {
  const root = path.resolve(publicDir);
  let rootStat;
  try {
    rootStat = fs.lstatSync(root);
  } catch {
    throw new Error('Required public directory is missing');
  }
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) {
    throw new Error('Required public directory is missing');
  }
  const realRoot = fs.realpathSync(root);
  const loaded = new Map();
  for (const file of FILES) {
    const full = path.join(root, ...file.rel.split('/'));
    let stat;
    try {
      stat = fs.lstatSync(full);
    } catch {
      throw new Error(`Missing required public file: ${file.rel}`);
    }
    if (stat.isSymbolicLink() || !stat.isFile()) {
      throw new Error(`Missing required public file: ${file.rel}`);
    }
    const real = fs.realpathSync(full);
    if (real !== realRoot && !real.startsWith(realRoot + path.sep)) {
      throw new Error(`Missing required public file: ${file.rel}`);
    }
    loaded.set(file.rel, { ...file, body: fs.readFileSync(real) });
  }
  return loaded;
}

function send(req, res, status, body, type, cache, extra = {}) {
  if (!Buffer.isBuffer(body)) body = Buffer.from(body);
  res.writeHead(status, {
    'Content-Type': type,
    'Content-Length': String(body.length),
    'Cache-Control': cache,
    'X-Robots-Tag': 'noindex, nofollow',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    ...extra,
  });
  res.end(req.method === 'HEAD' ? undefined : body);
}

const text = (req, res, status, message, extra) =>
  send(req, res, status, message, 'text/plain; charset=utf-8', 'no-store', extra);

export function createAppServer({ publicDir = DEFAULT_PUBLIC_DIR } = {}) {
  const files = loadPublicFiles(publicDir);
  const server = http.createServer((req, res) => {
    try {
      const rawUrl = typeof req.url === 'string' && req.url.length > 0 ? req.url : '/';
      const rawPath = rawUrl.split('?')[0].split('#')[0];
      let decodedPath;
      try {
        decodedPath = decodeURIComponent(rawPath);
      } catch {
        return text(req, res, 400, 'Bad Request');
      }
      const hasDotSegment = (p) => p.split('/').some((s) => s === '.' || s === '..');
      if (
        decodedPath.includes('\0') ||
        decodedPath.includes('\\') ||
        hasDotSegment(rawPath) ||
        hasDotSegment(decodedPath)
      ) {
        return text(req, res, 400, 'Bad Request');
      }
      if (decodedPath === '/api' || decodedPath.startsWith('/api/')) {
        return send(req, res, 503, API_BODY, 'application/json; charset=utf-8', 'no-store');
      }
      if (req.method !== 'GET' && req.method !== 'HEAD') {
        return text(req, res, 405, 'Method Not Allowed', { Allow: 'GET, HEAD' });
      }
      if (decodedPath === '/healthz') {
        return send(req, res, 200, HEALTH_BODY, 'application/json; charset=utf-8', 'no-store');
      }
      const rel = ROUTES.get(decodedPath);
      if (!rel) return text(req, res, 404, 'Not Found');
      const file = files.get(rel);
      return send(req, res, 200, file.body, file.type, file.cache);
    } catch {
      if (!res.headersSent) return text(req, res, 500, 'Internal Server Error');
      res.end();
    }
  });
  return server;
}

const isMain = (() => {
  try {
    return Boolean(process.argv[1]) && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
  } catch {
    return false;
  }
})();

if (isMain) {
  const rawPort = process.env.PORT;
  const port = rawPort === undefined ? 3000 : Number(rawPort);
  if (rawPort !== undefined && (!/^\d+$/.test(rawPort) || !Number.isInteger(port) || port < 1 || port > 65535)) {
    console.error('Failed to start: PORT must be an integer between 1 and 65535');
    process.exit(1);
  }
  let server;
  try {
    server = createAppServer({ publicDir: DEFAULT_PUBLIC_DIR });
  } catch (err) {
    console.error(`Failed to start: ${err.message}`);
    process.exit(1);
  }
  server.on('error', (err) => {
    console.error(`Failed to start: ${err.message}`);
    process.exit(1);
  });
  const shutdown = () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000).unref();
  };
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
  server.listen(port, '0.0.0.0', () => {
    console.log(`souls-of-muse listening on port ${port}`);
  });
}
