# Локальный воркер (бесплатная генерация видео)

Нужны: видеокарта NVIDIA от ~12 ГБ, Python 3.10+, ffmpeg, ~30 ГБ диска (модель скачивается при первом запуске).

```
cd worker
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python worker.py
```
Затем в `.env` приложения: `LOCAL_WORKER_URL=http://127.0.0.1:8188` и `npm start`.

Проверка связки без видеокарты: `WORKER_MOCK=1 python worker.py` (рисует тестовую картинку).

Ограничения (честно): модель LTX-Video рисует 768×512, выбранное качество (до 4K) получается апскейлом ffmpeg,
деталей он не добавляет. Звук не генерируется (видео без звука). Качество людей ниже платных Veo/Sora.
Время: от нескольких минут на ролик, зависит от карты.
