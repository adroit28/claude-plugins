import { Composition } from "remotion";
import { Short, FPS, TOTAL_FRAMES } from "./Short";
import { Multi } from "./Multi";
import { TL } from "./kit/lib";

export const RemotionRoot = () => (
  <>
    <Composition id="Short" component={Short} width={1080} height={1920} fps={FPS} durationInFrames={TOTAL_FRAMES} />
    <Composition id="Multi" component={Multi} width={1080} height={1920} fps={30} durationInFrames={Math.max(1, Math.round(TL.total * 30))} />
  </>
);
