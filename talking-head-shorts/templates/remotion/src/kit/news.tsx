// kit/news.tsx  news-style hook, ticker, glow-up wipe, 3D title.
// Hook         {title="BREAKING", sub="SARJAPUR NEWS", live="LIVE", color=RED}              slam in the first ~0.9 s
// NewsTicker   {tag="LIVE", label="SARJAPUR ALERT", headlines=[...], color=RED}              lower-third + scrolling crawl
// Makeup       {image?, logo?, label="HEAVY MAKEUP 💄"}                                      glow-up wipe on a photo from public/ (placeholder gradient without image), logo pops in
// RevealTitle  {line1="WESTSIDE", small="IS", line2="BACK", logo?, side1, side2, color1, color2}  CSS-3D extruded title, holds ~2 s
import React from "react";
import { Img } from "remotion";
import { W, YEL, RED, INK, ANTON, BARLOW, c01, prog, eOut, eIn, eInOut, eBack, lerp, rnd, pop, useSec, Fill, Abs, strokeText, pub } from "./lib";

export const Hook: React.FC<{ title?: string; sub?: string; live?: string; color?: string }> = ({ title = "BREAKING", sub = "SARJAPUR NEWS", live: liveLabel = "LIVE", color = RED }) => {
  const t = useSec();
  const slam = eBack(prog(t, 0, 0.14), 2.4);
  const live = Math.floor(t * 8) % 2 === 0;
  return (
    <>
      <Fill style={{ background: `radial-gradient(ellipse at 50% 30%, rgba(255,45,45,${0.5 * (1 - prog(t, 0, 0.9))}) 0%, rgba(255,45,45,0) 70%)` }} />
      <Abs style={{ left: 0, top: 300, width: W, transform: `translateX(${(1 - slam) * -W}px)` }}>
        <div style={{ margin: "0 60px", background: color, borderRadius: 14, padding: "10px 0 6px", textAlign: "center", boxShadow: "0 14px 0 rgba(0,0,0,.45)", border: "4px solid #fff" }}>
          <div style={{ fontFamily: ANTON, fontSize: 168, lineHeight: 1.0, color: "#fff", letterSpacing: 4 }}>{title}</div>
        </div>
        <div style={{ margin: "14px 60px 0 160px", background: "#fff", borderRadius: 12, padding: "8px 0 4px", textAlign: "center", boxShadow: "0 10px 0 rgba(0,0,0,.4)" }}>
          <div style={{ fontFamily: ANTON, fontSize: 84, lineHeight: 1.05, color: INK, letterSpacing: 3 }}>{sub}</div>
        </div>
      </Abs>
      <Abs style={{ left: 60, top: 226, display: "flex", alignItems: "center", gap: 12, opacity: pop(t, 0.12) > 0 ? 1 : 0 }}>
        <div style={{ width: 26, height: 26, borderRadius: 13, background: live ? color : "#7a1515", boxShadow: live ? "0 0 22px #ff2d2d" : "none" }} />
        <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 46, color: "#fff", letterSpacing: 5, ...strokeText(6) }}>{liveLabel}</div>
      </Abs>
    </>
  );
};

