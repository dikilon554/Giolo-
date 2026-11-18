import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

type Word = {text: string; start: number; end: number}; // секунды
type Page = {start: number; end: number; words: Word[]};

// Тайминги в секундах. Заменяйте на свои (или на результат транскрибации).
const line = (start: number, text: string, perWord = 0.42): Page => {
  const words = text.split(' ').map((t, i) => ({
    text: t,
    start: start + i * perWord,
    end: start + (i + 1) * perWord,
  }));
  return {start, end: words[words.length - 1].end + 0.35, words};
};

export const PAGES: Page[] = [
  line(0.3, 'Привет! Это новые субтитры'),
  line(2.9, 'Слова подсвечиваются по мере речи'),
  line(5.6, 'Плавно, ярко и читаемо'),
  line(7.9, 'Вот так лучше!', 0.5),
];

const ACCENT = '#ffd23f';
const FONT =
  '"Inter", "Segoe UI", "Helvetica Neue", Arial, "DejaVu Sans", sans-serif';

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const angle = interpolate(frame, [0, 300], [135, 215]);
  const glow = interpolate(frame, [0, 300], [20, 80]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${glow}% 30%, #3b2a8f 0%, transparent 55%), linear-gradient(${angle}deg, #0b1020, #1a1038 60%, #0b1020)`,
      }}
    />
  );
};

const CaptionPage: React.FC<{page: Page}> = ({page}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps + page.start; // абсолютное время, сек
  const dur = (page.end - page.start) * fps;

  const enter = spring({frame, fps, config: {damping: 16, stiffness: 140}});
  const exit = interpolate(frame, [dur - 8, dur], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });

  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center'}}>
      <div
        style={{
          marginBottom: 110,
          maxWidth: 1120,
          padding: '22px 38px',
          borderRadius: 28,
          background: 'rgba(8, 10, 24, 0.62)',
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: '0 18px 50px rgba(0,0,0,0.45)',
          opacity: enter * exit,
          translate: `0 ${interpolate(enter, [0, 1], [40, 0])}px`,
          scale: String(interpolate(enter, [0, 1], [0.92, 1])),
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '4px 30px',
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: 60,
          lineHeight: 1.2,
        }}
      >
        {page.words.map((w, i) => {
          const active = t >= w.start && t < w.end;
          const spoken = t >= w.end;
          const wf = Math.max(0, (t - w.start) * fps);
          const pop = active
            ? spring({frame: wf, fps, config: {damping: 10, stiffness: 220}})
            : 1;
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                color: active ? ACCENT : '#ffffff',
                opacity: active || spoken ? 1 : 0.5,
                scale: String(active ? interpolate(pop, [0, 1], [1, 1.07]) : 1),
                textShadow: active
                  ? `0 0 28px ${ACCENT}88, 0 3px 0 rgba(0,0,0,0.5)`
                  : '0 3px 0 rgba(0,0,0,0.5)',
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Subtitles: React.FC = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill>
      <Background />
      {PAGES.map((p, i) => (
        <Sequence
          key={i}
          from={Math.round(p.start * fps)}
          durationInFrames={Math.round((p.end - p.start) * fps)}
        >
          <CaptionPage page={p} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
