"""Meta Model API adapter with budget holds before any paid HTTP call.

Only /chat/completions is supported. /responses raises ConfigError before
HTTP rather than inventing a payload/schema. ASR paid route is disabled until
its usage contract is verified; WAV files are still inspected locally first.
SAM and TTS remain unimplemented with no local/system fallback.
Constructor performs no network I/O. No retries are performed.
"""
import json
import math
import os
import time
import wave
from pathlib import Path

OFFICIAL_BASE_URL = "https://api.meta.ai/v1"

import httpx

from .base import Adapter
from ..budget import KNOWN_CHAT_PRICES_USD_PER_MTOK, BudgetExceeded, UsageValidationError


class ConfigError(RuntimeError):
    pass


class MetaTransportError(RuntimeError):
    pass


class MetaAPIError(RuntimeError):
    pass


class MetaResponseError(RuntimeError):
    pass


MAX_REQUEST_BYTES = 32768
FRAMING_TOKENS = 2048
MAX_OUTPUT_TOKENS = 8192
# Documented Chat Completions reasoning_effort values (dev.meta.ai/docs/reasoning).
# "none" is not supported (upstream returns 400) and is rejected here first.
SUPPORTED_REASONING_EFFORTS = frozenset({"low", "medium", "high"})
ASR_DISABLED_REASON = "ASR paid route disabled: Meta ASR usage/billing contract is unverified, so no reservation or POST is made"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def inspect_wav(path):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise ConfigError("WAV file missing")
    size = p.stat().st_size
    if size <= 44 or size > 10 * 1024 * 1024:
        raise ConfigError("WAV file size unsupported")
    try:
        with wave.open(str(p), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.getnframes()
            comptype = wf.getcomptype()
    except Exception as exc:
        raise ConfigError("unsupported or malformed WAV file") from exc
    if comptype != "NONE" or channels != 1 or sampwidth != 2 or rate not in (16000, 24000) or frames <= 0:
        raise ConfigError("unsupported WAV format: require mono 16-bit PCM at 16kHz or 24kHz")
    duration = frames / float(rate)
    if duration <= 0 or duration > 60.0:
        raise ConfigError("WAV duration unsupported: require >0 and <=60 seconds")
    return {"duration_seconds": duration, "sample_rate": rate, "channels": channels, "sample_width": sampwidth, "frames": frames, "size_bytes": size}


class MetaAdapter(Adapter):
    name = "meta"

    def __init__(self, cfg, budget, transport=None, http_client=None, environ=None):
        self.cfg = cfg or {}
        self.budget = budget
        env = os.environ if environ is None else environ
        key_env = self.cfg.get("api_key_env", "MODEL_API_KEY")
        key = env.get(key_env, "") if hasattr(env, "get") else ""
        if not key:
            if transport is not None or http_client is not None:
                # Injected fake transports in tests may use an explicit fake env;
                # this placeholder is never a real credential and is not logged.
                key = "fake-key-for-injected-transport"
            else:
                raise ConfigError(f"missing {key_env} in environment; obtain a key from the provider console and export it (never commit keys)")
        self._key_env = key_env
        self.base = str(self.cfg.get("base_url", OFFICIAL_BASE_URL)).rstrip("/")
        if self.base != OFFICIAL_BASE_URL:
            raise ConfigError(f"base_url must be exactly {OFFICIAL_BASE_URL}; failing closed before client creation")
        if http_client is not None:
            base_url = str(getattr(http_client, "base_url", "")).rstrip("/")
            if base_url != OFFICIAL_BASE_URL:
                raise ConfigError("injected http_client base_url must match official; failing closed")
            headers = getattr(http_client, "headers", {}) or {}
            try:
                auth = headers.get("Authorization", "") if hasattr(headers, "get") else ""
            except Exception:
                auth = ""
            if auth and auth != f"Bearer {key}":
                raise ConfigError("injected http_client headers must not redirect key; failing closed")
            self.http = http_client
        else:
            self.http = httpx.Client(base_url=self.base, timeout=60, transport=transport, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})

    def _role(self, role):
        roles = self.cfg.get("roles") or {}
        rc = roles.get(role)
        if not isinstance(rc, dict):
            raise ConfigError(f"unknown role: {role}")
        return rc

    def _validate_chat_role(self, rc):
        endpoint = rc.get("endpoint")
        if endpoint != "/chat/completions":
            if endpoint == "/responses":
                raise ConfigError("/responses is unsupported by this adapter; only /chat/completions is supported")
            raise ConfigError(f"unsupported endpoint for chat adapter: {endpoint!r}; only /chat/completions is supported")
        model = rc.get("model")
        if model not in KNOWN_CHAT_PRICES_USD_PER_MTOK:
            raise ConfigError(f"unknown or disabled model for chat: {model!r}; failing closed before HTTP")
        if "max_tokens" not in rc:
            raise ConfigError("max_tokens must be explicit in role config")
        max_tokens = rc.get("max_tokens")
        if not _is_int(max_tokens) or max_tokens <= 0 or max_tokens > MAX_OUTPUT_TOKENS:
            raise ConfigError("max_tokens must be a positive integer within the explicit adapter bound")
        temp = rc.get("temperature", 0.1)
        if isinstance(temp, bool) or not isinstance(temp, (int, float)) or not math.isfinite(float(temp)) or temp < 0 or temp > 2:
            raise ConfigError("temperature must be a finite number in [0, 2]")
        reasoning_effort = None
        if "reasoning_effort" in rc:
            reasoning_effort = rc.get("reasoning_effort")
            if not isinstance(reasoning_effort, str) or reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
                raise ConfigError("reasoning_effort must be one of 'low', 'medium', 'high'; 'none' and other values are unsupported")
        return model, max_tokens, float(temp), reasoning_effort

    def complete(self, role, system, user, fault="none"):
        rc = self._role(role)
        model, max_tokens, temp, reasoning_effort = self._validate_chat_role(rc)
        if not isinstance(system, str) or not isinstance(user, str):
            raise ConfigError("system and user prompts must be strings")
        payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": temp, "max_tokens": max_tokens}
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except Exception as exc:
            raise ConfigError("request payload is not JSON serializable") from exc
        if len(body) > MAX_REQUEST_BYTES:
            raise ConfigError(f"serialized chat request exceeds {MAX_REQUEST_BYTES} UTF-8 bytes; failing closed before reservation/HTTP")
        # Deliberately overconservative: every serialized byte could be a token,
        # plus fixed framing allowance. This bounds input before the network.
        max_input_tokens = len(body) + FRAMING_TOKENS
        reservation_id = self.budget.reserve_chat(model, max_input_tokens, max_tokens)
        t0 = time.perf_counter()
        try:
            response = self.http.post("/chat/completions", content=body, headers={"Content-Type": "application/json"})
        except httpx.TimeoutException as exc:
            raise MetaTransportError("network timeout; full budget reservation remains on HOLD for operator review") from None
        except httpx.TransportError as exc:
            raise MetaTransportError("network transport error; full budget reservation remains on HOLD for operator review") from None
        latency = time.perf_counter() - t0
        if response.status_code != 200:
            raise MetaAPIError(f"Meta API returned HTTP {response.status_code}; full budget reservation remains on HOLD")
        try:
            data = response.json()
        except Exception as exc:
            raise MetaResponseError("malformed JSON response; full budget reservation remains on HOLD") from None
        if not isinstance(data, dict):
            raise MetaResponseError("malformed response object; full budget reservation remains on HOLD")
        usage = data.get("usage")
        if usage is None:
            raise MetaResponseError("response missing usage; full budget reservation remains on HOLD")
        try:
            cost = self.budget.settle(reservation_id, model, usage)
        except UsageValidationError as exc:
            raise MetaResponseError("response usage invalid or unknown; full budget reservation remains on HOLD") from None
        # BudgetExceeded from settle means BLOCKED/excess and must propagate.
        try:
            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        except Exception as exc:
            # Usage was trusted and settled, but payload shape is unusable.
            raise MetaResponseError("malformed response choices; usage was settled from trusted usage") from None
        if finish_reason == "length":
            # Truncated output (reasoning may consume the whole budget) must
            # never be delivered as a complete translation, even if partial.
            raise MetaResponseError("response truncated: finish_reason=length; usage was settled from trusted usage")
        try:
            text = choice["message"]["content"]
        except Exception as exc:
            raise MetaResponseError("malformed response choices; usage was settled from trusted usage") from None
        if not isinstance(text, str):
            raise MetaResponseError("malformed response text; usage was settled from trusted usage")
        return {"text": text, "usage": usage, "latency_s": round(latency, 3), "reservation_id": reservation_id, "cost_usd": cost}

    def transcribe(self, wav_path, keywords=None, language_bias=None):
        rc = self._role("asr")
        model = rc.get("model")
        # Inspect locally before any reservation/POST, even though route is disabled.
        info = inspect_wav(wav_path)
        _ = (model, info, keywords, language_bias)
        raise ConfigError(ASR_DISABLED_REASON)

    def segment(self, image_path, prompt):
        raise ConfigError("SAM segmentation is unimplemented in this adapter; no paid call or local fallback is attempted")

    def synthesize(self, text, **kwargs):
        raise ConfigError("TTS is unimplemented in this adapter; no system TTS or local fallback is claimed")
    # Compatibility name some benches probe for.
    def tts(self, text, **kwargs):
        return self.synthesize(text, **kwargs)
