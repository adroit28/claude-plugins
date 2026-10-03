import React from "react";
import { Audio, Easing, Img, interpolate, Sequence, staticFile } from "remotion";
import { FPS } from "../timing";
import { ramp, pop } from "./anim";
import { STROKE } from "./overlays";

// 2D props for explainer Shorts: archive photo cards with a name tag, speech bubbles, stamps,
// emoji props, a counter that runs across a phrase, hook ring arcs, sound effects and
// shake/sway wrappers. Every prop takes the time `t` and word times (from timing.ts), never frames.

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const back = Easing.out(Easing.back(1.6));
export const vis = (t: number, a: number, b: number) => t >= a && t < b;
export const PAPER = "#f3e7cf";
export const GOLD = "#ffc400";
export const RED = "#e01b22";

// horizontal shake that decays over `dur` (an impact on a word)
export const shake = (t: number, a: number, dur = 0.35, amp = 14) =>
  t < a || t > a + dur ? 0 : amp * Math.sin((t - a) * 90) * (1 - (t - a) / dur);

// A transform wrapper that covers the whole frame. Any wrapper with a transform must be
// absolute + inset 0, or its children land below the screen.
export const Layer = ({ children, transform, opacity = 1 }: { children: React.ReactNode; transform?: string; opacity?: number }) =>
  opacity <= 0 ? null : <div style={{ position: "absolute", inset: 0, transform, opacity }}>{children}</div>;
export const Shake = ({ t, at, children, amp = 14 }: { t: number; at: number; children: React.ReactNode; amp?: number }) =>
  <Layer transform={`translateX(${shake(t, at, 0.35, amp)}px)`}>{children}</Layer>;
export const Sway = ({ t, from, children, deg = 2, speed = 3 }: { t: number; from: number; children: React.ReactNode; deg?: number; speed?: number }) =>
  <Layer transform={`rotate(${deg * Math.sin((t - from) * speed)}deg)`}>{children}</Layer>;

// Photo in a paper frame. Slides in from a side (or zooms/slams in) at `a`, slow Ken Burns
// until `b`, then slides out. `pos` is the object-position (keep faces in frame). Children
// (a NameTag, a Bubble) are positioned relative to the card.
export const Card = ({ src, t, a, b, from = "right", w = 780, h = 900, top = 300, pos = "50% 20%", tilt = 0, slam, sepia = 0.25, fit = "cover", children }: {
  src: string; t: number; a: number; b: number; from?: "left" | "right" | "zoom"; w?: number; h?: number; top?: number;
  pos?: string; tilt?: number; slam?: boolean; sepia?: number; fit?: "cover" | "contain"; children?: React.ReactNode;
}) => {
  if (!vis(t, a - 0.01, b + 0.3)) return null;
  const k = ramp(t, a, a + 0.35, 0, 1, back);
  const out = ramp(t, b, b + 0.3);
  const dx = from === "zoom" ? 0 : (from === "left" ? -1 : 1) * 1200 * (1 - k);
  const s = from === "zoom" || slam ? interpolate(t - a, [0, 0.18, 0.32], [1.6, 0.96, 1], clamp) : 1;
  const kb = 1 + 0.06 * ramp(t, a, b, 0, 1, Easing.linear);
  return (
    <div style={{ position: "absolute", left: 540 - w / 2, top, width: w, height: h, opacity: 1 - out,
      transform: `translateX(${dx - out * 300}px) scale(${s}) rotate(${tilt}deg)` }}>
      <div style={{ width: "100%", height: "100%", overflow: "hidden", borderRadius: 18, border: `14px solid ${PAPER}`,
        boxShadow: "0 30px 70px rgba(0,0,0,.6)", background: PAPER }}>
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: fit, objectPosition: pos,
          transform: `scale(${kb})`, filter: `sepia(${sepia}) contrast(1.05)` }} />
      </div>
      {children}
    </div>
  );
};

// Small round photo (a face beside a diagram).
export const Avatar = ({ src, t, a, x, y, size = 300, pos = "50% 18%" }: { src: string; t: number; a: number; x: number; y: number; size?: number; pos?: string }) =>
  t < a ? null : (
    <div style={{ position: "absolute", left: x, top: y, width: size, height: size, borderRadius: "50%", overflow: "hidden",
      border: `12px solid ${PAPER}`, boxShadow: "0 20px 50px rgba(0,0,0,.6)", transform: `scale(${pop(t, a)})` }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos }} />
    </div>
  );

