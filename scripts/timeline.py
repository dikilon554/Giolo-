"""Общая шкала времени рилса: паузы 0.12 с, новые номера кадров и слова, подогнанные к реальным границам фраз."""
import json, os
FPS = 25
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIL = [(0, 0.318), (3.858, 4.519), (6.223, 6.452), (8.747, 9.413), (12.513, 13.143),
       (14.598, 14.869), (16.754, 17.091), (17.841, 18.215), (19.358, 19.697),
       (21.082, 21.634), (22.56, 22.927), (23.734, 24.116), (25.218, 25.778),
       (27.536, 27.893), (30.498, 31.067), (34.613, 34.855), (36.829, 37.207)]
KEEP, TOTAL = 0.12, 37.207
fr = lambda t: int(round(t * FPS))
cuts = [(0.0, 0.28)]
for a, b in SIL[1:-1]:
    if (b - a) - KEEP >= 0.04:
        cuts.append((a + KEEP / 2, b - KEEP / 2))
cuts.append((36.98, TOTAL))
cuts_f = [(fr(a), fr(b)) for a, b in cuts]
total_f = int(TOTAL * FPS)
cuts_f[-1] = (cuts_f[-1][0], total_f)
kept, _pos = [], 0
for a, b in cuts_f:
    if a > _pos: kept.append((_pos, a))
    _pos = b
if _pos < total_f: kept.append((_pos, total_f))
NEW_TOTAL = sum(b - a for a, b in kept)


def new_f(t):
    of, removed = fr(t), 0
    for a, b in cuts_f:
        if of >= b: removed += b - a
        elif of > a: removed += of - a
    return of - removed


def load_groups():
    words = json.load(open(f"{ROOT}/монтаж_слова/ЭТО_ВИДЕО_НА_МОНТАЖ.words.json", encoding="utf-8"))["words"]
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"][-1] in ".?!": groups.append(cur); cur = []
    if cur: groups.append(cur)
    assert len(groups) == 18
    chunks = [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14, 15], [16], [17]]
    speech = [(SIL[i][1], SIL[i + 1][0]) for i in range(len(SIL) - 1)]
    for ch, (ta, tb) in zip(chunks, speech):
        ws = [w for g in ch for w in groups[g]]
        w0, w1 = ws[0]["start"], ws[-1]["end"]
        for w in ws:
            w["s"] = ta + (w["start"] - w0) * (tb - ta) / (w1 - w0)
            w["e"] = ta + (w["end"] - w0) * (tb - ta) / (w1 - w0)
            w["f0"], w["f1"] = new_f(w["s"]), new_f(w["e"])
    return groups
