import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { SEAM } from "./panels";

// A sphere painted by a shader: each point takes the colour of its nearest cell centre
// (spherical Voronoi), with dark seams between cells and an optional twist for curved seams.
// Good for any "panel layout" or region map on a ball or planet. Up to 32 cells.
export type Cells = { pts: THREE.Vector3[]; kinds: number[] }; // kind 0 = colA, 1 = colB

const norm = (v: number[]) => new THREE.Vector3(...v).normalize();
export const OCTA = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]].map(norm);
export const CUBE = [-1, 1].flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) => norm([x, y, z]))));
export const TETRA = [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]].map(norm);

const VERT = `
varying vec3 vP; varying vec3 vN;
void main(){ vP = position; vN = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const FRAG = `
uniform vec3 pts[32]; uniform float kinds[32]; uniform int n; uniform float twist;
uniform vec3 colA; uniform vec3 colB; uniform vec3 seam; uniform float opacity; uniform vec3 L;
varying vec3 vP; varying vec3 vN;
void main(){
  vec3 p = normalize(vP);
  float a = twist * p.y; float c = cos(a), s = sin(a);
  p = vec3(c*p.x + s*p.z, p.y, -s*p.x + c*p.z);
  float b1 = -2.0, b2 = -2.0; int i1 = 0;
  for (int i = 0; i < 32; i++) { if (i >= n) break; float d = dot(p, pts[i]);
    if (d > b1) { b2 = b1; b1 = d; i1 = i; } else if (d > b2) { b2 = d; } }
  float gap = acos(clamp(b2, -1.0, 1.0)) - acos(clamp(b1, -1.0, 1.0));
  vec3 col = mix(colA, colB, kinds[i1]);
  col = mix(seam, col, smoothstep(0.035, 0.055, gap));
  float bulge = smoothstep(0.0, 0.3, gap);
  vec3 N = normalize(vN); vec3 l = normalize(L);
  float dif = 0.5 + 0.7 * max(dot(N, l), 0.0);
  float spec = pow(max(dot(reflect(-l, N), vec3(0.0, 0.0, 1.0)), 0.0), 24.0) * 0.3;
  gl_FragColor = vec4(col * dif * (0.8 + 0.2 * bulge) + spec, opacity);
}`;

export const PatternSphere = ({ cells, colA = "#f6f6f4", colB = "#141414", twist = 0, opacity = 1, radius = 1.012 }: {
  cells: Cells; colA?: string; colB?: string; twist?: number; opacity?: number; radius?: number;
}) => {
  const mat = useMemo(
    () => new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true,
      uniforms: {
        pts: { value: Array.from({ length: 32 }, () => new THREE.Vector3()) },
        kinds: { value: new Array(32).fill(0) }, n: { value: 0 }, twist: { value: 0 },
        colA: { value: new THREE.Color() }, colB: { value: new THREE.Color() }, seam: { value: SEAM.clone() },
        opacity: { value: 1 }, L: { value: new THREE.Vector3(0.4, 0.7, 0.6) },
      },
    }),
    [],
  );
  useEffect(() => () => mat.dispose(), [mat]);
  cells.pts.forEach((p, i) => mat.uniforms.pts.value[i].copy(p));
  mat.uniforms.kinds.value = Array.from({ length: 32 }, (_, i) => cells.kinds[i] ?? 0);
  mat.uniforms.n.value = Math.min(32, cells.pts.length);
  mat.uniforms.twist.value = twist;
  mat.uniforms.colA.value.set(colA);
  mat.uniforms.colB.value.set(colB);
  mat.uniforms.opacity.value = opacity;
  mat.depthWrite = opacity >= 1;
  if (opacity <= 0.001) return null;
  return (
    <mesh material={mat}>
      <sphereGeometry args={[radius, 160, 120]} />
    </mesh>
  );
};
