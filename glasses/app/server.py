# -*- coding: utf-8 -*-
"""Souls of Muse · очки: одно локальное приложение на три направления (стандартная библиотека, без зависимостей).

  .venv-mlx/bin/python app/server.py            # http://localhost:8765 (только этот Mac; HOST=0.0.0.0 — для телефона в той же Wi-Fi)
  страницы: /keys (клавиши по партитуре), /council (консилиум по договору), /notebook (аудиотетрадь)

Запуск стенда клавиш, чтение страниц договора (Muse Spark), консилиум (Hermes MoA muse-council) и чтение сетки
аккордов с фото (Muse Spark) идут подпроцессами; ключ Model API берётся только из файла --env-file профиля Jack
и никуда не печатается. Состояние подпроцессов — в памяти сервера, журналы в out/app/.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, threading, time, base64, mimetypes, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"; LIVE = ROOT / "out" / "live"; LOGS = ROOT / "out" / "app"; LOGS.mkdir(parents=True, exist_ok=True)
ENV_FILE = os.environ.get("MUSE_ENV_FILE", str(Path.home() / ".hermes" / "profiles" / "jack" / ".env"))
PY_MLX = ROOT / ".venv-mlx" / "bin" / "python"; PY_API = ROOT / ".venv" / "bin" / "python"
PORT = int(os.environ.get("PORT", "8765"))

class Job:
    """один подпроцесс с журналом: стенд, чтение страниц, консилиум, чтение сетки"""
    def __init__(self, name): self.name = name; self.proc = None; self.log = LOGS / f"{name}.log"; self.started = 0.0; self.meta = {}
    def start(self, cmd, cwd=ROOT, meta=None):
        self.stop()
        self.meta = meta or {}; self.started = time.time()
        self.proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=open(self.log, "w"), stderr=subprocess.STDOUT)
        return self.proc.pid
    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(5)
            except subprocess.TimeoutExpired: self.proc.kill()
    def state(self):
        if self.proc is None: return "idle"
        return "running" if self.proc.poll() is None else ("done" if self.proc.returncode == 0 else f"failed ({self.proc.returncode})")
    def tail(self, n=25):
        try: return "".join(open(self.log, errors="replace").readlines()[-n:])
        except FileNotFoundError: return ""

JOBS = {k: Job(k) for k in ("keys", "pages", "council", "chart")}

# ------------------------------------------------------------------ консилиум: разбор ответа
def parse_answer(text: str):
    """1. EAR / 2. REVIEW / 3. disclaimer → {ear, clauses:[{num,title,severity,body,alt,ref}], tail, disclaimer}"""
    ear = ""; review = text; disclaimer = ""
    m = re.search(r"^\s*1\.\s*EAR\s*$(.*?)^\s*2\.\s*REVIEW\s*$(.*)", text, re.S | re.M)
    if m: ear, review = m.group(1).strip(), m.group(2)
    m3 = re.search(r"^\s*3\.\s*(This is an opinion.*)$", review, re.M)
    if m3: disclaimer = m3.group(1).strip(); review = review[:m3.start()]
    clauses = []; tail = ""
    pat = re.compile(r"^Clause\s+([\d.]+)[,:]?\s*(.*?)\s*[—–-]\s*(red|amber|green)\s*$", re.M | re.I)
    heads = list(pat.finditer(review))
    intro = review[:heads[0].start()].strip() if heads else review.strip()
    for i, h in enumerate(heads):
        body = review[h.end():(heads[i + 1].start() if i + 1 < len(heads) else len(review))].strip()
        # хвост после последнего пункта (разногласия, план переговоров)
        if i == len(heads) - 1:
            mt = re.search(r"\n\s*\n(?=(Disagreements|Negotiation|Summary|Where|Points)\b)", body)
            if mt: tail = body[mt.start():].strip(); body = body[:mt.start()].strip()
        alt = ref = ""
        ma = re.search(r"Fair alternative:\s*(.*?)(?=\n\s*(Reference|Negotiation warning):|\Z)", body, re.S)
        if ma: alt = ma.group(1).strip()
        mr = re.search(r"(?:Reference|Negotiation warning):\s*(.*)", body, re.S)
        if mr: ref = mr.group(1).strip()
        finding = body.split("Fair alternative:")[0].strip()
        clauses.append({"num": h.group(1), "title": h.group(2), "severity": h.group(3).lower(), "finding": finding, "alt": alt, "ref": ref})
    return {"ear": ear, "intro": intro, "clauses": clauses, "tail": tail, "disclaimer": disclaimer}

def council_answers():
    out = ROOT / "council" / "out"; res = []
    for d in sorted(out.glob("*/answer.md"), reverse=True):
        res.append({"stamp": d.parent.name, "path": str(d.relative_to(ROOT)), "size": d.stat().st_size})
    return res

def council_pages():
    out = ROOT / "council" / "out"
    return [{"name": p.name, "path": str(p.relative_to(ROOT)), "size": p.stat().st_size} for p in sorted(out.glob("pages-*.md"), reverse=True)]

# ------------------------------------------------------------------ http
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
    def _file(self, p: Path, ctype=None):
        if not p.exists(): return self._send(404, {"error": f"нет {p.name}"})
        self._send(200, p.read_bytes(), ctype or mimetypes.guess_type(str(p))[0] or "application/octet-stream")
    def _json(self):
        n = int(self.headers.get("Content-Length") or 0); return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); p = u.path
        if p in ("/", "/index.html"): return self._file(STATIC / "hub.html")
        if p in ("/keys", "/council"): return self._file(STATIC / (p.strip("/") + ".html"))
        if p == "/notebook": return self._notebook_page()
        if p == "/shoot":
            md = (ROOT / "keys" / "SHOOT-2026-11-03.md").read_text()
            body = md.replace("&", "&amp;").replace("<", "&lt;")
            return self._send(200, f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Карточка съёмки</title><link rel="stylesheet" href="/static/app.css"></head><body><div class="app"><header class="top"><div><h1>Карточка съёмки 03.11</h1><div class="sub">keys/SHOOT-2026-11-03.md</div></div><nav class="nav"><a href="/">Хаб</a><a href="/keys">Клавиши</a><a href="/council">Консилиум</a><a href="/notebook">Аудиотетрадь</a></nav></header><section class="card"><pre style="white-space:pre-wrap;font:14px/1.5 Inter,system-ui,sans-serif;margin:0">{body}</pre></section></div></body></html>', "text/html; charset=utf-8")
        if p.startswith("/static/"): return self._file(STATIC / p[8:])
        if p == "/api/keys/status":
            st = LIVE / "status.json"; d = json.loads(st.read_text()) if st.exists() else {}
            d.update({"job": JOBS["keys"].state(), "log": JOBS["keys"].tail(12), "age": round(time.time() - st.stat().st_mtime, 1) if st.exists() else None}); return self._send(200, d)
        if p == "/api/keys/frame": return self._file(LIVE / "latest.jpg", "image/jpeg")
        if p == "/api/keys/side": return self._file(LIVE / "side.jpg", "image/jpeg")
        if p == "/api/council/status":
            which = q.get("answer", [None])[0]; answers = council_answers()
            a = next((x for x in answers if x["stamp"] == which), answers[0] if answers else None)
            parsed = parse_answer((ROOT / a["path"]).read_text(errors="replace")) if a else None
            return self._send(200, {"job_pages": JOBS["pages"].state(), "job_council": JOBS["council"].state(), "log_pages": JOBS["pages"].tail(8),
                                    "log_council": JOBS["council"].tail(8), "answers": answers, "pages": council_pages(), "current": a, "parsed": parsed,
                                    "elapsed": round(time.time() - JOBS["council"].started) if JOBS["council"].state() == "running" else None})
        if p == "/api/council/pages_text":
            f = ROOT / q.get("path", [""])[0]
            if not f.is_relative_to(ROOT / "council" / "out") or not f.exists(): return self._send(404, {"error": "нет файла"})
            return self._send(200, {"text": f.read_text(errors="replace")})
        if p == "/api/notebook/song":
            f = ROOT / "out" / "notebook" / "song.json"
            return self._send(200, {"song": json.loads(f.read_text()) if f.exists() else None, "job": JOBS["chart"].state(), "log": JOBS["chart"].tail(8)})
        if p.startswith("/clips/"):
            f = (ROOT / p[1:]).resolve()
            if f.is_relative_to(ROOT / "clips") and f.is_file(): return self._file(f)
        return self._send(404, {"error": "нет такой страницы"})

    def do_POST(self):
        p = urlparse(self.path).path
        try: body = self._json()
        except Exception as e: return self._send(400, {"error": f"плохой json: {e}"})
        # ---------------- клавиши
        if p == "/api/keys/start":
            layout = body.get("layout", "piano"); source = body.get("source", "webcam")
            cmd = [str(PY_MLX), str(ROOT / "keys" / "air_keys.py"), "--auto", "--layout", layout, "--tracker", "sam", "--sam-prompt", "finger", "--press", "score",
                   "--score", body.get("score", "fur_elise"), "--headless", "--log", "--snap-every", "0.3", "--keys", str(LIVE / f"keys_{layout}.json")]
            if layout == "piano" and body.get("hint"): cmd += ["--hint", str(int(body["hint"]))]
            if source == "video": cmd += ["--source", "video", "--file", body.get("file", ""), "--video-start", str(body.get("start", 0)), "--video-step", str(body.get("step", 12))]
            elif source == "window": cmd += ["--source", "window", "--window", body.get("window", "WhatsApp")]
            elif source == "screen": cmd += ["--source", "screen"]
            else: cmd += ["--source", "webcam", "--cam", str(body.get("cam", 0))]
            if body.get("no_sound"): cmd += ["--no-sound"]
            if body.get("instrument"): cmd += ["--instrument", body["instrument"]]
            if body.get("audio_out"): cmd += ["--audio-out", body["audio_out"]]
            if body.get("side_cam") not in (None, ""): cmd += ["--side-cam", str(int(body["side_cam"])), "--side-end", body.get("side_end", "treble")]
            if body.get("side_file"): cmd += ["--side-file", body["side_file"], "--side-end", body.get("side_end", "treble")]
            if body.get("dino_thr") is not None: cmd += ["--dino-thr", str(float(body["dino_thr"]))]
            if body.get("ensemble"): cmd += ["--ensemble", body.get("score", "fur_elise")]
            for f in ("status.json",):
                try: (LIVE / f).unlink()
                except FileNotFoundError: pass
            pid = JOBS["keys"].start(cmd, meta=body); return self._send(200, {"pid": pid, "cmd": cmd})
        if p == "/api/keys/stop": JOBS["keys"].stop(); return self._send(200, {"ok": True})
        # ---------------- консилиум
        if p == "/api/council/pages":
            stamp = time.strftime("%Y%m%d-%H%M%S"); d = ROOT / "clips" / "contract" / stamp; d.mkdir(parents=True, exist_ok=True); saved = []
            for i, im in enumerate(body.get("images", [])):
                m = re.match(r"data:(image/\w+);base64,(.*)", im.get("data", ""), re.S)
                if not m: continue
                ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/heic": ".heic"}.get(m.group(1), ".jpg")
                f = d / f"page_{i + 1:02d}{ext}"; f.write_bytes(base64.b64decode(m.group(2))); saved.append(str(f.relative_to(ROOT)))
            return self._send(200, {"dir": str(d.relative_to(ROOT)), "saved": saved})
        if p == "/api/council/read":
            files = [ROOT / f for f in body.get("files", [])]
            if not files: return self._send(400, {"error": "нет файлов"})
            cmd = [str(PY_API), str(ROOT / "council" / "read_pages.py"), "--env-file", ENV_FILE] + [str(f) for f in files]
            pid = JOBS["pages"].start(cmd); return self._send(200, {"pid": pid})
        if p == "/api/council/run":
            src = body.get("contract", "demo")
            if src == "demo": contract = ROOT / "council" / "demo-contract.md"
            else:
                contract = (ROOT / src).resolve()
                if not contract.is_relative_to(ROOT / "council" / "out") or not contract.exists(): return self._send(400, {"error": "договор не найден"})
            pid = JOBS["council"].start(["/bin/zsh", str(ROOT / "council" / "run_council.sh"), str(contract)], cwd=ROOT / "council")
            return self._send(200, {"pid": pid})
        if p == "/api/council/stop": JOBS["council"].stop(); JOBS["pages"].stop(); return self._send(200, {"ok": True})
        # ---------------- аудиотетрадь
        if p == "/api/notebook/read":
            m = re.match(r"data:(image/\w+);base64,(.*)", body.get("data", ""), re.S)
            if not m: return self._send(400, {"error": "нет картинки"})
            d = ROOT / "clips" / "score"; d.mkdir(parents=True, exist_ok=True)
            f = d / f"chart-{time.strftime('%Y%m%d-%H%M%S')}{'.png' if m.group(1) == 'image/png' else '.jpg'}"; f.write_bytes(base64.b64decode(m.group(2)))
            cmd = [str(PY_API), str(ROOT / "audionotebook" / "read_chart.py"), "--env-file", ENV_FILE, "--out", str(ROOT / "out" / "notebook" / "song.json"), str(f)]
            pid = JOBS["chart"].start(cmd); return self._send(200, {"pid": pid, "file": str(f.relative_to(ROOT))})
        if p == "/api/notebook/song":
            (ROOT / "out" / "notebook" / "song.json").write_text(json.dumps(body.get("song"), ensure_ascii=False, indent=1)); return self._send(200, {"ok": True})
        if p == "/api/notebook/clear":
            try: (ROOT / "out" / "notebook" / "song.json").unlink()
            except FileNotFoundError: pass
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "нет такого действия"})

    def _notebook_page(self):
        html = (ROOT / "audionotebook" / "index.html").read_text()
        f = ROOT / "out" / "notebook" / "song.json"
        inject = f"<script>window.__SONG__ = {f.read_text()};</script>\n" if f.exists() else ""
        html = html.replace('<script id="core">', inject + '<script id="core">', 1)
        return self._send(200, html, "text/html; charset=utf-8")

def main():
    srv = ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), PORT), H)   # только этот Mac; HOST=0.0.0.0 для телефона в той же сети
    print(f"Souls of Muse · очки: http://localhost:{PORT}  (клавиши /keys, консилиум /council, аудиотетрадь /notebook)", flush=True)
    try: srv.serve_forever()
    finally:
        for j in JOBS.values(): j.stop()

if __name__ == "__main__": main()
