import React from "react";
import { Easing, Img, interpolate, staticFile } from "remotion";
import { ramp, pop } from "./anim";
import { PIC_TOP, GOLD, PAPER, clamp } from "./props";

// Dynamic-by-default helpers (0.9.0). Nothing here is required; a Scene opts in. The rule they serve: no beat is a still picture.
// Every beat has a camera, parallax layers or particles moving ALL the time, and the storyboard says what moves.
//   rig       one camera, many layers: each layer scrolls by its own parallax factor p (1 = near, 0.1 = far / sun).
//   CamPhoto  a photo that is filmed: push, tilt, roll, a faster foreground strip, drifting wisps, dust, a pulsing flare, a light sweep.
//   SlotCounter  a digit that flips through 1-2-3 and lands, then glows and can explode.
//   Wisps / Dust / Stars / Cloud  ambient movers for skies and photos.  mix / rnd  colour mix (hex or rgb()) and a seeded random.

export const rnd = (i: number, s = 1) => { const v = Math.sin(i * 91.7 + s * 17.3) * 43758.5453; return v - Math.floor(v); };
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const hex = (h: string) => (h.startsWith("rgb") ? (h.match(/[\d.]+/g) as string[]).map(Number) : [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)));
export const mix = (a: string, b: string, k: number) => { const x = hex(a), y = hex(b); return `rgb(${x.map((v, i) => Math.round(lerp(v, y[i], k))).join(",")})`; };

// ---- one camera, many layers -----------------------------------------------------------------------------------
// cam: z zoom (1 = wide), k 0..1 how far the camera has moved from the wide shot onto the screen focus (fx, fy),
// travel: px the world has scrolled for a layer with p = 1 (e.g. tower height px * fraction climbed).
// Anchor (ax, ay) is the world point the zoom is about at k = 0 (identity transform at z = 1, k = 0).
export type Rig = { z: number; k: number; travel: number; ax: number; ay: number; fx: number; fy: number };
export const rigTransform = (r: Rig, p: number) => {
  const zp = 1 + (r.z - 1) * p, pfx = r.ax, pfy = r.ay - r.travel * p;
  const sx = lerp(pfx, r.fx, r.k), sy = lerp(pfy, r.fy, r.k);
  return {
    css: `translate(${sx}px, ${sy}px) scale(${zp}) translate(${-pfx}px, ${-pfy}px)`,   // on a div with transformOrigin "0 0"
    project: (x: number, y: number) => ({ x: sx + (x - pfx) * zp, y: sy + (y - pfy) * zp, zp }),
  };
};

// ---- ambient movers ----------------------------------------------------------------------------------------------
export const Cloud = ({ x, y, w, o, col }: { x: number; y: number; w: number; o: number; col: string }) => (
  <div style={{ position: "absolute", left: x - w / 2, top: y - w * 0.18, width: w, height: w * 0.36, opacity: o, filter: "blur(10px)" }}>
    {[[0.3, 0.55, 0.5], [0.5, 0.4, 0.6], [0.72, 0.55, 0.45], [0.5, 0.7, 0.8]].map(([cx, cy, r], i) => (
      <div key={i} style={{ position: "absolute", left: `${(cx - r / 2) * 100}%`, top: `${(cy - r * 0.35) * 100}%`, width: `${r * 100}%`, height: `${r * 70}%`, borderRadius: "50%", background: col }} />
    ))}
  </div>
);
export const Stars = ({ t, w, h, n = 50 }: { t: number; w: number; h: number; n?: number }) => (
  <>{Array.from({ length: n }, (_, i) => (
    <div key={i} style={{ position: "absolute", left: rnd(i, 1) * w, top: rnd(i, 2) * h * 0.8, width: 2 + rnd(i, 3) * 3, height: 2 + rnd(i, 3) * 3, borderRadius: "50%", background: "#fff",
      opacity: 0.3 + 0.7 * Math.abs(Math.sin(t * (1 + rnd(i, 4) * 2) + i)) }} />
  ))}</>
);
// percent-positioned (put inside a box); drifting soft ellipses and rising motes
export const Wisps = ({ t, n = 9, color = "200,225,255" }: { t: number; n?: number; color?: string }) => (
  <>{Array.from({ length: n }, (_, i) => {
    const sp = 14 + rnd(i, 2) * 40, dir = i % 2 ? 1 : -1;
    const x = ((rnd(i, 1) * 140 - 20 + (dir * t * sp) / 6) % 160 + 160) % 160 - 30, y = 6 + rnd(i, 3) * 80, w = 40 + rnd(i, 4) * 40;
    return <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: `${w}%`, height: `${w * 0.28}%`, borderRadius: "50%",
      background: `radial-gradient(ellipse, rgba(${color},.30) 0%, rgba(${color},0) 70%)`, mixBlendMode: "screen", filter: "blur(6px)" }} />;
  })}</>
);
export const Dust = ({ t, n = 34 }: { t: number; n?: number }) => (
  <>{Array.from({ length: n }, (_, i) => {
    const x = (rnd(i, 5) * 100 + Math.sin(t * 0.6 + i) * 3) % 100, sp = 3 + rnd(i, 6) * 7, y = (((rnd(i, 7) * 100 - t * sp) % 100) + 100) % 100, r = 2 + rnd(i, 8) * 4;
    return <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: r, height: r, borderRadius: "50%", background: "#fff", opacity: 0.25 + 0.4 * rnd(i, 9), filter: "blur(.6px)" }} />;
  })}</>
);

