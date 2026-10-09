// kit/misc.tsx  small stand-alone beats and the end card.
// ShoppingList {title="SHOPPING LIST", items=["Naye kapde","Jootey","Jeans","Ghar ka saaman"]}   sticky note, items tick one by one
// Engine       {label="ENGINE ON", unit="×1000 RPM"}                                              rev gauge needle sweeps into the red
// NayaStamp    {word="NAYA", color=GREEN}                                                         stamp slam with a particle burst
// BadaSize     {word="BADA!", sizes=["S","M","L","XL","XXXL"]}                                    size bar, last one biggest and red
// Barbaadi     {shuruAt, dur, loading="BARBAADI LOADING…", done="SHURU!"}                         loading bar completes at shuruAt (s into scene), confetti until dur
// EndCard      {logo?, title="WESTSIDE", sub="SARJAPUR · NAYA · BADA"}                            logo (image from public/, optional) + title + subtitle on a dark card
import React from "react";
import { Img } from "remotion";
import { W, YEL, RED, BLUE, GREEN, PINK, INK, ANTON, BARLOW, c01, prog, eOut, eIn, eInOut, eBack, lerp, rnd, pop, useSec, Fill, Abs, strokeText, pub } from "./lib";

export const ShoppingList: React.FC<{ title?: string; items?: string[] }> = ({ title = "SHOPPING LIST", items = ["Naye kapde", "Jootey", "Jeans", "Ghar ka saaman"] }) => {
  const t = useSec();
  const enter = eBack(prog(t, 0, 0.3), 1.7);
  return (
    <Abs style={{ left: 250, top: 250, width: 580, transform: `scale(${enter}) rotate(${lerp(-12, -3, enter)}deg)`, transformOrigin: "50% 0" }}>
      <div style={{ background: "linear-gradient(180deg,#FFE55C,#FFD400)", borderRadius: 8, padding: "26px 34px 22px", boxShadow: "0 24px 50px rgba(0,0,0,.55)", position: "relative" }}>
        <Abs style={{ left: 250, top: -22, width: 90, height: 42, background: "rgba(255,255,255,.55)", transform: "rotate(3deg)" }} />
        <div style={{ fontFamily: ANTON, fontSize: 64, color: INK, letterSpacing: 2, borderBottom: "4px solid rgba(0,0,0,.25)", paddingBottom: 4 }}>{title}</div>
        {items.map((it, i) => {
          const ap = pop(t, 0.18 + i * 0.1, 0.2);
          const tk = prog(t, 0.55 + i * 0.2, 0.7 + i * 0.2);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 14, opacity: ap > 0 ? 1 : 0, transform: `translateX(${(1 - Math.min(1, ap)) * 40}px)` }}>
              <div style={{ width: 46, height: 46, border: "5px solid " + INK, borderRadius: 8, position: "relative", flexShrink: 0 }}>
                <svg width={56} height={56} viewBox="0 0 56 56" style={{ position: "absolute", left: -2, top: -14 }}>
                  <path d="M6 30 L22 46 L52 6" fill="none" stroke={GREEN} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={90} strokeDashoffset={90 * (1 - tk)} />
                </svg>
              </div>
              <div style={{ position: "relative", fontFamily: BARLOW, fontWeight: 800, fontSize: 58, color: INK, letterSpacing: 1 }}>
                {it}
                <div style={{ position: "absolute", left: 0, top: 30, height: 6, width: `${tk * 100}%`, background: INK }} />
              </div>
            </div>
          );
        })}
      </div>
    </Abs>
  );
};

