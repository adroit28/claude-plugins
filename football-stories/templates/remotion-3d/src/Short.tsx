import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useFont } from "./fonts";
import { Scene, Overlays, BACKGROUND, CAMERA } from "./Scene";
import { Caption } from "./kit/overlays";
import { SubscribeBadge } from "./kit/Outro";
import { OUTRO_AT } from "./timing";

// The Short: background, narration, the topic's 3D scene and overlays (src/Scene.tsx),
// word-timed captions, then the like & subscribe badge. Topic code lives only in Scene.tsx.
export const Short = () => {
  useFont("Barlow", "BarlowCondensed-ExtraBold.ttf");
  useFont("BarlowSemi", "BarlowCondensed-SemiBold.ttf");
  useFont("Anton", "Anton-Regular.ttf");
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ background: BACKGROUND }}>
      <Audio src={staticFile("narration.wav")} />
      <ThreeCanvas width={width} height={height} camera={CAMERA}>
        <Scene />
      </ThreeCanvas>
      <Overlays t={t} />
      <Caption t={t} until={OUTRO_AT} />
      <SubscribeBadge t={t} start={OUTRO_AT} />
    </AbsoluteFill>
  );
};
