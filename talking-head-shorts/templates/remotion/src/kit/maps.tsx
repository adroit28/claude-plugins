// kit/maps.tsx  maps and roads.
// TrafficMap {place="SARJAPUR ROAD", eta="ETA: ∞", slow="SLOW", jam="JAM 🔥"}                      roads go red, cars honk
// MapsNav    {logo?, blocks=[[x,y,w,h,label]...], eta="2 min · 80 m", steps=[3 strings], arrived="ARRIVED", dest="KAPDE YAHAN HAIN"}   floor plan with a drawn route (needs ~1.8 s)
// RoadClosed {line1="ROAD", line2="CLOSED"}                                                         barricade drops (shake it from timeline.shakes)
import React from "react";
import { Img } from "remotion";
import { W, YEL, RED, GREEN, ANTON, BARLOW, EMOJI, c01, prog, eOut, eInOut, eBack, pop, useSec, Abs, strokeText, pub } from "./lib";

export const TrafficMap: React.FC<{ place?: string; eta?: string; slow?: string; jam?: string }> = ({ place = "SARJAPUR ROAD", eta = "ETA: ∞", slow = "SLOW", jam = "JAM 🔥" }) => {
  const t = useSec();
  const k = eOut(prog(t, 0, 0.25));
  const red = prog(t, 0.2, 1.1);
  const roads: [string, number][] = [["M60 330 L 520 330 L 520 560 L 1000 560", 0], ["M60 560 L 330 560 L 330 700", 0.4], ["M740 240 L 740 740", 0.7]];
  const cars = [[160, 318], [260, 318], [360, 318], [510, 400], [510, 480], [620, 548], [720, 548], [820, 548], [730, 420], [730, 640]];
  return (
    <Abs style={{ left: 40, top: 240, width: 1000, height: 520, opacity: k, transform: `scale(${0.94 + 0.06 * k})` }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 30, background: "#1b2230", border: "3px solid rgba(255,255,255,.25)", overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,.6)" }}>
        <svg width="1000" height="520" viewBox="40 240 1000 520">
          {[0, 1, 2, 3, 4].map((i) => <rect key={i} x={100 + i * 190} y={265 + (i % 2) * 20} width={120} height={50} rx={8} fill="#232d40" />)}
          {roads.map(([d], i) => <path key={i} d={d} stroke="#3a4560" strokeWidth={42} fill="none" strokeLinejoin="round" />)}
          {roads.map(([d, off], i) => {
            const m = c01(red * 1.6 - off);
            const col = m < 0.4 ? GREEN : m < 0.75 ? "#FFB300" : RED;
            return <path key={"r" + i} d={d} stroke={col} strokeWidth={22} fill="none" strokeLinejoin="round" strokeDasharray={m > 0.75 ? "none" : "26 16"} />;
          })}
        </svg>
        {cars.map(([x, y], i) => {
          const a = t - 0.3 - i * 0.05;
          return a > 0 ? <div key={i} style={{ position: "absolute", left: x - 40, top: y - 240 - 26 + Math.sin(t * 30 + i) * 2, fontSize: 50, fontFamily: EMOJI, transform: `scale(${eBack(a / 0.2)})` }}>{i % 3 === 0 ? "🚗" : i % 3 === 1 ? "🚕" : "🚌"}</div> : null;
        })}
        {[0, 1, 2].map((i) => { const a = t - 0.5 - i * 0.2; return a > 0 && a < 0.5 ? <div key={i} style={{ position: "absolute", left: 220 + i * 280, top: 60 + (i % 2) * 90, fontFamily: ANTON, fontSize: 60, color: YEL, ...strokeText(8), transform: `scale(${eBack(a / 0.15)}) rotate(${i * 8 - 8}deg)`, opacity: 1 - a * 1.5 }}>PEEP!</div> : null; })}
        <div style={{ position: "absolute", left: 20, top: 16, display: "flex", alignItems: "center", gap: 12, background: "rgba(0,0,0,.65)", padding: "8px 18px 4px", borderRadius: 14, fontFamily: ANTON, fontSize: 44, color: "#fff", letterSpacing: 2 }}>
          <span style={{ color: red > 0.8 ? RED : YEL }}>●</span> {place} · {red > 0.8 ? jam : slow}
        </div>
        <div style={{ position: "absolute", right: 20, bottom: 16, background: RED, padding: "6px 22px 2px", borderRadius: 12, fontFamily: ANTON, fontSize: 56, color: "#fff", letterSpacing: 2, transform: `scale(${pop(t, 0.9, 0.2)})` }}>{eta}</div>
      </div>
    </Abs>
  );
};

