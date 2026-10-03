import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./fonts";
import { Overlays, BACKGROUND } from "./Scene";
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
    <AbsoluteFill style={{ background: BACKGROUND, overflow: "hidden" }}>
      <Audio src={staticFile("narration.wav")} />
      <AbsoluteFill>
        <Overlays t={t} />
      </AbsoluteFill>
      {options.captions !== false && <Caption t={t} until={OUTRO_AT} />}
      <SubscribeBadge t={t} start={OUTRO_AT} />
    </AbsoluteFill>
  );
};
