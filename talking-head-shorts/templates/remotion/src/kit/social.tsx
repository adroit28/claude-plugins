// kit/social.tsx  people / reaction beats.
// ShareSheet {sendAt, title="SHARE WITH", friends=[[emoji,name,color]...x4], selected="SELECTED", send="SEND", sent="SENT ✓"}   contacts ticked one by one, SEND fires at sendAt
// ChatCTA    {title="SHOPPING PAGLU DOST", avatar="😎", msgs=[[at_s, mine, text]...]}                                          chat bubbles
// Shaheed    {text="SHAHEED", icon="👛", candle="🪔"}                                                                          garlanded memorial frame, comic beat
// Hunger     {title="SHOPPING BHOOK METER", sub="LAST SHOPPING: 2 MAHINE PEHLE", icon="🍽️"}                                    hunger meter to 100% with cobweb
// Langar     {paneerAt, caption="PANEER BANT RAHA HO"}                                                                         thali + swarming hands, freeze at paneerAt
// Lion       {s (scene start, output s), chunkId="B1", roarAt=36.95 (output s), roarText="ROARRR!"}                            mane ring on the tracked face of that chunk (needs track.json)
// MautCrowd  {title="MAUT KA NANGA NAACH", logo?}                                                                              shoppers stampede into a storefront
import React from "react";
import { Img, Easing, interpolate } from "remotion";
import { W, TL, YEL, RED, BLUE, GREEN, PINK, ANTON, BARLOW, EMOJI, c01, prog, eOut, eIn, eInOut, eBack, lerp, rnd, pop, useSec, Fill, Abs, glass, strokeText, faceAt, pub } from "./lib";

