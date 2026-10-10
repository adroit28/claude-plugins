import React from "react";
import { Easing, useCurrentFrame, useVideoConfig } from "remotion";
import { Trail, CameraMotionBlur } from "@remotion/motion-blur";
import { ramp, enter } from "./anim";
import { STROKE } from "./overlays";
import { W, H, EDGE, GOLD, RED, PIC_TOP, TITLE_TOP, back, fitSize, textWidth } from "./props";

// 0.8.0 effects. All opt-in; nothing here changes an existing component. Times are seconds (like the rest
// of the kit), colours default to the gold/red palette.
const rnd = (i: number, k = 0) => { const s = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return s - Math.floor(s); };
const lerp = (a: number, b: number, x: number) => a + (b - a) * x;
const inOut = Easing.inOut(Easing.cubic);

// ---- Glitch: RGB-split jitter slam with scan lines (a myth reveal) ---------------------------------------
// The word slams in at `a` (2.6x -> 1), jitters hard for 0.5 s, then settles; `sub` is a small gold line under it.
// Fades out at `b`. Pair with the glitch or scratch sfx. One per Short: it is loud.
export const Glitch = ({ t, a, b, text, sub, top = 520, size: size0 = 262, color = "#fff" }: {
  t: number; a: number; b: number; text: string; sub?: string; top?: number; size?: number; color?: string;
}) => {
  if (t < a || t > b + 0.3) return null;
  const age = t - a, hard = age < 0.5;
  const out = 1 - ramp(t, b, b + 0.25);
  const slam = ramp(t, a, a + 0.12, 0, 1, back);
  const size = fitSize(text, "Anton", size0, W - 2 * EDGE - 60, 2);
  const g = hard ? Math.sin(age * 140) : 0;
  const jx = (rnd(Math.floor(age * 30)) - 0.5) * 36 * (hard ? 1 : 0.2);
  const word = (x: React.CSSProperties) => (
    <div style={{ position: "absolute", left: 0, top: 0, width: W, textAlign: "center", fontFamily: "Anton", fontSize: size, lineHeight: 1,
      letterSpacing: 2, whiteSpace: "pre", ...x }}>{text}</div>
  );
  return (
    <div style={{ position: "absolute", inset: 0, opacity: out, background: `rgba(0,0,0,${0.35 * (1 - ramp(t, a + 0.5, a + 0.8))})` }}>
      <div style={{ position: "absolute", left: 0, top, width: W, height: size * 1.1,
        transform: `scale(${lerp(2.6, 1, slam)}) rotate(${(1 - slam) * -8 + g * 0.8}deg)` }}>
        {word({ color: "#00e5ff", transform: `translate(${-14 + jx}px, 0)`, mixBlendMode: "screen", opacity: 0.9 })}
        {word({ color: RED, transform: `translate(${14 - jx}px, 0)`, mixBlendMode: "screen", opacity: 0.9 })}
        {word({ color, transform: `translate(${jx * 0.3}px, 0)`, ...STROKE(10) })}
        <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, rgba(0,0,0,.28) 0 3px, transparent 3px 8px)", opacity: hard ? 1 : 0.5 }} />
        <div style={{ position: "absolute", left: 0, top: size * 0.45, width: W, height: 10, background: "#fff",
          opacity: hard && Math.floor(age * 24) % 3 === 0 ? 0.9 : 0, transform: `translateY(${rnd(Math.floor(age * 30), 4) * size * 0.45}px)` }} />
      </div>
      {sub && <div style={{ position: "absolute", left: 0, top: top + size * 1.12, width: W, textAlign: "center", fontFamily: "Barlow", fontSize: 58, color: GOLD,
        letterSpacing: 10, opacity: ramp(t, a + 0.2, a + 0.32), ...STROKE(8) }}>{sub}</div>}
    </div>
  );
};

