# Remotion в проекте

Проект Remotion уже в корне репозитория (`package.json`, `remotion.config.ts`, `src/Root.tsx`, `src/HelloWorld.tsx`, `src/Subtitles.tsx`). Версии `remotion`, `@remotion/cli`, `media`, `transitions`, `captions`, `layout-utils` — **строго одинаковые** (4.0.545), `npx remotion upgrade` обновляет все разом. Не смешивать версии.

## Когда Remotion, когда Python+ffmpeg
- **Python+ffmpeg+Pillow** (основной пайплайн рилса): резка, склейка, покадровая графика, субтитры, цифры, музыка. Быстрее и детерминированнее для нашего формата (`scripts/reel_new.py`).
- **Remotion** — анимированная графика на React с таймлайном (титры, графики, шаблонные сцены), когда удобнее описывать движение кодом. Рендерить в клип и класть как вставку/слой.

## Запуск в облаке
```
npm run dev                        # Remotion Studio (только если нужно смотреть)
npx remotion render <CompId> out/x.mp4 \
  --browser-executable=/opt/pw-browsers/chromium --chrome-mode=chrome-for-testing
npx remotion still <CompId> --frame=N out.png   # кадр для проверки (кадры с нуля)
```
`npm run build` напрямую в облаке падает (хост `remotion.media` закрыт, браузер не скачивается). Playwright уже есть, второй раз не ставить.

## Правила Remotion (из официального скилла remotion-best-practices)
- Вся анимация считается от кадра: `useCurrentFrame()`, `interpolate()`, `spring()` только если нужна физика; `useVideoConfig()` для fps/размера. `extrapolateLeft/Right: 'clamp'`.
- **Запрещено:** CSS-переходы, `@keyframes`, анимации Tailwind, `setTimeout`/`requestAnimationFrame` (рендер недетерминирован).
- Тайминг: `<Sequence from durationInFrames>` (внутри кадр с нуля), `layout="none"` для вставок, `<Series>` и `@remotion/transitions`. Длительности считать как секунды × fps.
- Для изменяемых в Studio значений: `interpolate()` в `style`, отдельные `scale`/`translate`/`rotate`, а не строка `transform`.
- Ассеты в `public/`, путь через `staticFile()`; изображения `<Img>`, видео/аудио `<Video>`/`<Audio>` из `@remotion/media`. Шрифты через `@remotion/google-fonts`/`@remotion/fonts` (в облаке Google недоступен, берём локальные `assets/fonts`). Субтитры: `@remotion/captions`.
- Параметризуемые видео: Zod-схема, `calculateMetadata` для длительности от данных. Прозрачное видео: ProRes 4444 или WebM VP8/VP9 с альфой.
- Рендер отличается от превью → искать недетерминизм (`Math.random` без `random(seed)`, `Date.now`, CSS-анимации, незагруженные шрифты).
- Перед новым видео проверить, нет ли уже проекта Remotion (есть, см. выше). Не создавать заново `create-video`.
