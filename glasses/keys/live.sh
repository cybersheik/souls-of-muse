#!/bin/zsh
# Живая проба: видеозвонок с очков → окно WhatsApp Desktop → локальный SAM 3.1 → ноты.
# Без своего окна (Stage Manager иначе уводит WhatsApp со сцены): ноты в журнал, оверлей в out/live/latest.jpg.
# Перекалибровать: touch glasses/out/live/RECALIBRATE
cd "$(dirname "$0")/.."
setopt nullglob; mkdir -p out/live; rm -f out/live/f*.jpg
exec .venv-mlx/bin/python keys/air_keys.py --source window --window WhatsApp --tracker hands --sam local \
  --keys keys/keys_live.json --auto --sam-res 336 --press strike --press-vy 1.5 \
  --headless --snap-every 1 --log --instrument sax "$@" 2>&1 | grep --line-buffered -v Deprecat | tee out/live/log.txt
