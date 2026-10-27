"""Детерминированный семантический валидатор (Harness v0.1).
Сравнивает НЕ строки, а эталонные множества: числа, отрицания, ноты, term_id.
term_id — из справочника (стабильный идентификатор, а не поверхностная форма).
"""
import json, re, unicodedata
from pathlib import Path

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
NEG_EN = re.compile(r"\b(?:not|no|never|n't|don'?t|do not)\b", re.I)
NEG_VI = re.compile(r"\b(?:không|đừng|chớ|đừng có|chưa)\b", re.I)
# Нота засчитывается только рядом с опорным словом — чтобы не путать ноту A и артикль a.
# Опорные слова даны на обоих языках: валидатор обязан читать и EN-источник, и VI-перевод.
NOTE_CTX = re.compile(
    r"\b([A-G])([#b♯♭]?)\s+(major|minor|chord|trưởng|thứ|hợp\s+âm)\b", re.I)

ORDINALS = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
            "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10"}


def load_glossary(path="data/seed_terms.jsonl"):
    terms = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            terms.append(json.loads(line))
    return terms


def _norm(s):
    return unicodedata.normalize("NFC", s.lower())


def numbers(text):
    t = _norm(text)
    for w, d in ORDINALS.items():
        t = re.sub(rf"\b{w}\b", d, t)
    return set(NUM_RE.findall(t))


def negation_count(text, lang):
    rx = NEG_VI if lang == "vi" else NEG_EN
    return len(rx.findall(_norm(text)))


def notes(text):
    out = set()
    for m in NOTE_CTX.finditer(text):
        acc = m.group(2).replace("♯", "#").replace("♭", "b")
        out.add(m.group(1).upper() + acc)
    return out


def term_ids(text, glossary):
    """Жадное совпадение от длинных форм к коротким с вычёркиванием занятых
    регионов: вложенные формы («rải hợp âm» ⊃ «hợp âm») не дают ложных term_id.
    Синонимы — это несколько форм одного term_id (списки в полях en/vi канона)."""
    t = " " + _norm(text) + " "
    forms = []
    for term in glossary:
        for lang in ("en", "vi"):
            fs = term[lang] if isinstance(term[lang], list) else [term[lang]]
            forms += [(_norm(f), term["term_id"]) for f in fs]
    ids = set()
    for f, tid in sorted(forms, key=lambda x: -len(x[0])):
        pat = re.compile(rf"(?<![\w]){re.escape(f)}(?![\w])")
        if pat.search(t):
            ids.add(tid)
            t = pat.sub(lambda m: " " * len(m.group()), t)
    return ids


def signature(text, lang, glossary):
    return {
        "numbers": numbers(text),
        "neg": negation_count(text, lang),
        "notes": notes(text),
        "terms": term_ids(text, glossary),
    }


def compare(src_sig, out_sig):
    """Возвращает список искажений; пустой список = смысл сохранён полностью."""
    issues = []
    lost = src_sig["numbers"] - out_sig["numbers"]
    extra = out_sig["numbers"] - src_sig["numbers"]
    if lost or extra:
        issues.append(f"числа: потеряно {sorted(lost) or '—'}, лишние {sorted(extra) or '—'}")
    if src_sig["neg"] != out_sig["neg"]:
        issues.append(f"отрицания: было {src_sig['neg']}, стало {out_sig['neg']}")
    if src_sig["notes"] != out_sig["notes"]:
        issues.append(f"ноты: было {sorted(src_sig['notes'])}, стало {sorted(out_sig['notes'])}")
    if src_sig["terms"] != out_sig["terms"]:
        issues.append(
            f"term_id: потеряно {sorted(src_sig['terms'] - out_sig['terms']) or '—'}, "
            f"лишние {sorted(out_sig['terms'] - src_sig['terms']) or '—'}")
    return issues
