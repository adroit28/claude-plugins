import { Composition } from "remotion";
import { Short } from "./Short";
import { FPS, DURATION_S } from "./timing";

export const RemotionRoot = () => (
  <Composition id="Short" component={Short} width={1080} height={1920} fps={FPS} durationInFrames={Math.round(DURATION_S * FPS)} />
);
