import * as THREE from "three";
import { useThree } from "@react-three/fiber";
import { ramp } from "./anim";

// Camera keyframes: each key eases from wherever the camera is to `cam` over [at, at + dur].
// Put the first frame's camera (HERO) first and last, so the Short loops.
export type Cam = { pos: [number, number, number]; look: [number, number, number] };
export type CamKey = { at: number; dur: number; cam: Cam };

export const lerpCam = (a: Cam, b: Cam, k: number): Cam => ({
  pos: a.pos.map((v, i) => v + (b.pos[i] - v) * k) as Cam["pos"],
  look: a.look.map((v, i) => v + (b.look[i] - v) * k) as Cam["look"],
});

export const camAt = (t: number, keys: CamKey[]) => {
  let cam = keys[0].cam;
  for (const k of keys.slice(1)) cam = lerpCam(cam, k.cam, ramp(t, k.at, k.at + k.dur));
  return cam;
};

export const CameraRig = ({ t, keys }: { t: number; keys: CamKey[] }) => {
  const { camera } = useThree();
  const cam = camAt(t, keys);
  camera.position.set(...cam.pos);
  camera.lookAt(new THREE.Vector3(...cam.look));
  camera.updateProjectionMatrix();
  return null;
};