export const Engine: React.FC<{ label?: string; unit?: string }> = ({ label = "ENGINE ON", unit = "×1000 RPM" }) => {
  const t = useSec();
  const enter = eBack(prog(t, 0, 0.22), 1.6);
  const rev = eOut(prog(t, 0.05, 0.75)) + Math.sin(t * 60) * 0.012 * prog(t, 0.6, 0.7);
  const ang = lerp(-125, 125, c01(rev));
  const R = 220, cx = 270, cy = 270;
  const pt = (deg: number, r: number) => [cx + r * Math.sin((deg * Math.PI) / 180), cy - r * Math.cos((deg * Math.PI) / 180)];
  const arc = (a: number, b: number, r: number) => { const [x1, y1] = pt(a, r), [x2, y2] = pt(b, r); return `M${x1} ${y1} A${r} ${r} 0 ${b - a > 180 ? 1 : 0} 1 ${x2} ${y2}`; };
  const shake = rev > 0.8 ? Math.sin(t * 90) * 4 : 0;
  return (
    <Abs style={{ left: (W - 540) / 2, top: 230, width: 540, height: 540, transform: `scale(${enter}) translate(${shake}px, ${-shake}px)` }}>
      <svg width={540} height={540}>
        <circle cx={cx} cy={cy} r={252} fill="#0a0a10" stroke="#fff" strokeWidth={6} />
        <circle cx={cx} cy={cy} r={238} fill="none" stroke="rgba(255,255,255,.18)" strokeWidth={3} />
        <path d={arc(-125, 60, R)} stroke={BLUE} strokeWidth={22} fill="none" strokeLinecap="round" />
        <path d={arc(60, 125, R)} stroke={RED} strokeWidth={22} fill="none" strokeLinecap="round" />
        {Array.from({ length: 11 }, (_, i) => { const a = -125 + i * 25; const [x1, y1] = pt(a, 172), [x2, y2] = pt(a, 196); const [lx, ly] = pt(a, 138); return (<g key={i}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#fff" strokeWidth={5} /><text x={lx} y={ly + 14} textAnchor="middle" fontFamily={BARLOW} fontWeight={800} fontSize={40} fill="#fff">{i}</text></g>); })}
        <g transform={`rotate(${ang} ${cx} ${cy})`}>
          <polygon points={`${cx - 9},${cy} ${cx + 9},${cy} ${cx},${cy - 200}`} fill={RED} style={{ filter: "drop-shadow(0 0 10px #ff2d2d)" }} />
        </g>
        <circle cx={cx} cy={cy} r={22} fill="#fff" />
        <text x={cx} y={cy + 128} textAnchor="middle" fontFamily={ANTON} fontSize={44} fill={YEL} letterSpacing={2}>{label}</text>
        <text x={cx} y={cy + 172} textAnchor="middle" fontFamily={BARLOW} fontWeight={800} fontSize={28} fill="#fff" letterSpacing={4}>{unit}</text>
      </svg>
    </Abs>
  );
};

export const NayaStamp: React.FC<{ word?: string; color?: string }> = ({ word = "NAYA", color = GREEN }) => {
  const t = useSec();
  const slam = eIn(prog(t, 0, 0.12));
  const after = t > 0.12 ? Math.max(0, 1 - (t - 0.12) / 0.3) : 0;
  const sc = lerp(3.2, 1, slam) + after * 0.05;
  return (
    <>
      <Abs style={{ left: 120, top: 330, width: 840, textAlign: "center", opacity: c01(t / 0.05), transform: `scale(${sc}) rotate(-6deg)` }}>
        <div style={{ display: "inline-block", padding: "10px 60px 0", border: `18px solid ${color}`, borderRadius: 28, color, fontFamily: ANTON, fontSize: 270, lineHeight: 1.12, letterSpacing: 10, background: "rgba(0,0,0,.35)", textShadow: "0 0 30px rgba(31,214,107,.6)" }}>{word}</div>
      </Abs>
      {t > 0.12 && Array.from({ length: 10 }).map((_, i) => {
        const a = (i / 10) * Math.PI * 2, d = (t - 0.12) * 900;
        return <div key={i} style={{ position: "absolute", left: 540 + Math.cos(a) * d, top: 500 + Math.sin(a) * d * 0.7, width: 18, height: 18, borderRadius: 9, background: color, opacity: Math.max(0, 1 - (t - 0.12) / 0.3) }} />;
      })}
    </>
  );
};

export const BadaSize: React.FC<{ word?: string; sizes?: string[] }> = ({ word = "BADA!", sizes = ["S", "M", "L", "XL", "XXXL"] }) => {
  const t = useSec();
  const fx = [0, 0.13, 0.26, 0.4, 0.55];
  const last = sizes.length - 1;
  return (
    <>
      <Abs style={{ left: 0, top: 250, width: W, textAlign: "center", fontFamily: ANTON, fontSize: 180, color: YEL, letterSpacing: 6, ...strokeText(16), textShadow: "0 10px 0 rgba(0,0,0,.5)", transform: `scale(${1 + 0.06 * Math.sin(t * 24)}) rotate(-2deg)`, opacity: pop(t, 0, 0.14) > 0 ? 1 : 0 }}>{word}</Abs>
      <Abs style={{ left: 60, top: 520, width: 960, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        {sizes.map((s, i) => {
          const k = pop(t, fx[i] ?? 0.55 + (i - 4) * 0.13, 0.18);
          const big = i === last;
          const h = 90 + i * 30;
          return (
            <div key={s + i} style={{ width: big ? 250 : 170 - i * 4, height: h * (big ? 1.4 : 1), borderRadius: 22, background: big ? RED : i % 2 ? BLUE : "#fff", color: big ? "#fff" : INK, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: ANTON, fontSize: 56 + i * 12, border: "5px solid #fff", boxShadow: "0 10px 0 rgba(0,0,0,.4)", transform: `scale(${k})`, transformOrigin: "50% 100%" }}>{s}</div>
          );
        })}
      </Abs>
    </>
  );
};

export const Barbaadi: React.FC<{ shuruAt: number; dur: number; loading?: string; done?: string }> = ({ shuruAt, dur, loading = "BARBAADI LOADING…", done: doneLabel = "SHURU!" }) => {
  const t = useSec();
  const k = eOut(prog(t, 0, 0.25));
  const lv = eInOut(prog(t, 0.15, shuruAt));
  const done = t >= shuruAt;
  const pct = Math.round(lv * 100);
  const sh = done ? Math.max(0, 1 - (t - shuruAt) / 0.4) : 0;
  return (
    <>
      <Abs style={{ left: 70, top: 300, width: 940, opacity: k, transform: `translateY(${(1 - k) * -40}px) scale(${1 + 0.05 * sh})` }}>
        <div style={{ fontFamily: ANTON, fontSize: 96, color: done ? GREEN : "#fff", textAlign: "center", letterSpacing: 3, ...strokeText(12), textShadow: "0 8px 0 rgba(0,0,0,.5)" }}>{done ? doneLabel : loading}</div>
        <div style={{ height: 96, borderRadius: 48, background: "#14141c", border: "6px solid #fff", overflow: "hidden", marginTop: 20 }}>
          <div style={{ width: `${Math.max(3, pct)}%`, height: "100%", background: `repeating-linear-gradient(135deg, ${YEL} 0 36px, #ffb300 36px 72px)`, backgroundPosition: `${t * 200}px 0`, boxShadow: `0 0 30px ${YEL}` }} />
        </div>
        <div style={{ fontFamily: ANTON, fontSize: 120, color: done ? GREEN : YEL, textAlign: "center", marginTop: 8, ...strokeText(10) }}>{done ? "100% ✓" : pct + "%"}</div>
      </Abs>
      {done && Array.from({ length: 46 }).map((_, i) => {
        const a = t - shuruAt;
        const ang = -Math.PI / 2 + (rnd(i) - 0.5) * 2.6;
        const sp = 500 + rnd(i, 3) * 900;
        const x = 540 + Math.cos(ang) * sp * a;
        const y = 460 + Math.sin(ang) * sp * a + 1400 * a * a;
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: 18 + rnd(i, 7) * 14, height: 30, background: [YEL, RED, BLUE, GREEN, PINK, "#fff"][i % 6], transform: `rotate(${a * 540 + i * 40}deg)`, opacity: c01(1 - a / (dur - shuruAt + 0.4)) }} />;
      })}
    </>
  );
};

export const EndCard: React.FC<{ logo?: string; title?: string; sub?: string }> = ({ logo, title = "WESTSIDE", sub = "SARJAPUR · NAYA · BADA" }) => {
  const t = useSec();
  const bg = eOut(prog(t, 0, 0.15));
  const k = eBack(prog(t, 0.05, 0.4), 1.5);
  return (
    <>
      <Fill style={{ background: `radial-gradient(ellipse at 50% 42%, #14243a 0%, #05070d 75%)`, opacity: bg }} />
      <Abs style={{ left: 0, top: logo ? 440 : 640, width: W, textAlign: "center", transform: `scale(${0.6 + 0.4 * k})`, opacity: c01(k * 2) }}>
        {logo && <Img src={pub(logo)!} style={{ width: 460, height: 460, filter: "drop-shadow(0 0 50px rgba(255,255,255,.35))" }} />}
        <div style={{ fontFamily: ANTON, fontSize: 130, color: "#fff", letterSpacing: 14, marginTop: 14 }}>{title}</div>
        <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 60, color: YEL, letterSpacing: 8, opacity: eOut(prog(t, 0.3, 0.6)) }}>{sub}</div>
      </Abs>
    </>
  );
};
