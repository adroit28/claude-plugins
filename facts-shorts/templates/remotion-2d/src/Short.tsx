import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./fonts";
import * as Scene from "./Scene";
import { LiveBg } from "./kit/motion";
import { Caption } from "./kit/overlays";
import { SubscribeBadge } from "./kit/Outro";
import { OUTRO_AT } from "./timing";
import options from "./options.json";

// The Short: background, narration, the topic's 2D scene (src/Scene.tsx), word-timed captions,
// then the like & subscribe badge. Topic code lives only in Scene.tsx. There is no 3D canvas, so
// every layer is an absolutely positioned div over the whole 1080x1920 frame.
export const Short = () => {
  useFont("Barlow", "BarlowCondensed-ExtraBold.ttf");
  useFont("BarlowSemi", "BarlowCondensed-SemiBold.ttf");
  useFont("Anton", "Anton-Regular.ttf");
  const t = useCurrentFrame() / useVideoConfig().fps;
  return (
    <AbsoluteFill style={{ background: Scene.BACKGROUND, overflow: "hidden" }}>
      {/* living background (drifting glows, dust, vignette); a Scene can export `BEATS` (seconds) to make the glow kick on story turns, or `LIVE_BG = false` to turn it off */}
      {(Scene as { LIVE_BG?: boolean }).LIVE_BG !== false && <LiveBg t={t} beats={(Scene as { BEATS?: number[] }).BEATS} />}
      <Audio src={staticFile("narration.wav")} />
      <AbsoluteFill>
        <Scene.Overlays t={t} />
      </AbsoluteFill>
      {options.captions !== false && <Caption t={t} until={OUTRO_AT} />}
      <SubscribeBadge t={t} start={OUTRO_AT} />
    </AbsoluteFill>
  );
};
