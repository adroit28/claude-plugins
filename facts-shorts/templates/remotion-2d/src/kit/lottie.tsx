import React from "react";
import { Sequence, Solid, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Lottie, type LottieAnimationData } from "@remotion/lottie";
import { lightLeak } from "@remotion/effects/light-leak";
import { ramp, enter } from "./anim";
import { RED } from "./props";
import sun from "../lottie/sun.json";
import eye from "../lottie/eye.json";
import nose from "../lottie/nose.json";
import relieved from "../lottie/relieved.json";
import sneeze from "../lottie/sneeze.json";
import zap from "../lottie/zap.json";

// Animated emoji (Noto Emoji Animation, CC BY 4.0, see src/lottie/CREDITS.md) and light-leak cuts.
// Added in 0.6.0 after the sun-sneeze v5 test. Both are optional; the old Emoji and Swipe still work.

// Bundled animated emoji. Use as `data={LOTTIE.sun}`. For any other emoji, download its lottie.json
// from fonts.gstatic.com/s/e/notoemoji/latest/<codepoint>/lottie.json (only after the user's yes),
// put it in src/lottie/, import it in the Scene, and log it in the Short's notes (CC BY 4.0 credit).
export const LOTTIE = { sun, eye, nose, relieved, sneeze, zap };

// Same contract as Emoji (props.tsx): pops in at `a`, optional rotation, `crossAt` greys it out with
// a red slash. The animation starts playing at `a` and loops. `data` is one of LOTTIE or an import.
export const LottieEmoji = ({ t, a, data, x, y, size = 290, rot = 0, crossAt, springy }: {
  t: number; a: number; data: unknown; x: number; y: number; size?: number; rot?: number; crossAt?: number; springy?: boolean;
}) => {
  const { fps } = useVideoConfig();
  if (t < a) return null;
  const slash = crossAt === undefined ? 0 : ramp(t, crossAt, crossAt + 0.2, 0, 1);
  const box = size * 1.15;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: box, height: box }}>
      <div style={{ width: box, height: box, transform: `scale(${enter(t, a, springy)}) rotate(${rot}deg)`, filter: `grayscale(${slash})` }}>
        <Sequence from={Math.round(a * fps)} layout="none">
          <Lottie animationData={data as LottieAnimationData} loop style={{ width: "100%", height: "100%" }} />
        </Sequence>
      </div>
      {slash > 0 && (
        <div style={{ position: "absolute", left: -10, top: size * 0.55, width: size * 1.25 * slash, height: 34, background: RED,
          borderRadius: 17, transform: "rotate(-40deg)", transformOrigin: "0 50%" }} />
      )}
    </div>
  );
};

const Leak = ({ seed, hue }: { seed: number; hue: number }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  return (
    <Solid width={width} height={height} effects={[lightLeak({ seed, hueShift: hue,
      progress: interpolate(frame, [0, durationInFrames - 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) })]} />
  );
};

// A colour wash that plays over a cut without changing any timing: starts 0.3 s before `at` (the next
// beat's start), lasts 0.8 s. `seed` changes its shape, `hue` (degrees) its colour. Pair with a whoosh.
// Put it at the story's turns (3-5 per Short), not on every line. Needs WebGL: remotion.config.ts sets
// the "angle" renderer. A Solid must not be moved or scaled by a parent Cam; keep it at the top level of Overlays.
export const LightLeakCut = ({ at, seed = 1, hue = 0 }: { at: number; seed?: number; hue?: number }) => {
  const { fps } = useVideoConfig();
  return (
    <Sequence from={Math.max(0, Math.round((at - 0.3) * fps))} durationInFrames={Math.round(0.8 * fps)} layout="none">
      <Leak seed={seed} hue={hue} />
    </Sequence>
  );
};
