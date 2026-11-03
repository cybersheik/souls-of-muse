const { test } = require("node:test");
const assert = require("node:assert/strict");
const handler = require("../api/harness/[...path].js");

function response() {
  return { headers: {}, setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.code = code; return this; },
    json(body) { this.body = body; return this; }, send(body) { this.body = body; return this; } };
}

test("gateway forwards participant cookie, preserves login cookie, omits global bearer credentials", async () => {
  const oldFetch = global.fetch;
  const oldURL = process.env.SOM_HARNESS_URL;
  process.env.SOM_HARNESS_URL = "https://backend.example";
  try {
    global.fetch = async (url, options) => {
      assert.equal(url.href, "https://backend.example/auth/login");
      assert.equal(options.headers.Cookie, "som_participant=private");
      assert.equal(options.headers.Authorization, undefined);
      assert.equal(options.headers.Origin, "https://soulsofmuse.app");
      return new Response('{"role":"maestro"}', { status: 200, headers: {
        "Set-Cookie": "som_participant=new; HttpOnly; Secure; SameSite=Strict; Path=/api/harness",
      } });
    };
    const res = response();
    await handler({ query: { path: ["auth", "login"] }, method: "POST", body: { username: "M" },
      headers: { cookie: "som_participant=private", authorization: "Bearer should-not-forward", origin: "https://soulsofmuse.app" } }, res);
    assert.equal(res.code, 200);
    assert.match(res.headers["Set-Cookie"], /HttpOnly/);
    assert.equal(res.headers["Cache-Control"], "no-store");
  } finally {
    global.fetch = oldFetch;
    if (oldURL === undefined) delete process.env.SOM_HARNESS_URL;
    else process.env.SOM_HARNESS_URL = oldURL;
  }
});

test("gateway rejects unexpected routes before making an upstream request", async () => {
  process.env.SOM_HARNESS_URL = "https://backend.example";
  const res = response();
  await handler({ query: { path: ["demo", "run"] }, method: "POST", headers: {} }, res);
  assert.equal(res.code, 404);
  delete process.env.SOM_HARNESS_URL;
});

test("gateway passes speech JSON for the approved message route", async () => {
  const oldFetch = global.fetch;
  process.env.SOM_HARNESS_URL = "https://backend.example";
  try {
    global.fetch = async url => {
      assert.equal(url.pathname, "/sessions/meeting/messages/message/speech");
      return new Response('{"wav_base64":"waveform","language":"vi"}', { status: 200 });
    };
    const res = response();
    await handler({ query: { path: ["sessions", "meeting", "messages", "message", "speech"] }, method: "POST", headers: {} }, res);
    assert.equal(res.code, 200);
    assert.equal(JSON.parse(res.body).language, "vi");
  } finally { global.fetch = oldFetch; delete process.env.SOM_HARNESS_URL; }
});

test("gateway permits only the scoped media controls", async () => {
  const oldFetch = global.fetch;
  process.env.SOM_HARNESS_URL = "https://backend.example";
  try {
    global.fetch = async () => new Response('{}', { status: 200 });
    for (const path of ["media/join", "media/leave", "media/status", "media/recordings", "media/recordings/id/stop", "media/recordings/id/cancel", "media/speech/id"]) {
      const res = response();
      await handler({ query: { path: ["sessions", "meeting", ...path.split("/")] }, method: "POST", headers: {} }, res);
      assert.equal(res.code, 200, path);
    }
    const res = response();
    await handler({ query: { path: ["sessions", "meeting", "media", "admin"] }, method: "POST", headers: {} }, res);
    assert.equal(res.code, 404);
  } finally { global.fetch = oldFetch; delete process.env.SOM_HARNESS_URL; }
});

test('gateway forwards only the scoped lesson workspace route', async()=>{
 const previous=global.fetch,oldURL=process.env.SOM_HARNESS_URL;process.env.SOM_HARNESS_URL='https://backend.example';
 try{
  let calls=0;global.fetch=async(url,options)=>{calls++;assert.equal(url.pathname,'/sessions/meeting/lesson');assert.equal(options.headers.Authorization,undefined);return new Response('{"revision":1}',{status:200});};
  for(const method of ['GET','POST']){const res=response();await handler({query:{path:['sessions','meeting','lesson']},method,headers:{},body:{revision:0}},res);assert.equal(res.code,200);}
  const res=response();await handler({query:{path:['sessions','meeting','lesson','admin']},method:'POST',headers:{}},res);assert.equal(res.code,404);assert.equal(calls,2);
 }finally{global.fetch=previous;if(oldURL===undefined)delete process.env.SOM_HARNESS_URL;else process.env.SOM_HARNESS_URL=oldURL;}
});
