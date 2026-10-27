"""P2 · Терминология EN↔VI и валидатор смысла (T-02: ≥95% реплик без искажений,
100% критических искажений остановлены до доставки). Корпус включает внесённые сбои
(fault) и контрольную adversarial-реплику без отрицания."""
import json
from pathlib import Path

from harness.validator import load_glossary, signature, compare

SYSTEM = ("Ты — interpreter Souls of Muse. Переведи реплику наставника с английского "
          "на вьетнамский. Сохрани числа, ноты, отрицания и музыкальные термины.")


def run(adapter, budget, mock_mode):
    replicas = json.loads(Path("data/replicas_en.json").read_text())
    glossary = load_glossary()
    rows, clean_preserved, faults_caught, faults_total = [], 0, 0, 0

    for rep in replicas:
        r = adapter.complete("interpreter", SYSTEM, rep["en"], fault=rep["fault"])
        src = signature(rep["en"], "en", glossary)
        out = signature(r["text"], "vi", glossary)
        issues = compare(src, out)
        if rep["fault"] == "none":
            faults_total += 0
            if not issues:
                clean_preserved += 1
        else:
            faults_total += 1
            if issues:
                faults_caught += 1
        rows.append({"id": rep["id"], "fault": rep["fault"],
                     "adversarial": rep.get("adversarial"),
                     "vi": r["text"], "issues": issues,
                     "src_terms": sorted(src["terms"]), "out_terms": sorted(out["terms"])})

    clean = [x for x in rows if x["fault"] == "none"]
    preserved_pct = clean_preserved / max(1, len(clean))
    caught_pct = faults_caught / max(1, faults_total)
    ok = preserved_pct >= 0.95 and caught_pct == 1.0
    return {"probe": "P2 · терминология и валидатор (T-02)",
            "status": "ok" if ok else "fail",
            "mode_note": "mock-перевод по глоссарию" if mock_mode else "реальный muse-spark-1.3",
            "clean_replicas": len(clean), "clean_preserved": clean_preserved,
            "preserved_pct": round(preserved_pct, 3),
            "faults_injected": faults_total, "faults_caught": faults_caught,
            "caught_pct": round(caught_pct, 3),
            "detail": f"чистые реплики сохранены {clean_preserved}/{len(clean)} "
                      f"({preserved_pct:.0%} при пороге 95%); внесённые искажения "
                      f"пойманы {faults_caught}/{faults_total} (нужно 100%)",
            "rows": rows}