const HEADLINES = ["WESTSIDE LAUT RAHA HAI", "SARJAPUR MEIN BADI KHABAR", "NAYE COLLECTION KE SAATH", "WALLETS ON HIGH ALERT", "BREAKING: SHOPPING SEASON SHURU", "CREDIT CARDS TAKE COVER"];
export const NewsTicker: React.FC<{ tag?: string; label?: string; headlines?: string[]; color?: string }> = ({ tag = "LIVE", label = "SARJAPUR ALERT", headlines = HEADLINES, color = RED }) => {
  const t = useSec();
  const enter = eOut(prog(t, 0, 0.3));
  const crawl = headlines.map((h) => h + "   ●   ").join("");
  const x = -t * 340;
  return (
    <Abs style={{ left: 0, top: 300, width: W, transform: `translateY(${(1 - enter) * -60}px)`, opacity: enter }}>
      <div style={{ display: "flex", margin: "0 60px", boxShadow: "0 14px 40px rgba(0,0,0,.55)", borderRadius: 14, overflow: "hidden", border: "3px solid #fff" }}>
        <div style={{ background: color, padding: "6px 30px 2px", fontFamily: ANTON, fontSize: 70, color: "#fff", letterSpacing: 3 }}>{tag}</div>
        <div style={{ flex: 1, background: "#fff", padding: "6px 24px 2px", fontFamily: ANTON, fontSize: 70, color: INK, letterSpacing: 2, whiteSpace: "nowrap", overflow: "hidden" }}>{label}</div>
      </div>
      <div style={{ margin: "12px 60px 0", height: 70, background: INK, borderRadius: 12, overflow: "hidden", position: "relative", border: "2px solid rgba(255,255,255,.25)" }}>
        <div style={{ position: "absolute", top: 8, left: 0, transform: `translateX(${x}px)`, whiteSpace: "nowrap", fontFamily: BARLOW, fontWeight: 800, fontSize: 46, color: YEL, letterSpacing: 3 }}>{crawl}{crawl}</div>
      </div>
    </Abs>
  );
};

const PINK_GRAD = "linear-gradient(90deg,#FF4FA3,#B84DFF)";
export const Makeup: React.FC<{ image?: string; logo?: string; label?: string }> = ({ image, logo, label = "HEAVY MAKEUP 💄" }) => {
  const t = useSec();
  const enter = eBack(prog(t, 0, 0.2), 1.6);
  const wipe = eInOut(prog(t, 0.12, 0.62));
  const cw = 470, ch = 480, left = (W - cw) / 2, top = 262;
  const logoP = pop(t, 0.58, 0.28);
  const sparks = Array.from({ length: 14 }, (_, i) => i);
  const pic = (filter: string) => image
    ? <Img src={pub(image)!} style={{ position: "absolute", width: cw, height: cw * 1.78, left: 0, top: -cw * 0.55, objectFit: "cover", filter }} />
    : <div style={{ position: "absolute", width: cw, height: ch, left: 0, top: 0, background: "linear-gradient(160deg,#6b7385,#2b2f3a 60%,#14161c)", filter }} />;
  return (
    <Abs style={{ left, top, width: cw, height: ch, transform: `scale(${enter}) rotate(${(1 - enter) * -6}deg)` }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 26, overflow: "hidden", border: "6px solid #fff", boxShadow: "0 24px 60px rgba(0,0,0,.6)" }}>
        {pic("grayscale(.85) brightness(.8) contrast(.9)")}
        <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0)` }}>
          {pic("saturate(1.9) contrast(1.2) brightness(1.18) hue-rotate(-8deg)")}
          <Fill style={{ width: cw, height: ch, background: "linear-gradient(115deg, rgba(255,79,163,.28), rgba(255,212,0,.22))", mixBlendMode: "screen" }} />
        </div>
        <Abs style={{ left: wipe * cw - 5, top: 0, width: 10, height: ch, background: "#fff", boxShadow: "0 0 34px 10px rgba(255,255,255,.9)", opacity: wipe > 0 && wipe < 1 ? 1 : 0 }} />
      </div>
      {sparks.map((i) => {
        const a = prog(t, 0.2 + rnd(i) * 0.4, 0.5 + rnd(i) * 0.4);
        const s = Math.sin(a * Math.PI);
        return <Abs key={i} style={{ left: rnd(i, 2) * cw - 20, top: rnd(i, 3) * ch - 20, fontSize: 54, opacity: s, transform: `scale(${s}) rotate(${a * 120}deg)` }}>✨</Abs>;
      })}
      <Abs style={{ left: -20, top: -64, background: PINK_GRAD, borderRadius: 14, padding: "6px 22px 2px", fontFamily: ANTON, fontSize: 56, color: "#fff", letterSpacing: 2, transform: "rotate(-4deg)", boxShadow: "0 8px 0 rgba(0,0,0,.4)", border: "3px solid #fff" }}>{label}</Abs>
      {logo && (
        <Abs style={{ right: -34, bottom: -50, width: 190, height: 190, borderRadius: 95, background: "rgba(8,8,14,.92)", border: "4px solid #fff", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${logoP})`, boxShadow: "0 0 50px rgba(43,168,255,.65)" }}>
          <Img src={pub(logo)!} style={{ width: 140, height: 140 }} />
        </Abs>
      )}
    </Abs>
  );
};