// ---- a filmed photo ------------------------------------------------------------------------------------------------
// The photo is wider than the card shows (w x imgH, imgH = w * aspect), so the camera can TILT along it: v 0 = top, 1 = bottom.
// keys: camera at times (s zoom about the centre, v tilt, x pan fraction, roll deg), eased between. A roll needs s >= ~1.1 or
// the corners show. Loop: pass `settle` = [OUTRO_AT, back-to-frame-0 seconds]: the camera eases back to keys[0] so the last frame = frame 0.
// Parallax: a faster foreground strip (the bottom `fg` of the photo) travels against the tilt; flares are glow blobs (percent coords)
// that pulse; sweep = [a, b] runs a light band from the bottom to the top (use it with the tilt up the subject).
export type PhotoKey = { at: number; s: number; v: number; x?: number; roll?: number };
export const CamPhoto = ({ t, src, aspect, keys, w = 900, h = 970, top = PIC_TOP, op = 1, fg = 0.14, flares = [], sweep, wisps = true, dust = true, punch = [], settle, children }: {
  t: number; src: string; aspect: number; keys: PhotoKey[]; w?: number; h?: number; top?: number; op?: number; fg?: number;
  flares?: { x: number; y: number; w: number; h: number; color?: string; rate?: number }[]; sweep?: [number, number]; wisps?: boolean; dust?: boolean;
  punch?: number[]; settle?: [number, number]; children?: React.ReactNode;
}) => {
  const imgH = w * aspect, ts = keys.map((k) => k.at), end = keys[keys.length - 1].at;
  const f = (key: "s" | "v" | "x" | "roll", d: number) => interpolate(Math.min(t, end), ts, keys.map((k) => (k[key] ?? d)), { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const drift = Math.min(1, t / 0.6) * (t >= end ? 0 : 1);
  let c = { s: f("s", 1), v: Math.min(1, Math.max(0, f("v", 0) + Math.sin(t * 1.3) * 0.01 * drift)), x: f("x", 0) + Math.sin(t * 0.9) * 0.004 * drift, roll: f("roll", 0) + Math.sin(t * 0.8) * 0.25 * drift };
  if (settle && t >= settle[0]) {
    const k = ramp(t, settle[0], settle[0] + settle[1]), z = keys[0];
    c = { s: lerp(c.s, z.s, k), v: lerp(c.v, z.v, k), x: lerp(c.x, z.x ?? 0, k), roll: lerp(c.roll, z.roll ?? 0, k) };
  }
  const pk = punch.reduce((m, a) => Math.max(m, 0.12 * ramp(t, a, a + 0.06) * (1 - ramp(t, a + 0.06, a + 0.3))), 0);
  const sw = sweep ? ramp(t, sweep[0], sweep[1], 0, 1, Easing.linear) : 0;
  return (
    <div style={{ position: "absolute", left: 540 - w / 2, top, width: w, height: h, opacity: op, borderRadius: 18, overflow: "hidden", border: `14px solid ${PAPER}`, boxShadow: "0 30px 70px rgba(0,0,0,.6)", background: PAPER, boxSizing: "content-box" }}>
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#050b18" }}>
        <div style={{ position: "absolute", inset: 0, transform: `translate(${c.x * w}px, 0) rotate(${c.roll}deg) scale(${c.s + pk})`, transformOrigin: "50% 50%" }}>
          <div style={{ position: "absolute", left: 0, top: -(imgH - h) * c.v, width: w, height: imgH }}>
            <Img src={staticFile(src)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
            {wisps && <Wisps t={t} />}
            {flares.map((fl, i) => (
              <div key={i} style={{ position: "absolute", left: `${fl.x}%`, top: `${fl.y}%`, width: `${fl.w}%`, height: `${fl.h}%`, borderRadius: "50%", mixBlendMode: "screen",
                background: `radial-gradient(ellipse, ${fl.color ?? "rgba(150,205,255,.85)"} 0%, rgba(0,0,0,0) 68%)`, opacity: 0.22 + 0.3 * (0.5 + 0.5 * Math.sin(t * (fl.rate ?? 3.2) + i)) }} />
            ))}
            {sweep && sw > 0 && sw < 1 && <div style={{ position: "absolute", left: "20%", width: "62%", height: "9%", top: `${100 - sw * 108}%`, mixBlendMode: "screen",
              background: "linear-gradient(180deg, rgba(180,220,255,0), rgba(220,240,255,.85), rgba(180,220,255,0))",
              WebkitMaskImage: "linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent)", maskImage: "linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent)" }} />}
            {dust && <Dust t={t} />}
            {fg > 0 && (
              <div style={{ position: "absolute", inset: 0, WebkitMaskImage: `linear-gradient(180deg, transparent ${(1 - fg - 0.02) * 100}%, #000 ${(1 - fg + 0.05) * 100}%)`, maskImage: `linear-gradient(180deg, transparent ${(1 - fg - 0.02) * 100}%, #000 ${(1 - fg + 0.05) * 100}%)` }}>
                <Img src={staticFile(src)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: `translate(${Math.sin(t * 0.9) * 10}px, ${(c.v - 0.5) * 170}px) scale(1.16)`, transformOrigin: "50% 100%" }} />
              </div>
            )}
          </div>
        </div>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,.45) 100%)" }} />
      </div>
      {children}
    </div>
  );
};

