import React from "react";
import { Easing, interpolate } from "remotion";
import { at, lineStart, ramp, pop, clamp, PIC_TOP, GOLD, STROKE, Layer, Sfx, Stamp, Badge, Shake, LightLeakCut, Flash } from "../../kit";
import { Burj, towerX, edge } from "./Burj";
import { Bed } from "../../kit/audio";
import { Cloud, mix, rnd } from "./sunbeat";

// Fact 3 (30.7-44.8 s): real wind. Curved streamlines that bend around the tower, dust / leaves / cloud wisps blown through, and a tower that
// flexes progressively (tiers displaced by flex * f^2, so the top moves most). Ghost outlines mark the two extremes; the 1.5 m bracket spans them.

export const F3 = {
  l4: lineStart("L4"), poori: at("L4", "poori"), hawa: at("L4", "hawa"), jhoolti: at("L4", "jhoolti"), tez: at("L4", "Tez"), m15: at("L4", "1.5"),
  sway: at("L4", "sway"), ghabrao: at("L4", "Ghabrao"), genius: at("L4", "genius"), flex: at("L4", "flex"), l5: lineStart("L5"),
};
const PX = 60, PY = PIC_TOP + 10, PW = 960, PH = 940;
const ST = 1.4, TH = 740, BASE = 900, CX = 480, K = TH / 1000, KX = K * ST;      // px per viewBox unit
const FLEX = 120;                                          // viewBox units of bend at the top at full wind (shown exaggerated)
const io = Easing.inOut(Easing.cubic);

// wind strength 0..1: starts at "hawa", gusts hard through "1.5 ... sway", calms from "Ghabrao"
export const wind = (t: number) => {
  const up = ramp(t, F3.hawa, F3.hawa + 1.4);
  const gust = ramp(t, F3.tez - 0.3, F3.tez + 0.6) * (1 - ramp(t, F3.ghabrao - 0.2, F3.ghabrao + 0.5));
  const calm = 1 - 0.78 * ramp(t, F3.ghabrao, F3.ghabrao + 1.4);
  return Math.min(1, (0.55 * up + 0.45 * gust) * calm) * (1 - ramp(t, F3.l5 - 0.9, F3.l5 - 0.2));
};
const swing = (t: number) => Math.sin(t * 2.6) * 0.85 + Math.sin(t * 4.1 + 1) * 0.15;
const flexAt = (t: number) => FLEX * wind(t) * swing(t) * (0.9 + 0.1 * Math.sin(t * 0.9));

const NL = 13;
const Streamlines = ({ t, w }: { t: number; w: number }) => {
  const fl = flexAt(t);
  const sp = 380 + 900 * w;
  return (
    <svg width={PW} height={PH} style={{ position: "absolute", left: 0, top: 0 }} opacity={Math.min(1, w * 2.2)}>
      {Array.from({ length: NL }, (_, i) => {
        const y0 = 70 + (i / (NL - 1)) * 800, f = Math.max(0, Math.min(1, (BASE - y0) / TH));
        const above = f > 1.02;
        const xc = CX + (fl * f * f) * KX, hw = above ? 0 : edge(1, Math.min(f, 0.99)) * KX + 14;
        const near = Math.exp(-Math.pow((y0 - (BASE - TH * 0.5)) / 520, 2));
        const side = i % 2 ? 1 : -1;
        const pts: string[] = [];
        for (let x = -60; x <= PW + 60; x += 24) {
          const dxn = (x - xc) / (hw * 2.4 + 90);
          const bend = side * (hw + 60) * 1.15 * Math.exp(-dxn * dxn) * (above ? 0.25 : 1);
          const wave = Math.sin(x * 0.012 - t * (2.4 + w * 3) + i) * (4 + 8 * w);
          pts.push(`${x},${y0 + bend * (0.4 + 0.6 * near) * w + wave}`);
        }
        const dash = 170 + (i % 4) * 60;
        return <polyline key={i} points={pts.join(" ")} fill="none" stroke="#fff" strokeWidth={5 + (i % 3) * 3} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={`${dash} ${170 + (i % 5) * 50}`} strokeDashoffset={-((t * sp * (0.8 + (i % 4) * 0.12) + i * 173) % 2000)} opacity={0.4 + 0.4 * ((i * 7) % 5) / 4} />;
      })}
    </svg>
  );
};

