import React from "react";
import { ramp } from "./anim";

// Particles (0.8.0). Burst = a ring of dots flying out of a point (a stamp landing); Confetti = coloured
// paper that shoots up and falls (a win, a payoff). Both are pure functions of `t`, no state.
// Deterministic pseudo-random so every render and every preview frame agrees.
const rnd = (i: number, k = 0) => { const s = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return s - Math.floor(s); };
const PARTY = ["#ffc400", "#e01b22", "#2ba8ff", "#1fd66b", "#ff4fa3", "#ffffff"];

export const Burst = ({ t, a, x, y, color = "#ffc400", n = 10, dur = 0.4, speed = 900 }: {
  t: number; a: number; x: number; y: number; color?: string; n?: number; dur?: number; speed?: number;
}) => {
  const age = t - a;
  if (age < 0 || age > dur) return null;
  return (
    <>
      {Array.from({ length: n }, (_, i) => {
        const ang = (i / n) * Math.PI * 2 + rnd(i) * 0.4, d = age * speed * (0.6 + rnd(i, 2) * 0.5);
        return <div key={i} style={{ position: "absolute", left: x + Math.cos(ang) * d - 9, top: y + Math.sin(ang) * d * 0.7 - 9, width: 18, height: 18,
          borderRadius: 9, background: color, opacity: Math.max(0, 1 - age / dur) }} />;
      })}
    </>
  );
};

// `x`,`y` = where the paper leaves from (default: upper middle). Gravity pulls it down; it fades over `dur`.
export const Confetti = ({ t, a, dur = 1.8, x = 540, y = 520, n = 46, colors = PARTY }: {
  t: number; a: number; dur?: number; x?: number; y?: number; n?: number; colors?: string[];
}) => {
  const age = t - a;
  if (age < 0 || age > dur) return null;
  return (
    <>
      {Array.from({ length: n }, (_, i) => {
        const ang = -Math.PI / 2 + (rnd(i) - 0.5) * 2.6, sp = 500 + rnd(i, 3) * 900;
        return <div key={i} style={{ position: "absolute", left: x + Math.cos(ang) * sp * age, top: y + Math.sin(ang) * sp * age + 1400 * age * age,
          width: 18 + rnd(i, 7) * 14, height: 30, background: colors[i % colors.length], transform: `rotate(${age * 540 + i * 40}deg)`,
          opacity: 1 - ramp(t, a + dur * 0.6, a + dur) }} />;
      })}
    </>
  );
};
