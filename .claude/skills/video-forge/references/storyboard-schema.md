# storyboard.json — схема

```jsonc
{
  "title": "Почему небо голубое",
  "format": "9:16",              // 9:16 | 16:9 | 1:1 | 4:5, или "resolution": "1280x720"
  "fps": 30,
  "palette": ["#0b1d3a", "#1e6fd9"], // цвета градиента по умолчанию
  "font": "/path/to/font.ttf",   // необязательно; по умолчанию DejaVu Sans Bold (есть кириллица)
  "subtitles": true,             // субтитры из narration внизу кадра
  "music": "pad",                // pad | dark | bright | "music/track.mp3" | null
  "music_volume": 0.15,
  "output": "final.mp4",
  "voice": {
    "provider": "auto",          // auto | elevenlabs | openai | edge | espeak | silent
    "voice": "Артём энергичный", // имя из каталога (120 голосов: vf.py voices), ID edge/ElevenLabs/OpenAI
    "effect": "robot",           // эффект(ы) голоса: robot, giant, gnome, monster, alien, ghost, deep,cave …
    "lang": "ru",                // для подбора запасного голоса
    "model": "eleven_multilingual_v2",          // elevenlabs (или gpt-4o-mini-tts для openai)
    "stability": 0.45, "similarity": 0.8, "style": 0.2,   // elevenlabs
    "rate": "+5%", "pitch": "+0Hz",             // edge
    "instructions": "Энергично, как ведущий",   // openai
    "volume": 1.0
  },
  "characters": {               // голоса персонажей для диалогов
    "Клод Код": { "voice": "Робот" },
    "Артемия":  { "voice": "Алина", "rate": "+5%" }  // поля поверх каталога
  },
  "scenes": [
    {
      "id": 1,                   // необязательно, нумеруется само
      "speaker": "Артемия",      // чей голос читает narration (ключ из characters)
      "narration": "Текст, который читает диктор.",
      "duration": 4,             // минимум секунд; иначе = длина озвучки + 0.8 с
      "visual": {
        "type": "text",          // text | image | video | color
        "source": "img/1.jpg",   // для image/video, путь относительно проекта
        "motion": "zoom_in",     // image: zoom_in | zoom_out | pan_left | pan_right | none
        "caption": "Заголовок",  // текст на экране (эмодзи вырезаются)
        "caption_pos": "center", // top | center | bottom
        "font_size": 90,
        "text_color": "white",
        "colors": ["#3a1c71", "#ffaf7b"], // градиент этой сцены
        "fade": 0.3,             // затемнение на входе/выходе, 0 = без
        "vignette": true,
        "description": "Что в кадре — для раскадровки"
      },
      "sfx": [
        { "name": "whoosh", "at": 0.0, "volume": 0.6 },
        { "prompt": "door creak", "name": "click", "at": 1.2, "length": 1.5 },
        { "file": "sfx/boom.mp3", "at": 2.0 }
      ]
    }
  ]
}
```

Поля, которые дописывает движок: `voice_file`, `voice_text`, `voice_duration`, `start`, `end`,
`sfx[].resolved`, `voice.used` (какой провайдер и голос реально сработали).

Структура проекта после сборки:

```
video-projects/<slug>/
  storyboard.json   storyboard.md   storyboard.png   final.mp4
  audio/voice/scene_01.wav …   audio/sfx/*.wav
  build/scene_01.mp4 …         (промежуточные клипы)
```
