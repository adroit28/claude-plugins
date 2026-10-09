// kit/finance.tsx  money beats.
// CreditCard   {pinAt (s into the scene), logo?, number="4242  ••••  ••••  0001", caption="CREDIT CARD", network="VISA", pinLabel="ENTER PIN", colors=[#1c7fd0,#0b2a66,#06142e]}  card flies in, PIN dots fill from pinAt
// BalanceChip  {dur, label="BANK BALANCE", from=48500, lowBelow=12000, format=money}           counts from `from` to 0 over dur
// Kangali      {word="KANGALI", sub="BALANCE: ₹0"}                                              full-screen glitch slam with a hard pause (0.85 s)
// Salary       {t1, t2, dur?, calendar="TAREEKH", creditTitle/creditAmount/creditBody/creditIcon, debitTitle/debitAmount/debitBody, logo?, debitIcon="💳"}  credit SMS + note rain, calendar 1 -> 2, debit SMS
import React from "react";
import { Img } from "remotion";
import { W, YEL, RED, GREEN, INK, ANTON, BARLOW, EMOJI, c01, prog, eOut, eIn, eInOut, eBack, lerp, rnd, pop, useSec, Fill, Abs, glass, glass1, strokeText, money, pub } from "./lib";

export const CreditCard: React.FC<{ pinAt: number; logo?: string; number?: string; caption?: string; network?: string; pinLabel?: string; colors?: [string, string, string] }> = ({ pinAt, logo, number = "4242  ••••  ••••  0001", caption = "CREDIT CARD", network = "VISA", pinLabel = "ENTER PIN", colors = ["#1c7fd0", "#0b2a66", "#06142e"] }) => {
  const t = useSec();
  const fly = eOut(prog(t, 0, 0.5));
  const dots = Math.min(4, Math.max(0, Math.floor((t - pinAt) / 0.14) + 1));
  const padP = pop(t, pinAt - 0.1, 0.25);
  const x = lerp(1300, 0, fly), r = lerp(35, -6, fly);
  return (
    <>
      <Abs style={{ left: 150, top: 250, width: 780, height: 330, borderRadius: 30, transform: `translateX(${x}px) rotate(${r}deg) rotateX(${Math.sin(t * 2) * 4}deg)`, background: `linear-gradient(135deg,${colors[0]} 0%,${colors[1]} 55%,${colors[2]} 100%)`, border: "3px solid rgba(255,255,255,.7)", boxShadow: "0 28px 60px rgba(0,0,0,.6)", overflow: "hidden" }}>
        <Abs style={{ left: -100, top: -100, width: 500, height: 500, borderRadius: 250, background: "radial-gradient(circle, rgba(255,255,255,.22), rgba(255,255,255,0) 70%)" }} />
        <Abs style={{ left: 44, top: 54, width: 92, height: 70, borderRadius: 12, background: "linear-gradient(135deg,#ffe58a,#c99a1e)" }} />
        {logo && <Abs style={{ right: 36, top: 30 }}><Img src={pub(logo)!} style={{ width: 120, height: 120 }} /></Abs>}
        <Abs style={{ left: 44, top: 170, fontFamily: BARLOW, fontWeight: 800, fontSize: 64, color: "#fff", letterSpacing: 8 }}>{number}</Abs>
        <Abs style={{ left: 44, top: 252, fontFamily: BARLOW, fontWeight: 600, fontSize: 36, color: "rgba(255,255,255,.8)", letterSpacing: 4 }}>{caption}</Abs>
        <Abs style={{ right: 40, top: 246, fontFamily: ANTON, fontSize: 44, color: "#fff", letterSpacing: 2 }}>{network}</Abs>
      </Abs>
      <Abs style={{ left: 280, top: 610, width: 520, transform: `scale(${padP})`, ...glass1, padding: "16px 0 20px", textAlign: "center" }}>
        <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 38, color: "rgba(255,255,255,.7)", letterSpacing: 6 }}>{pinLabel}</div>
        <div style={{ display: "flex", justifyContent: "center", gap: 30, marginTop: 8 }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} style={{ width: 62, height: 62, borderRadius: 31, border: "5px solid #fff", background: i < dots ? "#fff" : "transparent", transform: `scale(${i < dots ? 1 + 0.3 * Math.max(0, 1 - (t - pinAt - i * 0.14) / 0.1) : 1})` }} />
          ))}
        </div>
      </Abs>
    </>
  );
};

