# Окружение (контейнер каждый раз новый)

Репозиторий: `dikilon554/Giolo-`, ветка разработки `claude/skill-removal-setup-vgqppv`. Пушить туда, PR не создавать без просьбы.
Проверь, что уже стоит, прежде чем ставить. **Ставить новое — только с «ок» пользователя.**

## Что должно быть
| Что | Где / как |
|---|---|
| FFmpeg 6.1 (есть `zscale`, `libplacebo`, `loudnorm`, `lut3d`, `sidechaincompress`) | системный |
| Chromium (для Remotion и скриншотов) | `/opt/pw-browsers/chromium` |
| Python-окружение | `/home/user/gigaam-venv` (см. ниже) |
| Распознавание по словам | `scripts/words.py`, модель `/home/user/whisper-model` (faster-whisper large-v3-turbo, CPU int8) |
| Распознавание по фразам | `scripts/transcribe.py`, GigaAM-v3 e2e_rnnt в `/home/user/gigaam-model` |
| Детектор лица | `assets/models/face_detection_yunet_2023mar.onnx` (cv2.FaceDetectorYN) |
| Карта глубины | Depth Anything V2 Small, кэш `HF_HOME=/home/user/hf-cache` |
| Шрифты | `assets/fonts/` + копия в `~/.fonts` (Manrope ExtraBold/SemiBold, Unbounded ExtraBold/Black, Lora Italic, **Montserrat ExtraBold** — шрифт субтитров), Liberation Sans Bold (системный, плашки как на динозаврах), Noto Color Emoji (системный) |
| Remotion 4.0.545 | `npm i` в корне (`remotion`, `@remotion/cli`, `media`, `transitions`, `captions`, `layout-utils`, react 19) |

## Venv `/home/user/gigaam-venv`
`python3 -m venv`, затем:
- `pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch==2.8.0 torchaudio==2.8.0`
- `pip install transformers==4.57.1 hydra-core omegaconf sentencepiece soundfile`
- `pip install -c constraints.txt pyannote-audio==4.0.0` (нужен только загрузчику GigaAM; constraints фиксируют torch/transformers)
- `pip install faster-whisper opencv-python-headless pillow fonttools gdown`
- Всегда запускай `python -I` для чтения чужих файлов; скрипты запускай как `/home/user/gigaam-venv/bin/python scripts/…`.

## Модели
- **GigaAM-v3:** `HF_HUB_DISABLE_XET=1`, `snapshot_download('ai-sage/GigaAM-v3', revision='e2e_rnnt', local_dir='/home/user/gigaam-model')`. Файл `modeling_gigaam.py` один раз прочитан и проверен (только ffmpeg-вызов), перед запуском сверяй sha256 с проверенной копией, грузи с `trust_remote_code=True` **из локальной папки**, не из сети.
- **Whisper:** `snapshot_download('deepdml/faster-whisper-large-v3-turbo-ct2', local_dir='/home/user/whisper-model')`. Аудио в модель подавай массивом numpy (свой ffmpeg-декод), `av` не использовать (несовместим). `language='ru'` для нашего аудио, `'en'` для конкурента.

## Сеть (окружение `giolo-drive`, список разрешённых хостов)
`drive.google.com`, `drive.usercontent.google.com`, `docs.google.com`, `doc-*-6k-docs.googleusercontent.com`, `lh3.googleusercontent.com`, `huggingface.co`, `cdn-lfs.huggingface.co`, `cdn-lfs-us-1.huggingface.co`, `cas-bridge.xethub.hf.co`, `cas-server.xethub.hf.co`, `us.aws.cdn.hf.co`, `download.pytorch.org`, `download-r2.pytorch.org`, `cdn.chatwm.opensmodel.sberdevices.ru`.
- Новый хост добавляется через `update_environment` (окно подтверждения у пользователя). **Мобильное приложение Claude не показывает это окно** → попроси открыть сессию на claude.ai в браузере (https://claude.ai/code/session_…, при необходимости «версия для ПК»).
- Закрыты: YouTube, TikTok, Instagram, SoundCloud, Spotify, VK, pixabay, remotion.media (из-за этого Remotion не качает свой браузер, см. `remotion.md`). Скачивание треков по ссылке возможно только после добавления хоста и не гарантировано. Надёжный путь: пользователь присылает файл в чат.
- **Google Drive:** читать можно через `gdown.download_folder(url=…, skip_download=True, use_cookies=False)` и `gdown.download(id=…)`. **Писать в Drive нельзя**: коннектор «Google Drive» подключён, но выключен в чате; включить нужно на https://claude.ai/customize/connectors (разрешить инструменты). Пока так — отдавай файлы в чат.
- Скачивание на HF: `HF_HUB_DISABLE_XET=1` (иначе нужен ещё хост xet).

## Быстрая проверка
```
ffmpeg -hide_banner -filters | grep -E "zscale|libplacebo|loudnorm|sidechaincompress"
/home/user/gigaam-venv/bin/python -c "import torch,cv2,faster_whisper,PIL;print('ok')"
ls /home/user/whisper-model /home/user/gigaam-model assets/fonts assets/models
```
Если чего-то нет — скажи пользователю, что именно ставишь и зачем, и жди «ок».
