import React from "react";
import { Audio, Easing, Img, interpolate, Sequence, staticFile } from "remotion";
import { FPS } from "../timing";
import { ramp, pop, enter } from "./anim";
import { Burst } from "./burst";
import { STROKE } from "./overlays";
import { fontReady } from "../fonts";
import options from "../options.json";
import images from "../images.json";

// 2D props for explainer Shorts: archive photo cards with a name tag, speech bubbles, stamps,
// emoji props, a counter that runs across a phrase, hook ring arcs, sound effects and
// shake/sway wrappers. Every prop takes the time `t` and word times (from timing.ts), never frames.

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const back = Easing.out(Easing.back(1.6));
export const vis = (t: number, a: number, b: number) => t >= a && t < b;
export const PAPER = "#f3e7cf";
export const GOLD = "#ffc400";
export const RED = "#e01b22";

// Layout of the 1080x1920 frame. The title is one line at TITLE_TOP (it shrinks to fit); the
// picture (photos, hero emoji, diagrams) lives between PIC_TOP and picBottom(); captions sit
// below. Nothing with text goes closer than EDGE to a screen edge (the text props clamp it).
export const W = 1080, H = 1920, EDGE = 40;
export const TITLE_TOP = 110, PIC_TOP = 320;
export const picBottom = () => (options.captions === false ? 1700 : 1290);

// Pixel size of each photo in public/ ([w, h]), written by `anim.py sync`.
const DIMS = images as unknown as Record<string, [number, number]>;
export const aspect = (src: string) => { const d = DIMS[src] ?? DIMS[src.split("/").pop() ?? ""]; return d ? d[1] / d[0] : undefined; };

