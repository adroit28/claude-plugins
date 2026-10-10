import React, { useMemo } from "react";
import { Easing } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { ramp } from "./anim";
import { W, PIC_TOP } from "./props";

// ONE opt-in 3D beat inside a 2D Short (0.8.0). NOT exported from kit/index.ts: a Scene that never imports
// "./kit/hero3d" never bundles three.js, so old and 2D-only Shorts are unaffected. Import it by path:
//   import { Hero3D, EarCanal3D } from "./kit/hero3d";
//
// Hero3D puts a transparent three.js canvas (W x `height`, in the picture band) over the 2D layers between
// a and b, fading in and out; its children are three.js objects driven by the `t` you pass (never by frames or
// useFrame), so previews, stills and the render agree. Rules: at most ONE per Short, 2-4 s, at the story's key
// beat; keep text and captions in the 2D layers; the canvas is a box in the band, not the whole frame.
// Render cost: WebGL is on (remotion.config.ts sets the "angle" renderer); a 3 s beat adds ~30-60 s to a render.
export const Hero3D = ({ t, a, b, children, height = 900, top = PIC_TOP, fov = 35, camZ = 9.5 }: {
  t: number; a: number; b: number; children: React.ReactNode; height?: number; top?: number; fov?: number; camZ?: number;
}) => {
  if (t < a - 0.01 || t > b + 0.4) return null;
  const op = ramp(t, a, a + 0.3) * (1 - ramp(t, b, b + 0.3));
  return (
    <div style={{ position: "absolute", left: 0, top, width: W, height, opacity: op, transform: `scale(${0.9 + 0.1 * ramp(t, a, a + 0.4, 0, 1, Easing.out(Easing.back(1.4)))})` }}>
      <ThreeCanvas width={W} height={height} camera={{ position: [0, 0, camZ], fov }}>
        <ambientLight intensity={1.1} />
        <directionalLight position={[3, 4, 5]} intensity={2.2} />
        <pointLight position={[3.4, 0, 1.5]} intensity={18} color="#ff9a86" />
        {children}
      </ThreeCanvas>
    </div>
  );
};

// A worked example: an ear canal (translucent tube) with the eardrum at the far end, a lump of wax and a cotton
// swab that pushes it along the canal between `a` and `b` (push 0 -> 1). Swap the pieces for another subject.
export const EarCanal3D = ({ t, a, b, from = 0.18, to = 0.82 }: { t: number; a: number; b: number; from?: number; to?: number }) => {
  const curve = useMemo(() => new THREE.CatmullRomCurve3([new THREE.Vector3(-3.1, 0.5, 0), new THREE.Vector3(-1, 0.1, 0.2), new THREE.Vector3(1, -0.15, -0.1), new THREE.Vector3(2.7, 0, 0)]), []);
  const tube = useMemo(() => new THREE.TubeGeometry(curve, 64, 1.05, 32, false), [curve]);
  const push = ramp(t, a + 0.3, b, 0, 1, Easing.inOut(Easing.cubic));
  const u = from + (to - from) * push;
  const wax = curve.getPoint(u), end = curve.getPoint(1);
  const sway = 0.35 * Math.sin((t - a) * 0.9) + 0.3;
  return (
    <group rotation={[0.18, sway, 0]} position={[0, 0.2, 0]}>
      <mesh geometry={tube}>
        <meshPhysicalMaterial color="#f2b5a0" transparent opacity={0.38} side={THREE.DoubleSide} roughness={0.35} />
      </mesh>
      <mesh position={[end.x + 0.05, end.y, end.z]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[1.0, 1.0, 0.12, 48]} />
        <meshStandardMaterial color="#e9c2b2" emissive="#ff6a55" emissiveIntensity={0.25 + 0.2 * push} roughness={0.5} />
      </mesh>
      <mesh position={[end.x - 0.02, end.y, end.z]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.62, 0.05, 12, 48]} />
        <meshStandardMaterial color="#d89a86" />
      </mesh>
      <mesh position={[wax.x, wax.y, wax.z]} scale={[1.15, 1, 1]}>
        <sphereGeometry args={[0.55, 32, 24]} />
        <meshStandardMaterial color="#c98a2b" roughness={0.6} />
      </mesh>
      <group position={[wax.x - 0.55, wax.y, wax.z]}>
        <mesh>
          <sphereGeometry args={[0.38, 24, 16]} />
          <meshStandardMaterial color="#ffffff" roughness={0.95} />
        </mesh>
        <mesh position={[-1.7, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.09, 0.09, 3.4, 12]} />
          <meshStandardMaterial color="#f4f4f4" />
        </mesh>
      </group>
    </group>
  );
};
