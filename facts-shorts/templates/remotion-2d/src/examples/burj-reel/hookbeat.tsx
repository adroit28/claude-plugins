import React from "react";
import { Easing, Img, interpolate, staticFile } from "remotion";
import { at, OUTRO_AT, ramp, pop, clamp, PIC_TOP, GOLD, RED, PAPER, Layer, Sfx, Burst, Confetti, Flash, Glitch, Transition, Shake, Title3D, LAST_T } from "../../kit";

// Hook (0-10 s): a moving open. A flat photo cannot be split into real depth layers, so the depth comes from three tricks:
// the whole photo pushes and tilts as a camera; the bottom strip (palms) moves faster than the tower; cloud wisps, dust,
// a pulsing flare on the lit side and a light sweep up the tower all drift independently over it.

export const HK = {
  boring: at("L1", "boring"), three: at("L1", "3"), mind: at("L1", "mind-bending"), facts: at("L1", "facts"),
  third: at("L1", "third"), hosh: at("L1", "hosh"), oonchi: at("L1", "oonchi"), building: at("L1", "building", 1), uda: at("L1", "uda"),
};
const CARD_H = 970, CARD_W = 900, IMG_H = CARD_W * (737 / 415);
const HOOK_END = 9.9;

type Cam = { s: number; v: number; x: number; roll: number };  // v: 0 = look at the spire, 1 = look at the base
const K: [number, Cam][] = [
  [0.0, { s: 1.0, v: 0.05, x: 0, roll: 0 }],
  [HK.oonchi - 0.45, { s: 1.25, v: 1.0, x: 0, roll: 0 }],            // push in on the base
  [HK.oonchi + 0.65, { s: 1.25, v: 0.0, x: 0, roll: 0 }],            // tilt up the tower on "oonchi building"
  [3.25, { s: 1.15, v: 0.1, x: 0, roll: 0 }],
  [HK.boring - 0.12, { s: 1.0, v: 0.45, x: 0, roll: 0 }],            // pull back
  [HK.boring + 0.7, { s: 1.12, v: 0.4, x: 0, roll: -2.5 }],
  [HK.mind - 0.05, { s: 1.18, v: 0.35, x: 0, roll: -2 }],
  [HK.mind + 0.3, { s: 1.55, v: 0.0, x: 0, roll: 4 }],               // after the whip-pan: the crown of the tower
  [HK.hosh - 0.2, { s: 1.3, v: 0.15, x: 0, roll: 1 }],
  [HOOK_END, { s: 1.0, v: 0.05, x: 0, roll: 0 }],
];
const camRaw = (t: number): Cam => {
  const ts = K.map((k) => k[0]);
  const f = (key: keyof Cam) => interpolate(t, ts, K.map((k) => k[1][key]), { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const d = t >= HOOK_END ? 0 : Math.min(1, t / 0.6); // tiny handheld drift, zero at t=0
  return { s: f("s"), v: Math.min(1, Math.max(0, f("v") + Math.sin(t * 1.3) * 0.01 * d)), x: f("x") + Math.sin(t * 0.9) * 0.004 * d, roll: f("roll") + Math.sin(t * 0.8) * 0.25 * d };
};
const camAt = (t: number): Cam => {
  if (t < OUTRO_AT) return camRaw(Math.min(t, HOOK_END));
  const a = camRaw(HOOK_END), b = camRaw(0), k = ramp(t, OUTRO_AT, OUTRO_AT + 1.0);  // loop: ease back to the frame-0 state
  return { s: a.s + (b.s - a.s) * k, v: a.v + (b.v - a.v) * k, x: a.x + (b.x - a.x) * k, roll: a.roll + (b.roll - a.roll) * k };
};

const rnd = (i: number, s = 1) => { const v = Math.sin(i * 91.7 + s * 17.3) * 43758.5453; return v - Math.floor(v); };

const Wisps = ({ t }: { t: number }) => (
  <>
    {Array.from({ length: 9 }, (_, i) => {
      const sp = 14 + rnd(i, 2) * 40, dir = i % 2 ? 1 : -1;
      const x = ((rnd(i, 1) * 140 - 20 + (dir * t * sp) / 6) % 160 + 160) % 160 - 30; // percent
      const y = 6 + rnd(i, 3) * 80;
      const w = 40 + rnd(i, 4) * 40;
      return <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: `${w}%`, height: `${w * 0.28}%`, borderRadius: "50%",
        background: "radial-gradient(ellipse, rgba(200,225,255,.30) 0%, rgba(200,225,255,0) 70%)", mixBlendMode: "screen", filter: "blur(6px)" }} />;
    })}
  </>
);
const Dust = ({ t }: { t: number }) => (
  <>
    {Array.from({ length: 34 }, (_, i) => {
      const x = (rnd(i, 5) * 100 + Math.sin(t * 0.6 + i) * 3) % 100, sp = 3 + rnd(i, 6) * 7;
      const y = (((rnd(i, 7) * 100 - t * sp) % 100) + 100) % 100;
      const r = 2 + rnd(i, 8) * 4;
      return <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: r, height: r, borderRadius: "50%", background: "#fff", opacity: 0.25 + 0.4 * rnd(i, 9), filter: "blur(.6px)" }} />;
    })}
  </>
);