// Width of a line of text in px, measured with the real font once it has loaded (before that,
// a deliberately wide estimate, so nothing overflows on the first frame).
let ctx: CanvasRenderingContext2D | null = null;
const widths = new Map<string, number>();
export const textWidth = (text: string, family: string, size: number, spacing = 0) => {
  if (!fontReady(family) || typeof document === "undefined") return text.length * (size * 0.62 + spacing);
  const k = family + "|" + text;
  let w = widths.get(k);
  if (w === undefined) {
    ctx = ctx ?? document.createElement("canvas").getContext("2d");
    if (!ctx) return text.length * (size * 0.62 + spacing);
    ctx.font = `100px "${family}"`;
    w = ctx.measureText(text).width;
    widths.set(k, w);
  }
  return (w * size) / 100 + spacing * text.length;
};
// Largest font size up to `size` at which every line of `text` fits in `maxW` px.
export const fitSize = (text: string, family: string, size: number, maxW: number, spacing = 0) => {
  const widest = Math.max(...text.split("\n").map((l) => textWidth(l, family, size, spacing)));
  return widest <= maxW ? size : Math.floor((size * maxW) / widest);
};
const between = (v: number, lo: number, hi: number) => (lo > hi ? (lo + hi) / 2 : Math.min(hi, Math.max(lo, v)));

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
// until `b`, then slides out. Without `h` the card takes the photo's own shape (nothing is
// cropped: text on a cereal box or a poster stays readable), shrinks to fit the picture band
// and is centred in it; pass `h` only to crop on purpose (a face), with `pos` as the
// object-position. Children (a NameTag, a Bubble) are positioned relative to the card.
export const Card = ({ src, t, a, b, from = "right", w: w0 = 960, h: h0, top: top0, pos = "50% 20%", tilt = 0, slam, sepia = 0.25, fit = "cover", kb = 0.06, drift = 0, punch = [], flip, children }: {
  src: string; t: number; a: number; b: number; from?: "left" | "right" | "zoom"; w?: number; h?: number; top?: number;
  pos?: string; tilt?: number; slam?: boolean; sepia?: number; fit?: "cover" | "contain"; children?: React.ReactNode;
  flip?: "y" | "x";  // 3D flip-in instead of the slide: the card turns up from edge-on (perspective rotateY / rotateX) and settles with a small overshoot
  kb?: number; drift?: number; punch?: number[];  // slow push-in end (0.06 = 6 %), sideways drift in px (kept inside the photo), fast +8 % pushes on word times
}) => {
  if (!vis(t, a - 0.01, b + 0.3)) return null;
  const band = picBottom() - (top0 ?? PIC_TOP);
  let w = Math.min(w0, W - 2 * EDGE), h = h0 ?? 900;
  const r = aspect(src);
  if (h0 === undefined && r) { h = w * r; if (h > band) { h = band; w = h / r; } }
  const top = top0 ?? PIC_TOP + Math.max(0, (band - h) / 2);
  const k = ramp(t, a, a + 0.35, 0, 1, back);
  const out = ramp(t, b, b + 0.3);
  const dx = from === "zoom" || flip ? 0 : (from === "left" ? -1 : 1) * 1200 * (1 - k);
  const s = from === "zoom" || slam ? interpolate(t - a, [0, 0.18, 0.32], [1.6, 0.96, 1], clamp) : 1;
  const pn = punch.reduce((m, q) => Math.max(m, 0.08 * Math.max(0, Math.min(1, (t - q) / 0.08)) * (1 - Math.max(0, Math.min(1, (t - q - 0.18) / 0.5)))), 0);
  const kbs = 1 + kb * ramp(t, a, b, 0, 1, Easing.linear) + pn;
  const room = ((kbs - 1) / 2) * w;                       // how far the photo can slide before an edge shows
  const dxi = Math.max(-room, Math.min(room, drift * ramp(t, a, b, -0.5, 0.5, Easing.linear)));
  return (
    <div style={{ position: "absolute", left: 540 - w / 2, top, width: w, height: h, opacity: 1 - out,
      transform: `${flip ? `perspective(1600px) rotate${flip === "x" ? "X" : "Y"}(${(1 - k) * (flip === "x" ? 75 : -80)}deg) ` : ""}translateX(${dx - out * 300}px) scale(${s}) rotate(${tilt}deg)` }}>
      <div style={{ width: "100%", height: "100%", overflow: "hidden", borderRadius: 18, border: `14px solid ${PAPER}`,
        boxShadow: "0 30px 70px rgba(0,0,0,.6)", background: PAPER }}>
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: fit, objectPosition: pos,
          transformOrigin: pos, transform: `translateX(${dxi}px) scale(${kbs})`, filter: `sepia(${sepia}) contrast(1.05)` }} />
      </div>
      {children}
    </div>
  );
};

