#!/usr/bin/env python3
"""Анализ пака треков: BPM, длина, громкость, динамика, яркость, бас, плотность ударов, нарастание, «бит или эмбиент».
Запуск: python scripts/music_analyze.py <папка> <out.json>   (первые 100 с каждого трека, 4 процесса)"""
import sys, os, json, subprocess, tempfile, wave, re
import numpy as np
from multiprocessing import Pool

def analyze(path):
    name = os.path.basename(path); r = {"file": name}
    try:
        d = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path],capture_output=True,text=True).stdout.strip() or 0)
        r["dur"] = round(d, 1)
        tmp = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-t","100","-i",path,"-vn","-ac","1","-ar","22050",tmp],check=True)
        w = wave.open(tmp); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768; os.unlink(tmp)
        lu = subprocess.run(["ffmpeg","-nostdin","-t","100","-i",path,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lu); r["lufs"] = float(m[-1]) if m else None
        n, hop = 1024, 256; win = np.hanning(n); fr = np.fft.rfftfreq(n,1/sr); fps = sr/hop
        S = np.array([np.abs(np.fft.rfft(x[i:i+n]*win)) for i in range(0,len(x)-n,hop)])
        full = S.sum(1)+1e-9; bass = S[:,(fr>=40)&(fr<160)].sum(1); hi = S[:,(fr>=3000)&(fr<9000)].sum(1)
        mid = S[:,(fr>=300)&(fr<3400)].sum(1)
        r["bass%"] = round(bass.sum()/full.sum()*100,1); r["hi%"] = round(hi.sum()/full.sum()*100,1)
        r["centroid"] = int((S*fr).sum()/S.sum())
        on = lambda e: (lambda o: o-o.mean())(np.maximum(np.diff(np.log1p(e*40)),0))
        o = on(bass)+0.6*on(hi); o[o<0]=0
        # BPM по автокорреляции огибающей ударов, диапазон 70-180
        ac = np.correlate(o-o.mean(),o-o.mean(),'full')[len(o)-1:]
        cand = []
        for b in np.arange(70,180,0.5):
            lag = int(round(60/b*fps)); 
            if 2*lag < len(ac): cand.append((ac[lag]+0.5*ac[2*lag]+0.25*ac[min(4*lag,len(ac)-1)], b))
        cand.sort(reverse=True); bpm = cand[0][1]
        r["bpm"] = round(float(bpm),1); r["bpm2"] = [round(float(c[1]),1) for c in cand[1:3]]
        # «ритмичность»: доля энергии onset на сетке bpm
        T = 60/bpm*fps; best = max(o[(np.arange(ph,len(o)-1,T)).astype(int)].sum() for ph in np.arange(0,T,1.0))
        r["beat_strength"] = round(float(best/(o.sum()+1e-9)*T),2)
        # динамика/нарастание по 5-секундным окнам
        k = int(fps*5); E = np.array([full[i:i+k].mean() for i in range(0,len(full)-k,k)]); E = E/E.max()
        r["energy_start"] = round(float(E[:max(1,len(E)//8)].mean()),2)
        r["energy_mid"] = round(float(E[len(E)//3:2*len(E)//3].mean()),2)
        r["energy_var"] = round(float(E.std()),2)
        r["first40_avg"] = round(float(E[:8].mean()),2) if len(E)>=8 else None
        r["first40_slope"] = round(float(np.polyfit(np.arange(min(8,len(E))),E[:8],1)[0]),3) if len(E)>=4 else None
        r["mid%"] = round(mid.sum()/full.sum()*100,1)
    except Exception as e:
        r["error"] = str(e)[:80]
    return r

if __name__ == "__main__":
    folder, out = sys.argv[1], sys.argv[2]
    files = sorted(os.path.join(folder,f) for f in os.listdir(folder) if f.lower().endswith((".mp3",".m4a",".wav",".mp4")))
    with Pool(4) as p: res = p.map(analyze, files)
    json.dump(res, open(out,"w"), ensure_ascii=False, indent=1); print(len(res),"треков ->",out, "ошибок:",sum('error' in r for r in res))