// ---- Title3D: extruded one-line title with a light sweep (hook title) --------------------------------------
// Drop-in for Title (same accent/rest/opacity/top/size). Drawn settled from frame 0 (so the feed frame is the
// finished title) and static, which also keeps the last frame identical for the loop. A light sweep crosses at
// each time in `sweeps` (default 0.4 s; add LAST_T - 0.9 to sweep again before the loop point).
const Run = ({ accent, rest, ca, cr }: { accent: string; rest: string; ca: string; cr: string }) => (
  <><span style={{ color: ca }}>{accent}</span> <span style={{ color: cr }}>{rest}</span></>
);
export const Title3D = ({ t, accent, rest, opacity = 1, top = TITLE_TOP, size: size0 = 120, sweeps = [0.4], depth = 14, tilt = [-9, 5] }: {
  t: number; accent: string; rest: string; opacity?: number; top?: number; size?: number; sweeps?: number[]; depth?: number; tilt?: [number, number];
}) => {
  if (opacity <= 0) return null;
  const size = fitSize(`${accent} ${rest}`, "Anton", size0, W - 2 * EDGE - 90, 2);  // 90: extrusion + tilt
  const wText = textWidth(`${accent} ${rest}`, "Anton", size, 2);
  const sw = sweeps.map((s) => ramp(t, s, s + 0.6)).find((p) => p > 0 && p < 1) ?? -1;
  const common: React.CSSProperties = { fontFamily: "Anton", fontSize: size, letterSpacing: 2, whiteSpace: "nowrap", lineHeight: 1 };
  return (
    <div style={{ position: "absolute", top: top + (size0 - size) / 2, left: 0, width: "100%", display: "flex", justifyContent: "center", opacity: Math.min(1, opacity), perspective: 1100 }}>
      <div style={{ position: "relative", transformStyle: "preserve-3d", transform: `rotateY(${tilt[0]}deg) rotateX(${tilt[1]}deg)` }}>
        {Array.from({ length: depth }, (_, i) => (
          <div key={i} style={{ ...common, position: "absolute", left: 0, top: 0, transform: `translateZ(${-(i + 1) * 2.2}px)`, filter: `brightness(${0.75 - i / (depth * 2.2)})` }}>
            <Run accent={accent} rest={rest} ca="#b88a00" cr="#4b5566" />
          </div>
        ))}
        <div style={{ ...common, position: "relative", ...STROKE(8), textShadow: "0 0 30px rgba(255,255,255,.25)" }}><Run accent={accent} rest={rest} ca={GOLD} cr="#fff" /></div>
        {sw >= 0 && <div style={{ position: "absolute", top: -10, height: size * 1.3, width: size * 1.1, left: lerp(-size, wText + size * 0.2, sw),
          background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.7), rgba(255,255,255,0))", transform: "skewX(-20deg)", mixBlendMode: "overlay" }} />}
      </div>
    </div>
  );
};

// ---- CalendarFlip: a page-flip number that runs from -> to across a phrase (a year) ---------------------------
// The card pops in at `a`, flips `steps` times (rotateX, the old page folds away and the new one drops in) and
// lands on `to` at `b` with a gold punch. Numbers step evenly eased; non-numbers flip once. `until` fades it out.
export const CalendarFlip = ({ t, a, b, from, to, label = "YEAR", top = 380, steps = 6, until, color = RED, springy }: {
  t: number; a: number; b: number; from: number | string; to: number | string; label?: string; top?: number; steps?: number; until?: number; color?: string; springy?: boolean;
}) => {
  if (t < a) return null;
  const gone = until === undefined ? 0 : ramp(t, until, until + 0.3);
  if (gone >= 1) return null;
  const numeric = typeof from === "number" && typeof to === "number";
  const vals: (number | string)[] = numeric
    ? Array.from({ length: steps + 1 }, (_, i) => (i === steps ? to : i === 0 ? from : Math.round(lerp(from as number, to as number, inOut(i / steps)))))
    : [from, to];
  const n = vals.length - 1, f0 = Math.min(a + 0.25, b - 0.2), span = Math.max(0.2, b - f0), fd = Math.min(0.22, (span / n) * 0.9);
  let idx = 0, angle = 0, shown = vals[0];
  for (let k = n - 1; k >= 0; k--) {
    const st = f0 + ((k + 1) * span) / n - fd;
    if (t >= st) {
      const p = Math.min(1, (t - st) / fd);
      idx = k + 1; shown = p < 0.5 ? vals[k] : vals[k + 1]; angle = p >= 1 ? 0 : p < 0.5 ? p * 180 : (p - 1) * 180;
      break;
    }
  }
  const landed = t >= b ? 1 + 0.15 * Math.max(0, 1 - (t - b) / 0.3) : 1;
  const text = String(shown), fs = fitSize(text, "Anton", 230, 440);
  return (
    <div style={{ position: "absolute", left: 540 - 270, top, width: 540, opacity: 1 - gone, transform: `scale(${enter(t, a, springy)}) rotate(-3deg)` }}>
      <div style={{ background: "#fff", borderRadius: 28, overflow: "hidden", border: "5px solid #fff", boxShadow: "0 24px 60px rgba(0,0,0,.6)" }}>
        <div style={{ background: color, color: "#fff", fontFamily: "Anton", fontSize: 54, letterSpacing: 8, textAlign: "center", padding: "10px 0 4px" }}>{label}</div>
        <div style={{ height: 290, display: "flex", alignItems: "center", justifyContent: "center", perspective: 800, background: "linear-gradient(#fff, #eee)" }}>
          <div style={{ fontFamily: "Anton", fontSize: fs, lineHeight: 1, color: idx === n && t >= b ? "#c4161c" : "#0b0b0f", transform: `rotateX(${angle}deg) scale(${landed})` }}>{text}</div>
        </div>
      </div>
    </div>
  );
};

// ---- Transition: a cut effect at a time (changes no word timing) ---------------------------------------------
// Covers the screen for an instant around `at` (the next beat's start) and uncovers it, so the picture can change
// under it. `kind`: whip (fast panel + motion blur, for a hard turn), slide (panel, calmer), iris (circle closes then
// opens on the subject), flip (a card turns over), wipe (gold band then dark band, diagonal). Keep it at the TOP
// LEVEL of Overlays (never inside a Cam/Layer). Rule: 2-3 per Short, at the story's turns only. Pair with a whoosh.
type Kind = "whip" | "slide" | "iris" | "flip" | "wipe";
const DARK = "#0b0b10";
const Panels = ({ kind, at, dur, color, dir, cx, cy }: { kind: Kind; at: number; dur: number; color: string; dir: 1 | -1; cx: number; cy: number }) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const p = (t - (at - dur / 2)) / dur;
  if (p <= 0 || p >= 1) return null;
  const e = inOut(p), cover = p < 0.5 ? inOut(p * 2) : 1 - inOut(p * 2 - 1);
  if (kind === "iris") {
    const r = 1250 * (1 - cover);
    return <div style={{ position: "absolute", inset: 0, background: `radial-gradient(circle at ${cx}px ${cy}px, transparent ${r}px, ${color} ${r}px, ${color} ${r + 18}px, ${DARK} ${r + 18}px)` }} />;
  }
  if (kind === "flip") {
    const ang = p < 0.5 ? lerp(90, 0, inOut(p * 2)) : lerp(0, -90, inOut(p * 2 - 1));
    return (
      <div style={{ position: "absolute", inset: 0, perspective: 1500 }}>
        <div style={{ position: "absolute", inset: 0, transform: `rotateY(${ang * dir}deg)`, background: `linear-gradient(135deg, ${DARK}, #1c1c28)`, borderLeft: `18px solid ${color}`, borderRight: `18px solid ${color}` }} />
      </div>
    );
  }
  const wide = kind === "whip" ? W * 1.6 : W * 1.15;
  const left = dir === 1 ? lerp(W, -wide, e) : lerp(-wide, W, e);
  if (kind === "wipe") {
    const l2 = dir === 1 ? lerp(W, -wide, inOut(Math.max(0, p - 0.1) / 0.9)) : lerp(-wide, W, inOut(Math.max(0, p - 0.1) / 0.9));
    return (
      <>
        <div style={{ position: "absolute", top: -200, height: H + 400, width: wide, left: l2, background: DARK, transform: "skewX(-14deg)" }} />
        <div style={{ position: "absolute", top: -200, height: H + 400, width: wide * 0.9, left, background: color, transform: "skewX(-14deg)" }} />
      </>
    );
  }
  return (
    <div style={{ position: "absolute", top: 0, height: H, width: wide, left,
      background: kind === "whip"
        ? `repeating-linear-gradient(0deg, ${color} 0 40px, ${DARK} 40px 80px)`
        : `linear-gradient(${dir === 1 ? 90 : 270}deg, ${color} 0 3%, ${DARK} 3%)` }} />
  );
};
export const Transition = ({ kind = "whip", at, dur = 0.5, color = GOLD, dir = 1, x = 540, y = 900 }: {
  kind?: Kind; at: number; dur?: number; color?: string; dir?: 1 | -1; x?: number; y?: number;  // x,y: where an iris closes to
}) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  if (t < at - dur / 2 - 0.2 || t > at + dur / 2 + 0.2) return null;
  const inner = <Panels kind={kind} at={at} dur={dur} color={color} dir={dir} cx={x} cy={y} />;
  return <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>{kind === "whip" ? <Trail layers={5} lagInFrames={0.7} trailOpacity={0.7}>{inner}</Trail> : inner}</div>;
};