const Leaf = ({ x, y, r, s, c }: { x: number; y: number; r: number; s: number; c: string }) => (
  <svg width="40" height="24" viewBox="0 0 40 24" style={{ position: "absolute", left: x, top: y, transform: `rotate(${r}deg) scale(${s})` }}>
    <path d="M 2 12 Q 20 -4 38 12 Q 20 28 2 12 Z" fill={c} /><path d="M 2 12 L 38 12" stroke="rgba(0,0,0,.35)" strokeWidth="1.5" />
  </svg>
);
const Debris = ({ t, w }: { t: number; w: number }) => {
  if (w <= 0.02) return null;
  return (
    <>
      {Array.from({ length: 46 }, (_, i) => {
        const sp = 320 + rnd(i, 1) * 700, ph = rnd(i, 2) * (PW + 400), yb = 40 + rnd(i, 3) * 840;
        const x = ((t * sp * (0.35 + w) + ph) % (PW + 400)) - 200;
        const y = yb + Math.sin(t * (2 + rnd(i, 4) * 3) + i) * (18 + 30 * w) + (x / PW) * 40 * (rnd(i, 5) - 0.5);
        if (i % 3 === 0 || i % 7 === 2) return <Leaf key={i} x={x} y={y} r={t * (180 + rnd(i, 6) * 400) + i * 40} s={0.8 + rnd(i, 7) * 0.9} c={["#7aa83a", "#c58a2e", "#9a6a2a", "#5f8f3a"][i % 4]} />;
        if (i % 3 === 1) return <div key={i} style={{ position: "absolute", left: x, top: y, width: 4 + rnd(i, 8) * 6, height: 4 + rnd(i, 8) * 6, borderRadius: "50%", background: "#d9c7a0", opacity: 0.35 + 0.4 * rnd(i, 9) }} />;
        return i % 2 ? null : <div key={i} style={{ position: "absolute", left: x, top: y, width: 120 + rnd(i, 10) * 160, height: 8, borderRadius: 6, background: "linear-gradient(90deg, transparent, rgba(255,255,255,.4), transparent)", filter: "blur(2px)", opacity: 0.4 + 0.4 * w }} />;
      })}
    </>
  );
};

