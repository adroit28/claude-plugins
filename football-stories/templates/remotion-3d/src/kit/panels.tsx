import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { useCurrentFrame } from "remotion";

// Flat polygon panels for any solid or tiling: each panel is a dark seam polygon plus an inset
// coloured panel lifted along its outward normal, optionally inflated towards a sphere.

export const SEAM = new THREE.Color("#262626");

export const centroid = (pts: THREE.Vector3[]) =>
  pts.reduce((a, p) => a.add(p), new THREE.Vector3()).divideScalar(pts.length);

export const newell = (pts: THREE.Vector3[]) => {
  const n = new THREE.Vector3();
  pts.forEach((p, i) => {
    const q = pts[(i + 1) % pts.length];
    n.x += (p.y - q.y) * (p.z + q.z);
    n.y += (p.z - q.z) * (p.x + q.x);
    n.z += (p.x - q.x) * (p.y + q.y);
  });
  return n.normalize();
};

// regular polygon in the xz plane (y = 0)
export const regularPolygon = (cx: number, cz: number, radius: number, sides: number, rot = 0) =>
  Array.from({ length: sides }, (_, i) => {
    const a = rot + (i * 2 * Math.PI) / sides;
    return new THREE.Vector3(cx + radius * Math.cos(a), 0, cz + radius * Math.sin(a));
  });

// Triangles for many polygons in one buffer, each polygon fanned from its centre and
// subdivided K times so it can bulge when inflated.
export class Buf {
  pos: number[] = [];
  col: number[] = [];
  poly(pts: THREE.Vector3[], color: THREE.Color, K = 1, map?: (p: THREE.Vector3) => THREE.Vector3) {
    const C = centroid(pts);
    const put = (p: THREE.Vector3) => {
      const q = map ? map(p) : p;
      this.pos.push(q.x, q.y, q.z);
      this.col.push(color.r, color.g, color.b);
    };
    for (let s = 0; s < pts.length; s++) {
      const A = pts[s];
      const B = pts[(s + 1) % pts.length];
      const P = (i: number, j: number) =>
        C.clone().addScaledVector(A.clone().sub(C), i / K).addScaledVector(B.clone().sub(A), j / K);
      for (let i = 0; i < K; i++)
        for (let j = 0; j <= i; j++) {
          put(P(i, j)); put(P(i + 1, j)); put(P(i + 1, j + 1));
          if (j < i) { put(P(i, j)); put(P(i + 1, j + 1)); put(P(i, j + 1)); }
        }
    }
  }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(this.pos, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(this.col, 3));
    g.computeVertexNormals();
    return g;
  }
}

// push a point towards the sphere of radius r around `center` (inflate 0 = flat faces, 1 = round)
export const inflater = (inflate: number, r: number, center: THREE.Vector3) => (p: THREE.Vector3) => {
  if (inflate <= 0) return p;
  const d = p.clone().sub(center);
  const len = d.length();
  return center.clone().addScaledVector(d.normalize(), len + (r - len) * inflate);
};

export type PanelOpts = { inset?: number; K?: number; inflate?: number; center?: THREE.Vector3; radius?: number; seam?: THREE.Color };

export const panel = (buf: Buf, pts: THREE.Vector3[], color: THREE.Color, outward: THREE.Vector3, opts: PanelOpts = {}) => {
  const C = centroid(pts);
  let n = newell(pts);
  if (n.dot(outward) < 0) n = n.negate();
  const K = opts.K ?? 1;
  const inf = opts.inflate ?? 0;
  const center = opts.center ?? new THREE.Vector3();
  const r = opts.radius ?? 1;
  buf.poly(pts, opts.seam ?? SEAM, K, inflater(inf, r, center));
  const s = opts.inset ?? 0.9;
  buf.poly(pts.map((p) => C.clone().addScaledVector(p.clone().sub(C), s).addScaledVector(n, 0.01 * r)), color, K, inflater(inf, r * 1.012, center));
};

// One mesh rebuilt every frame from `build` (cheap at Short sizes: a few thousand triangles).
export const Panels = ({ build, opacity = 1, roughness = 0.45 }: { build: () => Buf; opacity?: number; roughness?: number }) => {
  const frame = useCurrentFrame();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const geo = useMemo(() => build().geometry(), [frame, opacity]);
  useEffect(() => () => geo.dispose(), [geo]);
  if (opacity <= 0.001) return null;
  // key: a fresh material whenever transparency flips. Reusing one across the switch leaves stale
  // shader state, and frames rendered after a fade come out greyer than the same frame rendered alone.
  return (
    <mesh geometry={geo}>
      <meshStandardMaterial key={opacity < 1 ? "fade" : "solid"} vertexColors side={THREE.DoubleSide} roughness={roughness} metalness={0}
        transparent={opacity < 1} opacity={opacity} depthWrite={opacity >= 1} />
    </mesh>
  );
};
