import React from "react";
import { Easing, interpolate } from "remotion";
import { at, endOf, lineStart, ramp, pop, clamp, PIC_TOP, OUTRO_AT, GOLD, STROKE, Layer, Sfx, Stamp, Badge, Bubble, Emoji, Shake, LightLeakCut, Flash, Burst } from "../../kit";
import { Burj, HL_F } from "./Burj";
import { Bed } from "../../kit/audio";
import { mix, rnd } from "./sunbeat";

// Bonus (44.9-55.4 s): the SAME Burj, now about its empty top 29 %. The lights in the core above the 29 % line go out one by one from the top,
// the section turns into a hollow violet void, "29%" counts up, the "?" lands with a riser into the comment ask, and the bubble sits on the
// right, clear of the tower.

export const F5 = {
  l5: lineStart("L5"), p29: at("L5", "29"), p29e: endOf("L5", "hissa"), bilkul: at("L5", "bilkul"), khali: at("L5", "khali"), khaliE: endOf("L5", "khali"),
  kyun: at("L5", "kyun"), part: at("L5", "Part"), tab: at("L5", "Tab"), comment: at("L5", "comment"),
};
const PX = 60, PY = PIC_TOP + 10, PW = 960, PH = 940;
const ST = 1.5, TH = 840, BASE = 910, CX = 290, K = TH / 1000;
const HLY = BASE - HL_F * TH, TOPY = BASE - TH;
const OUT_A = F5.p29e + 0.35, OUT_B = F5.khali;           // lights go out from the top, finishing as "khali" starts
const ROW_TOP = 0.8;
const io = Easing.inOut(Easing.cubic);
const litAt = (t: number) => (f: number, i: number) => {
  if (f < HL_F) return 0.8 + 0.2 * Math.sin(t * 2 + i);
  const tOut = OUT_A + ((ROW_TOP - f) / (ROW_TOP - HL_F)) * (OUT_B - OUT_A);
  if (t < tOut - 0.1) return 0.95;
  if (t < tOut) return Math.sin((t - tOut) * 90) > 0 ? 0.95 : 0.1;   // flicker, then out
  return 0;
};
// the times at which rows switch off (for ticks): 8 steps
const outTimes = Array.from({ length: 8 }, (_, k) => OUT_A + ((k + 0.5) / 8) * (OUT_B - OUT_A));

const Stars = ({ t }: { t: number }) => (
  <>
    {Array.from({ length: 60 }, (_, i) => (
      <div key={i} style={{ position: "absolute", left: rnd(i, 1) * PW, top: rnd(i, 2) * PH * 0.8, width: 2 + rnd(i, 3) * 3, height: 2 + rnd(i, 3) * 3, borderRadius: "50%", background: "#fff",
        opacity: 0.3 + 0.7 * Math.abs(Math.sin(t * (1 + rnd(i, 4) * 2) + i)) }} />
    ))}
  </>
);

const Void = ({ t }: { t: number }) => {
  const k = ramp(t, F5.khali - 0.05, F5.khali + 0.5);
  if (k <= 0) return null;
  const pulse = 0.65 + 0.35 * Math.sin(t * 3);
  return (
    <>
      <div style={{ position: "absolute", left: CX - 230, top: TOPY - 40, width: 460, height: HLY - TOPY + 90, borderRadius: "50%", opacity: k * pulse,
        background: "radial-gradient(ellipse, rgba(150,80,255,.55) 0%, rgba(80,30,160,.25) 45%, rgba(0,0,0,0) 70%)" }} />
      {[0, 0.6, 1.2].map((o, i) => { const q = ((t - F5.khali) * 0.8 + o) % 1.8 / 1.8; return t > F5.khali ? (
        <div key={i} style={{ position: "absolute", left: CX - 40 - 150 * q, top: HLY - 40 - 150 * q, width: 80 + 300 * q, height: 80 + 300 * q, borderRadius: "50%", border: "4px solid rgba(190,140,255,.7)", opacity: (1 - q) * k, transform: "scaleY(.5)" }} />) : null; })}
      {Array.from({ length: 16 }, (_, i) => (
        <div key={i} style={{ position: "absolute", left: CX - 40 + Math.sin(t * (0.7 + rnd(i, 1)) + i) * 50, top: HLY - 20 - (((t - F5.khali) * (30 + rnd(i, 2) * 40) + rnd(i, 3) * (HLY - TOPY)) % (HLY - TOPY)),
          width: 5, height: 5, borderRadius: "50%", background: "#d9b8ff", opacity: 0.6 * k }} />
      ))}
    </>
  );
};

