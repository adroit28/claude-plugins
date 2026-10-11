import React from "react";
import { Audio, Sequence, staticFile } from "remotion";
import { FPS } from "../timing";

// A sound bed whose volume is shaped per frame by vol(t) (t = seconds on the video clock), e.g. wind that swells with each gust,
// a hum that fades as the camera climbs, an air bed that rises with speed. Drive it from the SAME variable as the picture
// (the wind strength, the camera speed) and the sound follows the visual exactly.
// The file (public/sfx/<src>.wav, e.g. wind, air, hum from sfx.py) plays from its start at `at`, so pick one at least (b - at) s long.
// Level bands (voice stays clear): ambience 0.10-0.25 peak, short hits 0.20-0.35.
export const Bed = ({ src, at, b, vol }: { src: string; at: number; b: number; vol: (t: number) => number }) => (
  <Sequence from={Math.max(0, Math.round(at * FPS))} durationInFrames={Math.max(1, Math.round((b - at) * FPS))} layout="none">
    <Audio src={staticFile(`sfx/${src}.wav`)} volume={(f) => Math.max(0, vol(at + f / FPS))} />
  </Sequence>
);
