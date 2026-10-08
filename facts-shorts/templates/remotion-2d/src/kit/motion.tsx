import React from "react";
import { Easing, interpolate } from "remotion";
import { ramp, pulse } from "./anim";
import { Layer, W, H, EDGE, PIC_TOP, picBottom, GOLD, RED, fitSize, textWidth, vis, clamp } from "./props";
import { STROKE } from "./overlays";

// Motion-graphics layer for the 2D kit (added in 0.4.0): camera moves, kinetic type, drawn
// diagrams, a dot-grid for "x out of 100", transitions and a living background. Everything
// takes the time `t` and word times, like the rest of the kit; none of it changes how an old
// scene renders, you opt in per beat.

// ---- Camera --------------------------------------------------------------------------------

export type CamKey = { at: number; s?: number; x?: number; y?: number };
// Moves the whole beat like a camera: eased scale/translate between keyframes (`at` in seconds,
// `s` zoom, `x`/`y` px of pan), held before the first and after the last. Wrap a Card, a diagram
// or a whole beat. `punch` adds a fast +0.10 push on each listed time (a word that lands hard).
export const Cam = ({ t, keys, punch = [], origin = "50% 50%", children }: {
  t: number; keys: CamKey[]; punch?: number[]; origin?: string; children: React.ReactNode;
}) => {
  const ks = [...keys].sort((p, q) => p.at - q.at);
  const f = (k: "s" | "x" | "y", d: number) =>
    interpolate(t, ks.map((v) => v.at), ks.map((v) => v[k] ?? d), { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const p = punch.reduce((m, a) => Math.max(m, 0.1 * pulse(t, a, 0.08, 0.1, 0.45)), 0);
  return (
    <Layer transform={`translate(${f("x", 0)}px, ${f("y", 0)}px) scale(${f("s", 1) + p})`}>
      <div style={{ position: "absolute", inset: 0, transformOrigin: origin }}>{children}</div>
    </Layer>
  );
};

// ---- Kinetic type ----------------------------------------------------------------------------

// A word (or a short phrase, "\n" = lines) as the whole picture: slams in huge at `a` with a
// shake, stays until `b`. `strikeAt` draws a red line through it (a myth being crossed out) and
// dims it; `tilt` rotates it. Shrinks to fit the width (keeps EDGE px inside), never wraps by itself.
export const Kinetic = ({ t, a, b, text, color = "#fff", size: size0 = 330, top, tilt = -4, strikeAt, stagger = 0.12, sub, subColor = GOLD }: {
  t: number; a: number; b: number; text: string; color?: string; size?: number; top?: number; tilt?: number;
  strikeAt?: number; stagger?: number; sub?: string; subColor?: string;
}) => {
  if (!vis(t, a, b + 0.3)) return null;
  const size = fitSize(text, "Anton", size0, W - 2 * EDGE - 60, 4);
  const lines = text.split("\n");
  const bh = lines.length * size * 1.02;
  const y = top ?? PIC_TOP + (picBottom() - PIC_TOP - bh) / 2;
  const out = ramp(t, b, b + 0.3);
  const strike = strikeAt === undefined ? 0 : ramp(t, strikeAt, strikeAt + 0.22, 0, 1, Easing.out(Easing.quad));
  const dim = 1 - 0.55 * strike;
  return (
    <Layer opacity={1 - out} transform={`translateY(${-out * 80}px)`}>
      <div style={{ position: "absolute", left: 0, right: 0, top: y, textAlign: "center", transform: `rotate(${tilt}deg)` }}>
        {lines.map((l, i) => {
          const s0 = a + i * stagger;
          const k = interpolate(t - s0, [0, 0.14, 0.3], [3.2, 0.92, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
          const sh = t > s0 && t < s0 + 0.3 ? 12 * Math.sin((t - s0) * 80) * (1 - (t - s0) / 0.3) : 0;
          const w = textWidth(l, "Anton", size, 4);
          return (
            <div key={i} style={{ position: "relative", display: "block", fontFamily: "Anton", fontSize: size, lineHeight: 1.02, letterSpacing: 4,
              color, opacity: (t < s0 ? 0 : 1) * dim, transform: `translateX(${sh}px) scale(${k})`, ...STROKE(Math.round(size / 28)) }}>
              {l}
              {strike > 0 && (
                <div style={{ position: "absolute", left: `calc(50% - ${w / 2 + 20}px)`, width: (w + 40) * strike, top: "52%", height: Math.max(18, size / 12),
                  background: RED, borderRadius: 10, boxShadow: "0 0 0 5px #fff", transform: "rotate(-3deg)", transformOrigin: "0 50%", opacity: 1 / dim }} />
              )}
            </div>
          );
        })}
        {sub && (
          <div style={{ fontFamily: "Barlow", fontSize: 64, letterSpacing: 6, color: subColor, marginTop: 10, opacity: ramp(t, a + 0.3, a + 0.55), ...STROKE(7) }}>{sub}</div>
        )}
      </div>
    </Layer>
  );
};

// ---- Drawn diagrams ---------------------------------------------------------------------------

// An SVG path that draws itself from `a` to `b`, with a glowing head and an optional dot where it ends.
export const Draw = ({ t, a, b, d, color = GOLD, width = 22, head = true, glow = true, fadeAt }: {
  t: number; a: number; b: number; d: string; color?: string; width?: number; head?: boolean; glow?: boolean; fadeAt?: number;
}) => {
  if (t < a) return null;
  const p = ramp(t, a, b, 0, 1, Easing.out(Easing.cubic));
  const op = fadeAt === undefined ? 1 : 1 - ramp(t, fadeAt, fadeAt + 0.3);
  if (op <= 0) return null;
  return (
    <svg width={W} height={H} style={{ position: "absolute", inset: 0, opacity: op, overflow: "visible" }}>
      <path d={d} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round"
        style={glow ? { filter: `drop-shadow(0 0 ${width}px ${color})` } : undefined} />
      {head && p > 0 && p < 1 && (
        <HeadDot d={d} p={p} color="#fff" r={width * 0.75} />
      )}
    </svg>
  );
};
// position of the point at fraction p along a path (measured in the browser)
const HeadDot = ({ d, p, color, r }: { d: string; p: number; color: string; r: number }) => {
  if (typeof document === "undefined") return null;
  const el = document.createElementNS("http://www.w3.org/2000/svg", "path");
  el.setAttribute("d", d);
  const pt = el.getPointAtLength(el.getTotalLength() * p);
  return <circle cx={pt.x} cy={pt.y} r={r} fill={color} style={{ filter: `drop-shadow(0 0 ${r}px ${GOLD})` }} />;
};

// "x out of 100": a 10x10 grid of people-dots that fill from `from` to `to` across a phrase
// (word time a -> b), each new dot popping. The filled dots are gold, the rest dim.
export const Dots = ({ t, a, b, from = 0, to, show = a, until = Infinity, top = PIC_TOP + 60, color = GOLD, n = 100, cols = 10, size = 76, gap = 22, char }: {
  t: number; a: number; b: number; from?: number; to: number; show?: number; until?: number; top?: number; color?: string;
  n?: number; cols?: number; size?: number; gap?: number; char?: string;
}) => {
  if (!vis(t, show, until + 0.3)) return null;
  const rows = Math.ceil(n / cols);
  const v = interpolate(t, [a, b], [from, to], clamp);
  const gw = cols * size + (cols - 1) * gap;
  return (
    <Layer opacity={ramp(t, show, show + 0.25) * (1 - ramp(t, until, until + 0.3))}>
      <div style={{ position: "absolute", left: 540 - gw / 2, top, width: gw }}>
        {Array.from({ length: n }, (_, i) => {
          const on = v > i;
          const born = on ? ramp(v, i, i + 1, 0, 1) : 0;
          const sc = on ? 1 + 0.35 * Math.sin(Math.PI * Math.min(1, born * 1)) * (1 - Math.min(1, (v - i) / 2)) : 1;
          return (
            <div key={i} style={{ position: "absolute", left: (i % cols) * (size + gap), top: Math.floor(i / cols) * (size + gap), width: size, height: size,
              borderRadius: "50%", background: on ? color : "rgba(255,255,255,0.14)", transform: `scale(${sc})`,
              boxShadow: on ? `0 0 24px ${color}` : "none", fontSize: size * 0.8, lineHeight: `${size}px`, textAlign: "center" }}>{on && char ? char : ""}</div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: top + rows * (size + gap) + 20, textAlign: "center", fontFamily: "Anton", fontSize: 150, color, ...STROKE(9) }}>
        {Math.round(v)}<span style={{ fontSize: 80, color: "#fff" }}> / {n}</span>
      </div>
    </Layer>
  );
};

// Myth vs truth: the top half is the myth, the bottom half the truth; a divider wipes in from the
// left at `a`. Children go in `myth` / `truth` (any props); labels are drawn for you.
export const Versus = ({ t, a, b, myth, truth, mythLabel = "MYTH", truthLabel = "SACH" }: {
  t: number; a: number; b: number; myth: React.ReactNode; truth: React.ReactNode; mythLabel?: string; truthLabel?: string;
}) => {
  if (!vis(t, a, b + 0.3)) return null;
  const k = ramp(t, a, a + 0.5, 0, 1, Easing.out(Easing.cubic));
  const mid = (PIC_TOP + picBottom()) / 2;
  const tag = (txt: string, y: number, bg: string) => (
    <div style={{ position: "absolute", left: EDGE, top: y, background: bg, color: "#fff", fontFamily: "Anton", fontSize: 70, padding: "2px 28px", borderRadius: 12,
      border: "6px solid #fff", transform: `scale(${k})` }}>{txt}</div>
  );
  return (
    <Layer opacity={1 - ramp(t, b, b + 0.3)}>
      <div style={{ position: "absolute", left: 0, right: 0, top: PIC_TOP, height: mid - PIC_TOP }}>{myth}</div>
      {tag(mythLabel, PIC_TOP, RED)}
      <div style={{ position: "absolute", left: EDGE, top: mid - 6, height: 12, width: (W - 2 * EDGE) * k, background: GOLD, borderRadius: 6 }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: mid, height: picBottom() - mid, opacity: k }}>{truth}</div>
      {tag(truthLabel, mid + 20, "#1ba94c")}
    </Layer>
  );
};

// ---- Transitions and flashes ----------------------------------------------------------------

// A slanted gold panel that sweeps across the screen in 0.4 s starting at `at`, covering the cut
// in the middle of the sweep. Put the next beat's start at `at + 0.2`. Pair with a whoosh.
export const Swipe = ({ t, at, color = GOLD, dir = 1 }: { t: number; at: number; color?: string; dir?: 1 | -1 }) => {
  if (t < at || t > at + 0.45) return null;
  const p = (t - at) / 0.45;
  const x = interpolate(p, [0, 1], [-1.4 * W, 1.4 * W]) * dir;
  return (
    <div style={{ position: "absolute", top: -50, bottom: -50, left: 0, width: W * 1.1, background: `linear-gradient(90deg, ${color}, #fff 60%, ${color})`,
      transform: `translateX(${x}px) skewX(-14deg)`, opacity: 0.96, boxShadow: `0 0 120px ${color}` }} />
  );
};

// Full-screen flash (an impact, a spark): rises at `at`, fades over `dur`.
export const Flash = ({ t, at, color = "#fff", peak = 0.8, dur = 0.35 }: { t: number; at: number; color?: string; peak?: number; dur?: number }) =>
  t < at || t > at + dur ? null : <div style={{ position: "absolute", inset: 0, background: color, opacity: peak * (1 - (t - at) / dur) }} />;

// ---- Living background --------------------------------------------------------------------

// Drifting colour glows, rising dust and a vignette over the Scene's own BACKGROUND. Cheap
// (a few gradients, 28 dots), deterministic, rendered by Short.tsx for every Short. `glow` is
// the accent colour (default the channel gold); `beats` (seconds) kick the glow brighter, so the
// room reacts when the story turns.
const rnd = (i: number, k: number) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
export const LiveBg = ({ t, glow = "#ffb300", beats = [] }: { t: number; glow?: string; beats?: number[] }) => {
  const kick = beats.reduce((m, a) => Math.max(m, pulse(t, a, 0.1, 0.1, 0.9)), 0);
  const blob = (i: number, color: string, size: number) => {
    const x = 540 + 420 * Math.sin(t * 0.22 + i * 2.1), y = 960 + 700 * Math.sin(t * 0.17 + i * 1.3 + 1);
    return <div key={i} style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: "50%",
      background: `radial-gradient(circle, ${color} 0%, transparent 68%)`, opacity: 0.16 + 0.22 * kick }} />;
  };
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      {blob(0, glow, 1100)}{blob(1, "#35d0ff", 900)}{blob(2, "#ff4d8d", 800)}
      {Array.from({ length: 28 }, (_, i) => {
        const sp = 18 + 40 * rnd(i, 1), x0 = W * rnd(i, 2), r = 3 + 6 * rnd(i, 3);
        const y = ((H + 100) - ((t * sp + H * rnd(i, 4)) % (H + 200)));
        return <div key={i} style={{ position: "absolute", left: x0 + 30 * Math.sin(t * 0.6 + i), top: y, width: r, height: r, borderRadius: "50%",
          background: "#fff", opacity: 0.1 + 0.18 * rnd(i, 5) }} />;
      })}
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,0.5) 100%)" }} />
    </div>
  );
};
