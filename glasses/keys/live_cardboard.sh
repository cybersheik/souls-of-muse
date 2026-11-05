#!/bin/zsh
# Картонная клавиатура Камилы: очки → WhatsApp → чертёж 24+17 по чёрным клавишам → пианино.
# Ноты заданы чертежом, карта следует за головой каждые 0,7 с. Перед запуском выключить Stage Manager.
cd "$(dirname "$0")/.."
setopt nullglob; mkdir -p out/live; rm -f out/live/f*.jpg
exec .venv-mlx/bin/python keys/air_keys.py --source window --window WhatsApp --tracker hands --sam local \
  --layout cardboard --keys keys/keys_live.json --auto --sam-res 336 --press strike --press-vy 1.5 \
  --headless --snap-every 1 --log --instrument piano "$@" 2>&1 | grep --line-buffered -v Deprecat | tee out/live/log.txt
