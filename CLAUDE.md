# Giolo — монтаж рилсов

Скиллы монтажа лежат в `.claude/skills/` (`/две-крупности`, `/крупные-слова`, `/один-план`, `/экран-сверху`).
Работаем по пути Б: ffmpeg + whisper + Python/Pillow (DaVinci в облаке недоступен).

## Инструменты (лежат в контейнере, не в репозитории)
- Python со всем нужным: `/home/user/gigaam-venv/bin/python` (torch CPU, faster-whisper, opencv, Pillow, numpy).
- Пословные таймкоды: `scripts/words.py` (faster-whisper large-v3-turbo, модель `/home/user/whisper-model`).
- Расшифровка по фразам GigaAM-v3: `scripts/transcribe.py` (модель `/home/user/gigaam-model`).
- Детектор лица YuNet: `assets/models/face_detection_yunet_2023mar.onnx` (`cv2.FaceDetectorYN`).
- Шрифты: `assets/fonts/` (Manrope ExtraBold/SemiBold, Unbounded ExtraBold/Black, Lora Italic), скопированы и в `~/.fonts`.
- Remotion (`npm run dev`) — для анимированной графики; в этой среде рендерить с
  `--browser-executable=/opt/pw-browsers/chromium --chrome-mode=chrome-for-testing`.
- Если контейнер новый: venv и модели нужно поставить заново (зависят от сетевых хостов окружения `giolo-drive`).

## Правила
- Исходники не трогать, результаты в `монтаж_<дата>/`. Правки пользователя — в `правила_монтажа.md`.
- Только программы этого компьютера; платные сервисы и сайты без разрешения не открывать.
