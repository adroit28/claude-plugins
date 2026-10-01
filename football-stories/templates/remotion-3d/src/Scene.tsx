import * as THREE from "three";
import { Easing, useCurrentFrame, useVideoConfig } from "remotion";
import { ramp, pulse, loopTo, shown } from "./kit/anim";
import { CameraRig, type Cam, type CamKey } from "./kit/camera";
import { PatternSphere, CUBE } from "./kit/pattern";
import { Ring } from "./kit/Ring";
import { Tag } from "./kit/overlays";
import { WORDS, at, lineEnd, END, LAST_T } from "./timing";

// STARTER SCENE: renders for any story so the scaffold can be checked end to end.
// The animate skill replaces this file with the topic's storyboard: one shot per line,
// anchored to words with at(line, word). See the kit/ modules and examples/ball.ts.

export const BACKGROUND = "radial-gradient(ellipse at 50% 40%, #1d3b6e 0%, #0b1a35 60%, #060e1f 100%)";
export const CAMERA = { fov: 40, near: 0.05, far: 100, position: [0, 0, 8] as [number, number, number] };

const lines = [...new Set(WORDS.map((w) => w.line))];
const HERO: Cam = { pos: [0, 0, 8], look: [0, 0, 0] }; // first and last frame
const KEYS: CamKey[] = [
  { at: 0, dur: 0, cam: HERO },
  { at: at(lines[0], -1), dur: 1.2, cam: { pos: [1.4, 0.6, 5.2], look: [0, 0, 0] } },
  { at: END - 0.4, dur: 1.4, cam: HERO },
];

// spoken numbers -> a tag on each (the real scene uses the fact behind the number instead)
const NUM = /^(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|hundred|thousand|million)$/;
const NUMBERS = WORDS.filter((w) => NUM.test(w.w.toLowerCase().replace(/[^a-z0-9]/g, "")));

const spin = loopTo((t) => 0.6 * t, END, LAST_T);

export const Scene = () => {
  const t = useCurrentFrame() / useVideoConfig().fps;
  const ring = shown(t, at(lines[0], 0), lineEnd(lines[0]), 0.25, 0.4);
  const flash = Math.max(0, ...NUMBERS.map((w) => pulse(t, w.start)));
  const colB = new THREE.Color("#141414").lerp(new THREE.Color("#ffc400"), flash);
  return (
    <>
      <CameraRig t={t} keys={KEYS} />
      <ambientLight intensity={1.25} />
      <directionalLight position={[3, 6, 5]} intensity={2.6} />
      <directionalLight position={[-4, 2, -3]} intensity={0.7} color="#9fb8ff" />
      <group rotation={[0.28, spin(t), 0]} scale={ramp(t, 0, 0.4, 0.85, 1, Easing.out(Easing.back(2)))}>
        <PatternSphere cells={{ pts: CUBE, kinds: CUBE.map((p) => (p.x * p.y * p.z > 0 ? 1 : 0)) }} colB={`#${colB.getHexString()}`} radius={1.3} />
      </group>
      <Ring opacity={ring} radius={1.45} />
    </>
  );
};

export const Overlays = ({ t }: { t: number }) => {
  const i = NUMBERS.reduce((k, w, j) => (t >= w.start ? j : k), -1);
  if (i < 0) return null;
  const w = NUMBERS[i];
  return <Tag t={t} at={w.start} value={w.w.replace(/[^\w]/g, "").toUpperCase()} opacity={shown(t, w.start, w.end + 0.6, 0.05, 0.25)} />;
};
