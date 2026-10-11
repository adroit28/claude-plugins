import React from "react";
import { Easing, interpolate } from "remotion";
import { at, lineStart, ramp, clamp, PIC_TOP, Layer, Sfx, Badge, Stamp, Shake, LightLeakCut, Flash, Burst } from "../../kit";
import { Burj } from "./Burj";
import { Bed } from "../../kit/audio";

// Fact 1 (10.4-21.7 s): a camera ride. Low-angle skyline at sunset, then a glass cab climbs the Burj with the camera riding along
// (skyline drops, horizon curves, clouds pass, speed lines) and the sun comes back above the horizon with a lens flare.
// Layers share ONE camera (zoom z, focus fraction f up the tower, ride-in k) but scroll at different parallax p (1 near ... 0.08 sun).

export const F1 = {
  l2: lineStart("L2"), baar: at("L2", "baar"), zameen: at("L2", "Zameen"), dhalte: at("L2", "dhalte"), phir: at("L2", "phir"),
  super: at("L2", "superfast"), elev: at("L2", "elevator"), bhago: at("L2", "bhago"), boom: at("L2", "boom"), suraj: at("L2", "Suraj", 2), l3: lineStart("L3"),
};
const PW = 960, PH = 940, PX = 60, PY = PIC_TOP + 10;
const G = 700, H0 = 690, XT = 650, FX = 480, FY = 600;
export const rnd = (i: number, s = 1) => { const v = Math.sin(i * 91.7 + s * 17.3) * 43758.5453; return v - Math.floor(v); };
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const hex = (h: string) => (h.startsWith("rgb") ? (h.match(/[\d.]+/g) as string[]).map(Number) : [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)));
export const mix = (a: string, b: string, k: number) => { const x = hex(a), y = hex(b); return `rgb(${x.map((v, i) => Math.round(lerp(v, y[i], k))).join(",")})`; };
const io = Easing.inOut(Easing.cubic);

const RIDE_A = F1.elev + 0.1, RIDE_B = F1.boom;       // the climb
const ZIN_A = F1.phir + 0.1, ZIN_B = F1.elev + 0.1;    // zoom in on the base
const SET_A = F1.zameen, SET_B = F1.phir - 0.1;        // the sun goes down
const SUN_UP = F1.suraj;                               // sun is back

const cam = (t: number) => {
  const k = ramp(t, ZIN_A, ZIN_B);
  const zoomed = 1 + 2.15 * ramp(t, ZIN_A, ZIN_B, 0, 1, io) - 1.5 * ramp(t, F1.boom, F1.suraj + 0.9, 0, 1, io);
  const wide = 1 + 0.16 * ramp(t, F1.l2, ZIN_A, 0, 1, Easing.linear);  // slow push on the street view
  const z = t < ZIN_A ? wide : zoomed + (wide - 1) * (1 - ramp(t, ZIN_A, ZIN_B));
  const climb = ramp(t, RIDE_A, RIDE_B, 0, 1, Easing.bezier(0.5, 0.05, 0.6, 1));
  const f = 0.03 + 0.67 * climb + 0.12 * ramp(t, RIDE_B, F1.l3 - 0.2, 0, 1, io);
  const speed = interpolate(t, [RIDE_A, RIDE_A + 0.35, RIDE_B - 0.3, RIDE_B + 0.1], [0, 1, 1, 0], clamp);
  return { z, f, k, speed };
};
// screen position of a world point (x, y) on a layer with parallax p
const proj = (t: number, p: number, x: number, y: number) => {
  const c = cam(t);
  const zp = 1 + (c.z - 1) * p, pfx = XT, pfy = G - H0 * c.f * p;
  const sx = lerp(pfx, FX, c.k), sy = lerp(pfy, FY, c.k);
  return { x: sx + (x - pfx) * zp, y: sy + (y - pfy) * zp, zp };
};
const layerTf = (t: number, p: number) => {
  const c = cam(t), zp = 1 + (c.z - 1) * p, pfx = XT, pfy = G - H0 * c.f * p;
  const sx = lerp(pfx, FX, c.k), sy = lerp(pfy, FY, c.k);
  return `translate(${sx}px, ${sy}px) scale(${zp}) translate(${-pfx}px, ${-pfy}px)`;
};

const dark = (t: number) => {
  const set = ramp(t, SET_A, SET_B, 0, 1, Easing.inOut(Easing.quad));
  return set * (1 - 0.7 * ramp(t, SUN_UP, SUN_UP + 1.0));
};

