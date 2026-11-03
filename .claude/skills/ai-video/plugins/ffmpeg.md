# Плагин: FFmpeg

Универсальный инструмент для обработки видео и аудио.

## Установка

```bash
sudo apt install ffmpeg      # Linux
brew install ffmpeg          # macOS
winget install ffmpeg        # Windows
ffmpeg -version
```

## Информация о файле

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of json in.mp4
```

## Нарезка

```bash
# Быстро, без перекодирования (резка по ключевым кадрам)
ffmpeg -ss 00:01:00 -to 00:01:45 -i in.mp4 -c copy work/cut.mp4

# Точно до кадра (с перекодированием)
ffmpeg -ss 00:01:00 -to 00:01:45 -i in.mp4 -c:v libx264 -crf 20 -preset medium -c:a aac -b:a 192k work/cut.mp4
```

## Склейка

```bash
# list.txt:
# file 'part1.mp4'
# file 'part2.mp4'
ffmpeg -f concat -safe 0 -i list.txt -c copy output/joined.mp4
```
Если у частей разные кодеки/размеры — убери `-c copy` и перекодируй.

## Вертикаль 9:16 (Shorts / Reels / TikTok)

```bash
# Кроп по центру
ffmpeg -i in.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:v libx264 -crf 20 -c:a copy output/vertical.mp4

# Вписать с размытым фоном
ffmpeg -i in.mp4 -filter_complex \
"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg]; \
 [0:v]scale=1080:-2[fg]; [bg][fg]overlay=(W-w)/2:(H-h)/2" \
-c:v libx264 -crf 20 -c:a copy output/vertical_blur.mp4
```

## Субтитры

```bash
# Вшить SRT в картинку (со стилем)
ffmpeg -i in.mp4 -vf "subtitles=work/subs.srt:force_style='FontName=Arial,FontSize=14,Outline=2,Alignment=2,MarginV=60'" -c:a copy output/subbed.mp4

# Добавить как отключаемую дорожку
ffmpeg -i in.mp4 -i work/subs.srt -c copy -c:s mov_text -metadata:s:s:0 language=rus output/softsub.mp4
```

## Звук

```bash
# Извлечь звук для Whisper
ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 work/audio.wav

# Заменить звук
ffmpeg -i video.mp4 -i voice.mp3 -map 0:v -map 1:a -c:v copy -shortest output/out.mp4

# Подложить музыку тише голоса
ffmpeg -i video.mp4 -i music.mp3 -filter_complex "[1:a]volume=0.15[m];[0:a][m]amix=inputs=2:duration=first[a]" -map 0:v -map "[a]" -c:v copy output/with_music.mp4

# Нормализация громкости (стандарт для соцсетей)
ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy output/normalized.mp4
```

## Прочее

```bash
# Сжать для отправки
ffmpeg -i in.mp4 -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart output/small.mp4

# Кадр-превью
ffmpeg -ss 00:00:05 -i in.mp4 -frames:v 1 output/thumb.jpg

# GIF
ffmpeg -i in.mp4 -vf "fps=12,scale=480:-1:flags=lanczos" output/clip.gif

# Ускорить в 1.5 раза
ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=PTS/1.5[v];[0:a]atempo=1.5[a]" -map "[v]" -map "[a]" output/fast.mp4

# Наложить логотип в правый верхний угол
ffmpeg -i in.mp4 -i assets/logo.png -filter_complex "overlay=W-w-40:40" -c:a copy output/logo.mp4
```

## Советы

- Для публикации всегда добавляй `-movflags +faststart` и `-pix_fmt yuv420p`.
- `-crf`: 18 — почти без потерь, 23 — по умолчанию, 28 — сильно сжато.
- Пути с пробелами и кириллицей бери в кавычки.
