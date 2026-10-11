import React from "react";
import { Easing, interpolate } from "remotion";
import { at, lineStart, ramp, pop, clamp, PIC_TOP, GOLD, Layer, Sfx, Stamp, Emoji, Shake, LightLeakCut, Flash, Burst } from "../../kit";
import { Burj } from "./Burj";
import { Bed } from "../../kit/audio";
import { Cloud, mix, rnd } from "./sunbeat";

// Fact 2 (21.8-30.6 s): split screen, explained top to bottom. Left: the Burj with a marker that rides from the bottom to the top
// (camera follows: heat shimmer and sun at the bottom, clouds pass, sky goes red -> blue). Right: a temperature scale whose mercury
// rises to the hot reading, then drops while the marker climbs; a bracket joins the two readings and "6°" pops.

export const F2 = {
  l3: lineStart("L3"), neeche: at("L3", "Neeche"), garmi: at("L3", "garmi"), paseene: at("L3", "paseene"), top: at("L3", "top"),
  pahunchte: at("L3", "pahunchte"), six: at("L3", "6"), thanda: at("L3", "thanda"), l4: lineStart("L4"),
};
const PX = 60, PY = PIC_TOP + 10, SW = 440, SH = 920, GAP = 40;       // two sub-panels
const LX = PX + 16, RX = PX + 16 + SW + GAP;                              // frame x of each sub-panel
const TH = 1300, TB = 1300, MK_Y = 610, TX = 300;                         // tower height, tower-base world y, marker screen y, tower centre x (sub-panel coords)
const CLIMB_A = F2.top - 0.1, CLIMB_B = F2.six - 0.2;
const io = Easing.inOut(Easing.cubic);
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

const climb = (t: number) => ramp(t, CLIMB_A, CLIMB_B, 0, 1, Easing.bezier(0.4, 0, 0.5, 1));
const heatIn = (t: number) => ramp(t, F2.neeche - 0.4, F2.garmi + 0.2);
// mercury (0 = bulb, 1 = hot reading) rises, then falls to the cool reading
const HOT_Y = 170, COOL_Y = 470, BULB_Y = 760, TICK = 50;                 // 6 ticks between the readings = 6 degrees
const mercY = (t: number) => {
  const up = ramp(t, F2.neeche, F2.garmi + 0.5, 0, 1, Easing.out(Easing.cubic));
  const down = ramp(t, CLIMB_A + 0.15, F2.six + 0.15, 0, 1, io);
  const jit = t > F2.garmi + 0.5 && t < CLIMB_A ? Math.sin(t * 38) * 2.5 : 0;
  return (t < CLIMB_A + 0.15 ? lerp(BULB_Y - 20, HOT_Y, up) : lerp(HOT_Y, COOL_Y, down)) + jit;
};
const dropTimes = Array.from({ length: 6 }, (_, k) => {
  const target = (k + 1) / 6; // solve ease inOut cubic inverse numerically
  let lo = 0, hi = 1;
  for (let i = 0; i < 24; i++) { const m = (lo + hi) / 2; if (io(m) < target) lo = m; else hi = m; }
  return CLIMB_A + 0.15 + lo * (F2.six + 0.15 - (CLIMB_A + 0.15));
});

const Shimmer = ({ t, a }: { t: number; a: number }) => {
  if (a <= 0) return null;
  return (
    <svg width={SW} height={SH} style={{ position: "absolute", left: 0, top: 0 }} opacity={a}>
      {Array.from({ length: 9 }, (_, i) => {
        const y = 560 + i * 38, amp = 9 + i, ph = t * 5 + i * 1.7;
        const pts = Array.from({ length: 23 }, (_, j) => `${j * 20},${y + Math.sin(ph + j * 0.9) * amp * 0.5}`);
        return <polyline key={i} points={pts.join(" ")} fill="none" stroke="rgba(255,200,120,.35)" strokeWidth={5 + (i % 3) * 2} strokeLinecap="round" />;
      })}
      {Array.from({ length: 12 }, (_, i) => {
        const x = 30 + i * 36 + Math.sin(t * 3 + i) * 8, y = 880 - ((t * (90 + i * 13) + i * 97) % 520);
        return <path key={`w${i}`} d={`M ${x} ${y} q 8 -16 0 -32 q -8 -16 0 -32`} fill="none" stroke="rgba(255,230,170,.4)" strokeWidth="4" />;
      })}
    </svg>
  );
};