export const Fact3 = ({ t }: { t: number }) => {
  const intro = F3.l4 - 0.1, outro = 1 - ramp(t, F3.l5 - 0.45, F3.l5 - 0.12);
  if (t < intro || outro <= 0) return <Beds />;
  const w = wind(t), fl = flexAt(t);
  const reveal = ramp(t, F3.l4 + 0.35, F3.l4 + 1.5, 0, 1, io);
  const mk = ramp(t, F3.m15 - 0.1, F3.m15 + 0.3) * (1 - ramp(t, F3.l5 - 0.8, F3.l5 - 0.4));
  const hit = Math.abs(swing(t)) > 0.93 && w > 0.5 ? 1 : 0;
  const gx = (s: number) => CX - TH * 0.12 * ST + towerX(1, s * FLEX) * KX;   // frame x of the tip at +/- extreme
  const topY = BASE - TH;
  const slide = (1 - ramp(t, intro, intro + 0.5, 0, 1, Easing.out(Easing.back(1.3)))) * 700;
  const skyShift = ramp(t, F3.hawa, F3.hawa + 2);
  return (
    <>
      <Beds />
      <Layer opacity={outro}>
        <div style={{ position: "absolute", left: PX, top: PY, width: PW, height: PH, borderRadius: 30, overflow: "hidden", border: "6px solid rgba(255,255,255,.85)", boxSizing: "content-box",
          boxShadow: "0 30px 70px rgba(0,0,0,.55)", transform: `translateX(${slide}px)`,
          background: `linear-gradient(180deg, ${mix("#3b8be6", "#2c3a52", skyShift)}, ${mix("#bfe3ff", "#8d98b0", skyShift)})` }}>
          {[{ y: 120, x: 150 }, { y: 260, x: 700 }, { y: 420, x: 300 }, { y: 560, x: 850 }, { y: 700, x: 120 }].map((c, i) => (
            <Cloud key={i} x={((c.x + t * (60 + i * 30) * (0.3 + w * 1.6)) % (PW + 500)) - 150} y={c.y + Math.sin(t * 0.7 + i) * 14} w={340 + i * 30} o={0.6 + 0.2 * w} col={mix("#ffffff", "#c9ced9", skyShift)} />
          ))}
          <div style={{ position: "absolute", left: 0, right: 0, top: BASE, height: 200, background: "linear-gradient(180deg, #3d4358, #1d2030)" }} />
          <div style={{ position: "absolute", left: CX - TH * 0.12 * ST, top: topY, clipPath: `inset(${(1 - reveal) * 100}% -200px 0 -200px)` }}>
            <Burj id="f3" stretch={ST} h={TH} t={t} flex={fl} glass={["#e6f2ff", "#5f86b3"]} rim="#cfe6ff" lit={() => 0.5} />
            {mk > 0 && <div style={{ position: "absolute", left: 0, top: 0, opacity: mk * (0.45 + 0.4 * hit) }}><Burj id="g1" stretch={ST} h={TH} flex={FLEX} ghost light={false} /></div>}
            {mk > 0 && <div style={{ position: "absolute", left: 0, top: 0, opacity: mk * (0.45 + 0.4 * hit) }}><Burj id="g2" stretch={ST} h={TH} flex={-FLEX} ghost light={false} /></div>}
          </div>
          <Streamlines t={t} w={w} />
          <Debris t={t} w={w} />
          {mk > 0 && (
            <svg width={PW} height={260} style={{ position: "absolute", left: 0, top: topY - 150, overflow: "visible" }} opacity={mk}>
              <path d={`M ${gx(-1)} 170 L ${gx(-1)} 140 L ${gx(1)} 140 L ${gx(1)} 170`} fill="none" stroke={GOLD} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
              <text x={(gx(-1) + gx(1)) / 2} y="110" textAnchor="middle" fontFamily="Anton" fontSize="120" fill={GOLD} stroke="#000" strokeWidth="12" paintOrder="stroke"
                transform={`translate(0 ${12 - 12 * pop(t, F3.m15)})`}>1.5 m</text>
            </svg>
          )}
        </div>
      </Layer>
      <Stamp t={t} a={F3.l4} text="FACT 3" until={F3.l4 + 1.4} top={700} />
      {t >= F3.ghabrao + 0.3 && t < F3.l5 - 0.2 && <Badge t={t} a={F3.ghabrao + 0.3} text="GENIUS ENGINEERING" x={70} y={1130} size={90} bg="#0a8f3c" rot={-4} until={F3.l5 - 0.4} />}
      <Flash t={t} at={F3.m15 + 0.02} color="#fff" peak={0.2} dur={0.2} />
    </>
  );
};

// sound: wind from "hawa" to "Ghabrao" (swelling with each gust, fading as the sway calms), creak + rumble at the max sway
const Beds = () => (
  <>
    <Sfx at={F3.l4 - 0.15} src="whoosh" vol={0.22} />
    <Sfx at={F3.l4} src="stamp" vol={0.35} />
    <Bed src="wind" at={F3.hawa - 0.1} b={F3.ghabrao + 1.8} vol={(tt) => {
      const gust = 0.5 + 0.5 * Math.abs(Math.sin(tt * 1.3));       // one swell per sway half-cycle
      const fade = 1 - ramp(tt, F3.ghabrao, F3.ghabrao + 1.6);
      return 0.24 * ramp(tt, F3.hawa - 0.1, F3.hawa + 0.7) * (0.4 + 0.6 * wind(tt)) * (0.55 + 0.45 * gust) * fade;
    }} />
    <Sfx at={F3.m15 + 0.02} src="ding" vol={0.28} />
    <Sfx at={F3.sway - 0.45} src="rumble" vol={0.28} />
    <Sfx at={F3.sway - 0.1} src="creak" vol={0.3} />
    <Sfx at={F3.ghabrao + 0.3} src="pop" vol={0.25} />
    <Sfx at={F3.ghabrao + 1.0} src="whoosh" vol={0.15} />
  </>
);