const HookCard = ({ t, op }: { t: number; op: number }) => {
  const c = camAt(t);
  const punch = 0.12 * Math.max(ramp(t, HK.boring, HK.boring + 0.06) * (1 - ramp(t, HK.boring + 0.06, HK.boring + 0.3)),
                                ramp(t, HK.uda, HK.uda + 0.08) * (1 - ramp(t, HK.uda + 0.08, HK.uda + 0.4)));
  const s = c.s + punch;
  const tr = `translate(${c.x * CARD_W}px, 0px) rotate(${c.roll}deg) scale(${s})`;
  const imgTop = -(IMG_H - CARD_H) * c.v;
  const pulse = 0.55 + 0.45 * Math.sin(t * 3.2);
  const sweep = ramp(t, HK.oonchi - 0.1, HK.oonchi + 0.75, 0, 1);
  const sweepOn = sweep > 0 && sweep < 1;
  const fgShift = (c.v - 0.5) * 170; // the bottom strip moves against the camera: nearer, so it travels more
  return (
    <div style={{ position: "absolute", left: 540 - CARD_W / 2, top: PIC_TOP, width: CARD_W, height: CARD_H, opacity: op, borderRadius: 18, overflow: "hidden",
      border: `14px solid ${PAPER}`, boxShadow: "0 30px 70px rgba(0,0,0,.6)", background: PAPER, boxSizing: "content-box" }}>
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#050b18" }}>
        <div style={{ position: "absolute", inset: 0, transform: tr, transformOrigin: "50% 50%" }}>
         <div style={{ position: "absolute", left: 0, top: imgTop, width: CARD_W, height: IMG_H }}>
          <Img src={staticFile("burj2.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
          <Wisps t={t} />
          {/* pulsing flare on the lit side and crown */}
          <div style={{ position: "absolute", left: "49%", top: "14%", width: "46%", height: "36%", borderRadius: "50%", mixBlendMode: "screen",
            background: "radial-gradient(ellipse, rgba(150,205,255,.85) 0%, rgba(150,205,255,0) 68%)", opacity: 0.22 + 0.3 * pulse }} />
          <div style={{ position: "absolute", left: "42%", top: "2%", width: "26%", height: "18%", borderRadius: "50%", mixBlendMode: "screen",
            background: "radial-gradient(ellipse, rgba(255,255,255,.9) 0%, rgba(255,255,255,0) 66%)", opacity: 0.15 + 0.35 * (0.5 + 0.5 * Math.sin(t * 5 + 1)) }} />
          {/* light sweep up the tower */}
          {sweepOn && <div style={{ position: "absolute", left: "20%", width: "62%", height: "9%", top: `${100 - sweep * 108}%`, mixBlendMode: "screen",
            background: "linear-gradient(180deg, rgba(180,220,255,0), rgba(220,240,255,.85), rgba(180,220,255,0))",
            WebkitMaskImage: "linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent)", maskImage: "linear-gradient(90deg, transparent, #000 25%, #000 75%, transparent)" }} />}
          <Dust t={t} />
          {/* foreground strip (palms): same photo, faster, faded into the base */}
          <div style={{ position: "absolute", inset: 0, WebkitMaskImage: "linear-gradient(180deg, transparent 84%, #000 91%)", maskImage: "linear-gradient(180deg, transparent 84%, #000 91%)" }}>
            <Img src={staticFile("burj2.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover",
              transform: `translate(${Math.sin(t * 0.9) * 10}px, ${fgShift}px) scale(1.16)`, transformOrigin: "50% 100%" }} />
          </div>
         </div>
        </div>
        {/* vignette */}
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,.45) 100%)" }} />
      </div>
    </div>
  );
};

