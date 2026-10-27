"""P3 · ASR-проба Muse Voice Transcribe (T-01): WER по корпусу WAV с эталонами,
фокус — вьетнамский + музыкальные термины; keyword biasing строится из справочника.
Корпус кладётся в data/asr_corpus/ как name.wav + name.ref.txt (PCM 16-бит 24 кГц —
конвертация: ffmpeg -i in.mp3 -ac 1 -ar 24000 -sample_fmt s16 name.wav)."""
from pathlib import Path

from harness.validator import load_glossary

CORPUS = Path("data/asr_corpus")


def _wer(ref, hyp):
    r, h = ref.lower().split(), hyp.lower().split()
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[-1][-1] / max(1, len(r))


def build_bias_lists():
    terms = load_glossary()
    en, vi = set(), set()
    for t in terms:
        en.update(t["en"] if isinstance(t["en"], list) else [t["en"]])
        en.add(t["legacy_it"])
        vi.update(t["vi"] if isinstance(t["vi"], list) else [t["vi"]])
    Path("data/asr_bias_en.txt").write_text("\n".join(sorted(en)), encoding="utf-8")
    Path("data/asr_bias_vi.txt").write_text("\n".join(sorted(vi)), encoding="utf-8")
    return sorted(en), sorted(vi)


def run(adapter, budget, mock_mode):
    en_bias, vi_bias = build_bias_lists()
    wavs = sorted(CORPUS.glob("*.wav"))
    rows, wers = [], []
    for w in wavs:
        ref_path = w.with_suffix("").with_suffix(".ref.txt")
        if not ref_path.exists():
            rows.append({"file": w.name, "error": "нет .ref.txt эталона"})
            continue
        r = adapter.transcribe(str(w), keywords=en_bias, language_bias=None)
        ref = ref_path.read_text(encoding="utf-8").strip()
        wer = round(_wer(ref, r["text"]), 3)
        wers.append(wer)
        rows.append({"file": w.name, "wer": wer, "latency_s": r["latency_s"],
                     "hyp": r["text"][:120]})
    avg = sum(wers) / len(wers) if wers else None
    note = ("корпус пуст — ждём записи EN/VI-реплик наставника (DW1, P05); "
            "биас-листы сгенерированы: data/asr_bias_en.txt, data/asr_bias_vi.txt") if not wavs \
           else f"прогнано {len(wavs)} файлов"
    return {"probe": "P3 · ASR Voice Transcribe (T-01)",
            "status": "blocked" if not wavs else ("ok" if avg is not None and avg <= 0.10 else "fail"),
            "mode_note": "mock-распознавание" if mock_mode else "реальный Voice Transcribe",
            "files": len(wavs), "avg_wer": avg, "target_wer": 0.10,
            "bias_terms_en": len(en_bias), "bias_terms_vi": len(vi_bias),
            "detail": note, "rows": rows}