// ---- a counter that flips like a slot machine ---------------------------------------------------------------------
// Digits cycle (default 1, 2, 3 repeated `laps` times), slow to a stop on the LAST digit at a + dur. Use `slotTicks(a, dur, laps)` for the
// tick sounds (one per flip). `hot` (seconds) turns it red and pulses it; `boom` (seconds) makes it swell and vanish (pair with Burst + Confetti + a flash).
export const slotTicks = (a: number, dur = 0.95, laps = 8, delay = 0.18) => Array.from({ length: laps }, (_, k) => a + delay + dur * (1 - Math.pow(1 - (k + 1) / laps, 1 / 3)));
export const SlotCounter = ({ t, a, x = 540, y = 790, w = 300, h = 400, digits = [1, 2, 3], laps = 8, dur = 0.95, hot, boom, color = GOLD }: {
  t: number; a: number; x?: number; y?: number; w?: number; h?: number; digits?: number[]; laps?: number; dur?: number; hot?: number; boom?: number; color?: string;
}) => {
  if (t < a) return null;
  const gone = boom === undefined ? 0 : ramp(t, boom, boom + 0.25);
  if (gone >= 1) return null;
  const cell = h * 0.85, n = digits.length;
  const u = ramp(t, a + 0.18, a + 0.18 + dur, 0, 1, Easing.out(Easing.cubic)), p = u * laps;
  const hh = hot === undefined ? 0 : ramp(t, hot, hot + 0.25) * (1 - gone);
  const scale = pop(t, a) * (1 + hh * 0.08 + 0.6 * gone) + hh * 0.04 * Math.sin(((hot ?? 0) - t) * 14);
  const strip = Array.from({ length: n * 4 }, (_, i) => digits[i % n]);
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, transform: `scale(${scale}) rotate(${-3 + 3 * u}deg)`, opacity: 1 - gone }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 46, overflow: "hidden", background: hh > 0.05 ? `rgb(${Math.round(20 + 190 * hh)},20,28)` : "#0d0d12",
        border: `10px solid ${hh > 0.05 ? "#fff" : color}`, boxShadow: `0 0 ${40 + 70 * hh}px ${hh > 0.05 ? "rgba(255,60,60,.9)" : "rgba(255,200,0,.55)"}, 0 30px 60px rgba(0,0,0,.6)` }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: (h - 20 - cell) / 2, filter: `blur(${(1 - u) * 9}px)`, transform: `translateY(${-(p % n) * cell}px)` }}>
          {strip.map((d, i) => <div key={i} style={{ height: cell, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Anton", fontSize: cell * 0.97, lineHeight: 1, color: hh > 0.1 ? "#fff" : color, textShadow: "0 8px 0 rgba(0,0,0,.45)" }}>{d}</div>)}
        </div>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,.65), rgba(0,0,0,0) 28%, rgba(0,0,0,0) 72%, rgba(0,0,0,.65))" }} />
      </div>
    </div>
  );
};
