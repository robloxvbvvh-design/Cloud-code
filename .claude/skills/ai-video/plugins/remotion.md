# Плагин: Remotion

Создание видео на React: каждый кадр — это React-компонент. Подходит для титров, моушн-графики, шаблонов и видео из данных.

Документация: https://www.remotion.dev/docs

## Установка и запуск

```bash
npx create-video@latest my-video   # выбрать шаблон (Hello World / Blank / TikTok и др.)
cd my-video
npm run dev                        # Remotion Studio — превью в браузере
```

## Рендер

```bash
npx remotion render <CompositionId> output/video.mp4
npx remotion render <CompositionId> output/video.mp4 --props='{"title":"Привет"}'
npx remotion still <CompositionId> output/frame.png --frame=30   # один кадр для проверки
npx remotion render <CompositionId> output/part.mp4 --frames=0-89 # только первые 3 сек при 30fps
```

## Регистрация композиции (`src/Root.tsx`)

```tsx
import { Composition } from "remotion";
import { MyVideo } from "./MyVideo";

export const RemotionRoot = () => (
  <Composition
    id="MyVideo"
    component={MyVideo}
    durationInFrames={300}   // 10 сек при 30 fps
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ title: "Заголовок" }}
  />
);
```

## Пример компонента

```tsx
import { AbsoluteFill, Sequence, OffthreadVideo, Audio, staticFile,
         useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export const MyVideo: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <OffthreadVideo src={staticFile("clip.mp4")} />
      <Audio src={staticFile("music.mp3")} volume={0.2} />
      <Sequence from={0} durationInFrames={90}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <h1 style={{ color: "white", fontSize: 90, opacity, transform: `scale(${scale})` }}>
            {title}
          </h1>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
```

## Ключевые API

- `useCurrentFrame()` — номер текущего кадра; вся анимация считается от него.
- `interpolate()` / `spring()` — плавные переходы и пружинные анимации.
- `<Sequence from durationInFrames>` — сцена в нужный момент времени.
- `<OffthreadVideo>`, `<Audio>`, `<Img>`, `staticFile()` — медиа из папки `public/`.
- `@remotion/captions` — работа с субтитрами (можно подать JSON из Whisper).

## Советы

- Не используй `setTimeout`, CSS-анимации и `Math.random()` — анимация должна зависеть только от `frame` (для случайностей есть `random(seed)` из `remotion`).
- Файлы клади в `public/` и подключай через `staticFile()`.
- Лицензия: бесплатно для частных лиц и небольших команд; компаниям может понадобиться платная лицензия — см. https://www.remotion.dev/license.
