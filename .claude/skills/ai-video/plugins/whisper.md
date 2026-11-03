# Плагин: Whisper

Распознавание речи (OpenAI Whisper): транскрипция, перевод на английский, субтитры с таймкодами.

## Установка

```bash
pip install -U openai-whisper     # нужен FFmpeg в системе
# Быстрее и экономнее по памяти:
pip install -U faster-whisper
```

## Модели

| Модель | Скорость | Качество | VRAM |
|---|---|---|---|
| `tiny` / `base` | очень быстро | черновик | ~1 ГБ |
| `small` | быстро | нормально | ~2 ГБ |
| `medium` | средне | хорошо (рекомендуется для русского) | ~5 ГБ |
| `large-v3` / `turbo` | медленнее | лучшее | ~6–10 ГБ |

## CLI (openai-whisper)

```bash
# Субтитры SRT на русском
whisper work/audio.mp3 --model medium --language ru --output_format srt --output_dir work/

# Все форматы сразу (txt, srt, vtt, tsv, json)
whisper src/video.mp4 --model medium --language ru --output_format all --output_dir work/

# Перевод речи на английский
whisper work/audio.mp3 --model medium --task translate

# Пословные таймкоды (для анимированных субтитров)
whisper work/audio.mp3 --model medium --language ru --word_timestamps True --output_format json
```

## Python (faster-whisper) — пословные таймкоды

```python
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="auto", compute_type="auto")
segments, info = model.transcribe("work/audio.mp3", language="ru", word_timestamps=True)

for seg in segments:
    for w in seg.words:
        print(f"{w.start:.2f}-{w.end:.2f} {w.word}")
```

JSON со словами и таймкодами удобно передавать в Remotion/HyperFrames для караоке-субтитров.

## Советы

- Указывай `--language ru` явно — точнее и быстрее автоопределения.
- Перед распознаванием длинного видео извлеки звук: `ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 work/audio.wav`.
- Проверяй и исправляй имена, термины и числа в расшифровке вручную.
- Субтитры для Shorts: не больше 1–2 строк и ~32 символов в строке.
