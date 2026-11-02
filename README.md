# video-forge — скилл Claude Code для создания видео

Скилл превращает идею или сценарий в готовое видео в три шага:

1. **Сценарий**: вы присылаете текст или описываете идею, и Claude пишет сценарий сам.
2. **Голос**: вы выбираете диктора, например *Adam*, Rachel, Josh (ElevenLabs), Dmitry или Svetlana (бесплатно) либо голос OpenAI.
3. **Сборка**: Claude разбивает сценарий на сцены, делает раскадровку, озвучивает каждую сцену, добавляет звуковые эффекты, фоновую музыку и субтитры, затем собирает `final.mp4`.

![пример раскадровки](.claude/skills/video-forge/examples/demo/storyboard.png)

Пример результата: [`examples/demo/final.mp4`](.claude/skills/video-forge/examples/demo/final.mp4)
и [`storyboard.md`](.claude/skills/video-forge/examples/demo/storyboard.md).

## Установка

Нужны **Python 3.9+** и **ffmpeg**.

```bash
# ffmpeg
sudo apt install ffmpeg        # или: brew install ffmpeg

# бесплатная озвучка (необязательно)
pip install edge-tts

# скилл для всех проектов
git clone https://github.com/robloxvbvvh-design/Cloud-code.git
mkdir -p ~/.claude/skills
cp -r Cloud-code/.claude/skills/video-forge ~/.claude/skills/
```

Если открыть этот репозиторий в Claude Code, скилл подключится сам: он лежит в `.claude/skills/`.

### Голоса

| Движок | Что нужно | Голоса |
|---|---|---|
| ElevenLabs | `export ELEVENLABS_API_KEY=...` | Adam, Rachel, Antoni, Josh, Bella, Arnold, Domi, Elli, Sam или любой voice_id из вашей библиотеки |
| OpenAI | `export OPENAI_API_KEY=...` | alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer |
| edge-tts | `pip install edge-tts`, бесплатно | ru-RU-DmitryNeural, ru-RU-SvetlanaNeural и сотни других |
| silent | ничего | без озвучки |

Если выбранный голос недоступен (например, Adam без ключа ElevenLabs), скилл подставит ближайший доступный и сообщит об этом.

## Использование

В Claude Code:

```
/video-forge ролик на 30 секунд о том, почему небо голубое
```

или просто: «сделай видео…». Claude спросит сценарий и голос, покажет раскадровку и соберёт ролик.

Движок можно запускать и вручную:

```bash
VF=.claude/skills/video-forge/scripts/vf.py
python3 $VF check                         # что доступно
python3 $VF voices --provider edge --lang ru
python3 $VF sfx-list                      # встроенные эффекты и музыка
python3 $VF all video-projects/my-video   # озвучка + эффекты + сборка
python3 $VF render video-projects/my-video --scenes 2   # пересобрать сцену
```

Формат `storyboard.json` описан в [`references/storyboard-schema.md`](.claude/skills/video-forge/references/storyboard-schema.md).

## Возможности

- Форматы 9:16, 16:9, 1:1, 4:5.
- Фоны: анимированный градиент с заголовком, ваши картинки с движением камеры (zoom/pan) или ваши видео.
- Длительность каждой сцены подстраивается под озвучку.
- Субтитры синхронизированы с речью.
- 17 встроенных звуковых эффектов синтезируются через ffmpeg, скачивать ничего не нужно: whoosh, impact, riser, ding, pop, typing, heartbeat, rain и другие. С ключом ElevenLabs эффекты можно генерировать по текстовому описанию.
- Фоновая музыка: встроенные `pad`, `dark`, `bright` или ваш трек. Под голосом музыка автоматически приглушается (sidechain).
- Раскадровка: `storyboard.md` (таблица с таймкодами) и `storyboard.png` (кадры сцен).
