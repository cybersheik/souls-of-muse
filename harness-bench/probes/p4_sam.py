"""P4 · Контракт маски лиц SAM 3.1 (T-05: ни одного открытого лица; руки и
инструмент сохраняются). Здесь — проверка КОНТРАКТА ответа сегментации и геометрии
маски; боевой вызов требует пути Media segmentation из документации (config).
"""
from . import __name__  # noqa
from harness.adapters.meta import ConfigError

REQUIRED_KEYS = {"bbox", "prompt"}


def _valid_mask(m):
    if not REQUIRED_KEYS <= set(m):
        return "нет обязательных полей bbox/prompt"
    bb = m["bbox"]
    if len(bb) != 4 or not all(0.0 <= v <= 1.0 for v in bb):
        return "bbox вне нормировки 0..1"
    if not (bb[2] > 0 and bb[3] > 0):
        return "нулевая геометрия маски"
    return None


def run(adapter, budget, mock_mode):
    try:
        res = adapter.segment("data/synthetic_face.png", prompt="face")
    except ConfigError as e:
        return {"probe": "P4 · маска лиц SAM 3.1 (T-05)", "status": "blocked",
                "mode_note": "боевой адаптер", "detail": str(e),
                "action": "заполнить endpoint из dev.meta.ai/docs (Media segmentation)"}
    errors = [err for m in res["masks"] if (err := _valid_mask(m))]
    ok = not errors and len(res["masks"]) >= 1
    return {"probe": "P4 · маска лиц SAM 3.1 (T-05)",
            "status": "ok" if ok else "fail",
            "mode_note": "контрактная проверка на mock-ответе" if mock_mode else "реальный SAM",
            "masks": len(res["masks"]), "contract_errors": errors,
            "detail": f"масок {len(res['masks'])}, ошибок контракта {len(errors)}; "
                      "след. шаг — прогон на реальных кадрах урока с проверкой "
                      "сохранности рук/инструмента (GT, H04)"}
