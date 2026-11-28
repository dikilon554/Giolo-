#!/usr/bin/env python3
"""Отправка черновика поста в Telegram через бота (только стандартная библиотека).

Токен берётся из переменной окружения TELEGRAM_BOT_TOKEN (задаётся в настройках
облачного окружения, в репозиторий НЕ кладётся).
ID чата, куда слать черновики, хранится в scripts/tg_config.json.

Использование:
  python3 scripts/tg_send.py --check            # проверить токен (getMe)
  python3 scripts/tg_send.py --find-chat        # найти чат после того, как нажали Start у бота
  python3 scripts/tg_send.py --find-chat group  # найти группу (бота добавили, в группе написали /start@<бот>)
  python3 scripts/tg_send.py post.html          # отправить пост (HTML-разметка Telegram)
  python3 scripts/tg_send.py post.html --poll poll.txt   # + опрос: 1-я строка вопрос, дальше варианты
  python3 scripts/tg_send.py post.html --photo cover.jpg # обложка + текст (короткий ≤1024 — подписью к картинке, иначе следом)

Разметка поста (parse_mode=HTML): <b>жирный</b>, <i>курсив</i>, <a href="URL">слово-ссылка</a>.
Переносы строк сохраняются как есть.
"""
import json
import mimetypes
import uuid
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).with_name("tg_config.json")


def api(method, **params):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Нет TELEGRAM_BOT_TOKEN: добавь его в Environment variables окружения и открой новую сессию.")
    data = urllib.parse.urlencode(
        {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in params.items()}
    ).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        res = json.load(e)
    if not res.get("ok"):
        sys.exit(f"Telegram ответил ошибкой: {res.get('description')}")
    return res["result"]


def send_photo(path, caption=None):
    """Отправка картинки (multipart/form-data, без сторонних библиотек)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Нет TELEGRAM_BOT_TOKEN: добавь его в Environment variables окружения и открой новую сессию.")
    b = uuid.uuid4().hex
    p = Path(path)
    extra = ''
    if caption:
        extra = (f'--{b}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                 f'--{b}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n')
    body = (f'--{b}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id()}\r\n{extra}'
            f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="cover{p.suffix}"\r\n'
            f'Content-Type: {mimetypes.guess_type(p.name)[0] or "image/jpeg"}\r\n\r\n').encode() \
        + p.read_bytes() + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        res = json.load(e)
    if not res.get("ok"):
        sys.exit(f"Telegram ответил ошибкой: {res.get('description')}")


def chat_id():
    if CONFIG.exists():
        cid = json.loads(CONFIG.read_text()).get("chat_id")
        if cid:
            return cid
    sys.exit("Чат не найден: нажми Start у бота и запусти --find-chat.")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if argv[0] == "--check":
        me = api("getMe")
        print(f"Токен рабочий, бот @{me['username']}")
        return
    if argv[0] == "--find-chat":
        want = ("group", "supergroup") if "group" in argv[1:] else ("private",)
        chats = {}
        for u in api("getUpdates"):
            m = u.get("message") or u.get("my_chat_member") or {}
            c = m.get("chat")
            if c and c.get("type") in want:
                chats[c["id"]] = c.get("title") or (c.get("first_name", "") + " @" + str(c.get("username", "")))
        if not chats:
            sys.exit("Чат не найден. Личный: открой бота и нажми Start. Группа: добавь бота в группу и напиши там /start@<бот>. Потом повтори.")
        if len(chats) > 1:
            print("Нашёл несколько чатов, сохраняю последний:", chats)
        cid, who = list(chats.items())[-1]
        CONFIG.write_text(json.dumps({"chat_id": cid}, ensure_ascii=False, indent=2) + "\n")
        print(f"Сохранил чат {who} в {CONFIG.name}")
        return
    text = Path(argv[0]).read_text(encoding="utf-8").strip()
    import re
    short = len(re.sub(r"<[^>]+>", "", text)) <= 1024  # лимит подписи к картинке в Telegram
    if "--photo" in argv and short:
        send_photo(argv[argv.index("--photo") + 1], caption=text)
    else:
        if "--photo" in argv:
            send_photo(argv[argv.index("--photo") + 1])
        api("sendMessage", chat_id=chat_id(), text=text, parse_mode="HTML",
            link_preview_options={"is_disabled": True})
    if "--poll" in argv:
        lines = [l.strip() for l in Path(argv[argv.index("--poll") + 1]).read_text(encoding="utf-8").splitlines() if l.strip()]
        api("sendPoll", chat_id=chat_id(), question=lines[0],
            options=[{"text": o} for o in lines[1:]], is_anonymous=True)
    print("Отправил в Telegram")


if __name__ == "__main__":
    main(sys.argv[1:])
