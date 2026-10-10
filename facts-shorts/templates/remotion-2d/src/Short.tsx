import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./fonts";
import * as Scene from "./Scene";
import { motion } from "./kit/anim";
import { LiveBg } from "./kit/motion";
import { Caption, HotCaption } from "./kit/overlays";
import { SubscribeBadge } from "./kit/Outro";
import { OUTRO_AT } from "./timing";
import options from "./options.json";

// Written by `anim.py sync` from the story's "video" block; older synced files may lack the 0.8 fields.
const opt = options as unknown as { captions?: boolean; hotCaptions?: boolean; hot?: [string, number][]; grain?: number };

// The Short: background, narration, the topic's 2D scene (src/Scene.tsx), word-timed captions,
// then the like & subscribe badge. Topic code lives only in Scene.tsx. There is no 3D canvas, so
// every layer is an absolutely positioned div over the whole 1080x1920 frame (a Scene may drop one
// opt-in 3D beat in with kit/hero3d).
export const Short = () => {
  useFont("Barlow", "BarlowCondensed-ExtraBold.ttf");
  useFont("BarlowSemi", "BarlowCondensed-SemiBold.ttf");
  useFont("Anton", "Anton-Regular.ttf");
  const frame = useCurrentFrame();
  const t = frame / useVideoConfig().fps;
  motion.springy = (Scene as { SPRINGY?: boolean }).SPRINGY === true;  // spring() entrances only for scenes that opt in
  return (
    <AbsoluteFill style={{ background: Scene.BACKGROUND, overflow: "hidden" }}>
      {/* living background (drifting glows, dust, vignette); a Scene can export `BEATS` (seconds) to make the glow kick on story turns, or `LIVE_BG = false` to turn it off */}
      {(Scene as { LIVE_BG?: boolean }).LIVE_BG !== false && <LiveBg t={t} beats={(Scene as { BEATS?: number[] }).BEATS} />}
      <Audio src={staticFile("narration.wav")} />
      <AbsoluteFill>
        <Scene.Overlays t={t} />
      </AbsoluteFill>
      {opt.captions !== false && (opt.hotCaptions ? <HotCaption t={t} hot={opt.hot ?? []} until={OUTRO_AT} /> : <Caption t={t} until={OUTRO_AT} />)}
      {/* film grain: off unless the story sets video.grain (it can double the file size); capped at 0.08 by anim.py sync */}
      {!!opt.grain && (
        <AbsoluteFill style={{ backgroundImage: `url(${staticFile("grain.png")})`, backgroundSize: "256px 256px", mixBlendMode: "overlay", opacity: opt.grain,
          backgroundPosition: `${(frame * 37) % 256}px ${(frame * 91) % 256}px`, pointerEvents: "none" }} />
      )}
      <SubscribeBadge t={t} start={OUTRO_AT} />
    </AbsoluteFill>
  );
};
