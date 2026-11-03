# Плагин: yt-dlp

Скачивание видео, аудио и субтитров с YouTube, VK, TikTok, Twitter/X и сотен других сайтов.

## Установка

```bash
pip install -U yt-dlp        # или: brew install yt-dlp / winget install yt-dlp
yt-dlp --version
```
Для склейки видео+аудио нужен установленный FFmpeg.

## Основные команды

```bash
# Лучшее качество в MP4
yt-dlp -f "bv*+ba/b" --merge-output-format mp4 -o "src/%(title)s.%(ext)s" "<URL>"

# Не выше 1080p
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 "<URL>"

# Только аудио в MP3 (для Whisper)
yt-dlp -x --audio-format mp3 -o "work/audio.%(ext)s" "<URL>"

# Только фрагмент (с 1:00 до 2:30)
yt-dlp --download-sections "*00:01:00-00:02:30" -f "bv*+ba/b" --merge-output-format mp4 "<URL>"

# Субтитры без видео (ручные + автоматические, русский)
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "ru,en" --convert-subs srt "<URL>"

# Список доступных форматов
yt-dlp -F "<URL>"

# Метаданные в JSON (название, длительность, главы)
yt-dlp -j "<URL>"

# Плейлист
yt-dlp -o "src/%(playlist_index)03d - %(title)s.%(ext)s" "<URL_плейлиста>"
```

## Советы

- Ошибки при скачивании — сначала обнови: `yt-dlp -U` (или `pip install -U yt-dlp`).
- Для контента с возрастным ограничением/входом: `--cookies-from-browser chrome`.
- Используй `--restrict-filenames`, чтобы избежать проблем с пробелами и кириллицей в именах.
- Скачивай только то, на что у пользователя есть права.