const TowerView = ({ t }: { t: number }) => {
  const c = climb(t);
  const f = 0.05 + 0.66 * c;
  const fy = TB - TH * f;                       // world y at the marker
  const hot = 1 - c;                            // 1 at the bottom, 0 at the top
  const skyTop = mix(mix("#ff5a2a", "#1d5fc0", c), "#0a0a1a", 0), skyBot = mix("#ffb04a", "#8fcbff", c);
  const toScreen = (wy: number, p: number) => MK_Y + (wy - fy) * p;
  const CL = [{ wy: 1020, x: 90 }, { wy: 880, x: 380 }, { wy: 760, x: 150 }, { wy: 640, x: 400 }, { wy: 520, x: 90 }, { wy: 420, x: 360 }, { wy: 300, x: 130 }];
  const sunY = toScreen(900, 0.1) - 160;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: SW, height: SH, borderRadius: 26, overflow: "hidden", border: "6px solid rgba(255,255,255,.85)", boxSizing: "content-box",
      background: `linear-gradient(180deg, ${skyTop}, ${skyBot})`, boxShadow: "0 24px 60px rgba(0,0,0,.55)" }}>
      <div style={{ position: "absolute", left: 40, top: sunY, width: 150, height: 150, borderRadius: "50%", background: mix("#fff6c8", "#fffdf2", c),
        boxShadow: `0 0 ${120 * hot + 30}px ${50 * hot + 10}px rgba(255,220,120,${0.35 + 0.5 * hot})`, opacity: 0.35 + 0.65 * hot }} />
      {CL.map((cl, i) => <Cloud key={i} x={cl.x + Math.sin(t * 0.6 + i) * 20 + (t - F2.l3) * (i % 2 ? 7 : -7)} y={toScreen(cl.wy, 1.35)} w={260} o={0.7} col="#ffffff" />)}
      {/* ground + tower */}
      <div style={{ position: "absolute", left: 0, right: 0, top: toScreen(TB, 1), height: 1200, background: mix("#5a2a1a", "#1b1b30", 0) }} />
      <div style={{ position: "absolute", left: TX - TH * 0.12, top: toScreen(TB - TH, 1) }}>
        <Burj id="f2" h={TH} t={t} glass={["#e6f2ff", "#6a93c0"]} rim="#ffd27a" glow={0.15} lit={() => 0.55} />
      </div>
      <Shimmer t={t} a={hot * heatIn(t)} />
      {/* speed streaks while climbing */}
      {Array.from({ length: 12 }, (_, i) => {
        const v = interpolate(t, [CLIMB_A, CLIMB_A + 0.3, CLIMB_B - 0.2, CLIMB_B + 0.1], [0, 1, 1, 0], clamp);
        return v > 0 ? <div key={i} style={{ position: "absolute", left: 20 + rnd(i, 3) * (SW - 40), width: 3, height: 200 + rnd(i, 4) * 200, background: "#fff", opacity: 0.35 * v, borderRadius: 2,
          top: ((t * (2600 + rnd(i, 5) * 1600) + i * 173) % (SH + 500)) - 300 }} /> : null;
      })}
      {/* marker: ripple rings + tag, fixed on screen, labels the position */}
      <div style={{ position: "absolute", left: TX - 18, top: MK_Y - 18, width: 36, height: 36, borderRadius: "50%", background: GOLD, border: "5px solid #fff", boxShadow: `0 0 30px 8px ${GOLD}` }} />
      {[0, 0.5].map((o, i) => { const k = (t * 1.4 + o) % 1; return <div key={i} style={{ position: "absolute", left: TX - 18 - 50 * k, top: MK_Y - 18 - 50 * k, width: 36 + 100 * k, height: 36 + 100 * k, borderRadius: "50%", border: `4px solid ${GOLD}`, opacity: 1 - k }} />; })}
      <div style={{ position: "absolute", right: SW - (TX - 34), top: MK_Y - 34, padding: "4px 18px", background: "#111", color: GOLD, border: `4px solid ${GOLD}`, borderRadius: 12, fontFamily: "Anton", fontSize: 54, letterSpacing: 2 }}>{c < 0.5 ? "NEECHE" : "TOP"}</div>
    </div>
  );
};