// ---- skyline ------------------------------------------------------------------------------------
type Bd = { x: number; w: number; h: number; kind?: "spire" | "sail" | "tri" };
const mkFar = (): Bd[] => Array.from({ length: 36 }, (_, i) => ({ x: -40 + i * 30 + rnd(i) * 8, w: 22 + rnd(i, 2) * 22, h: 30 + rnd(i, 3) * 120 }));
const mkMid = (): Bd[] => {
  const out: Bd[] = [];
  let x = -30;
  for (let i = 0; i < 18; i++) { const w = 46 + rnd(i, 4) * 40; out.push({ x, w, h: 70 + rnd(i, 5) * 200 }); x += w - 6 + rnd(i, 6) * 14; }
  out.push({ x: 120, w: 36, h: 330, kind: "tri" }, { x: 168, w: 36, h: 280, kind: "tri" });  // twin triangular-topped towers
  out.push({ x: 800, w: 90, h: 190, kind: "sail" });                                           // a sail-shaped hotel
  return out;
};
const FAR = mkFar(), MID = mkMid();
const Skyline = ({ bs, base, color, lights, t, win }: { bs: Bd[]; base: number; color: string; lights: number; t: number; win: string }) => (
  <svg width={PW + 200} height={500} viewBox={`-100 ${base - 480} ${PW + 200} 500`} style={{ position: "absolute", left: -100, top: base - 480, overflow: "visible" }}>
    {bs.map((b, i) => {
      const top = base - b.h;
      const body = b.kind === "tri" ? `M ${b.x} ${base} L ${b.x} ${top + 40} L ${b.x + b.w / 2} ${top} L ${b.x + b.w} ${top + 40} L ${b.x + b.w} ${base} Z`
        : b.kind === "sail" ? `M ${b.x} ${base} Q ${b.x - 10} ${top + 70} ${b.x + 18} ${top} Q ${b.x + b.w + 20} ${top + 60} ${b.x + b.w} ${base} Z`
        : `M ${b.x} ${base} L ${b.x} ${top} L ${b.x + b.w} ${top} L ${b.x + b.w} ${base} Z`;
      const n = Math.floor(b.h / 14);
      return (
        <g key={i}>
          <path d={body} fill={color} />
          {lights > 0 && Array.from({ length: n }, (_, j) => (rnd(i * 31 + j, 8) > 0.55 ? (
            <rect key={j} x={b.x + 5 + (j % 3) * (b.w / 3.2)} y={top + 50 + (j * 11) % Math.max(10, b.h - 56)} width="4" height="5" fill={win}
              opacity={lights * (0.5 + 0.5 * Math.sin(t * 2 + i + j))} />) : null))}
        </g>
      );
    })}
  </svg>
);

// ---- clouds that the ride passes through -------------------------------------------------------------
const CLOUDS = [{ f: 0.22, x: 120 }, { f: 0.3, x: 770 }, { f: 0.4, x: 380 }, { f: 0.5, x: 900 }, { f: 0.58, x: 150 }, { f: 0.66, x: 700 }, { f: 0.78, x: 300 }];
export const Cloud = ({ x, y, w, o, col }: { x: number; y: number; w: number; o: number; col: string }) => (
  <div style={{ position: "absolute", left: x - w / 2, top: y - w * 0.18, width: w, height: w * 0.36, opacity: o, filter: "blur(10px)" }}>
    {[[0.3, 0.55, 0.5], [0.5, 0.4, 0.6], [0.72, 0.55, 0.45], [0.5, 0.7, 0.8]].map(([cx, cy, r], i) => (
      <div key={i} style={{ position: "absolute", left: `${(cx - r / 2) * 100}%`, top: `${(cy - r * 0.35) * 100}%`, width: `${r * 100}%`, height: `${r * 70}%`, borderRadius: "50%", background: col }} />
    ))}
  </div>
);

