// Multi.tsx  the multi-clip composition (docs/multi-clip.md). Everything comes from src/timeline.json (+ src/track.json).
// Chunk (picture from clips/<vid>.mp4 at ca, zoom steps, whip transitions, Freeze for holds), Captions, Shaker, Flashes, Finish.
// A chunk may carry "anchor":[x,y] to zoom around a fixed point instead of the tracked face.
// Graphics live in ./Scenes (one line per scene) built from ./kit.
import React from "react";
import { AbsoluteFill, Easing, Freeze, OffthreadVideo, interpolate, staticFile, useCurrentFrame } from "remotion";
import { TL, FPS, W, H, YEL, ANTON, prog, eOut, eBack, strokeText, useFonts, Seq, Fill, faceAt } from "./kit/lib";
import { Scenes } from "./Scenes";

const Chunk: React.FC<{ c: any }> = ({ c }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const dF = Math.round(c.d * FPS);
  const srcT = c.a + Math.min(t, c.d) * c.speed;
  const zk: number[][] = c.z;
  const z = interpolate(srcT, zk.map((k) => k[0]), zk.map((k) => k[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const [fx, fy] = c.anchor ? c.anchor : faceAt(c.clip, c.a + 0.4);
  const wh = (TL.whips || []).find((w: any) => Math.abs(w.t - c.o) < 0.05);
  const wp = wh ? 1 - eOut(prog(t, 0, wh.d)) : 0;
  const video = (
    <OffthreadVideo src={staticFile(`clips/${c.vid ?? c.clip}.mp4`)} startFrom={Math.round((c.ca ?? c.a) * FPS)} muted
      style={{ width: W, height: H, filter: "contrast(1.08) saturate(1.12) brightness(1.03)" }} />
  );
  return (
    <Fill style={{ transform: wh ? `translateX(${wp * 320 * wh.dir}px)` : undefined, filter: wh && wp > 0.01 ? `blur(${wp * 22}px)` : undefined }}>
      <Fill style={{ transform: `scale(${z})`, transformOrigin: `${fx}px ${fy}px` }}>
        {frame >= dF ? <Freeze frame={dF - 1}>{video}</Freeze> : video}
      </Fill>
    </Fill>
  );
};

// captions: words appear as they are spoken, the spoken word lights up, HOT words get the big treatment
const Captions: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const ph = [...(TL.phrases || [])].reverse().find((p: any) => t >= p.a - 0.03 && t < p.b + 0.16);
  if (!ph) return null;
  const chars = ph.words.map((w: any) => w.w).join(" ").length;
  const size = chars <= 13 ? 118 : chars <= 19 ? 104 : 92;
  const enter = eBack(prog(t, ph.a - 0.03, ph.a + 0.1), 1.4);
  return (
    <div style={{ position: "absolute", left: 60, width: 900, top: 1318, height: 230, display: "flex", flexWrap: "wrap", justifyContent: "center", alignContent: "center", columnGap: 38, rowGap: 0, transform: `scale(${0.88 + 0.12 * enter})` }}>
      {ph.words.map((w: any, i: number) => {
        if (t < w.a - 0.02) return null;
        const cur = t >= w.a && t < w.b + 0.02 && t < ph.b + 0.02;
        const age = t - w.a;
        const sc = (w.hot ? 1.1 : 1) * (1 + 0.2 * Math.max(0, 1 - age / 0.12) * (w.hot ? 1.2 : 1));
        const col = w.hot ? (cur ? "#FF5A36" : YEL) : cur ? YEL : "#fff";
        return (
          <span key={i} style={{ fontFamily: ANTON, fontSize: size, lineHeight: 1.06, color: col, letterSpacing: 2, transform: `scale(${sc}) rotate(${w.hot && cur ? (i % 2 ? 2.5 : -2.5) : 0}deg)`, ...strokeText(13), textShadow: "0 8px 0 rgba(0,0,0,.55)", display: "inline-block", margin: w.hot ? "0 18px" : 0 }}>{w.w}</span>
        );
      })}
    </div>
  );
};

const Shaker: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const t = useCurrentFrame() / FPS;
  let x = 0, y = 0, r = 0;
  for (const s of TL.shakes || []) {
    const age = t - s.t;
    if (age < 0 || age > s.d) continue;
    const env = Math.pow(1 - age / s.d, 2);
    x += s.a * env * Math.sin(age * 95 + s.t * 7);
    y += s.a * env * Math.cos(age * 83 + s.t * 3);
    r += s.a * 0.025 * env * Math.sin(age * 71);
  }
  return <Fill style={{ transform: `translate(${x}px, ${y}px) rotate(${r}deg) scale(1.03)` }}>{children}</Fill>;
};

const Flashes: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  return (
    <>
      {(TL.flashes || []).map((f: any, i: number) => {
        const age = t - f.t;
        if (age < 0 || age > 0.18) return null;
        return <Fill key={i} style={{ background: f.c, opacity: Math.pow(1 - age / 0.18, 2) * 0.85 }} />;
      })}
    </>
  );
};

// vignette + film grain (public/grain.png ships with the template; set "grain": false in timeline.json to drop it)
const Finish: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <Fill style={{ background: "radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 52%, rgba(0,0,0,.6) 100%)" }} />
      {TL.grain !== false && (
        <Fill style={{ backgroundImage: `url(${staticFile("grain.png")})`, backgroundSize: "256px 256px", backgroundPosition: `${(frame * 37) % 256}px ${(frame * 91) % 256}px`, mixBlendMode: "overlay", opacity: 0.2 }} />
      )}
    </>
  );
};

export const Multi: React.FC = () => {
  useFonts();
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Shaker>
        {TL.chunks.map((c: any) => <Seq key={c.id} from={c.o} to={c.o + c.d + c.hold}><Chunk c={c} /></Seq>)}
        <Scenes />
      </Shaker>
      <Captions />
      <Finish />
      <Flashes />
    </AbsoluteFill>
  );
};
