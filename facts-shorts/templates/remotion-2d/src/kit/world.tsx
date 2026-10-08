import React from "react";
import { Easing } from "remotion";
import { Cam, CamKey } from "./motion";
import { ramp } from "./anim";
import { Layer, W, H, EDGE, GOLD, textWidth } from "./props";

// Scale-axis worlds (added in 0.5.0): a camera that travels along a height (or depth) axis with a
// live metre counter, a sky that fades with the value, a ruler of ticks, objects drawn at their
// true size and labels pinned to them. For "how high / how deep / how far" Shorts.
//
//   <DepthWorld t={t}
//     keys={[{ at: 0, v: 0, ppm: 40 }, { at: 6, v: 8848, ppm: 0.06 }, { at: 20, v: 400000, ppm: 0.0004 }]}
//     sky={[{ v: 0, color: "#6ec6ff" }, { v: 12000, color: "#1b4f9c" }, { v: 100000, color: "#000" }]}
//     objects={[{ v: 0, h: 1.7, emoji: "🧍", label: "AAP" }, { v: 8848, line: true, label: "EVEREST" }]}
//     punch={[6]} />
//
// `keys` say where the camera is (metres) at a time and how zoomed it is (px per metre); between
// two keys it eases with ramp(), in log space by default, so 0 m -> 35,786,000 m stays smooth. The
// `ppm` of a key holds until the next key that sets one. Objects are placed by their `v` (metres,
// the base of the object) and drawn `h` metres tall at the current px per metre, so every
// size is true at every frame; one that would be under `minPx` is drawn as a dot (never faked
// bigger) and keeps its label. `direction="down"` flips the axis for depth: pass depths as v.

export type WorldKey = { at: number; v: number; ppm?: number; ease?: "in" | "out" | "lin" }; // ease (0.5.2): easing of the move that ENDS at this key ("in" = accelerates into it, a slam; default in-out cubic)
export type SkyStop = { v: number; color: string };
export type WorldObj = {
  v: number;                 // metres: base of the object (altitude, or depth with direction="down")
  h?: number;                // metres tall (true size); omit for a line/dot
  emoji?: string;            // flat emoji drawn h metres tall
  render?: (px: number) => React.ReactNode; // custom flat art, given the height in px
  line?: boolean;            // full-width dashed line at v (Karman line, sea level)
  label?: string;            // pinned label
  sub?: string;              // second line under the label (e.g. "100 km")
  color?: string;            // label/line accent
  x?: number;                // centre x in px (default 700)
  side?: "left" | "right";   // label side of the object (default "right")
  from?: number; until?: number; // seconds the object exists
  pinned?: boolean;          // off-screen: keep a chip at the screen edge with an arrow
};

const lerp = (a: number, b: number, u: number) => a + (b - a) * u;

// camera value (metres) and zoom (px per metre) at time t
export const worldAt = (keys: WorldKey[], t: number, log = true) => {
  const ks = [...keys].sort((p, q) => p.at - q.at);
  const ppm: number[] = [];
  let last: number | undefined;
  for (let i = ks.length - 1; i >= 0; i--) { if (ks[i].ppm !== undefined) last = ks[i].ppm; ppm[i] = last ?? 1; }
  for (let i = 0, c = ppm[0]; i < ks.length; i++) { if (ks[i].ppm !== undefined) c = ks[i].ppm!; ppm[i] = c; }
  if (t <= ks[0].at) return { v: ks[0].v, ppm: ppm[0] };
  const n = ks.length - 1;
  if (t >= ks[n].at) return { v: ks[n].v, ppm: ppm[n] };
  let i = 0;
  while (t >= ks[i + 1].at) i++;
  const ez = ks[i + 1].ease;
  const u = ramp(t, ks[i].at, ks[i + 1].at, 0, 1, ez === "in" ? Easing.in(Easing.cubic) : ez === "out" ? Easing.out(Easing.cubic) : ez === "lin" ? (x: number) => x : undefined);
  const v = log
    ? Math.exp(lerp(Math.log(ks[i].v + 1), Math.log(ks[i + 1].v + 1), u)) - 1
    : lerp(ks[i].v, ks[i + 1].v, u);
  return { v, ppm: Math.exp(lerp(Math.log(ppm[i]), Math.log(ppm[i + 1]), u)) };
};

const rgb = (hex: string) => {
  const h = hex.replace("#", "");
  const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  return [0, 2, 4].map((k) => parseInt(f.slice(k, k + 2), 16));
};