const Palm = ({ x, y, s, flip, t }: { x: number; y: number; s: number; flip?: boolean; t: number }) => (
  <svg width="300" height="420" viewBox="0 0 300 420" style={{ position: "absolute", left: x - 150 * s, top: y - 420 * s, transform: `scale(${s}${flip ? ", " + s : ""})`, transformOrigin: "50% 100%" }}>
    <g transform={flip ? "translate(300 0) scale(-1 1)" : undefined}>
      <path d="M 150 420 C 140 300 160 220 175 130" stroke="#0b0912" strokeWidth="13" fill="none" strokeLinecap="round" />
      {Array.from({ length: 9 }, (_, i) => {
        const a = -170 + i * 22 + Math.sin(t * 1.4 + i) * 3, L = 110 + (i % 3) * 18;
        const r = (a * Math.PI) / 180;
        const ex = 175 + Math.cos(r) * L, ey = 130 + Math.sin(r) * L * 0.8 + 40;
        return <path key={i} d={`M 175 130 Q ${175 + Math.cos(r) * L * 0.5} ${130 + Math.sin(r) * L * 0.6 - 25} ${ex} ${ey}`} stroke="#0b0912" strokeWidth="7" fill="none" strokeLinecap="round" />;
      })}
    </g>
  </svg>
);

const Sun = ({ t }: { t: number }) => {
  const d = dark(t);
  const worldY = lerp(210, 640, ramp(t, SET_A, SET_B, 0, 1, Easing.inOut(Easing.quad)));
  const lift = 150 * ramp(t, SUN_UP - 0.2, SUN_UP + 1.3, 0, 1, Easing.out(Easing.cubic));
  const p = proj(t, 0.08, 230, worldY);
  const col = mix("#fff3b0", "#ff6a13", d);
  const r = 78 * (1 + 0.35 * d);
  return <div style={{ position: "absolute", left: p.x - r, top: p.y - lift - r, width: r * 2, height: r * 2, borderRadius: "50%", background: col, boxShadow: `0 0 ${110 + 60 * d}px ${50 + 30 * d}px ${mix("#fff3b0", "#ff6a13", d)}` }} />;
};

const Flare = ({ t }: { t: number }) => {
  const a = ramp(t, SUN_UP, SUN_UP + 0.25) * (1 - ramp(t, F1.l3 - 0.5, F1.l3 - 0.1));
  if (a <= 0) return null;
  const lift = 150 * ramp(t, SUN_UP - 0.2, SUN_UP + 1.3, 0, 1, Easing.out(Easing.cubic));
  const s = proj(t, 0.08, 230, 640);
  const sx = s.x, sy = s.y - lift;
  const pulse = 0.8 + 0.2 * Math.sin(t * 9);
  const gx = FX - sx, gy = FY - sy;
  return (
    <Layer opacity={a}>
      <div style={{ position: "absolute", left: sx - 600, top: sy - 10, width: 1200, height: 20, background: "linear-gradient(90deg, transparent, rgba(255,230,160,.9), transparent)", filter: "blur(3px)", opacity: pulse, mixBlendMode: "screen" }} />
      <div style={{ position: "absolute", left: sx - 5, top: sy - 300, width: 10, height: 600, background: "linear-gradient(180deg, transparent, rgba(255,230,160,.5), transparent)", filter: "blur(3px)", mixBlendMode: "screen" }} />
      {[0.35, 0.6, 0.85, 1.15, 1.5].map((k, i) => (
        <div key={i} style={{ position: "absolute", left: sx + gx * k - 28 * (1 + i * 0.3), top: sy + gy * k - 28 * (1 + i * 0.3), width: 56 * (1 + i * 0.3), height: 56 * (1 + i * 0.3), borderRadius: "50%", mixBlendMode: "screen",
          background: `radial-gradient(circle, ${["rgba(255,200,120,.5)", "rgba(160,220,255,.4)", "rgba(255,150,200,.35)", "rgba(200,255,200,.3)", "rgba(255,240,180,.35)"][i]}, transparent 70%)` }} />
      ))}
    </Layer>
  );
};