const GMAPS = [["G", "#4285F4"], ["o", "#EA4335"], ["o", "#FBBC05"], ["g", "#4285F4"], ["l", "#34A853"], ["e", "#EA4335"]];
const BLOCKS: [number, number, number, number, string][] = [[180, 340, 230, 120, "JEANS"], [560, 260, 150, 80, "TEES"], [180, 140, 260, 100, "ETHNIC"], [700, 380, 220, 100, "SHOES"]];
export const MapsNav: React.FC<{ logo?: string; blocks?: [number, number, number, number, string][]; eta?: string; steps?: string[]; arrived?: string; dest?: string }> = ({ logo, blocks = BLOCKS, eta = "2 min · 80 m", steps = ["ENTRANCE SE SEEDHA...", "RIGHT MUDO →", "AAGE JAO ↑"], arrived = "ARRIVED", dest = "KAPDE YAHAN HAIN" }) => {
  const t = useSec();
  const k = eOut(prog(t, 0, 0.25));
  const route = "M 120 420 L 120 300 L 520 300 L 520 220 L 840 220 L 840 340";
  const len = 1000;
  const draw = eInOut(prog(t, 0.45, 1.7));
  const arrive = t > 1.7;
  return (
    <Abs style={{ left: 50, top: 240, width: 980, height: 520, opacity: k, transform: `scale(${0.94 + 0.06 * k})` }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 30, background: "#eef0f4", border: "5px solid #fff", overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,.6)" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 980, height: 90, background: "#fff", display: "flex", alignItems: "center", padding: "0 28px", gap: 4, boxShadow: "0 4px 12px rgba(0,0,0,.15)" }}>
          {GMAPS.map(([c, col], i) => <span key={i} style={{ fontFamily: "Arial, Helvetica, sans-serif", fontWeight: 700, fontSize: 56, color: col, letterSpacing: -1 }}>{c}</span>)}
          <span style={{ fontFamily: "Arial, Helvetica, sans-serif", fontWeight: 700, fontSize: 56, color: "#5f6368", marginLeft: 14 }}>Maps</span>
          <span style={{ marginLeft: "auto", fontFamily: BARLOW, fontWeight: 800, fontSize: 36, color: "#1a73e8", letterSpacing: 1 }}>{arrive ? arrived : eta}</span>
        </div>
        <svg width="980" height="520" viewBox="0 0 980 520" style={{ position: "absolute", left: 0, top: 0 }}>
          <g transform="translate(0 70)">
            {blocks.map(([x, y, w, h, label], i) => (
              <g key={i}>
                <rect x={x} y={y - 120} width={w} height={h} rx={12} fill="#d6dae3" stroke="#b9bfcc" strokeWidth={3} />
                <text x={x + w / 2} y={y - 120 + h / 2 + 12} textAnchor="middle" fontFamily="Anton" fontSize={34} fill="#6b7385" letterSpacing={2}>{label}</text>
              </g>
            ))}
            <path d={route} stroke="rgba(26,115,232,.28)" strokeWidth={26} fill="none" strokeLinejoin="round" strokeLinecap="round" transform="translate(0 -70)" />
            <path d={route} stroke="#1a73e8" strokeWidth={14} fill="none" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={len} strokeDashoffset={len * (1 - draw)} transform="translate(0 -70)" />
          </g>
        </svg>
        <div style={{ position: "absolute", left: 120 - 46, top: 374, width: 92, height: 92, borderRadius: "50%", background: "#0b0b0f", border: "5px solid #fff", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 18px rgba(0,0,0,.4)", transform: `scale(${pop(t, 0.15, 0.25)})` }}>
          {logo ? <Img src={pub(logo)!} style={{ width: 68, height: 68 }} /> : <div style={{ width: 36, height: 36, borderRadius: 18, background: "#1a73e8", border: "4px solid #fff" }} />}
        </div>
        <div style={{ position: "absolute", left: 840 - 50, top: 340 + 2 - 30, transform: `scale(${pop(t, 1.6, 0.25)})`, transformOrigin: "50% 100%", textAlign: "center", width: 100 }}>
          <div style={{ fontSize: 90, fontFamily: EMOJI, lineHeight: 1 }}>📍</div>
        </div>
        <div style={{ position: "absolute", right: 24, bottom: 20, background: arrive ? GREEN : "#1a73e8", color: "#fff", fontFamily: ANTON, fontSize: 48, letterSpacing: 3, padding: "6px 24px 2px", borderRadius: 14, transform: `scale(${pop(t, 1.65, 0.2)})` }}>{arrive ? dest : ""}</div>
        <div style={{ position: "absolute", left: 150, bottom: 20, background: "#1a73e8", color: "#fff", fontFamily: BARLOW, fontWeight: 800, fontSize: 34, padding: "6px 20px 2px", borderRadius: 12, letterSpacing: 2, opacity: arrive ? 0 : 1 }}>{t < 1.0 ? steps[0] : t < 1.4 ? steps[1] : steps[2]}</div>
      </div>
    </Abs>
  );
};

export const RoadClosed: React.FC<{ line1?: string; line2?: string }> = ({ line1 = "ROAD", line2 = "CLOSED" }) => {
  const t = useSec();
  const drop = eBack(prog(t, 0, 0.26), 1.2);
  const bounce = t > 0.26 ? Math.sin((t - 0.26) * 40) * 8 * Math.max(0, 1 - (t - 0.26) / 0.4) : 0;
  const stripes = "repeating-linear-gradient(135deg, #fff 0 34px, #FF5A1F 34px 68px)";
  const blink = Math.floor(t * 5) % 2 === 0;
  return (
    <Abs style={{ left: 0, top: 0, width: W, transform: `translateY(${(drop - 1) * 500 + bounce}px)`, opacity: c01(drop * 4) }}>
      <Abs style={{ left: 130, top: 590, width: 12, height: 190, background: "#444" }} />
      <Abs style={{ left: 938, top: 590, width: 12, height: 190, background: "#444" }} />
      <Abs style={{ left: 60, top: 300, width: 960, height: 120, background: stripes, borderRadius: 14, border: "6px solid #fff", boxShadow: "0 14px 0 rgba(0,0,0,.4)" }} />
      <Abs style={{ left: 120, top: 440, width: 840, height: 120, background: stripes, backgroundPosition: "68px 0", borderRadius: 14, border: "6px solid #fff", boxShadow: "0 14px 0 rgba(0,0,0,.4)" }} />
      <Abs style={{ left: 290, top: 400, width: 500, height: 200, background: RED, borderRadius: 24, border: "8px solid #fff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: "0 16px 0 rgba(0,0,0,.5)" }}>
        <div style={{ fontFamily: ANTON, fontSize: 92, color: "#fff", lineHeight: 1, letterSpacing: 3 }}>{line1}</div>
        <div style={{ fontFamily: ANTON, fontSize: 92, color: "#fff", lineHeight: 1, letterSpacing: 3 }}>{line2}</div>
      </Abs>
      <Abs style={{ left: 90, top: 215, width: 100, height: 100, borderRadius: 50, background: blink ? "#FFB300" : "#7a5a00", boxShadow: blink ? "0 0 70px #FFB300" : "none" }} />
      <Abs style={{ left: 890, top: 215, width: 100, height: 100, borderRadius: 50, background: blink ? "#7a5a00" : "#FFB300", boxShadow: blink ? "none" : "0 0 70px #FFB300" }} />
      <Abs style={{ left: 180, top: 640, fontSize: 130, fontFamily: EMOJI }}>🚧</Abs>
      <Abs style={{ left: 760, top: 640, fontSize: 130, fontFamily: EMOJI }}>🚧</Abs>
    </Abs>
  );
};