const Scale = ({ t }: { t: number }) => {
  const my = mercY(t);
  const cool = ramp(t, CLIMB_A + 0.2, F2.six + 0.15);
  const col = mix("#ff3b30", "#3da8ff", cool);
  const bg0 = mix("#5a1410", "#10305a", cool), bg1 = mix("#c2371b", "#2a7bd6", cool);
  const hotLine = ramp(t, F2.garmi + 0.4, F2.garmi + 0.8), coolLine = ramp(t, F2.six - 0.05, F2.six + 0.2);
  const br = ramp(t, F2.six - 0.05, F2.six + 0.4, 0, 1, Easing.out(Easing.cubic));
  const six = ramp(t, F2.six, F2.six + 0.35, 0, 1, Easing.out(Easing.back(2.2)));
  const jig = t > F2.six && t < F2.six + 0.4 ? Math.sin((t - F2.six) * 80) * 7 * (1 - (t - F2.six) / 0.4) : 0;
  const tx = 130;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: SW, height: SH, borderRadius: 26, overflow: "hidden", border: "6px solid rgba(255,255,255,.85)", boxSizing: "content-box",
      background: `linear-gradient(180deg, ${bg0}, ${bg1})`, boxShadow: "0 24px 60px rgba(0,0,0,.55)" }}>
      <svg width={SW} height={SH} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        {Array.from({ length: 15 }, (_, i) => { const y = BULB_Y - 40 - i * TICK; return y > 90 ? <line key={i} x1={tx + 52} x2={tx + (i % 2 ? 78 : 96)} y1={y} y2={y} stroke="rgba(255,255,255,.7)" strokeWidth={i % 2 ? 4 : 6} strokeLinecap="round" /> : null; })}
        <rect x={tx - 36} y="70" width="72" height={BULB_Y - 70} rx="36" fill="rgba(8,14,26,.85)" stroke="#fff" strokeWidth="7" />
        <circle cx={tx} cy={BULB_Y + 50} r="84" fill="rgba(8,14,26,.85)" stroke="#fff" strokeWidth="7" />
        <rect x={tx - 20} y={my} width="40" height={BULB_Y + 50 - my} fill={col} />
        <circle cx={tx} cy={BULB_Y + 50} r="66" fill={col} />
        <line x1={tx - 70} x2={tx + 110} y1={HOT_Y} y2={HOT_Y} stroke="#ff5a4a" strokeWidth="6" strokeDasharray="14 9" opacity={hotLine} />
        <line x1={tx - 70} x2={tx + 110} y1={COOL_Y} y2={COOL_Y} stroke="#7fd0ff" strokeWidth="6" strokeDasharray="14 9" opacity={coolLine} />
        <path d={`M ${tx + 120} ${HOT_Y} L ${tx + 150} ${HOT_Y} L ${tx + 150} ${COOL_Y} L ${tx + 120} ${COOL_Y}`} fill="none" stroke={GOLD} strokeWidth="12" strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray="640" strokeDashoffset={640 * (1 - br)} />
        <g transform={`translate(${tx + 245 + jig} ${(HOT_Y + COOL_Y) / 2 + 55}) scale(${six})`} opacity={six > 0 ? 1 : 0}>
          <text textAnchor="middle" fontFamily="Anton" fontSize="150" fill={GOLD} stroke="#000" strokeWidth="12" paintOrder="stroke">6°</text>
        </g>
      </svg>
    </div>
  );
};

const slide = (t: number, a: number, dir: 1 | -1) => (1 - ramp(t, a, a + 0.5, 0, 1, Easing.out(Easing.back(1.4)))) * 520 * dir;
export const Fact2 = ({ t }: { t: number }) => {
  const intro = F2.l3 - 0.1, outro = 1 - ramp(t, F2.l4 - 0.45, F2.l4 - 0.1);
  const on = t >= intro && outro > 0;
  const at6 = F2.six;
  return (
    <>
      <Sfx at={F2.l3 - 0.15} src="whoosh" vol={0.25} />
      <Sfx at={F2.l3} src="stamp" vol={0.35} />
      <Bed src="hum" at={F2.neeche - 0.2} b={CLIMB_B + 0.4} vol={(tt) => 0.1 * ramp(tt, F2.neeche - 0.2, F2.garmi) * (1 - ramp(tt, CLIMB_A, CLIMB_B))} />
      <Bed src="air" at={CLIMB_A - 0.2} b={F2.l4 - 0.2} vol={(tt) => 0.13 * ramp(tt, CLIMB_A - 0.2, CLIMB_A + 0.6) * (1 - ramp(tt, F2.thanda + 0.4, F2.l4 - 0.3))} />
      <Sfx at={CLIMB_A} src="whoosh" vol={0.25} />
      <Sfx at={CLIMB_A + 0.6} src="whoosh" vol={0.2} />
      <Sfx at={F2.garmi - 0.5} src="pop" vol={0.25} />
      {dropTimes.map((d, i) => <Sfx key={i} at={d} src="tick" vol={0.2} />)}
      <Sfx at={F2.six - 0.9} src="pop" vol={0.25} />
      <Sfx at={at6 + 0.03} src="ding" vol={0.3} />
      <Sfx at={F2.thanda + 0.4} src="sparkle" vol={0.15} />
      {on && (
        <Layer opacity={outro}>
          <Shake t={t} at={at6} amp={10}>
            <div style={{ position: "absolute", left: LX, top: PY, transform: `translateX(${slide(t, intro, -1)}px)` }}><TowerView t={t} /></div>
            <div style={{ position: "absolute", left: RX, top: PY, transform: `translateX(${slide(t, intro, 1)}px)` }}><Scale t={t} /></div>
          </Shake>
          {t < CLIMB_A + 0.45 && <Emoji t={t} a={F2.garmi - 0.4} char="🥵" x={LX + 24} y={PY + 330} size={170} wobble />}
          {t >= F2.paseene && t < CLIMB_A + 0.6 && <Emoji t={t} a={F2.paseene} char="💦" x={LX + 150} y={PY + 300} size={110} wobble />}
          {t >= F2.six - 0.7 && <Emoji t={t} a={F2.six - 0.7} char="😎" x={LX + 24} y={PY + 150} size={170} />}
          <Burst t={t} a={at6 + 0.05} x={RX + 400} y={PY + 560} n={14} dur={0.5} speed={800} color={GOLD} />
        </Layer>
      )}
      <Stamp t={t} a={F2.l3} text="FACT 2" until={F2.l3 + 1.5} top={700} />
      <Flash t={t} at={at6 + 0.02} color="#cfeaff" peak={0.3} dur={0.25} />
      <LightLeakCut at={F2.l4} seed={3} hue={190} />
    </>
  );
};