export const SunPanel = ({ t }: { t: number }) => {
  const c = cam(t), d = dark(t);
  const intro = ramp(t, F1.l2, F1.l2 + 0.3), outro = 1 - ramp(t, F1.l3 - 0.45, F1.l3 - 0.1);
  if (intro * outro <= 0) return null;
  const alt = c.f;
  const skyTop = mix(mix("#2b8cff", "#150b30", d), "#07102e", Math.min(1, alt * 0.9) * (1 - 0.7 * ramp(t, SUN_UP, SUN_UP + 1.0)));
  const skyMid = mix(mix("#8cc8ff", "#6a2a66", d), "#27306d", Math.min(1, alt * 0.8) * (1 - 0.6 * ramp(t, SUN_UP, SUN_UP + 1.0)));
  const skyLow = mix(mix("#ffe3a3", "#ff7a2a", d), "#ff8a3d", 0);
  const curve = 160 * alt;
  const lights = Math.min(1, d * 1.4);
  const shown = (p: number, x: number, w: number) => ({ p, x, w });
  void shown;
  return (
    <Layer opacity={intro * outro}>
      <div style={{ position: "absolute", left: PX, top: PY, width: PW, height: PH, borderRadius: 30, overflow: "hidden", border: "6px solid rgba(255,255,255,.85)", boxShadow: "0 30px 70px rgba(0,0,0,.55)",
        background: `linear-gradient(180deg, ${skyTop} 0%, ${skyMid} 50%, ${skyLow} 78%)`, boxSizing: "content-box" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: PW, height: PH, overflow: "hidden", transform: `rotate(${1.3 * Math.sin(t * 7) * c.speed}deg) scale(${1 + 0.02 * c.speed})` }}>
          {/* stars once it is dark */}
          {d > 0.5 && Array.from({ length: 40 }, (_, i) => <div key={i} style={{ position: "absolute", left: rnd(i, 11) * PW, top: rnd(i, 12) * PH * 0.5, width: 3, height: 3, borderRadius: "50%", background: "#fff",
            opacity: (d - 0.5) * 2 * (0.4 + 0.6 * Math.abs(Math.sin(t * 2 + i))) }} />)}
          {/* sun, then clouds (far), skyline layers, horizon ground, Burj, near clouds, street, palms */}
          <Sun t={t} />
          <div style={{ position: "absolute", inset: 0, transformOrigin: "0 0", transform: layerTf(t, 0.22) }}>
            <Skyline bs={FAR} base={G - 20} color={mix("#6b78a0", "#2a1d42", d)} lights={lights * 0.6} t={t} win="#ffd27a" />
            <svg width={PW + 1600} height={900} style={{ position: "absolute", left: -800, top: G - 20, overflow: "visible" }}>
              <path d={`M -400 0 Q ${PW / 2 + 800} ${-curve * 2.2} ${PW + 1200} 0 L ${PW + 1200} 900 L -400 900 Z`} fill={mix("#3a3d5c", "#150c24", d)} />
              {alt > 0.1 && Array.from({ length: 90 }, (_, i) => <circle key={i} cx={-200 + rnd(i, 21) * (PW + 1000)} cy={20 + rnd(i, 22) * 300} r="2.2" fill="#ffd27a" opacity={Math.min(1, lights + 0.3) * (0.4 + 0.6 * Math.abs(Math.sin(t * 3 + i)))} />)}
            </svg>
          </div>
          {CLOUDS.map((cl, i) => {
            const p = proj(t, 1.2, cl.x + Math.sin(t * 0.5 + i) * 30 + t * (i % 2 ? 6 : -6), G - H0 * cl.f);
            return <Cloud key={i} x={p.x} y={p.y} w={380 * p.zp * 0.55} o={0.55 * (1 - 0.35 * d)} col={mix("#ffffff", "#e7a9c9", d * 0.9)} />;
          })}
          <div style={{ position: "absolute", inset: 0, transformOrigin: "0 0", transform: layerTf(t, 0.55) }}>
            <Skyline bs={MID} base={G} color={mix("#4a5578", "#161129", d)} lights={lights} t={t} win="#ffe3a0" />
          </div>
          {/* the Burj */}
          <div style={{ position: "absolute", inset: 0, transformOrigin: "0 0", transform: layerTf(t, 1) }}>
            <div style={{ position: "absolute", left: XT - H0 * 0.12, top: G - H0 }}>
              <Burj id="s1" h={H0} t={t} glass={["#cfe6ff", "#4d7fb0"]} rim={d > 0.25 ? "#ff9d4d" : undefined} glow={d * 0.6}
                lit={(f, i) => Math.min(1, 0.15 + d * 0.9) * (0.4 + 0.6 * ((i * 7) % 5) / 4)}
                style={{ filter: `brightness(${1 - 0.28 * d})` }} />
            </div>
            <div style={{ position: "absolute", left: -200, right: -200, top: G, height: 900, background: mix("#2c2a4a", "#0d0a18", d) }} />
          </div>
          {/* rails + cab (screen fixed once we ride) */}
          {c.k > 0.45 && (
            <Layer opacity={ramp(c.k, 0.45, 0.9)}>
              <div style={{ position: "absolute", left: FX - 46, top: 0, width: 5, height: PH, background: "rgba(255,255,255,.35)" }} />
              <div style={{ position: "absolute", left: FX + 41, top: 0, width: 5, height: PH, background: "rgba(255,255,255,.35)" }} />
              <div style={{ position: "absolute", left: FX - 58, top: FY - 90 + Math.sin(t * 11) * 3 * c.speed, width: 116, height: 160, borderRadius: 22,
                background: "linear-gradient(160deg, rgba(220,245,255,.85), rgba(120,170,220,.55))", border: "5px solid #fff", boxShadow: "0 0 50px 10px rgba(255,235,170,.7), 0 18px 40px rgba(0,0,0,.5)" }}>
                <div style={{ position: "absolute", left: 14, right: 14, top: 14, bottom: 14, borderRadius: 14, background: "radial-gradient(circle at 50% 30%, #fff3c4, #ffc861)" }} />
                <div style={{ position: "absolute", left: "50%", top: 14, bottom: 14, width: 4, background: "rgba(255,255,255,.7)" }} />
              </div>
            </Layer>
          )}
          {/* street level: lamp glows and palms zoom past on the nearest layer */}
          <div style={{ position: "absolute", inset: 0, transformOrigin: "0 0", transform: layerTf(t, 1.3), opacity: 1 - ramp(c.k, 0, 0.5) }}>
            <Palm x={90} y={G + 215} s={1.4} t={t} /><Palm x={860} y={G + 230} s={1.25} flip t={t} /><Palm x={20} y={G + 250} s={0.9} t={t} />
            {[170, 420, 760].map((x, i) => <div key={i} style={{ position: "absolute", left: x, top: G + 60, width: 10, height: 150, background: "#0b0912" }}><div style={{ position: "absolute", left: -18, top: -14, width: 46, height: 46, borderRadius: "50%", background: "radial-gradient(circle, #ffd27a, transparent 70%)", opacity: 0.4 + 0.6 * d }} /></div>)}
          </div>
          {/* speed lines */}
          {c.speed > 0 && Array.from({ length: 26 }, (_, i) => (
            <div key={i} style={{ position: "absolute", left: rnd(i, 31) * PW, width: 3 + rnd(i, 32) * 4, height: 220 + rnd(i, 33) * 300, borderRadius: 3, background: "#fff", opacity: 0.45 * c.speed * (0.4 + 0.6 * rnd(i, 34)),
              top: ((t * (3200 + rnd(i, 35) * 2200) + i * 237) % (PH + 600)) - 400 }} />
          ))}
          <Flare t={t} />
          {/* warm sunset grade over everything at dusk */}
          <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 70% 80%, rgba(255,120,40,.25), transparent 60%)", opacity: d }} />
        </div>
      </div>
    </Layer>
  );
};