// ---- Blur: motion blur on a fast move ---------------------------------------------------------------------------
// `children` is a function of time: <Blur a={t0} b={t1}>{(t) => <Emoji t={t} .../>}</Blur>. Between a and b the subtree is
// drawn several times at slightly earlier moments (kind "trail": ghost layers behind a fast mover, "camera": a shutter
// average over `samples` sub-frames, the cinema look). Outside [a, b] it is drawn once, with no cost. Costs render
// time: roughly layers x (or samples x) the work of that subtree for those frames, so wrap only the fast prop
// (a sweep, flying germs), never the whole scene, and keep the window short. No Sfx/Audio inside it.
const Timed = ({ children }: { children: (t: number) => React.ReactNode }) => {
  const { fps } = useVideoConfig();
  return <>{children(useCurrentFrame() / fps)}</>;
};
export const Blur = ({ a, b, kind = "trail", layers = 5, lag = 0.8, opacity = 0.6, shutter = 180, samples = 8, children }: {
  a: number; b: number; kind?: "trail" | "camera"; layers?: number; lag?: number; opacity?: number; shutter?: number; samples?: number;
  children: (t: number) => React.ReactNode;
}) => {
  const { fps } = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const body = <Timed>{children}</Timed>;
  if (t < a || t > b) return body;
  return kind === "camera"
    ? <CameraMotionBlur shutterAngle={shutter} samples={samples}>{body}</CameraMotionBlur>
    : <Trail layers={layers} lagInFrames={lag} trailOpacity={opacity}>{body}</Trail>;
};

