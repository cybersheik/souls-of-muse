#!/bin/zsh
# Следить за живым стендом: ждать окно звонка и клавиши, печатать события из журнала.
cd "$(dirname "$0")/.."
tail -n 0 -F out/live/log.txt | grep --line-buffered -E "окно|КЛАВИШИ|пропали|ON |OFF " 