export const Fact1 = ({ t }: { t: number }) => (
  <>
    <Sfx at={F1.l2 - 0.25} src="whoosh" vol={0.3} />
    <Sfx at={F1.l2} src="stamp" vol={0.35} />
    <Bed src="air" at={F1.l2} b={F1.l3 - 0.2} vol={(tt) => 0.12 * ramp(tt, F1.l2, F1.l2 + 0.8) * (1 - ramp(tt, F1.l3 - 0.9, F1.l3 - 0.2)) * (1 + 0.8 * cam(tt).speed)} />
    <Sfx at={F1.phir + 0.35} src="riser" vol={0.22} />
    <Sfx at={F1.elev - 0.05} src="revwhoosh" vol={0.28} />
    <Sfx at={F1.elev + 0.1} src="ding" vol={0.2} />
    <Sfx at={F1.elev + 0.7} src="whoosh" vol={0.22} />
    <Sfx at={F1.elev + 1.3} src="whoosh" vol={0.22} />
    <Sfx at={F1.boom + 0.22} src="boom" vol={0.3} />
    <Sfx at={F1.suraj + 0.12} src="sparkle" vol={0.3} />
    <SunPanel t={t} />
    <Stamp t={t} a={F1.l2} text="FACT 1" until={F1.l2 + 1.7} top={700} />
    {t >= F1.dhalte && t < F1.suraj - 0.1 && <Badge t={t} a={F1.dhalte} text="SUNSET #1" x={100} y={380} size={95} until={F1.suraj - 0.25} />}
    {t >= F1.suraj && t < F1.l3 - 0.15 && <Badge t={t} a={F1.suraj} text="SUNSET #2" x={100} y={380} size={95} until={F1.l3 - 0.3} />}
    <Shake t={t} at={F1.boom + 0.2} amp={0}><span /></Shake>
    <Flash t={t} at={F1.suraj} color="#fff3c4" peak={0.55} dur={0.45} />
    <LightLeakCut at={F1.suraj} seed={2} hue={35} />
  </>
);
