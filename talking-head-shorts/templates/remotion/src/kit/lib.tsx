// kit/lib.tsx  shared helpers for the graphics kit (no football, no brand content).
// Data: TL (src/timeline.json), M (its marks), TRACK (src/track.json, plus TL.tracks when present).
// Palette: YEL RED BLUE GREEN PINK INK; fonts ANTON, BARLOW (loaded by useFonts from public/fonts/), EMOJI.
// Math: c01 prog eOut eIn eInOut eBack lerp rnd pop; time: useSec (seconds since the enclosing Seq started).
// Layout: Seq(from,to,children) in seconds, Fill, Abs, glass/glass1 card styles, strokeText, money, faceAt(clip, srcT).
import React, { useState } from "react";
import { Sequence, continueRender, delayRender, staticFile, useCurrentFrame } from "remotion";
import timeline from "../timeline.json";
import track from "../track.json";

export const TL: any = timeline;
export const TRACK: Record<string, number[][]> = { ...((track as any) || {}), ...(((timeline as any).tracks) || {}) };
export const M: Record<string, number> = TL.marks || {};
export const FPS = 30;
export const W = 1080;
export const H = 1920;

// palette
export const YEL = "#FFD400", RED = "#FF2D2D", BLUE = "#2BA8FF", GREEN = "#1FD66B", PINK = "#FF4FA3", INK = "#0b0b0f";
export const ANTON = "Anton, Impact, sans-serif";
export const BARLOW = "Barlow Condensed, Arial Narrow, sans-serif";
export const EMOJI = "Apple Color Emoji, Noto Color Emoji, sans-serif";

// ---- fonts: block rendering until the files are in document.fonts --------------------------------------------------
const loaded = new Set<string>();
const pending = new Set<string>();
export const useFonts = () => {
  const [, bump] = useState(0);
  const want: [string, string, string][] = [["Anton", "Anton-Regular.ttf", "400"], ["Barlow Condensed", "BarlowCondensed-ExtraBold.ttf", "800"], ["Barlow Condensed", "BarlowCondensed-SemiBold.ttf", "600"]];
  for (const [fam, file, weight] of want) {
    const key = fam + weight;
    if (loaded.has(key) || pending.has(key)) continue;
    pending.add(key);
    const h = delayRender("font " + key);
    new FontFace(fam, `url(${staticFile("fonts/" + file)})`, { weight }).load().then((f) => { document.fonts.add(f); loaded.add(key); bump((n) => n + 1); requestAnimationFrame(() => continueRender(h)); }).catch(() => continueRender(h));
  }
};

// ---- math ---------------------------------------------------------------------------------------------------------
export const c01 = (x: number) => Math.max(0, Math.min(1, x));
export const prog = (t: number, a: number, b: number) => c01((t - a) / (b - a));
export const eOut = (x: number) => 1 - Math.pow(1 - c01(x), 3);
export const eIn = (x: number) => Math.pow(c01(x), 2.2);
export const eInOut = (x: number) => { x = c01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
export const eBack = (x: number, s = 1.9) => { x = c01(x); const c = s + 1; return 1 + c * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); };
export const lerp = (a: number, b: number, x: number) => a + (b - a) * x;
export const rnd = (i: number, k = 0) => { const s = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return s - Math.floor(s); };
// pop-in scale with overshoot starting at `a`
export const pop = (t: number, a: number, d = 0.28) => (t < a ? 0 : eBack((t - a) / d));

// seconds since the enclosing Sequence started
export const useSec = () => useCurrentFrame() / FPS;
// Sequence in seconds (layout none: children are absolutely placed)
export const Seq: React.FC<{ from: number; to: number; children: React.ReactNode }> = ({ from, to, children }) => (
  <Sequence from={Math.round(from * FPS)} durationInFrames={Math.max(1, Math.round((to - from) * FPS))} layout="none">{children}</Sequence>
);
export const Fill: React.FC<{ style?: React.CSSProperties; children?: React.ReactNode }> = ({ style, children }) => (
  <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, ...style }}>{children}</div>
);
export const Abs: React.FC<{ style: React.CSSProperties; children?: React.ReactNode }> = ({ style, children }) => (
  <div style={{ position: "absolute", ...style }}>{children}</div>
);
const glassBase = (a: number, b: number): React.CSSProperties => ({
  background: `linear-gradient(180deg, rgba(20,20,28,${a}), rgba(8,8,12,${b}))`,
  border: "2px solid rgba(255,255,255,.14)",
  boxShadow: "0 18px 50px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.12)",
  borderRadius: 28,
});
export const glass: React.CSSProperties = glassBase(0.9, 0.94);
export const glass1: React.CSSProperties = glassBase(0.88, 0.92);
export const strokeText = (px = 10, color = "#000"): React.CSSProperties => ({ WebkitTextStroke: `${px}px ${color}`, paintOrder: "stroke fill" as any });
export const money = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
export const faceAt = (clip: string, srcT: number) => { const tr = TRACK[clip]; if (!tr || !tr.length) return [540, 1000, 330]; const i = Math.max(0, Math.min(tr.length - 1, Math.round(srcT * FPS))); return tr[i]; };
// optional image from public/ (the user's logo, photo ...); returns undefined when the prop is not given
export const pub = (f?: string) => (f ? staticFile(f) : undefined);