// Comic speech bubble, popping in at `a`; x/y is its centre. Text is what someone SAID or a
// single word; never put a paraphrase in a bubble as if it were a quote.
export const Bubble = ({ t, a, text, x, y, color = "#111", bg = "#fff", size = 120, tail = "left", rot = -4 }: {
  t: number; a: number; text: string; x: number; y: number; color?: string; bg?: string; size?: number; tail?: "left" | "right"; rot?: number;
}) => {
  if (t < a) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%,-50%) scale(${pop(t, a, 0.32, 0.3, 1.25)}) rotate(${rot}deg)` }}>
      <div style={{ position: "relative", background: bg, borderRadius: 60, padding: "18px 46px", border: "8px solid #111",
        boxShadow: "0 14px 30px rgba(0,0,0,.45)", fontFamily: "Anton", fontSize: size, lineHeight: 1.05, color, whiteSpace: "nowrap" }}>
        {text}
        <div style={{ position: "absolute", bottom: -40, [tail]: 70, width: 0, height: 0,
          borderLeft: "26px solid transparent", borderRight: "26px solid transparent", borderTop: "44px solid #111" }} />
      </div>
    </div>
  );
};

// Yellow name bar (and optional black subtitle) along the bottom of a Card: who is in the photo.
export const NameTag = ({ t, a, name, sub }: { t: number; a: number; name: string; sub?: string }) => (
  <div style={{ position: "absolute", left: 0, right: 0, bottom: 28, textAlign: "center",
    transform: `translateY(${interpolate(t - a, [0, 0.3], [80, 0], { ...clamp, easing: back })}px)`, opacity: ramp(t, a, a + 0.2) }}>
    <span style={{ background: GOLD, color: "#111", fontFamily: "Barlow", fontSize: 54, padding: "8px 26px", borderRadius: 10,
      letterSpacing: 2, boxShadow: "0 8px 20px rgba(0,0,0,.4)" }}>{name}</span>
    {sub && <div style={{ marginTop: 12 }}><span style={{ background: "#111", color: "#fff", fontFamily: "BarlowSemi", fontSize: 40,
      padding: "4px 18px", borderRadius: 8, letterSpacing: 3 }}>{sub}</span></div>}
  </div>
);

// Rubber stamp that slams down at `a` (pair with the "stamp" sfx).
export const Stamp = ({ t, a, text, top = 690, color = RED, size = 150, rot = -9 }: {
  t: number; a: number; text: string; top?: number; color?: string; size?: number; rot?: number;
}) =>
  t < a ? null : (
    <div style={{ position: "absolute", left: 0, right: 0, top, textAlign: "center",
      transform: `scale(${interpolate(t - a, [0, 0.12, 0.22], [2.4, 0.95, 1], clamp)}) rotate(${rot}deg)`, opacity: ramp(t, a, a + 0.06) }}>
      <span style={{ fontFamily: "Anton", fontSize: size, color, border: `14px solid ${color}`, borderRadius: 18,
        padding: "0 36px", background: "rgba(255,255,255,.85)", letterSpacing: 4 }}>{text}</span>
    </div>
  );

// Year or label badge, tilted, popping in (e.g. "1877").
export const Badge = ({ t, a, text, x = 90, y = 240, bg = "#c4161c", size = 130, rot = -8 }: {
  t: number; a: number; text: string; x?: number; y?: number; bg?: string; size?: number; rot?: number;
}) =>
  t < a ? null : (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${pop(t, a)}) rotate(${rot}deg)`,
      background: bg, color: "#fff", fontFamily: "Anton", fontSize: size, padding: "4px 34px", borderRadius: 16,
      border: "8px solid #fff", boxShadow: "0 14px 30px rgba(0,0,0,.5)" }}>{text}</div>
  );

// Emoji prop: pops in at `a`, optional wobble (a ringing bell) and grey-out + red slash (`crossAt`).
export const Emoji = ({ t, a, char, x, y, size = 290, rot = 0, wobble = false, crossAt }: {
  t: number; a: number; char: string; x: number; y: number; size?: number; rot?: number; wobble?: boolean; crossAt?: number;
}) => {
  if (t < a) return null;
  const slash = crossAt === undefined ? 0 : ramp(t, crossAt, crossAt + 0.2, 0, 1, Easing.out(Easing.quad));
  const wob = wobble && (crossAt === undefined || t < crossAt) ? 16 * Math.sin(t * 40) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: size * 1.15, height: size * 1.15 }}>
      <div style={{ fontSize: size, lineHeight: 1, textAlign: "center", filter: `grayscale(${slash})`,
        transform: `scale(${pop(t, a)}) rotate(${rot + wob}deg)` }}>{char}</div>
      {slash > 0 && (
        <div style={{ position: "absolute", left: -10, top: size * 0.55, width: size * 1.25 * slash, height: 34, background: RED,
          borderRadius: 17, transform: "rotate(-40deg)", transformOrigin: "0 50%", boxShadow: "0 0 0 6px #fff" }} />
      )}
    </div>
  );
};