// sky colour at a value: stops blended in log (or linear) value
export const skyAt = (stops: SkyStop[], v: number, log = true) => {
  const ss = [...stops].sort((p, q) => p.v - q.v);
  const x = (n: number) => (log ? Math.log(Math.max(n, 0) + 1) : n);
  if (v <= ss[0].v) return ss[0].color;
  if (v >= ss[ss.length - 1].v) return ss[ss.length - 1].color;
  let i = 0;
  while (v >= ss[i + 1].v) i++;
  const u = (x(v) - x(ss[i].v)) / (x(ss[i + 1].v) - x(ss[i].v));
  const a = rgb(ss[i].color), b = rgb(ss[i + 1].color);
  return `rgb(${a.map((c, k) => Math.round(lerp(c, b[k], u))).join(",")})`;
};

export const fmtM = (m: number) => Math.round(m).toLocaleString("en-US");
const fmtTick = (m: number) => (m >= 1000 ? `${+(m / 1000).toPrecision(9)} km` : `${+m.toPrecision(9)} m`).replace(/^\d+/, (n) => Number(n).toLocaleString("en-US"));

// 1, 2, 5 x 10^k: the smallest step that keeps ticks at least `gap` px apart
const niceStep = (ppm: number, gap: number) => {
  const raw = gap / ppm;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  return ([1, 2, 5, 10].map((m) => m * p).find((s) => s >= raw) ?? 10 * p);
};

