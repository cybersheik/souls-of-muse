"""P1 · Сквозная задержка речевой петли (T-04: P95 ≤ 5 с).
Цепочка: ASR(оценка/замер) → interpreter → валидатор → (reviewer при отказе) → TTS(оценка).
В mock-режиме задержки СИМУЛИРОВАНЫ — в отчёт пишется пометка; реальные цифры — в meta-режиме.
"""
import json, statistics, time, uuid
from datetime import datetime, timezone
from pathlib import Path

from harness.validator import load_glossary, signature, compare
from harness.schema import validate_event

ASR_EST_S = 0.60   # оценка файлового ASR на реплику ~4 с (уточняется пробой P3)
TTS_EST_S = 0.70   # неподтвержденная оценка; TTS Meta еще не подключен

SYSTEM = ("Ты — interpreter Souls of Muse. Переведи реплику наставника с английского "
          "на вьетнамский. Сохрани числа, ноты, отрицания и музыкальные термины. "
          "Только перевод, без пояснений.")


def run(adapter, budget, mock_mode):
    replicas = json.loads(Path("data/replicas_en.json").read_text())
    glossary = load_glossary()
    totals, escalations, events_bad = [], 0, 0
    lesson_id = f"bench-{uuid.uuid4().hex[:8]}"
    seq = 0

    for rep in replicas:
        for _ in range(3):  # 3 прогона на реплику
            t0 = time.perf_counter()
            r1 = adapter.complete("interpreter", SYSTEM, rep["en"], fault=rep["fault"])
            issues = compare(signature(rep["en"], "en", glossary),
                             signature(r1["text"], "vi", glossary))
            lat = ASR_EST_S + r1["latency_s"] + TTS_EST_S
            if issues:  # отказ валидатора → reviewer (повторная обработка/эскалация)
                r2 = adapter.complete("reviewer", SYSTEM, r1["text"], fault=rep["fault"])
                lat += r2["latency_s"]
                escalations += 1
            totals.append(round(lat, 3))

            ev = {"event_id": str(uuid.uuid4()), "lesson_id": lesson_id, "seq": seq,
                  "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                  "type": "validator.fail" if issues else "interpret.done",
                  "actor": "muse", "lang": "vi",
                  "payload": {"replica": rep["id"], "issues": issues},
                  "trace": {"interpreter_ms": int(r1["latency_s"] * 1000)}}
            seq += 1
            if validate_event(ev):
                events_bad += 1

    p50 = statistics.median(totals)
    p95 = sorted(totals)[int(len(totals) * 0.95) - 1]
    ok = p95 <= 5.0 and events_bad == 0
    return {"probe": "P1 · расчет задержки (T-04, не приемка E2E)",
            "status": ("ok" if ok else "fail") if mock_mode else "partial",
            "measurement_scope": "simulated" if mock_mode else "text API measured; ASR and TTS estimated; live voice E2E unmeasured",
            "mode_note": "задержки симулированы mock-моделью" if mock_mode else "измерен только текстовый API; ASR и TTS оценены; реальный голосовой E2E не проверен",
            "runs": len(totals), "p50_s": round(p50, 3), "p95_s": round(p95, 3),
            "budget_s": 5.0, "escalations": escalations,
            "schema_events_bad": events_bad,
            "detail": f"Расчет: P50={p50:.2f} с, P95={p95:.2f} с при пороге 5 с; ASR/TTS не измерены; "
                      f"эскалаций валидатора {escalations}; события схемы: {events_bad} ошибок"}
