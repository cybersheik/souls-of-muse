# Souls of Muse · очки Ray-Ban Meta: приложение на три направления

Один локальный сервер без зависимостей (стандартная библиотека Python), три страницы.

```bash
cd ~/Souls\ of\ Muse/glasses && .venv-mlx/bin/python app/server.py
```

→ http://localhost:8765 (слушает только этот Mac; `HOST=0.0.0.0 … app/server.py` — чтобы открыть с телефона в той же Wi-Fi).

| Страница | Что делает | Что под капотом |
|---|---|---|
| `/keys` Клавиши по партитуре | Запуск и остановка стенда, живой кадр с оверлеем, большая ожидаемая нота, лента партитуры, подтверждения | `keys/air_keys.py --press score --score fur_elise --layout piano|cardboard` (SAM 3.1 → чертёж → слежение по чёрным → замок октавы по первой ноте → DINOv2 «вид клавиши изменился»); состояние в `out/live/status.json`, кадр в `out/live/latest.jpg` |
| `/council` Консилиум по договору | Фото страниц → сохранить → прочитать (Muse Spark 1.3) → консилиум → выжимка в ухо (кнопка «Произнести», очки по Bluetooth слышат как гарнитура), пункты с цветом, пакет переговоров | `council/read_pages.py`, `council/run_council.sh` (Hermes MoA пресет `muse-council`: wonder-1.0 + spark-1.3 + spark-1.2, агрегатор wonder-1.0, плейбук `council/playbook-v0.md`); ответы в `council/out/<stamp>/answer.md` |
| `/notebook` Аудиотетрадь | Сетка аккордов, темп, голос в ухо (аккорд, следующий, к чему готовиться), тихий щелчок; «Сетка с фото» — фото пюпитра → Muse Spark → песня | `audionotebook/index.html` (Web Audio + Web Speech), `audionotebook/read_chart.py` → `out/notebook/song.json` |

Ключ Meta Model API берётся из `~/.hermes/profiles/jack/.env` (переменная окружения `MUSE_ENV_FILE` — другой файл) и никуда не печатается.
Журналы подпроцессов: `out/app/{keys,pages,council,chart}.log`.

Источники кадров для стенда: окно звонка WhatsApp на Mac (очки звонят «Музе»), веб-камера, видеофайл (для проверки по записи), экран.