export const ShareSheet: React.FC<{ sendAt: number; title?: string; friends?: string[][]; selected?: string; send?: string; sent?: string }> = ({ sendAt, title = "SHARE WITH", friends = [["🤪", "Paglu Dost 1", "#FF8A3D"], ["😜", "Paglu Dost 2", "#B26BFF"], ["🥴", "Paglu Dost 3", "#2BC4A8"], ["🤡", "Paglu Dost 4", "#FF4FA3"]], selected = "SELECTED", send = "SEND", sent: sentLabel = "SENT ✓" }) => {
  const t = useSec();
  const slide = eOut(prog(t, 0, 0.32));
  const tickT = (i: number) => 0.55 + i * 0.28;
  const pressed = t >= sendAt - 0.08 && t < sendAt + 0.1;
  const sent = t >= sendAt;
  const fly = eIn(prog(t, sendAt, sendAt + 0.5));
  return (
    <Abs style={{ left: 70, top: 290, width: 940, transform: `translateY(${(1 - slide) * -80}px)`, opacity: slide }}>
      <div style={{ ...glass, padding: "26px 32px 30px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontFamily: ANTON, fontSize: 60, color: "#fff", letterSpacing: 2 }}>{title}</div>
          <div style={{ fontFamily: ANTON, fontSize: 40, color: YEL, letterSpacing: 2, opacity: sent ? 0.3 : 1 }}>
            {friends.filter((_, i) => t >= tickT(i)).length} {selected}
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 26 }}>
          {friends.map(([em, nm, col], i) => {
            const k = pop(t, tickT(i), 0.24);
            return (
              <div key={i} style={{ width: 196, textAlign: "center", position: "relative" }}>
                <div style={{ width: 150, height: 150, margin: "0 auto", borderRadius: 75, background: col as string, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 88, fontFamily: EMOJI, boxShadow: k > 0 ? `0 0 0 6px #fff, 0 0 34px ${col}` : "none", transform: `scale(${1 + 0.06 * Math.min(1, k)})` }}>{em}</div>
                <div style={{ position: "absolute", left: 110, top: 100, width: 52, height: 52, borderRadius: 26, background: GREEN, border: "4px solid #fff", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${k})`, color: "#fff", fontFamily: ANTON, fontSize: 34 }}>✓</div>
                <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 34, color: "#fff", marginTop: 12, letterSpacing: 1 }}>{nm}</div>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 26, display: "flex", justifyContent: "center", position: "relative", height: 100 }}>
          <div style={{ width: 520, height: 96, borderRadius: 48, background: sent ? GREEN : BLUE, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: ANTON, fontSize: 56, color: "#fff", letterSpacing: 4, transform: `scale(${pressed ? 0.92 : 1})`, boxShadow: `0 8px 0 rgba(0,0,0,.4), 0 0 ${pressed ? 50 : 0}px ${BLUE}` }}>
            {sent ? sentLabel : send}
          </div>
        </div>
      </div>
      {sent && fly < 1 && (
        <div style={{ position: "absolute", left: 420 + fly * 700, top: 330 - fly * 420, fontSize: 140, fontFamily: EMOJI, transform: `rotate(${-20 - fly * 15}deg) scale(${1 - fly * 0.5})`, opacity: 1 - fly * 0.6 }}>📨</div>
      )}
    </Abs>
  );
};

export const ChatCTA: React.FC<{ title?: string; avatar?: string; msgs?: [number, boolean, string][] }> = ({ title = "SHOPPING PAGLU DOST", avatar = "😎", msgs = [[0.15, false, "bhai ye dekh 👀"], [0.6, false, "Westside wapas aa raha hai!!"], [1.1, true, "sach mein?? 😳"], [1.55, true, "chal sath chalte hain 🛍️"]] }) => {
  const t = useSec();
  const k = eOut(prog(t, 0, 0.25));
  return (
    <Abs style={{ left: 60, top: 250, width: 960, opacity: k, transform: `translateY(${(1 - k) * -40}px)` }}>
      <div style={{ ...glass, padding: "22px 26px 26px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, borderBottom: "2px solid rgba(255,255,255,.12)", paddingBottom: 14, marginBottom: 14 }}>
          <div style={{ width: 70, height: 70, borderRadius: 35, background: PINK, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 44, fontFamily: EMOJI }}>{avatar}</div>
          <div style={{ fontFamily: ANTON, fontSize: 46, color: "#fff", letterSpacing: 2 }}>{title}</div>
          <div style={{ marginLeft: "auto", width: 18, height: 18, borderRadius: 9, background: GREEN, boxShadow: `0 0 12px ${GREEN}` }} />
        </div>
        {msgs.map(([at, mine, txt], i) => {
          const p = pop(t, at, 0.22);
          if (p <= 0) return <div key={i} style={{ height: 76 }} />;
          return (
            <div key={i} style={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start", marginBottom: 10, transform: `scale(${p})`, transformOrigin: mine ? "100% 50%" : "0 50%" }}>
              <div style={{ background: mine ? BLUE : "#2c2c38", color: "#fff", fontFamily: BARLOW, fontWeight: 800, fontSize: 46, padding: "6px 28px 2px", borderRadius: 34, borderBottomRightRadius: mine ? 8 : 34, borderBottomLeftRadius: mine ? 34 : 8, letterSpacing: 0.5, lineHeight: 1.3 }}>{txt}</div>
            </div>
          );
        })}
      </div>
    </Abs>
  );
};

export const Shaheed: React.FC<{ text?: string; icon?: string; candle?: string }> = ({ text = "SHAHEED", icon = "👛", candle = "🪔" }) => {
  const t = useSec();
  const k = eBack(prog(t, 0, 0.35), 1.3);
  const drift = t * 10;
  const garland = Array.from({ length: 15 }).map((_, i) => {
    const u = i / 14;
    const x = 20 + u * 400;
    const y = 40 + Math.sin(u * Math.PI) * 120;
    return <div key={i} style={{ position: "absolute", left: x - 20, top: y - 20, width: 40, height: 40, borderRadius: 20, background: i % 3 === 0 ? "#FF7A00" : i % 3 === 1 ? YEL : "#FF4A1C", boxShadow: "inset 0 -6px 0 rgba(0,0,0,.2), 0 3px 6px rgba(0,0,0,.4)" }} />;
  });
  return (
    <>
      <Fill style={{ background: "rgba(0,0,0,.45)", opacity: eOut(prog(t, 0, 0.2)) }} />
      <Abs style={{ left: 330, top: 236, width: 420, transform: `scale(${0.4 + 0.6 * k}) rotate(${(1 - k) * -8}deg)`, opacity: c01(k * 3), transformOrigin: "50% 40%" }}>
        <div style={{ position: "relative", padding: 16, background: "linear-gradient(135deg,#5b3a1a,#2b1a0a)", borderRadius: 10, boxShadow: "0 18px 50px rgba(0,0,0,.7)", border: "3px solid #d9b25c" }}>
          <div style={{ height: 330, background: "radial-gradient(circle at 50% 40%, #e8e8e8, #8a8a8a)", display: "flex", alignItems: "center", justifyContent: "center", filter: "grayscale(1)", fontSize: 190, fontFamily: EMOJI }}>{icon}</div>
          <div style={{ position: "absolute", left: -6, top: -20, width: 430, height: 190, pointerEvents: "none" }}>{garland}</div>
          <div style={{ position: "absolute", right: 26, top: 24, fontSize: 44, fontFamily: EMOJI, transform: `translateY(${Math.sin(drift) * 3}px)` }}>{candle}</div>
        </div>
        <div style={{ textAlign: "center", marginTop: 10, fontFamily: ANTON, fontSize: 104, color: "#fff", letterSpacing: 6, ...strokeText(12), textShadow: "0 8px 0 rgba(0,0,0,.5)", transform: `scale(${pop(t, 0.22, 0.25)})` }}>{text}</div>
      </Abs>
    </>
  );
};

export const Hunger: React.FC<{ title?: string; sub?: string; icon?: string }> = ({ title = "SHOPPING BHOOK METER", sub = "LAST SHOPPING: 2 MAHINE PEHLE", icon = "🍽️" }) => {
  const t = useSec();
  const k = eOut(prog(t, 0, 0.3));
  const level = eInOut(prog(t, 0.2, 1.7));
  const pct = Math.round(level * 100);
  const col = level < 0.5 ? YEL : level < 0.8 ? "#FF8A00" : RED;
  const shake = level > 0.8 ? Math.sin(t * 90) * 5 : 0;
  const spider = eOut(prog(t, 0.5, 1.1));
  return (
    <Abs style={{ left: 70, top: 270, width: 940, transform: `translate(${shake}px, ${(1 - k) * -60}px)`, opacity: k }}>
      <div style={{ ...glass, padding: "24px 32px 28px", position: "relative", overflow: "hidden" }}>
        <svg width="260" height="260" viewBox="0 0 260 260" style={{ position: "absolute", right: 0, top: 0, opacity: 0.7 }}>
          {[0, 1, 2, 3, 4, 5].map((i) => <line key={i} x1={260} y1={0} x2={260 - 250 * Math.cos((i / 5) * Math.PI / 2)} y2={250 * Math.sin((i / 5) * Math.PI / 2)} stroke="#fff" strokeWidth="2" />)}
          {[1, 2, 3, 4].map((r) => <path key={r} d={Array.from({ length: 6 }).map((_, i) => `${i ? "L" : "M"}${260 - r * 58 * Math.cos((i / 5) * Math.PI / 2)} ${r * 58 * Math.sin((i / 5) * Math.PI / 2)}`).join(" ")} stroke="#fff" strokeWidth="2" fill="none" />)}
        </svg>
        <div style={{ position: "absolute", right: 120, top: 0, width: 3, height: spider * 150, background: "#ddd" }} />
        <div style={{ position: "absolute", right: 90, top: spider * 150 - 10, fontSize: 64, fontFamily: EMOJI }}>🕷️</div>
        <div style={{ fontFamily: ANTON, fontSize: 58, color: "#fff", letterSpacing: 2 }}>{title}</div>
        <div style={{ fontFamily: BARLOW, fontWeight: 800, fontSize: 36, color: "rgba(255,255,255,.65)", letterSpacing: 2 }}>{sub}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 24 }}>
          <div style={{ fontSize: 80, fontFamily: EMOJI }}>{icon}</div>
          <div style={{ flex: 1, height: 74, borderRadius: 37, background: "#1a1a22", border: "4px solid #fff", overflow: "hidden" }}>
            <div style={{ width: `${Math.max(4, pct)}%`, height: "100%", background: `linear-gradient(90deg, ${YEL}, ${col})`, boxShadow: `0 0 30px ${col}` }} />
          </div>
        </div>
        <div style={{ fontFamily: ANTON, fontSize: 130, lineHeight: 1.0, color: col, textAlign: "center", marginTop: 12, ...strokeText(10) }}>{pct}%{level > 0.97 && Math.floor(t * 10) % 2 === 0 ? " 😵" : ""}</div>
      </div>
    </Abs>
  );
};

export const Langar: React.FC<{ paneerAt: number; caption?: string }> = ({ paneerAt, caption = "PANEER BANT RAHA HO" }) => {
  const t = useSec();
  const enter = eOut(prog(t, 0, 0.25));
  const frozen = t >= paneerAt;
  const hands = Array.from({ length: 10 });
  const toCentre = eInOut(prog(t, 0.1, paneerAt));
  const katori = (x: number, y: number, col: string, em: string, big = false) => (
    <div style={{ position: "absolute", left: x, top: y, width: big ? 150 : 120, height: big ? 150 : 120, borderRadius: "50%", background: col, border: "6px solid #d8d8e0", boxShadow: "inset 0 -10px 0 rgba(0,0,0,.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: big ? 84 : 64, fontFamily: EMOJI }}>{em}</div>
  );
  return (
    <>
      <Abs style={{ left: 290, top: 350, width: 500, height: 500, opacity: enter, transform: `scale(${0.8 * (0.7 + 0.3 * enter)}) rotate(${frozen ? 0 : t * 4}deg)`, transformOrigin: "50% 0" }}>
        <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "radial-gradient(circle at 40% 35%, #f4f4f8, #b4b4c0)", border: "10px solid #8a8a98", boxShadow: "0 22px 50px rgba(0,0,0,.6)" }} />
        {katori(80, 100, "#C98A2E", "🍛")}
        {katori(300, 100, "#E8C26A", "🥘")}
        {katori(80, 290, "#B9431F", "🫘")}
        {katori(300, 290, "#F2E6B5", "🍚")}
        <div style={{ position: "absolute", left: 175, top: 195, width: 150, height: 150, borderRadius: "50%", background: "#FFC94A", border: "8px solid #fff", boxShadow: frozen ? `0 0 60px ${YEL}` : "none", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 76, fontFamily: EMOJI }}>🧀</div>
      </Abs>
      {hands.map((_, i) => {
        const a = (i / hands.length) * Math.PI * 2 + 0.3;
        const r = lerp(620, 150, toCentre) + (frozen ? 0 : Math.sin(t * 20 + i) * 14);
        const x = 540 + Math.cos(a) * r * 1.0 - 50;
        const y = 550 + Math.sin(a) * r * 0.6 - 50;
        if (y < 200) return null;
        return <div key={i} style={{ position: "absolute", left: x, top: y, fontSize: 100, fontFamily: EMOJI, transform: `rotate(${(a * 180) / Math.PI + 90}deg)`, filter: "drop-shadow(0 8px 6px rgba(0,0,0,.5))" }}>{i % 2 ? "🫳" : "🤲"}</div>;
      })}
      {frozen && (
        <Abs style={{ left: 0, top: 236, width: W, textAlign: "center", fontFamily: ANTON, fontSize: 84, color: YEL, letterSpacing: 3, ...strokeText(12), textShadow: "0 8px 0 rgba(0,0,0,.5)", transform: `scale(${pop(t, paneerAt, 0.2)}) rotate(-3deg)` }}>{caption}</Abs>
      )}
    </>
  );
};

export const Lion: React.FC<{ s: number; chunkId?: string; roarAt?: number; roarText?: string }> = ({ s, chunkId = "B1", roarAt = 36.95, roarText = "ROARRR!" }) => {
  const t = useSec();
  const B1 = TL.chunks.find((c: any) => c.id === chunkId);
  if (!B1) throw new Error(`Lion: no chunk with id "${chunkId}" in timeline.json`);
  const clip = B1.clip;
  const srcT = B1.a + t + (s - B1.o);
  const [cx0, cy0, fw0] = faceAt(clip, srcT);
  // replicate the Chunk camera: scale around the clip's anchor face
  const [ox, oy] = faceAt(clip, B1.a + 0.4);
  const zk: number[][] = B1.z;
  const z = interpolate(srcT, zk.map((k) => k[0]), zk.map((k) => k[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const cx = ox + (cx0 - ox) * z, cy = oy + (cy0 - oy) * z, fw = fw0 * z;
  const grow = eBack(prog(t, 0, 0.3), 1.6);
  const roarT = roarAt - s;
  const roar = t >= roarT ? Math.sin((t - roarT) * 55) * Math.max(0, 1 - (t - roarT) / 0.5) : 0;
  const rx = fw * 0.6, ry = fw * 0.78;
  const spikes = 26;
  const pts: string[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const a = (i / (spikes * 2)) * Math.PI * 2;
    const out = i % 2 === 0 ? 1.0 + rnd(i) * 0.14 + roar * 0.05 : 0.8;
    pts.push(`${Math.cos(a) * fw * 1.02 * out},${Math.sin(a) * fw * 1.18 * out}`);
  }
  const hole = `M ${rx} 0 A ${rx} ${ry} 0 1 0 ${-rx} 0 A ${rx} ${ry} 0 1 0 ${rx} 0 Z`;
  const outer = "M " + pts.join(" L ") + " Z";
  const inner: string[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const a = (i / (spikes * 2)) * Math.PI * 2 + 0.06;
    const out = i % 2 === 0 ? 0.84 : 0.7;
    inner.push(`${Math.cos(a) * fw * 1.02 * out},${Math.sin(a) * fw * 1.18 * out}`);
  }
  const innerPath = "M " + inner.join(" L ") + " Z";
  const sz = fw * 3;
  return (
    <>
      <Abs style={{ left: cx - sz / 2, top: cy - sz / 2, width: sz, height: sz, transform: `scale(${grow}) rotate(${roar * 1.5}deg)`, opacity: c01(grow * 2) }}>
        <svg width={sz} height={sz} viewBox={`${-sz / 2} ${-sz / 2} ${sz} ${sz}`} style={{ overflow: "visible" }}>
          <defs>
            <radialGradient id="mane" cx="50%" cy="50%" r="50%">
              <stop offset="40%" stopColor="#7a3b10" />
              <stop offset="100%" stopColor="#c8741f" />
            </radialGradient>
          </defs>
          <circle cx={-fw * 0.78} cy={-fw * 0.9} r={fw * 0.2} fill="#c8741f" stroke="#4a210a" strokeWidth={8} />
          <circle cx={fw * 0.78} cy={-fw * 0.9} r={fw * 0.2} fill="#c8741f" stroke="#4a210a" strokeWidth={8} />
          <circle cx={-fw * 0.78} cy={-fw * 0.9} r={fw * 0.1} fill="#f2a46a" />
          <circle cx={fw * 0.78} cy={-fw * 0.9} r={fw * 0.1} fill="#f2a46a" />
          <path d={outer + " " + hole} fill="url(#mane)" fillRule="evenodd" stroke="#4a210a" strokeWidth={7} strokeLinejoin="round" />
          <path d={innerPath + " " + hole} fill="#e8a13a" fillRule="evenodd" opacity={0.55} />
          <path d={hole} fill="none" stroke="rgba(74,33,10,.9)" strokeWidth={6} />
        </svg>
      </Abs>
      <Abs style={{ left: 0, top: 330, width: W, textAlign: "center", transform: `scale(${pop(t, roarT, 0.18)}) rotate(${-3 + roar * 2}deg)`, fontFamily: ANTON, fontSize: 150, color: YEL, letterSpacing: 6, ...strokeText(14), textShadow: "0 10px 0 rgba(0,0,0,.5)" }}>{t >= roarT ? roarText : ""}</Abs>
    </>
  );
};

export const MautCrowd: React.FC<{ title?: string; logo?: string }> = ({ title = "MAUT KA NANGA NAACH", logo }) => {
  const t = useSec();
  const enter = eOut(prog(t, 0, 0.2));
  const runners = Array.from({ length: 21 });
  return (
    <>
      <Abs style={{ left: 0, top: 236, width: W, textAlign: "center", fontFamily: ANTON, fontSize: 92, color: YEL, letterSpacing: 3, ...strokeText(12), textShadow: "0 8px 0 rgba(0,0,0,.5)", transform: `scale(${pop(t, 0, 0.2)}) rotate(${Math.sin(t * 30) * 1.2}deg)` }}>{title}</Abs>
      <Abs style={{ left: 740, top: 360, width: 300, height: 380, opacity: enter, transform: `scale(${0.8 + 0.2 * enter})`, transformOrigin: "100% 100%" }}>
        <div style={{ height: 120, background: "#0b0b0f", border: "5px solid #fff", borderRadius: "16px 16px 0 0", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 40px rgba(255,255,255,.35)" }}>
          {logo ? <Img src={pub(logo)!} style={{ width: 96, height: 96 }} /> : <span style={{ fontSize: 64, fontFamily: EMOJI }}>🏬</span>}
        </div>
        <div style={{ height: 260, background: "linear-gradient(180deg,#2b2b36,#14141a)", border: "5px solid #fff", borderTop: "none", display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 10, paddingBottom: 0 }}>
          <div style={{ width: 120, height: 210, background: "rgba(255,230,150,.85)", boxShadow: "0 0 50px rgba(255,214,0,.7)", borderRadius: "8px 8px 0 0" }} />
        </div>
      </Abs>
      {runners.map((_, i) => {
        const row = i % 3;
        const start = (i * 0.037) % 0.5;
        const x = lerp(-120, 760 + rnd(i) * 40, c01((t - start) / 0.85));
        const vis = x < 800 ? 1 : 0;
        const y = 470 + row * 85 + Math.abs(Math.sin(t * 22 + i)) * -22;
        return <div key={i} style={{ position: "absolute", left: x, top: y, fontSize: 130 - row * 8, fontFamily: EMOJI, opacity: vis, filter: "drop-shadow(0 8px 6px rgba(0,0,0,.5))" }}>{i % 3 === 0 ? "🏃‍♀️" : i % 3 === 1 ? "🏃" : "🏃‍♂️"}</div>;
      })}
      {runners.slice(0, 9).map((_, i) => {
        const x = lerp(0, 700, c01((t - (i * 0.05)) / 0.85));
        return <div key={"b" + i} style={{ position: "absolute", left: x + 40, top: 440 + (i % 3) * 85, fontSize: 80, fontFamily: EMOJI, opacity: x < 700 ? 1 : 0 }}>🛍️</div>;
      })}
      <Abs style={{ left: 40, top: 700, width: 800, height: 12, background: "repeating-linear-gradient(90deg, #fff 0 40px, transparent 40px 80px)", backgroundPosition: `${-t * 900}px 0`, opacity: 0.5 }} />
    </>
  );
};