export const BalanceChip: React.FC<{ dur: number; label?: string; from?: number; lowBelow?: number; format?: (n: number) => string }> = ({ dur, label = "BANK BALANCE", from = 48500, lowBelow = 12000, format = money }) => {
  const t = useSec();
  const enter = eBack(prog(t, 0, 0.18), 1.6);
  const v = from * (1 - eInOut(prog(t, 0.05, dur - 0.05)));
  const low = v < lowBelow;
  const blink = low && Math.floor(t * 10) % 2 === 0;
  return (
    <Abs style={{ left: 180, top: 300, width: 720, transform: `scale(${enter})`, ...glass1, border: `3px solid ${low ? RED : "rgba(255,255,255,.2)"}`, padding: "18px 0 22px", textAlign: "center" }}>
      <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 38, color: "rgba(255,255,255,.65)", letterSpacing: 8 }}>{label}</div>
      <div style={{ fontFamily: ANTON, fontSize: 150, lineHeight: 1.05, color: low ? (blink ? "#fff" : RED) : GREEN, letterSpacing: 2 }}>{format(v)}</div>
    </Abs>
  );
};

export const Kangali: React.FC<{ word?: string; sub?: string }> = ({ word: text = "KANGALI", sub = "BALANCE: ₹0" }) => {
  const t = useSec();
  const slam = eBack(prog(t, 0, 0.12), 2.8);
  const out = 1 - eIn(prog(t, 0.72, 0.85));
  const g = t < 0.5 ? Math.sin(t * 140) : 0;
  const jx = (rnd(Math.floor(t * 30)) - 0.5) * 36 * (t < 0.5 ? 1 : 0.2);
  const word = (extra: React.CSSProperties) => (
    <div style={{ position: "absolute", left: 0, top: 0, width: W, textAlign: "center", fontFamily: ANTON, fontSize: 262, lineHeight: 1, letterSpacing: 2, ...extra }}>{text}</div>
  );
  return (
    <Fill style={{ opacity: out, background: `rgba(0,0,0,${0.35 * (1 - prog(t, 0.5, 0.8))})` }}>
      <Abs style={{ left: 0, top: 330, width: W, height: 300, transform: `scale(${lerp(2.6, 1, slam)}) rotate(${(1 - slam) * -8 + g * 0.8}deg)` }}>
        {word({ color: "#00e5ff", transform: `translate(${-14 + jx}px, 0)`, mixBlendMode: "screen", opacity: 0.9 })}
        {word({ color: RED, transform: `translate(${14 - jx}px, 0)`, mixBlendMode: "screen", opacity: 0.9 })}
        {word({ color: "#fff", transform: `translate(${jx * 0.3}px, 0)`, ...strokeText(10, "#000") })}
        <Abs style={{ left: 0, top: 128, width: W, height: 10, background: "#fff", opacity: t < 0.4 && Math.floor(t * 24) % 3 === 0 ? 0.9 : 0, transform: `translateY(${rnd(Math.floor(t * 30), 4) * 120}px)` }} />
      </Abs>
      <Abs style={{ left: 0, top: 596, width: W, textAlign: "center", fontFamily: BARLOW, fontWeight: 800, fontSize: 58, color: YEL, letterSpacing: 10, opacity: prog(t, 0.2, 0.32), ...strokeText(8) }}>{sub}</Abs>
    </Fill>
  );
};