// ---- Meter: a danger / level gauge that fills across a phrase ---------------------------------------------------
// Fills 0 -> `to` (0-1) between word times a and b, yellow -> orange -> red, shakes and blinks near the top.
// `label` is the title ("DANGER"), `sub` a small line, `icon` an emoji at the left. Give it an `until`.
export const Meter = ({ t, a, b, to = 1, label = "DANGER", sub, icon = "⚠️", top = PIC_TOP + 40, until, unit = "%" }: {
  t: number; a: number; b: number; to?: number; label?: string; sub?: string; icon?: string; top?: number; until?: number; unit?: string;
}) => {
  if (t < a - 0.3) return null;
  const gone = until === undefined ? 0 : ramp(t, until, until + 0.3);
  if (gone >= 1) return null;
  const k = ramp(t, a - 0.3, a - 0.05, 0, 1, Easing.out(Easing.cubic));
  const lv = ramp(t, a, b, 0, to, inOut);
  const col = lv < 0.5 ? GOLD : lv < 0.8 ? "#ff8a00" : RED;
  const hot = lv > 0.8, shake = hot ? Math.sin(t * 90) * 5 : 0;
  const pct = Math.round(lv * 100);
  return (
    <div style={{ position: "absolute", left: 70, top, width: 940, opacity: k * (1 - gone), transform: `translate(${shake}px, ${(1 - k) * -60}px)` }}>
      <div style={{ background: "linear-gradient(180deg, rgba(20,20,28,.92), rgba(8,8,12,.95))", border: `3px solid ${hot ? RED : "rgba(255,255,255,.2)"}`, borderRadius: 28,
        boxShadow: "0 18px 50px rgba(0,0,0,.55)", padding: "24px 32px 28px" }}>
        <div style={{ fontFamily: "Anton", fontSize: 62, color: "#fff", letterSpacing: 3 }}>{label}</div>
        {sub && <div style={{ fontFamily: "Barlow", fontSize: 36, color: "rgba(255,255,255,.65)", letterSpacing: 2 }}>{sub}</div>}
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 22 }}>
          <div style={{ fontSize: 80, lineHeight: 1 }}>{icon}</div>
          <div style={{ flex: 1, height: 74, borderRadius: 37, background: "#1a1a22", border: "4px solid #fff", overflow: "hidden" }}>
            <div style={{ width: `${Math.max(4, pct)}%`, height: "100%", background: `linear-gradient(90deg, ${GOLD}, ${col})`, boxShadow: `0 0 30px ${col}` }} />
          </div>
        </div>
        <div style={{ fontFamily: "Anton", fontSize: 130, lineHeight: 1, color: col, textAlign: "center", marginTop: 12, ...STROKE(10) }}>
          {pct}{unit}{lv > 0.97 && Math.floor(t * 10) % 2 === 0 ? " 😵" : ""}
        </div>
      </div>
    </div>
  );
};

