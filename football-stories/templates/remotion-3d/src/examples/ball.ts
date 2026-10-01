import * as THREE from "three";

// EXAMPLE MODULE from the football-shape Short (shorts/football-shape/anim). Nothing in kit/ imports it;
// import it from Scene.tsx only when the topic is the ball itself, or copy the pattern for another solid.
//
// The classic ball (truncated icosahedron) on a unit sphere, plus an "unrolled" sheet
// around one pentagon. wrap(c) curls that sheet: c=0 flat on the ground, c=1 closes
// exactly into the 12+20 ball (radius 1, centre (0,1,0), touching the ground at the origin).

const PHI = (1 + Math.sqrt(5)) / 2;

export type Kind = "pent" | "hex";
export type Face = {
  kind: Kind;
  verts: THREE.Vector3[]; // on the unit sphere, counter-clockwise seen from outside
  // sheet coordinates of each vertex: polar angle d from the bottom pentagon, azimuth th
  sheet: { d: number; th: number }[];
  d: number; // polar angle of the face centre (reveal order)
  th: number;
};

const sortAround = (pts: THREE.Vector3[], axis: THREE.Vector3) => {
  const n = axis.clone().normalize();
  const c = pts.reduce((a, p) => a.add(p), new THREE.Vector3()).divideScalar(pts.length);
  const u = pts[0].clone().sub(c).normalize();
  const w = n.clone().cross(u);
  const ang = (p: THREE.Vector3) => {
    const q = p.clone().sub(c);
    return Math.atan2(q.dot(w), q.dot(u));
  };
  return [...pts].sort((a, b) => ang(a) - ang(b));
};

// basis of the unrolled sheet: n = bottom pentagon centre (becomes +y of the curled ball)
export const FRAME = { n: new THREE.Vector3(), u: new THREE.Vector3(), w: new THREE.Vector3() };
// a unit-sphere direction in ball coordinates -> its direction from the curled ball's centre
export const toBall = (p: THREE.Vector3) =>
  new THREE.Vector3(p.dot(FRAME.u), p.dot(FRAME.n), p.dot(FRAME.w)).normalize();

const buildBall = (): Face[] => {
  const v: THREE.Vector3[] = [];
  for (const a of [-1, 1])
    for (const b of [-1, 1]) {
      v.push(new THREE.Vector3(0, a, b * PHI), new THREE.Vector3(a, b * PHI, 0), new THREE.Vector3(a * PHI, 0, b));
    }
  const near = (i: number, j: number) => Math.abs(v[i].distanceTo(v[j]) - 2) < 1e-6;
  const P = (i: number, j: number) => v[i].clone().lerp(v[j], 1 / 3);
  const raw: { kind: Kind; verts: THREE.Vector3[] }[] = [];
  for (let i = 0; i < 12; i++) {
    const nb = v.map((_, j) => j).filter((j) => j !== i && near(i, j));
    raw.push({ kind: "pent", verts: sortAround(nb.map((j) => P(i, j)), v[i]) });
  }
  for (let a = 0; a < 12; a++)
    for (let b = a + 1; b < 12; b++)
      for (let c = b + 1; c < 12; c++) {
        if (!(near(a, b) && near(b, c) && near(a, c))) continue;
        const pts = [P(a, b), P(b, a), P(b, c), P(c, b), P(c, a), P(a, c)];
        raw.push({ kind: "hex", verts: sortAround(pts, v[a].clone().add(v[b]).add(v[c])) });
      }
  const R = raw[0].verts[0].length();
  raw.forEach((f) => f.verts.forEach((p) => p.divideScalar(R)));

  // frame: n points at the bottom pentagon's centre
  const n = raw[0].verts.reduce((a, p) => a.add(p), new THREE.Vector3()).normalize();
  const u = new THREE.Vector3(0, 0, 1).cross(n).normalize();
  const w = n.clone().cross(u);
  const polar = (p: THREE.Vector3) => {
    const q = p.clone().normalize();
    return { d: Math.acos(Math.max(-1, Math.min(1, q.dot(n)))), th: Math.atan2(q.dot(w), q.dot(u)) };
  };
  FRAME.n = n; FRAME.u = u; FRAME.w = w;
  return raw.map((f) => {
    const c = polar(f.verts.reduce((a, p) => a.add(p), new THREE.Vector3()));
    return { ...f, sheet: f.verts.map(polar), d: c.d, th: c.th };
  });
};

export const BALL = buildBall();
export const EDGE = BALL[0].verts[0].distanceTo(BALL[0].verts[1]); // panel edge on a unit ball
// reveal order: outward from the bottom pentagon, then around
export const ORDER = BALL.map((_, i) => i).sort(
  (a, b) => BALL[a].d - BALL[b].d || BALL[a].th - BALL[b].th,
);

export const wrap = (d: number, th: number, c: number) => {
  if (c < 1e-5) return new THREE.Vector3(d * Math.cos(th), 0, d * Math.sin(th));
  const r = 1 / c;
  const a = d * c;
  return new THREE.Vector3(r * Math.sin(a) * Math.cos(th), r * (1 - Math.cos(a)), r * Math.sin(a) * Math.sin(th));
};

// flat-top honeycomb with the same edge as the ball's panels, centre hexagon at the origin
export const honeycomb = (rings: number) => {
  const out: { q: number; r: number; x: number; z: number; ring: number }[] = [];
  for (let q = -rings; q <= rings; q++)
    for (let r = -rings; r <= rings; r++) {
      const s = -q - r;
      const ring = Math.max(Math.abs(q), Math.abs(r), Math.abs(s));
      if (ring > rings) continue;
      out.push({ q, r, ring, x: EDGE * 1.5 * q, z: EDGE * Math.sqrt(3) * (r + q / 2) });
    }
  return out;
};

export const regularPolygon = (cx: number, cz: number, radius: number, sides: number, rot = 0) =>
  Array.from({ length: sides }, (_, i) => {
    const a = rot + (i * 2 * Math.PI) / sides;
    return new THREE.Vector3(cx + radius * Math.cos(a), 0, cz + radius * Math.sin(a));
  });