const Extruded: React.FC<{ text: string; size: number; color: string; depth: number; sideColor: string }> = ({ text, size, color, depth, sideColor }) => (
  <div style={{ position: "relative", fontFamily: ANTON, fontSize: size, lineHeight: 1, letterSpacing: 4, whiteSpace: "nowrap", transformStyle: "preserve-3d" }}>
    {Array.from({ length: depth }, (_, i) => (
      <div key={i} style={{ position: "absolute", left: 0, top: 0, color: sideColor, transform: `translateZ(${-(i + 1) * 2}px)`, filter: `brightness(${1 - i / (depth * 1.6)})` }}>{text}</div>
    ))}
    <div style={{ position: "relative", color, textShadow: "0 0 30px rgba(255,255,255,.25)" }}>{text}</div>
  </div>
);
export const RevealTitle: React.FC<{ line1?: string; small?: string; line2?: string; logo?: string; color1?: string; color2?: string; side1?: string; side2?: string }> = ({ line1 = "WESTSIDE", small = "IS", line2 = "BACK", logo, color1 = "#fff", color2 = YEL, side1 = "#1c7fd0", side2 = "#a88900" }) => {
  const t = useSec();
  const inP = eOut(prog(t, 0.05, 0.75));
  const rotY = lerp(-70, -12, inP) + Math.sin(t * 2.2) * 5;
  const rotX = lerp(24, 8, inP);
  const scale = lerp(0.4, 1, eBack(prog(t, 0.05, 0.6), 1.5));
  const logoP = pop(t, 0.05, 0.4);
  const sweep = prog(t, 0.7, 1.3);
  const out = 1 - eIn(prog(t, 1.85, 2.05));
  return (
    <Fill style={{ opacity: out }}>
      {logo && (
        <Abs style={{ left: 0, top: 232, width: W, textAlign: "center", transform: `scale(${logoP})` }}>
          <Img src={pub(logo)!} style={{ width: 200, height: 200, filter: "drop-shadow(0 0 28px rgba(43,168,255,.9)) drop-shadow(0 10px 0 rgba(0,0,0,.4))" }} />
        </Abs>
      )}
      <Abs style={{ left: 0, top: 460, width: W, display: "flex", flexDirection: "column", alignItems: "center", perspective: 1100 }}>
        <div style={{ transform: `rotateY(${rotY}deg) rotateX(${rotX}deg) scale(${scale})`, transformStyle: "preserve-3d", display: "flex", flexDirection: "column", alignItems: "center", gap: 0, opacity: c01(inP * 3) }}>
          <Extruded text={line1} size={190} color={color1} depth={26} sideColor={side1} />
          <div style={{ display: "flex", gap: 26, alignItems: "baseline", marginTop: 6 }}>
            {small ? <Extruded text={small} size={120} color={color2} depth={20} sideColor={side2} /> : null}
            <Extruded text={line2} size={190} color={color2} depth={26} sideColor={side2} />
          </div>
        </div>
        <Abs style={{ left: lerp(-300, 1300, sweep), top: 0, width: 140, height: 420, background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.55), rgba(255,255,255,0))", transform: "skewX(-20deg)", mixBlendMode: "overlay" }} />
      </Abs>
    </Fill>
  );
};