const Sms: React.FC<{ y: number; at: number; title: string; body: string; amount: string; col: string; logo?: string; icon?: string }> = ({ y, at, title, body, amount, col, logo, icon }) => {
  const t = useSec();
  const k = eBack(prog(t, at, at + 0.3), 1.5);
  if (t < at) return null;
  return (
    <Abs style={{ left: 410, top: y, width: 600, transform: `translateX(${(1 - k) * 300}px) scale(${0.9 + 0.1 * k})`, opacity: c01(k * 2), transformOrigin: "100% 50%" }}>
      <div style={{ ...glass, borderRadius: 24, padding: "16px 20px", display: "flex", gap: 16, alignItems: "center", borderLeft: `10px solid ${col}` }}>
        <div style={{ width: 84, height: 84, borderRadius: 42, background: logo ? "#0b0b0f" : "#fff", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", border: "3px solid rgba(255,255,255,.3)", overflow: "hidden", fontSize: 50, fontFamily: EMOJI }}>
          {logo ? <Img src={pub(logo)!} style={{ width: 62, height: 62 }} /> : icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 28, color: "rgba(255,255,255,.65)", letterSpacing: 2 }}>{title}</div>
          <div style={{ fontFamily: ANTON, fontSize: 52, color: col, letterSpacing: 1, lineHeight: 1.1 }}>{amount}</div>
          <div style={{ fontFamily: BARLOW, fontWeight: 600, fontSize: 28, color: "#fff" }}>{body}</div>
        </div>
      </div>
    </Abs>
  );
};
export const Salary: React.FC<{ t1: number; t2: number; dur?: number; calendar?: string; creditTitle?: string; creditAmount?: string; creditBody?: string; creditIcon?: string; debitTitle?: string; debitAmount?: string; debitBody?: string; debitIcon?: string; logo?: string }> = ({ t1, t2, calendar = "TAREEKH", creditTitle = "SALARY CREDITED", creditAmount = "+ ₹48,500", creditBody = "Account mein aa gaye 🎉", creditIcon = "🏦", debitTitle = "WESTSIDE · DEBIT ALERT", debitAmount = "− ₹48,500", debitBody = "Paid at Westside counter", debitIcon = "💳", logo }) => {
  const t = useSec();
  const day = t >= t2 ? 2 : 1;
  const flip = prog(t, t2 - 0.12, t2 + 0.1);
  const rain = t < t2 - 0.1 ? c01(1 - prog(t, t2 - 0.5, t2 - 0.1)) : 0;
  const enter = eOut(prog(t, 0, 0.3));
  return (
    <>
      {t >= t1 && Array.from({ length: 16 }).map((_, i) => {
        const at = t1 + 0.04 * i;
        const age = t - at;
        if (age < 0) return null;
        const y = 220 + age * (520 + rnd(i) * 300);
        if (y > 780) return null;
        return <div key={i} style={{ position: "absolute", left: 40 + rnd(i, 2) * 960, top: y, fontSize: 70 + rnd(i, 4) * 30, fontFamily: EMOJI, opacity: rain, transform: `rotate(${(rnd(i, 5) - 0.5) * 80 + age * 160}deg)` }}>💸</div>;
      })}
      <Abs style={{ left: 70, top: 300, width: 310, opacity: enter, transform: `scale(${0.8 + 0.2 * enter})`, transformOrigin: "0 0" }}>
        <div style={{ background: "#fff", borderRadius: 26, overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,.6)", border: "4px solid #fff" }}>
          <div style={{ background: RED, color: "#fff", fontFamily: ANTON, fontSize: 48, letterSpacing: 6, textAlign: "center", padding: "10px 0 4px" }}>{calendar}</div>
          <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", perspective: 700 }}>
            <div style={{ fontFamily: ANTON, fontSize: 190, color: INK, lineHeight: 1, transform: `rotateX(${flip < 0.5 ? flip * 180 : (flip - 1) * 180}deg) scale(${day === 2 ? 1 + 0.15 * Math.max(0, 1 - (t - t2) / 0.3) : 1})` }}>{day}</div>
          </div>
        </div>
      </Abs>
      <Sms y={262} at={t1} title={creditTitle} amount={creditAmount} body={creditBody} col={GREEN} icon={creditIcon} />
      <Sms y={500} at={t2 + 0.1} title={debitTitle} amount={debitAmount} body={debitBody} col={RED} logo={logo} icon={debitIcon} />
    </>
  );
};
