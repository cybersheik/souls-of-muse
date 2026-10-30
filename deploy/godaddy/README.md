# GoDaddy Node.js deployment

This wrapper serves the existing `web/` design preview. It does not implement live lessons, authentication, media rooms, the Python Harness, or paid Meta API calls. `/healthz` is liveness only; it explicitly reports `liveLessons: false` and `metaApiEnabled: false`. `/api/*` returns 503.

Author: Meta Muse Wonder 1.0. CX1 integrated, packaged, and verified the exact output. The UI remains the existing Claude Design export, with the separately attributed soft preview notice. A fresh Muse Wonder review found no preview-upload blockers; asset caching for up to one hour remains a consideration when updating same-name files.

## Prepare and verify

From the repository root, copy the five approved public files into the ignored staging directory:

```sh
mkdir -p deploy/godaddy/public
cp -R web/. deploy/godaddy/public/
cd deploy/godaddy
npm test
npm run build
```

Tests use actual local HTTP requests on 127.0.0.1 with temporary ports, not mocks. They close each test server. Node 22 is required. There are no external npm dependencies.

## Upload

Create a ZIP whose root contains `package.json`, `package-lock.json`, `server.mjs`, `test/server.test.mjs`, and `public/`. Do not add a wrapper directory, `.git`, secrets, `.env`, local evidence, or `node_modules`. In GoDaddy choose **Deploy a Node.js app → Upload ZIP**.

Build command: `npm run build`. Start command: `npm start`. The process listens on GoDaddy's `PORT`; the production origin is GoDaddy, never the developer's Mac. Upload success alone does not prove publication, custom-domain HTTPS, or live lessons. Verify the cloud preview, logs, asset responses, apex/www DNS and HTTPS separately. Preserve the domain's email records.

Official requirements: https://developer.godaddy.com/en/docs/api-users/hosting/app-requirements