export const DepthWorld = ({
  t, keys, sky, objects = [], punch = [], cam = [], log = true, direction = "up", focusY = 1000, ground,
  counterTop = 120, counterColor = GOLD, counter = true, axis = true, axisX = 150, tickGap = 170, rulerSpan = 0,
}: {
  t: number; keys: WorldKey[]; sky: SkyStop[]; objects?: WorldObj[]; punch?: number[]; cam?: CamKey[];
  log?: boolean; direction?: "up" | "down";
  focusY?: number;           // screen y of the camera value (default 1000: ahead is above it)
  ground?: string | false;   // colour below v = 0 (up) / water-air line (down off); default earth brown, false = none
  counterTop?: number; counterColor?: string; counter?: boolean; axis?: boolean; axisX?: number; tickGap?: number;
  rulerSpan?: number;        // 0.5.1: ruler zoom independent of the object zoom. >0 caps the ruler so the screen always spans at least this fraction of the camera value (0.4: at 160 km ticks 150/160/170 km; at 35,040 km ticks every 2,000 km). 0 = ruler follows ppm
}) => {
  const { v, ppm } = worldAt(keys, t, log);
  const dir = direction === "down" ? -1 : 1;
  // screen y of metre `a` (altitude up: larger a is higher on screen; depth down: larger a is lower)
  const yOf = (a: number) => focusY - dir * (a - v) * ppm;
  const top = dir === 1 ? v + focusY / ppm : v - focusY / ppm;
  const bottom = dir === 1 ? v - (H - focusY) / ppm : v + (H - focusY) / ppm;
  const bg = `linear-gradient(180deg, ${skyAt(sky, Math.max(top, 0), log)} 0%, ${skyAt(sky, Math.max(bottom, 0), log)} 100%)`;

  const gc = ground === undefined ? "#4a3626" : ground;
  const y0 = yOf(0);
  const rppm = rulerSpan > 0 ? Math.min(ppm, H / (rulerSpan * Math.max(v, 10))) : ppm;
  const yR = (a: number) => focusY - dir * (a - v) * rppm;   // ruler y (same as yOf when rulerSpan is 0)
  const rTop = dir === 1 ? v + focusY / rppm : v - focusY / rppm;
  const rBottom = dir === 1 ? v - (H - focusY) / rppm : v + (H - focusY) / rppm;
  const step = niceStep(rppm, tickGap);
  const from = Math.ceil(Math.min(rTop, rBottom) / step), to = Math.floor(Math.max(rTop, rBottom) / step);
  const ticks: number[] = [];
  for (let k = Math.max(from, 0); k <= to && ticks.length < 24; k++) ticks.push(k * step);

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: bg }} />
      <Cam t={t} keys={cam.length ? cam : [{ at: 0 }]} punch={punch}>
        {gc && dir === 1 && y0 < H && (
          <div style={{ position: "absolute", left: 0, right: 0, top: Math.max(y0, 0), height: H, background: gc, borderTop: y0 > -4 ? "6px solid #2c2118" : undefined }} />
        )}
        {axis && (
          <>
            <div style={{ position: "absolute", left: axisX, top: 0, width: 4, height: H, background: "rgba(255,255,255,0.35)" }} />
            {ticks.map((m) => {
              const y = yR(m);
              if (y < -40 || y > H + 40) return null;
              return (
                <React.Fragment key={m}>
                  <div style={{ position: "absolute", left: axisX - 18, top: y - 2, width: 40, height: 4, background: "rgba(255,255,255,0.8)" }} />
                  <div style={{ position: "absolute", left: axisX + 34, top: y - 22, fontFamily: "Anton", fontSize: 38, letterSpacing: 2,
                    color: "rgba(255,255,255,0.85)", textShadow: "0 2px 6px rgba(0,0,0,0.6)", whiteSpace: "nowrap" }}>{fmtTick(m)}</div>
                </React.Fragment>
              );
            })}
          </>
        )}
        {objects.map((o, i) => {
          if ((o.from !== undefined && t < o.from) || (o.until !== undefined && t > o.until)) return null;
          const y = yOf(o.v);                       // base of the object
          const px = (o.h ?? 0) * ppm;               // true height on screen
          const color = o.color ?? "#fff";
          const x = o.x ?? 700;
          const tiny = !o.line && px < 16;
          const topY = y - px * dir;                 // top edge (up: above the base)
          const mid = o.line ? y : tiny ? y : (y + topY) / 2;
          const off = mid < -80 || mid > H + 80;
          if (off && !o.pinned) return null;
          const size = 44, sub = 34;
          const lw = Math.max(textWidth(o.label ?? "", "Anton", size, 2), textWidth(o.sub ?? "", "Anton", sub, 2)) + 44;
          const right = (o.side ?? "right") === "right";
          const half = o.line ? 0 : Math.max(px / 2, tiny ? 12 : 0) + 20;
          const lx = Math.min(Math.max(right ? x + half : x - half - lw, EDGE), W - EDGE - lw);
          const ly = Math.min(Math.max(mid, 90), H - 90);
          const arrow = off ? (mid < 0 ? "▲ " : "▼ ") : "";
          return (
            <React.Fragment key={i}>
              {o.line && (
                <div style={{ position: "absolute", left: 0, right: 0, top: y - 3, height: 6, opacity: off ? 0 : 1,
                  backgroundImage: `repeating-linear-gradient(90deg, ${color} 0 36px, transparent 36px 64px)` }} />
              )}
              {!o.line && !off && (tiny ? (
                <div style={{ position: "absolute", left: x - 12, top: y - 12, width: 24, height: 24, borderRadius: 12, background: color, boxShadow: "0 0 0 6px rgba(255,255,255,0.35)" }} />
              ) : (
                <div style={{ position: "absolute", left: x - px, width: px * 2, top: Math.min(y, topY), height: px, display: "flex", alignItems: "center", justifyContent: "center", overflow: "visible" }}>
                  {o.render ? o.render(px) : <span style={{ fontSize: px * 0.88, lineHeight: 1, display: "block" }}>{o.emoji}</span>}
                </div>
              ))}
              {o.label && (
                <div style={{ position: "absolute", left: off ? (right ? W - EDGE - lw : EDGE) : lx, top: ly - (o.sub ? 46 : 32), width: lw, boxSizing: "border-box", padding: "8px 22px",
                  borderRadius: 18, background: "rgba(0,0,0,0.58)", borderLeft: `8px solid ${color}`, fontFamily: "Anton", color: "#fff", letterSpacing: 2 }}>
                  <div style={{ fontSize: size, lineHeight: 1.1, whiteSpace: "nowrap" }}>{arrow}{o.label}</div>
                  {o.sub && <div style={{ fontSize: sub, lineHeight: 1.1, color, whiteSpace: "nowrap" }}>{o.sub}</div>}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </Cam>
      {counter && (
        <Layer>
          <div style={{ position: "absolute", left: 0, right: 0, top: counterTop, textAlign: "center", fontFamily: "Anton", color: counterColor, letterSpacing: 3,
            WebkitTextStroke: "7px #000", paintOrder: "stroke fill" } as React.CSSProperties}>
            <div style={{ fontSize: 150, lineHeight: 1 }}>{fmtM(v)} m</div>
            {v >= 1000 && <div style={{ fontSize: 56, lineHeight: 1.2, color: "#fff" }}>{v >= 1e6 ? `${(v / 1000).toLocaleString("en-US", { maximumFractionDigits: 0 })}` : (v / 1000).toFixed(1)} km</div>}
          </div>
        </Layer>
      )}
    </div>
  );
};