// Two photos for one beat (then vs now, A vs B), stacked one above the other in the picture
// band, never side by side: on a 9:16 frame side-by-side cuts each photo to a sliver. Each
// keeps its own shape; both shrink together until they fit. `tag` adds a NameTag.
type PairItem = { src: string; tag?: string; sub?: string };
export const Pair = ({ t, a, b, first, second, stagger = 0.25, gap = 50 }: {
  t: number; a: number; b: number; first: PairItem; second: PairItem; stagger?: number; gap?: number;
}) => {
  const band = picBottom() - PIC_TOP - gap;
  const r1 = aspect(first.src) ?? 0.66, r2 = aspect(second.src) ?? 0.66;
  const w = Math.min(W - 2 * EDGE, band / (r1 + r2));
  const h1 = w * r1, h2 = w * r2, y = PIC_TOP + (band - h1 - h2) / 2;
  return (
    <>
      <Card src={first.src} t={t} a={a} b={b} from="left" w={w} h={h1} top={y} pos="50% 50%">
        {first.tag && <NameTag t={t} a={a + 0.2} name={first.tag} sub={first.sub} />}
      </Card>
      <Card src={second.src} t={t} a={a + stagger} b={b} from="right" w={w} h={h2} top={y + h1 + gap} pos="50% 50%">
        {second.tag && <NameTag t={t} a={a + stagger + 0.2} name={second.tag} sub={second.sub} />}
      </Card>
    </>
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
// single word; never put a paraphrase in a bubble as if it were a quote. A real line break in
// `text` makes two lines. The text shrinks until the bubble fits the screen width, and x/y are
// moved in so the whole bubble stays EDGE px inside the frame (x={100} can't push it off).
export const Bubble = ({ t, a, text, x, y, color = "#111", bg = "#fff", size: size0 = 120, tail = "left", rot = -4 }: {
  t: number; a: number; text: string; x: number; y: number; color?: string; bg?: string; size?: number; tail?: "left" | "right"; rot?: number;
}) => {
  if (t < a) return null;
  const chrome = 2 * 46 + 2 * 8 + 20;  // padding + border + room for the tilt
  const size = fitSize(text, "Anton", size0, W - 2 * EDGE - chrome);
  const lines = text.split("\n");
  const bw = Math.max(...lines.map((l) => textWidth(l, "Anton", size))) + chrome;
  const bh = lines.length * size * 1.05 + 2 * 18 + 2 * 8;
  const cx = between(x, EDGE + bw / 2, W - EDGE - bw / 2), cy = between(y, EDGE + bh / 2, H - EDGE - bh / 2 - 44);
  return (
    <div style={{ position: "absolute", left: cx, top: cy, transform: `translate(-50%,-50%) scale(${pop(t, a, 0.32, 0.3, 1.25)}) rotate(${rot}deg)` }}>
      <div style={{ position: "relative", background: bg, borderRadius: 60, padding: "18px 46px", border: "8px solid #111",
        boxShadow: "0 14px 30px rgba(0,0,0,.45)", fontFamily: "Anton", fontSize: size, lineHeight: 1.05, color, whiteSpace: "pre", textAlign: "center" }}>
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

// Rubber stamp that slams down at `a` (pair with the "stamp" sfx). Optional `until` (s): fades out
// there; without it the stamp stays to the last frame, so give every stamp an `until`.
export const Stamp = ({ t, a, text, top = 690, color = RED, size: size0 = 150, rot = -9, until, burst }: {
  t: number; a: number; text: string; top?: number; color?: string; size?: number; rot?: number; until?: number;
  burst?: boolean | string;  // particles fly out of the stamp as it lands (true = the stamp colour, or a colour)
}) => {
  if (t < a) return null;
  const gone = until === undefined ? 0 : ramp(t, until, until + 0.3);
  if (gone >= 1) return null;
  const size = fitSize(text, "Anton", size0, W - 2 * EDGE - 2 * 36 - 2 * 14 - 40, 4);  // padding, border, tilt
  return (
    <>
      <div style={{ position: "absolute", left: 0, right: 0, top, textAlign: "center", whiteSpace: "pre",
        transform: `scale(${interpolate(t - a, [0, 0.12, 0.22], [2.4, 0.95, 1], clamp)}) rotate(${rot}deg)`,
        opacity: until === undefined ? ramp(t, a, a + 0.06) : ramp(t, a, a + 0.06) * (1 - gone) }}>
        <span style={{ fontFamily: "Anton", fontSize: size, color, border: `14px solid ${color}`, borderRadius: 18,
          padding: "0 36px", background: "rgba(255,255,255,.85)", letterSpacing: 4 }}>{text}</span>
      </div>
      {burst && <Burst t={t} a={a + 0.12} x={540} y={top + size * 0.62} color={typeof burst === "string" ? burst : color} />}
    </>
  );
};

// Year or label badge, tilted, popping in (e.g. "1877"). Optional `until` (s): fades out there;
// give every badge an `until` or it stays to the last frame.
export const Badge = ({ t, a, text, x: x0 = 90, y = 240, bg = "#c4161c", size: size0 = 130, rot = -8, until }: {
  t: number; a: number; text: string; x?: number; y?: number; bg?: string; size?: number; rot?: number; until?: number;
}) => {
  if (t < a) return null;
  const gone = until === undefined ? 0 : ramp(t, until, until + 0.3);
  if (gone >= 1) return null;
  const chrome = 2 * 34 + 2 * 8 + 30;  // padding, border, tilt
  const size = fitSize(text, "Anton", size0, W - 2 * EDGE - chrome);
  const x = between(x0, EDGE, W - EDGE - textWidth(text, "Anton", size) - chrome);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${pop(t, a)}) rotate(${rot}deg)`, whiteSpace: "nowrap",
      background: bg, color: "#fff", fontFamily: "Anton", fontSize: size, padding: "4px 34px", borderRadius: 16,
      border: "8px solid #fff", boxShadow: "0 14px 30px rgba(0,0,0,.5)", ...(until === undefined ? {} : { opacity: 1 - gone }) }}>{text}</div>
  );
};

// Emoji prop: pops in at `a`, optional wobble (a ringing bell) and grey-out + red slash (`crossAt`).
export const Emoji = ({ t, a, char, x, y, size = 290, rot = 0, wobble = false, crossAt, springy }: {
  t: number; a: number; char: string; x: number; y: number; size?: number; rot?: number; wobble?: boolean; crossAt?: number; springy?: boolean;
}) => {
  if (t < a) return null;
  const slash = crossAt === undefined ? 0 : ramp(t, crossAt, crossAt + 0.2, 0, 1, Easing.out(Easing.quad));
  const wob = wobble && (crossAt === undefined || t < crossAt) ? 16 * Math.sin(t * 40) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: size * 1.15, height: size * 1.15 }}>
      <div style={{ fontSize: size, lineHeight: 1, textAlign: "center", filter: `grayscale(${slash})`,
        transform: `scale(${enter(t, a, springy)}) rotate(${rot + wob}deg)` }}>{char}</div>
      {slash > 0 && (
        <div style={{ position: "absolute", left: -10, top: size * 0.55, width: size * 1.25 * slash, height: 34, background: RED,
          borderRadius: 17, transform: "rotate(-40deg)", transformOrigin: "0 50%", boxShadow: "0 0 0 6px #fff" }} />
      )}
    </div>
  );
};

// The main object of a beat with no photo (📻 🥣 🔋 ⏰): one big emoji centred in the picture
// band, popping in at `a`, gently floating, fading out at `b`. 700 px fills the band; an Emoji
// at its default 290 is an accent beside a hero or a card, not a whole beat. Two objects
// side by side: two Heroes with `x` 290 / 790 and size ~460. `crossAt`/`wobble` as on Emoji.
export const Hero = ({ t, a, b, char, size = 700, x = 540, dy = 0, wobble = false, crossAt, springy }: {
  t: number; a: number; b: number; char: string; size?: number; x?: number; dy?: number; wobble?: boolean; crossAt?: number; springy?: boolean;
}) => {
  if (!vis(t, a, b + 0.3)) return null;
  const box = size * 1.15;
  const top = PIC_TOP + (picBottom() - PIC_TOP - box) / 2 + dy + 14 * Math.sin((t - a) * 2.4);
  return (
    <Layer opacity={1 - ramp(t, b, b + 0.3)}>
      <Emoji t={t} a={a} char={char} x={x - box / 2} y={top} size={size} wobble={wobble} crossAt={crossAt} springy={springy} />
    </Layer>
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

// Hook title in the top band, gently breathing. `accent` is drawn in gold before `rest`. Always
// one line: a long title shrinks to fit the width instead of wrapping onto the picture below
// (it ends above PIC_TOP, where Cards and the hook prop start).
export const Title = ({ t, accent, rest, opacity, top = TITLE_TOP, size: size0 = 120 }: { t: number; accent: string; rest: string; opacity: number; top?: number; size?: number }) => {
  if (opacity <= 0) return null;
  const size = fitSize(`${accent} ${rest}`, "Anton", size0, W - 2 * EDGE - 40, 2);  // 40: breathing + stroke
  return (
    <div style={{ position: "absolute", top: top + (size0 - size) / 2, width: "100%", textAlign: "center", opacity: Math.min(1, opacity), fontFamily: "Anton", fontSize: size,
      color: "#fff", letterSpacing: 2, whiteSpace: "nowrap", ...STROKE(10), transform: `scale(${1 + 0.02 * Math.sin(t * 6)})` }}>
      <span style={{ color: GOLD }}>{accent}</span> {rest}
    </div>
  );
};

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
