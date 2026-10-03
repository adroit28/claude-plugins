import { Easing, interpolate } from "remotion";
import { ramp } from "./anim";
import channel from "../channel.json";

// Like & subscribe badge after the last narration word. No voice. OUTRO_S is the one place its
// length is set: timing.ts adds it to the Short's duration, and the badge is gone on the last
// frame so the loop back to frame 0 stays clean. Name, tagline and avatar come from
// src/channel.json, which anim.py copies from the content folder's channel.json.
export const OUTRO_S = 3.0; // channel rule: on screen 2.5 s at the very least, 3 s by default
const C = channel as { name?: string; tagline?: string; avatar?: string };
export const CHANNEL = C.name || "Like & Subscribe";
export const HANDLE = C.tagline || "for more surprising stories";
export const AVATAR = C.avatar || "☎️";
export const OUTRO_TOP = 1300; // where the captions were

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const back = Easing.out(Easing.back(1.8));

const Thumb = ({ color }: { color: string }) => (
  <svg viewBox="0 0 48 48" width={66} height={66}>
    <rect x="4" y="20" width="9" height="22" rx="2" fill={color} />
    <path d="M16 22 L23.5 8.5 Q25.5 4.5 28.8 5.6 Q32.4 7 31.2 11.4 L29.4 18.5 H39.5 Q44.3 18.5 43.6 23.4 L41.3 37.6 Q40.6 42 36.2 42 H16 Z" fill={color} />
  </svg>
);

export const SubscribeBadge = ({ t, start }: { t: number; start: number }) => {
  const u = t - start;
  if (u < 0 || u > OUTRO_S) return null;
  const inS = interpolate(u, [0, 0.28], [0.7, 1], { ...clamp, easing: back });
  const outK = ramp(u, OUTRO_S - 0.28, OUTRO_S - 0.04, 0, 1, Easing.in(Easing.cubic));
  const opacity = ramp(u, 0, 0.12) * (1 - outK);
  const y = interpolate(u, [0, 0.28], [70, 0], { ...clamp, easing: back }) + 40 * outK;

  // thumb pops in, then a tap: squeeze, turn blue, bounce
  const thumbS = interpolate(u, [0.15, 0.32, 0.42, 0.56, 0.62, 0.72, 0.84], [0, 1.2, 1, 1, 0.85, 1.12, 1], clamp);
  const liked = u >= 0.62;
  const subS = interpolate(u, [0.28, 0.46, 0.56], [0, 1.12, 1], { ...clamp, easing: Easing.out(Easing.quad) })
    * interpolate(u, [0.82, 0.9, 1.02, 1.12], [1, 0.92, 1.06, 1], clamp)
    * (u > 1.3 ? 1 + 0.018 * Math.sin((u - 1.3) * 5) : 1); // idle pulse so the hold isn't frozen
  const shine = interpolate(u, [0.9, 1.25], [-30, 130], clamp);

  return (
    <div style={{ position: "absolute", top: OUTRO_TOP, left: 0, width: "100%", display: "flex", justifyContent: "center", opacity,
      transform: `translateY(${y}px) scale(${inS * (1 - 0.15 * outK)})` }}>
      <div style={{ width: 880, background: "rgba(255,255,255,0.97)", borderRadius: 52, padding: "34px 40px",
        boxShadow: "0 24px 60px rgba(0,0,0,.45)", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
          <div style={{ width: 124, height: 124, borderRadius: 62, background: "#0b1a35", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 76 }}>{AVATAR}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontFamily: "Barlow", fontSize: 66, lineHeight: 1.05, color: "#111" }}>{CHANNEL}</div>
            <div style={{ fontFamily: "BarlowSemi", fontSize: 44, color: "#606060" }}>{HANDLE}</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
          <div style={{ width: 124, height: 124, borderRadius: 62, background: liked ? "#1e7cff" : "#ececec",
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${thumbS})` }}>
            <Thumb color={liked ? "#fff" : "#111"} />
          </div>
          <div style={{ flex: 1, height: 124, borderRadius: 62, background: "#ff0000", position: "relative", overflow: "hidden",
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${subS})` }}>
            <div style={{ fontFamily: "Barlow", fontSize: 70, color: "#fff", letterSpacing: 4 }}>SUBSCRIBE</div>
            <div style={{ position: "absolute", top: 0, bottom: 0, left: `${shine}%`, width: "18%",
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,.45), transparent)", transform: "skewX(-20deg)" }} />
          </div>
        </div>
      </div>
    </div>
  );
};
