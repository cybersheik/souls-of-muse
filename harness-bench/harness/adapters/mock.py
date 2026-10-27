"""Детерминированный офлайн-эмулятор моделей. Кредиты не тратит, сеть не трогает.
Нужен, чтобы проверять логику Harness (маршрутизацию, валидатор, бюджетный страж)
до подключения ключа MODEL_API_KEY. Задержки СИМУЛИРУЮТСЯ моделью логнормального
распределения — это НЕ измерения реального API (в отчётах помечается явно).
"""
import hashlib, random, re, unicodedata
from pathlib import Path

from .base import Adapter
from ..validator import load_glossary, _norm

NEG_MAP = [(r"\bdo not\b", "đừng"), (r"\bdon'?t\b", "đừng"), (r"\bnot\b", "không"),
           (r"\bnever\b", "không bao giờ"), (r"\bno\b", "không")]
VI_NEG_TOKENS = ("đừng", "không")


def _seed_of(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


class MockAdapter(Adapter):
    name = "mock"

    def __init__(self, cfg, budget):
        self.cfg = cfg
        self.budget = budget
        self.glossary = load_glossary()

    # --- правдоподобный EN→VI по глоссарию: термины подставляются, остальное
    # остаётся английским каркасом (стенд проверяет логику, а не качество mock-перевода)
    def _translate(self, text, fault):
        out = " " + text + " "
        forms = []
        for term in self.glossary:
            ens = term["en"] if isinstance(term["en"], list) else [term["en"]]
            forms += [(e, term["vi"]) for e in ens]
        for en_form, vi_form in sorted(forms, key=lambda x: -len(x[0])):
            rx = re.compile(rf"(?<![\w]){re.escape(_norm(en_form))}(?![\w])", re.I)
            out = rx.sub(" " + vi_form + " ", out)
        for pat, rep in NEG_MAP:
            out = re.sub(pat, rep, out, flags=re.I)
        if fault == "drop_negation":          # смоделированный сбой: потеря отрицания
            for tok in VI_NEG_TOKENS:
                out = re.sub(rf"(?<![\w]){tok}(?![\w])", "", out, count=1)
        if fault == "wrong_number":           # смоделированный сбой: порча числа
            out = re.sub(r"\d+", lambda m: str(int(m.group()) + 1), out, count=1)
        return re.sub(r"\s+", " ", out).strip()

    def complete(self, role, system, user, fault="none"):
        rng = random.Random(_seed_of(role + user))
        base_ms = {"interpreter": 900, "reviewer": 550, "orchestrator": 2400}.get(role, 700)
        latency = max(0.15, rng.lognormvariate(0, 0.25)) * base_ms / 1000
        if role == "interpreter":
            text = self._translate(user, fault)
        elif role == "reviewer":
            text = "OK" if fault == "none" else "REJECT: семантическое искажение"
        else:
            text = "ack"
        usage = {"prompt_tokens": len(user) // 4 + 120,
                 "completion_tokens": len(text) // 4 + 20}
        return {"text": text, "usage": usage, "latency_s": round(latency, 3)}

    def transcribe(self, wav_path, keywords=None, language_bias=None):
        rng = random.Random(_seed_of(str(wav_path)))
        ref = Path(str(wav_path).replace(".wav", ".ref.txt"))
        if ref.exists():                       # есть эталон — «распознаём» его с редкой ошибкой
            text = ref.read_text(encoding="utf-8").strip()
            if rng.random() < 0.15:
                text = re.sub(r"\b\w+\b", lambda m: m.group()[:-1], text, count=1)
        else:
            text = f"[mock transcript of {Path(wav_path).name}]"
        return {"text": text, "latency_s": round(0.4 + rng.random() * 0.3, 3), "seconds": 4.0}

    def segment(self, image_path, prompt):
        return {"masks": [{"bbox": [0.31, 0.18, 0.38, 0.30], "prompt": prompt,
                           "area_ratio": 0.114, "source": "mock"}],
                "latency_s": 0.9}
