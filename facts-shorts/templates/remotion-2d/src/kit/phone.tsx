import React from "react";
import { ramp, pop, enter } from "./anim";
import { GOLD, PIC_TOP } from "./props";

// 0.8.0 phone screens: generic text props, no brand content. Times are seconds (absolute, like the rest of the
// kit). All three are cards in the picture band; give each an `until` so nothing stays to the last frame.
const BLUE = "#2ba8ff", GREEN = "#1fd66b", PINK = "#ff4fa3";
const card: React.CSSProperties = {
  background: "linear-gradient(180deg, rgba(20,20,28,.9), rgba(8,8,12,.94))", border: "2px solid rgba(255,255,255,.14)",
  boxShadow: "0 18px 50px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.12)", borderRadius: 28,
};
const life = (t: number, a: number, until?: number) => (until === undefined ? 0 : ramp(t, until, until + 0.3));

// A chat: `msgs` = [time, mine, text][]; each bubble pops in at its time (theirs left grey, yours right blue).
export const ChatBubbles = ({ t, a, title = "FRIENDS", avatar = "😎", msgs, top = PIC_TOP + 20, until }: {
  t: number; a: number; title?: string; avatar?: string; msgs: [number, boolean, string][]; top?: number; until?: number;
}) => {
  if (t < a) return null;
  const gone = life(t, a, until); if (gone >= 1) return null;
  const k = ramp(t, a, a + 0.25, 0, 1, (x) => 1 - Math.pow(1 - x, 3));
  return (
    <div style={{ position: "absolute", left: 60, top, width: 960, opacity: k * (1 - gone), transform: `translateY(${(1 - k) * -40}px)` }}>
      <div style={{ ...card, padding: "22px 26px 26px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, borderBottom: "2px solid rgba(255,255,255,.12)", paddingBottom: 14, marginBottom: 14 }}>
          <div style={{ width: 70, height: 70, borderRadius: 35, background: PINK, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 44 }}>{avatar}</div>
          <div style={{ fontFamily: "Anton", fontSize: 46, color: "#fff", letterSpacing: 2 }}>{title}</div>
          <div style={{ marginLeft: "auto", width: 18, height: 18, borderRadius: 9, background: GREEN, boxShadow: `0 0 12px ${GREEN}` }} />
        </div>
        {msgs.map(([at, mine, txt], i) => {
          const p = pop(t, at, 0.22);
          if (t < at) return <div key={i} style={{ height: 76 }} />;
          return (
            <div key={i} style={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start", marginBottom: 10, transform: `scale(${p})`, transformOrigin: mine ? "100% 50%" : "0 50%" }}>
              <div style={{ background: mine ? BLUE : "#2c2c38", color: "#fff", fontFamily: "Barlow", fontSize: 46, padding: "6px 28px 2px", borderRadius: 34,
                borderBottomRightRadius: mine ? 8 : 34, borderBottomLeftRadius: mine ? 34 : 8, lineHeight: 1.3 }}>{txt}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// A phone notification dropping in from the top edge (pair with the notify sfx).
export const Notify = ({ t, a, app = "NEWS", title, body, icon = "🔔", top = PIC_TOP, until, springy }: {
  t: number; a: number; app?: string; title: string; body?: string; icon?: string; top?: number; until?: number; springy?: boolean;
}) => {
  if (t < a) return null;
  const gone = life(t, a, until); if (gone >= 1) return null;
  const k = enter(t, a, springy), y = (1 - Math.min(1, ramp(t, a, a + 0.3))) * -300;
  return (
    <div style={{ position: "absolute", left: 60, top: top + y, width: 960, opacity: (1 - gone) * Math.min(1, ramp(t, a, a + 0.1)), transform: `scale(${0.9 + 0.1 * k})`, transformOrigin: "50% 0" }}>
      <div style={{ ...card, borderRadius: 36, padding: "22px 26px", display: "flex", gap: 22, alignItems: "center", background: "rgba(34,34,44,.96)" }}>
        <div style={{ width: 110, height: 110, borderRadius: 26, background: BLUE, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 70, flex: "none" }}>{icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "Barlow", fontSize: 32, color: "rgba(255,255,255,.6)", letterSpacing: 3 }}><span>{app}</span><span>now</span></div>
          <div style={{ fontFamily: "Anton", fontSize: 54, color: "#fff", lineHeight: 1.1 }}>{title}</div>
          {body && <div style={{ fontFamily: "BarlowSemi", fontSize: 40, color: "rgba(255,255,255,.85)", lineHeight: 1.15 }}>{body}</div>}
        </div>
      </div>
    </div>
  );
};

// Share sheet as an ending CTA: contacts get ticked one by one from `a`, SEND is pressed at `sendAt` and an envelope flies off.
// `friends` = [emoji, name, colour][] (up to 4). Time the ticks with `tickAt` (seconds, one per contact) or let them run every 0.28 s.
export const ShareSheet = ({ t, a, sendAt, title = "SHARE WITH", friends = [["😎", "Friend 1", "#FF8A3D"], ["🙂", "Friend 2", "#B26BFF"], ["😄", "Friend 3", "#2BC4A8"], ["🤓", "Friend 4", "#FF4FA3"]],
  selected = "SELECTED", send = "SEND", sent = "SENT ✓", tickAt, top = PIC_TOP, until }: {
  t: number; a: number; sendAt: number; title?: string; friends?: string[][]; selected?: string; send?: string; sent?: string; tickAt?: number[]; top?: number; until?: number;
}) => {
  if (t < a) return null;
  const gone = life(t, a, until); if (gone >= 1) return null;
  const slide = ramp(t, a, a + 0.32, 0, 1, (x) => 1 - Math.pow(1 - x, 3));
  const tickT = (i: number) => tickAt?.[i] ?? a + 0.55 + i * 0.28;
  const pressed = t >= sendAt - 0.08 && t < sendAt + 0.1, done = t >= sendAt;
  const fly = ramp(t, sendAt, sendAt + 0.5, 0, 1, (x) => Math.pow(x, 2.2));
  return (
    <div style={{ position: "absolute", left: 70, top, width: 940, opacity: slide * (1 - gone), transform: `translateY(${(1 - slide) * -80}px)` }}>
      <div style={{ ...card, padding: "26px 32px 30px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontFamily: "Anton", fontSize: 60, color: "#fff", letterSpacing: 2 }}>{title}</div>
          <div style={{ fontFamily: "Anton", fontSize: 40, color: GOLD, letterSpacing: 2, opacity: done ? 0.3 : 1 }}>{friends.filter((_, i) => t >= tickT(i)).length} {selected}</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 26 }}>
          {friends.map(([em, nm, col], i) => {
            const k = t >= tickT(i) ? pop(t, tickT(i), 0.24) : 0;
            return (
              <div key={i} style={{ width: 196, textAlign: "center", position: "relative" }}>
                <div style={{ width: 150, height: 150, margin: "0 auto", borderRadius: 75, background: col, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 88,
                  boxShadow: k > 0 ? `0 0 0 6px #fff, 0 0 34px ${col}` : "none", transform: `scale(${1 + 0.06 * Math.min(1, k)})` }}>{em}</div>
                <div style={{ position: "absolute", left: 110, top: 100, width: 52, height: 52, borderRadius: 26, background: GREEN, border: "4px solid #fff", display: "flex", alignItems: "center", justifyContent: "center",
                  transform: `scale(${k})`, color: "#fff", fontFamily: "Anton", fontSize: 34 }}>✓</div>
                <div style={{ fontFamily: "Barlow", fontSize: 34, color: "#fff", marginTop: 12, letterSpacing: 1 }}>{nm}</div>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 26, display: "flex", justifyContent: "center", height: 100 }}>
          <div style={{ width: 520, height: 96, borderRadius: 48, background: done ? GREEN : BLUE, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Anton", fontSize: 56, color: "#fff",
            letterSpacing: 4, transform: `scale(${pressed ? 0.92 : 1})`, boxShadow: `0 8px 0 rgba(0,0,0,.4), 0 0 ${pressed ? 50 : 0}px ${BLUE}` }}>{done ? sent : send}</div>
        </div>
      </div>
      {done && fly < 1 && (
        <div style={{ position: "absolute", left: 420 + fly * 700, top: 330 - fly * 420, fontSize: 140, transform: `rotate(${-20 - fly * 15}deg) scale(${1 - fly * 0.5})`, opacity: 1 - fly * 0.6 }}>📨</div>
      )}
    </div>
  );
};
