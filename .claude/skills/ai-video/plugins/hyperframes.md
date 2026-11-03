# Плагин: HyperFrames

Open-source фреймворк (HeyGen) для создания видео из обычного **HTML + CSS + JS**. Сцена — это HTML-страница, анимации — GSAP-таймлайн, рендер — в MP4. Особенно удобен для ИИ: модели отлично пишут HTML.

Документация и репозиторий: https://github.com/heygen-com/hyperframes

> Проект молодой и быстро меняется — при расхождении команд с этой инструкцией сверяйся с README репозитория.

## Установка и запуск

```bash
npx hyperframes init my-video     # создать проект
cd my-video
npx hyperframes preview           # превью в браузере с live-reload
npx hyperframes render            # рендер в MP4
```
Требуется Node.js 18+ и FFmpeg.

## Пример композиции (`index.html`)

```html
<div id="stage" data-composition-id="main" data-width="1080" data-height="1920">
  <video id="bg" src="assets/clip.mp4"
         data-start="0" data-duration="10" data-track-index="0" muted playsinline></video>

  <h1 id="title" class="clip"
      data-start="0.5" data-duration="4" data-track-index="1">Привет!</h1>

  <audio src="assets/music.mp3" data-start="0" data-duration="10"
         data-track-index="2" data-volume="0.2"></audio>
</div>

<style>
  #stage { position: relative; width: 1080px; height: 1920px; background: #000; overflow: hidden; }
  #bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  #title { position: absolute; top: 40%; width: 100%; text-align: center;
           color: #fff; font: 800 96px/1.1 sans-serif; }
</style>

<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script>
  const tl = gsap.timeline({ paused: true });
  tl.from("#title", { y: 80, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.5);
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;   // таймлайн регистрируется по id композиции
</script>
```

## Основные атрибуты

- `data-start` — когда элемент появляется (сек).
- `data-duration` — сколько длится (сек).
- `data-track-index` — слой/дорожка (порядок наложения).
- `data-volume` — громкость аудио.
- `data-composition-id`, `data-width`, `data-height` — параметры композиции.

## Советы

- Анимации делай только через GSAP-таймлайн (`paused: true`) — рендерер сам проматывает время кадр за кадром. Не используй `setInterval`/`requestAnimationFrame` для анимации.
- Все медиа клади локально в `assets/`.
- Пословные таймкоды из Whisper (JSON) можно превратить в GSAP-анимацию караоке-субтитров.
- Сначала проверь в `preview`, затем рендери.