// Number that counts from `from` to `to` across a whole phrase (word time a -> word time b),
// with an optional unit and a progress bar. Run it over a phrase, not two adjacent words, or it jumps.
export const CountUp = ({ t, a, b, from, to, unit, top = 860, bar = true, show = a, until = Infinity, decimals = 0 }: {
  t: number; a: number; b: number; from: number; to: number; unit?: string; top?: number; bar?: boolean; show?: number; until?: number; decimals?: number;
}) => {
  if (!vis(t, show, until)) return null;
  const v = interpolate(t, [a, b], [from, to], clamp);
  return (
    <>
      <div style={{ position: "absolute", left: 0, right: 0, top, textAlign: "center", transform: `scale(${pop(t, show)})` }}>
        <span style={{ fontFamily: "Anton", fontSize: 230, color: GOLD, ...STROKE(10) }}>{v.toFixed(decimals)}</span>
        {unit && <span style={{ fontFamily: "Anton", fontSize: 110, color: "#fff", marginLeft: 20, ...STROKE(8) }}>{unit}</span>}
      </div>
      {bar && <div style={{ position: "absolute", left: 160, top: top + 310, height: 22, borderRadius: 11, background: GOLD,
        width: 760 * interpolate(t, [a, b], [0.5, 1], clamp) }} />}
    </>
  );
};

// Expanding rings around a point (a ringing phone, a shout, a signal). `half` clips to the right half (sound going one way).
export const Rings = ({ t, x, y, r0 = 230, grow = 220, speed = 1.6, n = 2, color = GOLD, width = 10, half = false }: {
  t: number; x: number; y: number; r0?: number; grow?: number; speed?: number; n?: number; color?: string; width?: number; half?: boolean;
}) => (
  <>
    {Array.from({ length: n }, (_, i) => {
      const p = (t * speed + i / n) % 1;
      const r = r0 + grow * p;
      return <div key={i} style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: "50%",
        border: `${width}px solid ${color}`, opacity: 1 - p, clipPath: half ? "inset(0 0 0 50%)" : undefined }} />;
    })}
  </>
);

// Big hook object: an emoji that shakes while `active` (ringing, buzzing), with rings, used for
// the opening and again during the outro so the last frame matches the first.
export const HookProp = ({ t, char, active, scale = 1, y = 560, opacity = 1, size = 470 }: {
  t: number; char: string; active: boolean; scale?: number; y?: number; opacity?: number; size?: number;
}) => {
  if (opacity <= 0) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: y, height: 600, opacity: Math.min(1, opacity), transform: `scale(${scale})` }}>
      {active && <Rings t={t} x={540} y={300} />}
      <div style={{ position: "absolute", width: "100%", top: 30, textAlign: "center", fontSize: size, lineHeight: 1,
        transform: `rotate(${active ? 9 * Math.sin(t * 70) : 0}deg)` }}>{char}</div>
    </div>
  );
};

// Hook title in the top band, gently breathing. `accent` is drawn in gold before `rest`.
export const Title = ({ t, accent, rest, opacity, top = 120, size = 120 }: { t: number; accent: string; rest: string; opacity: number; top?: number; size?: number }) =>
  opacity <= 0 ? null : (
    <div style={{ position: "absolute", top, width: "100%", textAlign: "center", opacity: Math.min(1, opacity), fontFamily: "Anton", fontSize: size,
      color: "#fff", letterSpacing: 2, ...STROKE(10), transform: `scale(${1 + 0.02 * Math.sin(t * 6)})` }}>
      <span style={{ color: GOLD }}>{accent}</span> {rest}
    </div>
  );

// Giant wobbling question mark (the "why?" beat).
export const Question = ({ t, a, b, top = 380 }: { t: number; a: number; b: number; top?: number }) => {
  if (!vis(t, a, b + 0.2)) return null;
  const s = interpolate(t, [a, a + 0.5], [0, 1], { ...clamp, easing: back }) * (1 + 0.04 * Math.sin(t * 9));
  return (
    <div style={{ position: "absolute", width: "100%", top, textAlign: "center", fontFamily: "Anton", fontSize: 720,
      lineHeight: 1, color: GOLD, opacity: 1 - ramp(t, b, b + 0.2), ...STROKE(14),
      transform: `scale(${s}) rotate(${6 * Math.sin(t * 4)}deg)` }}>?</div>
  );
};

// One sound effect from public/sfx/<name>.wav (made by sfx.py) starting at `at` seconds.
export const Sfx = ({ at, src, vol = 0.5 }: { at: number; src: string; vol?: number }) => (
  <Sequence from={Math.max(0, Math.round(at * FPS))} layout="none">
    <Audio src={staticFile(`sfx/${src}.wav`)} volume={vol} />
  </Sequence>
);