// slot machine "3": 1-2-3 flip through three laps, lands on 3, glows red on "third", explodes after "hosh".
const SLOT_A = HK.three, SLOT_D = 0.95, LAPS = 8;
const SLOT_X = 540, SLOT_Y = 790, SW = 300, SH = 400, CELL = 340;
const Slot = ({ t }: { t: number }) => {
  if (t < SLOT_A) return null;
  const boom = HK.uda + 0.02;
  const gone = ramp(t, boom, boom + 0.25);
  if (gone >= 1) return null;
  const u = ramp(t, SLOT_A + 0.18, SLOT_A + 0.18 + SLOT_D, 0, 1, Easing.out(Easing.cubic));
  const p = u * LAPS;                       // digit units; lands at 8 -> digit index 2 -> "3"
  const vel = Math.max(0, 1 - u) * 1;       // for blur
  const base = pop(t, SLOT_A);
  const hot = ramp(t, HK.third, HK.third + 0.25) * (1 - gone);
  const wob = hot * 0.04 * Math.sin((t - HK.third) * 14);
  const scale = base * (1 + hot * 0.08 + 0.6 * ramp(t, boom, boom + 0.25)) + wob;
  const off = -(p % 3) * CELL;
  const digit = (n: number) => <div key={n} style={{ height: CELL, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Anton", fontSize: 330, lineHeight: 1,
    color: hot > 0.1 && n === 3 ? "#fff" : GOLD, textShadow: "0 8px 0 rgba(0,0,0,.45)" }}>{n}</div>;
  return (
    <div style={{ position: "absolute", left: SLOT_X - SW / 2, top: SLOT_Y - SH / 2, width: SW, height: SH, transform: `scale(${scale}) rotate(${-3 + 3 * u}deg)`, opacity: 1 - gone }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 46, overflow: "hidden", background: hot > 0.05 ? `rgb(${Math.round(20 + 190 * hot)},20,28)` : "#0d0d12",
        border: `10px solid ${hot > 0.05 ? "#fff" : GOLD}`, boxShadow: `0 0 ${40 + 70 * hot}px ${hot > 0.05 ? "rgba(255,60,60,.9)" : "rgba(255,200,0,.55)"}, 0 30px 60px rgba(0,0,0,.6)` }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: (SH - 20 - CELL) / 2, filter: `blur(${vel * 9}px)`, transform: `translateY(${off + CELL * 3}px)` }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: -CELL * 3 }}>{[1, 2, 3, 1, 2, 3, 1, 2, 3, 1].map((n, i) => <div key={i}>{digit(n)}</div>)}</div>
        </div>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,.65), rgba(0,0,0,0) 28%, rgba(0,0,0,0) 72%, rgba(0,0,0,.65))" }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 4, background: "rgba(255,255,255,.18)" }} />
      </div>
    </div>
  );
};
const slotTicks = Array.from({ length: LAPS }, (_, k) => SLOT_A + 0.18 + SLOT_D * (1 - Math.pow(1 - (k + 1) / LAPS, 1 / 3)));

export const Hook = ({ t }: { t: number }) => {
  const loopIn = ramp(t, OUTRO_AT, OUTRO_AT + 0.4);
  const op = Math.min(1, 1 - ramp(t, 10.0, 10.35) + loopIn);
  const inHook = t < 10.4 || t >= OUTRO_AT;
  return (
    <>
      <Sfx at={0.02} src="whoosh" vol={0.22} />
      <Sfx at={HK.oonchi - 0.2} src="revwhoosh" vol={0.22} />
      <Sfx at={HK.boring + 0.02} src="glitch" vol={0.28} />
      <Sfx at={HK.boring + 0.05} src="stamp" vol={0.3} />
      <Sfx at={HK.mind - 0.1} src="whoosh" vol={0.3} />
      {slotTicks.map((s, i) => <Sfx key={i} at={s} src="tick" vol={0.2} />)}
      <Sfx at={6.75} src="riser" vol={0.22} />
      <Sfx at={HK.uda + 0.02} src="boom" vol={0.35} />
      <Sfx at={HK.uda + 0.05} src="confetti" vol={0.25} />
      {inHook && (
        <Shake t={t} at={HK.boring} amp={16}>
          <Shake t={t} at={HK.uda} amp={24}>
            <HookCard t={t} op={op} />
            <Title3D t={t} accent="BURJ KHALIFA" rest="BORING?" opacity={op} sweeps={[0.4, HK.mind - 0.3, LAST_T - 0.9]} />
            <Layer opacity={1 - ramp(t, 10.0, 10.3)}>
              <Slot t={t} />
              <Burst t={t} a={HK.uda + 0.02} x={SLOT_X} y={SLOT_Y} n={16} dur={0.6} speed={1100} color={GOLD} />
              <Burst t={t} a={HK.uda + 0.08} x={SLOT_X} y={SLOT_Y} n={12} dur={0.6} speed={800} color={RED} />
              <Confetti t={t} a={HK.uda + 0.05} x={SLOT_X} y={SLOT_Y} />
              <Glitch t={t} a={HK.boring} b={HK.boring + 0.62} text="BORING?" top={640} color={RED} size={230} />
            </Layer>
          </Shake>
        </Shake>
      )}
      <Flash t={t} at={HK.boring} color="#ff2a2a" peak={0.3} dur={0.25} />
      <Flash t={t} at={HK.mind - 0.02} color="#ffffff" peak={0.55} dur={0.3} />
      <Flash t={t} at={HK.uda + 0.02} color="#ffffff" peak={0.7} dur={0.4} />
      <Transition kind="whip" at={HK.mind} dur={0.4} color={GOLD} />
    </>
  );
};