export const Bonus = ({ t }: { t: number }) => {
  const intro = F5.l5 - 0.1, outro = 1 - ramp(t, OUTRO_AT - 0.1, OUTRO_AT + 0.3);
  const beds = (
    <>
      <Sfx at={F5.l5 - 0.15} src="whoosh" vol={0.25} />
      <Sfx at={F5.l5} src="stamp" vol={0.35} />
      <Sfx at={F5.p29 + 0.05} src="pop" vol={0.28} />
      {outTimes.map((o, i) => <Sfx key={i} at={o} src="tick" vol={0.2} />)}
      <Sfx at={F5.khali + 0.45} src="boom" vol={0.28} />
      <Bed src="hum" at={F5.khali - 0.1} b={F5.kyun + 2.5} vol={(tt) => 0.12 * ramp(tt, F5.khali - 0.1, F5.khali + 0.8) * (1 - ramp(tt, F5.kyun + 1.2, F5.kyun + 2.4))} />
      <Sfx at={F5.kyun - 0.55} src="riser" vol={0.22} />
      <Sfx at={F5.kyun + 0.05} src="pop" vol={0.3} />
      <Sfx at={F5.part + 0.05} src="pop" vol={0.25} />
      <Sfx at={F5.tab - 0.35} src="riser" vol={0.22} />
      <Sfx at={F5.comment - 0.12} src="pop" vol={0.3} />
      <Sfx at={F5.comment + 0.1} src="notify" vol={0.22} />
    </>
  );
  if (t < intro || outro <= 0) return beds;
  const slide = (1 - ramp(t, intro, intro + 0.5, 0, 1, Easing.out(Easing.back(1.3)))) * 700;
  const reveal = ramp(t, F5.l5 + 0.3, F5.l5 + 1.5, 0, 1, io);
  const hl = ramp(t, F5.p29 - 0.3, F5.p29 + 0.2);
  const hollow = ramp(t, F5.khali - 0.05, F5.khali + 0.4);
  const z = 1 + 0.14 * ramp(t, F5.l5, OUTRO_AT, 0, 1, Easing.linear) + 0.05 * Math.max(0, Math.sin(Math.min(1, Math.max(0, (t - F5.khali) / 0.5)) * Math.PI));
  const q = t >= F5.kyun;
  const qs = pop(t, F5.kyun, 0.4, 0.3, 1.3);
  const shake = Math.sin((t - F5.kyun) * 5) * 8 * ramp(t, F5.kyun, F5.kyun + 0.4);
  const cnt = Math.round(interpolate(t, [F5.p29, F5.p29e], [0, 29], clamp));
  return (
    <>
      {beds}
      <Layer opacity={outro}>
        <div style={{ position: "absolute", left: PX, top: PY, width: PW, height: PH, borderRadius: 30, overflow: "hidden", border: "6px solid rgba(255,255,255,.85)", boxSizing: "content-box",
          boxShadow: "0 30px 70px rgba(0,0,0,.55)", transform: `translateX(${slide}px)`, background: "linear-gradient(180deg, #060b22, #1a1246 60%, #3a1d5e)" }}>
          <div style={{ position: "absolute", inset: 0, transformOrigin: `${CX}px ${HLY}px`, transform: `scale(${z})` }}>
            <Stars t={t} />
            <div style={{ position: "absolute", left: 0, right: 0, top: BASE, height: 200, background: "linear-gradient(180deg, #2a2148, #0e0a1e)" }} />
            <div style={{ position: "absolute", left: CX - TH * 0.12 * ST, top: TOPY, clipPath: `inset(${(1 - reveal) * 100}% -200px 0 -200px)` }}>
              <Burj id="bn" stretch={ST} h={TH} t={t} glass={["#d6e8ff", "#5a7fae"]} rim="#c8b2ff" glow={0.35} lit={litAt(t)} />
              {hollow > 0 && (
                <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: HLY - TOPY, overflow: "hidden", opacity: hollow }}>
                  <Burj id="bh" stretch={ST} h={TH} ghost light={false} ghostFill="rgba(32,10,70,.9)" ghostStroke="#c9a6ff" />
                </div>
              )}
            </div>
            <Void t={t} />
          </div>
          {/* the 29 % marker: dashed line at the cut, bracket along the top part, connector to the counter */}
          {hl > 0 && (
            <svg width={PW} height={PH} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }} opacity={hl}>
              <line x1="60" x2="520" y1={HLY} y2={HLY} stroke={GOLD} strokeWidth="6" strokeDasharray="16 10" />
              <path d={`M 80 ${TOPY} L 55 ${TOPY} L 55 ${HLY} L 80 ${HLY}`} fill="none" stroke={GOLD} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
          {hl > 0 && (
            <div style={{ position: "absolute", left: 540, top: TOPY - 10, opacity: hl, transform: `scale(${pop(t, F5.p29)})`, transformOrigin: "0 50%" }}>
              <span style={{ fontFamily: "Anton", fontSize: 200, color: GOLD, ...STROKE(10) }}>{cnt}%</span>
            </div>
          )}
          {q && (
            <div style={{ position: "absolute", left: 650, top: 330, fontFamily: "Anton", fontSize: 280, lineHeight: 1, color: "#fff", ...STROKE(14),
              textShadow: "0 0 50px rgba(190,140,255,.9)", transform: `translateX(${shake}px) scale(${qs}) rotate(${6 * Math.sin((t - F5.kyun) * 4)}deg)`, transformOrigin: "50% 60%" }}>?</div>
          )}
        </div>
        {/* comment ask: bubble on the right, clear of the tower */}
        {t >= F5.comment - 0.12 && (
          <>
            <Bubble t={t} a={F5.comment - 0.12} text={"SABSE CRAZY\nFACT KAUNSA?"} x={PX + 700} y={PY + 770} size={64} color="#111" bg="#fff" tail="left" rot={-3} />
            <Emoji t={t} a={F5.comment + 0.1} char="💬" x={PX + 800} y={PY + 600} size={110} wobble />
          </>
        )}
      </Layer>
      <Burst t={t} a={F5.khali + 0.4} x={PX + CX} y={PY + HLY} n={14} dur={0.6} speed={700} color="#c9a6ff" />
      <Flash t={t} at={F5.khali + 0.4} color="#d9c2ff" peak={0.3} dur={0.3} />
      <Stamp t={t} a={F5.l5} text="BONUS" until={F5.l5 + 1.3} top={820} />
      {t >= F5.part && t < F5.part + 1.3 && <Badge t={t} a={F5.part} text="PART 2" x={560} y={900} size={90} bg="#6a2bd9" rot={5} until={F5.part + 1.1} />}
      <LightLeakCut at={F5.l5} seed={4} hue={280} />
    </>
  );
};
