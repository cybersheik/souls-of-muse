#!/bin/zsh
# Первый прогон солиста: стенд пишет ноты в clips/kamila/take1.notes.json (для снятия партитуры), звук — пианино.
cd "$(dirname "$0")/.."; setopt nullglob; mkdir -p out/live clips/kamila; rm -f out/live/f*.jpg
exec .venv-mlx/bin/python keys/air_keys.py --source window --window WhatsApp --tracker hands --sam local \
  --keys keys/keys_live.json --auto --sam-res 336 --press strike --press-vy 1.5 \
  --headless --snap-every 1 --log --instrument piano --record clips/kamila/take1.notes.json "$@" 2>&1 | grep --line-buffered -v Deprecat | tee out/live/log.txt
