#!/bin/zsh
# Второй прогон: партитура снята с первого (ensemble/kamila.py), ансамбль идёт за солисткой. Солист — настоящее пианино, стенд молчит сам.
cd "$(dirname "$0")/.."; setopt nullglob; mkdir -p out/live; rm -f out/live/f*.jpg
exec .venv-mlx/bin/python keys/air_keys.py --source window --window WhatsApp --tracker hands --sam local \
  --keys keys/keys_live.json --auto --sam-res 336 --press strike --press-vy 1.5 \
  --headless --snap-every 1 --log --no-sound --ensemble kamila "$@" 2>&1 | grep --line-buffered -v Deprecat | tee out/live/log.txt
