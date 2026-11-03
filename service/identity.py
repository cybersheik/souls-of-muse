"""Private participant login. Passwords and role assignment stay server-side."""
import hashlib
import hmac
import json
import secrets
import time
from contextlib import closing

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

COOKIE = "som_participant"
COOKIE_PATH = "/api/harness"


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}${digest}"


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class Identity:
    def __init__(self, app, db, commit, env, origins):
        self.db = db
        self.commit = commit
        self.secure = env.get("SOM_COOKIE_SECURE", "1") != "0"
        self.origins = origins
        self.on_logout = None
        self.accounts = json.loads(env.get("SOM_WEB_ACCOUNTS", "{}"))
        for user, account in self.accounts.items():
            if not user or account.get("role") not in ("maestro", "artist"):
                raise ValueError("invalid participant configuration")
            if len(account.get("password_hash", "")) < 130:
                raise ValueError("participant password hash required")
        with closing(db()) as c:
            c.execute("CREATE TABLE IF NOT EXISTS web_logins(token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires INTEGER NOT NULL)")
            commit(c)

        @app.post("/auth/login")
        def login(body: Login, request: Request):
            if not self.same_origin(request):
                return JSONResponse({"detail": "origin_not_allowed"}, status_code=403)
            account = self.accounts.get(body.username)
            # A dummy scrypt prevents fast username enumeration.
            stored = account["password_hash"] if account else "0" * 32 + "$" + "0" * 128
            salt = stored.split("$", 1)[0]
            if not hmac.compare_digest(password_hash(body.password, salt), stored):
                return JSONResponse({"detail": "invalid_login"}, status_code=401)
            token = secrets.token_urlsafe(32)
            with closing(db()) as c:
                c.execute("DELETE FROM web_logins WHERE expires < ?", (int(time.time()),))
                c.execute("INSERT INTO web_logins VALUES(?,?,?)", (self.digest(token), body.username, int(time.time()) + 28800))
                commit(c)
            response = JSONResponse(self.public(body.username))
            response.set_cookie(COOKIE, token, httponly=True, secure=self.secure,
                                samesite="strict", max_age=28800, path=COOKIE_PATH)
            response.headers["Cache-Control"] = "no-store"
            return response

        @app.get("/auth/me")
        def me(request: Request):
            user = self.user(request)
            return JSONResponse(self.public(user) if user else {"detail": "unauthorized"},
                                status_code=200 if user else 401, headers={"Cache-Control": "no-store"})

        @app.post("/auth/logout")
        async def logout(request: Request):
            if not self.same_origin(request):
                return JSONResponse({"detail": "origin_not_allowed"}, status_code=403)
            cleanup_pending = False
            user = self.user(request)
            if user and self.on_logout:
                try:
                    await self.on_logout(user)
                except Exception:
                    cleanup_pending = True
            with closing(db()) as c:
                c.execute("DELETE FROM web_logins WHERE token_hash=?", (self.digest(request.cookies.get(COOKIE, "")),))
                commit(c)
            response = JSONResponse({"signed_out": True, **({"detail":"media_cleanup_pending"} if cleanup_pending else {})}, status_code=503 if cleanup_pending else 200)
            response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=self.secure, httponly=True, samesite="strict")
            return response

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def same_origin(self, request):
        origin = request.headers.get("origin")
        local_origin = f"{request.url.scheme}://{request.url.netloc}"
        return origin in self.origins or origin == local_origin

    def public(self, user):
        account = self.accounts[user]
        return {"id": user, "role": account["role"], "name": account.get("name", user)}

    def user(self, request):
        token = request.cookies.get(COOKIE)
        if not token:
            return None
        with closing(self.db()) as c:
            row = c.execute("SELECT username FROM web_logins WHERE token_hash=? AND expires>?", (self.digest(token), int(time.time()))).fetchone()
        return row[0] if row and row[0] in self.accounts else None
