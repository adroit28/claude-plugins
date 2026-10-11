import React from "react";

// ONE shared Burj Khalifa for the whole video. Slim tapering Y-plan tower: ~22 tiers that narrow smoothly, spiral
// setbacks (left and right wings peel off on staggered tiers), a thin core, a long needle spire with a blinking light.
// viewBox 240 x 1000, centre x = 120, f = height fraction (0 base, 1 tip), y = 1000 * (1 - f).
// Every point goes through dx(f), so `flex` bends the whole tower progressively (top moves most), not as a rigid block.

export const BURJ_ASPECT = 0.24;
export const HL_F = 0.71; // the habitable top ends here: above is the empty top 29 %
const TIERS = 22, TOP_TIER = HL_F, CX = 120;
const env = (f: number) => 20 + 36 * Math.pow(Math.max(0, 1 - f / TOP_TIER), 1.05);
const tf = (k: number) => (k / TIERS) * TOP_TIER;
// setback depth on one side at tier k: wings drop out on staggered tiers (the spiral)
const notch = (side: -1 | 1, k: number) => {
  const steps = side < 0 ? [3, 7, 11, 14, 17, 20] : [5, 9, 12, 15, 18, 21];
  return 3.6 * steps.filter((s) => k >= s).length;
};
const Yf = (f: number) => 1000 * (1 - f);

// half-width of one side at height f (no flex), piecewise: tier-slanted below HL_F, core then needle above
export const edge = (side: -1 | 1, f: number): number => {
  if (f >= 0.98) return 0.6;
  if (f > 0.78) return 0.6 + 4.4 * (0.98 - f) / 0.2; // needle
  if (f > TOP_TIER) return 10 + 3 * (0.78 - f) / (0.78 - TOP_TIER); // thin core, slight taper
  const k = Math.min(TIERS - 1, Math.floor((f / TOP_TIER) * TIERS));
  const a = tf(k), b = tf(k + 1), u = (f - a) / (b - a);
  const wa = env(a) - notch(side, k) * (side < 0 ? 0.8 : 1), wb = env(b) - notch(side, k) * (side < 0 ? 0.8 : 1);
  return Math.max(12, wa + (wb - wa) * u);
};
export const dxAt = (f: number, flex: number) => flex * f * f; // px (in viewBox units) at height f
export const towerX = (f: number, flex = 0, side = 0) => CX + dxAt(f, flex) + (side ? side * edge(side as -1 | 1, f) : 0);

const FS = Array.from({ length: 140 }, (_, i) => (i / 139));
const outline = (flex: number) => {
  const L = FS.map((f) => `${(towerX(f, flex, -1)).toFixed(1)},${Yf(f).toFixed(1)}`);
  const R = FS.slice().reverse().map((f) => `${(towerX(f, flex, 1)).toFixed(1)},${Yf(f).toFixed(1)}`);
  return [...L, ...R].join(" ");
};
const half = (flex: number, side: -1 | 1) => {
  const E = FS.map((f) => `${towerX(f, flex, side).toFixed(1)},${Yf(f).toFixed(1)}`);
  const C = FS.slice().reverse().map((f) => `${towerX(f, flex).toFixed(1)},${Yf(f).toFixed(1)}`);
  return [...E, ...C].join(" ");
};

const ROWS = 80, ROW_TOP = 0.8; // window rows reach into the thin core, so the top 29 % has lights to switch off
const hash = (n: number) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };

export type BurjProps = {
  h: number;
  stretch?: number;            // horizontal stretch of the drawing (1 = true proportions)
  id?: string;
  t?: number;                  // time (s) for the aviation light blink
  flex?: number;               // viewBox units of bend at the very top
  lit?: (f: number, row: number) => number; // 0..1 window brightness per row (default: mostly lit)
  glass?: [string, string];    // light face, dark face
  rim?: string;                // rim-light colour on the lit edge (sunset orange, moon blue ...)
  glow?: number;               // 0..1 soft halo behind the tower
  ghost?: boolean;             // outline only (the extreme-sway ghost)
  ghostFill?: string; ghostStroke?: string;
  light?: boolean;             // draw the aviation light
  style?: React.CSSProperties;
};

export const Burj = ({ h, stretch = 1, id = "b", t = 0, flex = 0, lit, glass = ["#cfe6ff", "#4d7fb0"], rim, glow = 0, ghost, ghostFill = "rgba(255,255,255,.08)", ghostStroke = "#fff", light = true, style }: BurjProps) => {
  const w = h * BURJ_ASPECT * stretch;
  const outPts = outline(flex);
  const topX = towerX(1, flex);
  const blink = (Math.sin(t * 5.2) > 0.55) ? 1 : 0.12;
  const rows = Array.from({ length: ROWS }, (_, i) => {
    const f = (i + 0.5) / ROWS * ROW_TOP;
    return { f, y: Yf(f) - 7, dx: dxAt(f, flex), i };
  });
  const litF = lit ?? ((f, i) => (hash(i * 3.3) > 0.18 ? 1 : 0.35));
  if (ghost) {
    return (
      <svg width={w} height={h} viewBox="0 0 240 1000" preserveAspectRatio="none" style={{ overflow: "visible", ...style }}>
        <polygon points={outPts} fill={ghostFill} stroke={ghostStroke} strokeWidth="3" strokeDasharray="10 7" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg width={w} height={h} viewBox="0 0 240 1000" preserveAspectRatio="none" style={{ overflow: "visible", ...style }}>
      <defs>
        <linearGradient id={`${id}L`} x1="0" x2="1"><stop offset="0" stopColor={glass[1]} /><stop offset="1" stopColor={glass[0]} /></linearGradient>
        <linearGradient id={`${id}R`} x1="0" x2="1"><stop offset="0" stopColor={glass[1]} /><stop offset="1" stopColor="#1d3556" /></linearGradient>
        <linearGradient id={`${id}V`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".28" /><stop offset=".5" stopColor="#fff" stopOpacity="0" /><stop offset="1" stopColor="#000" stopOpacity=".35" /></linearGradient>
        <radialGradient id={`${id}G`}><stop offset="0" stopColor={rim ?? "#9fd0ff"} stopOpacity=".7" /><stop offset="1" stopColor={rim ?? "#9fd0ff"} stopOpacity="0" /></radialGradient>
        <clipPath id={`${id}C`}><polygon points={outPts} /></clipPath>
      </defs>
      {glow > 0 && <ellipse cx={CX + flex * 0.4} cy="520" rx="170" ry="560" fill={`url(#${id}G)`} opacity={glow} />}
      <polygon points={half(flex, -1)} fill={`url(#${id}L)`} />
      <polygon points={half(flex, 1)} fill={`url(#${id}R)`} />
      <g clipPath={`url(#${id}C)`}>
        {/* tier bands and floor rows */}
        {Array.from({ length: TIERS + 1 }, (_, k) => {
          const f = tf(k), y = Yf(f);
          return <rect key={k} x={CX - 80 + dxAt(f, flex)} y={y - 1.6} width="160" height="3.2" fill="#0b1b30" opacity=".55" />;
        })}
        {rows.map((r) => {
          const b = litF(r.f, r.i);
          return <line key={r.i} x1={CX - 80 + r.dx} x2={CX + 80 + r.dx} y1={r.y + 3.5} y2={r.y + 3.5} stroke="#ffe3a0" strokeWidth="5" strokeDasharray="3.2 2.4" opacity={0.85 * b} />;
        })}
        {/* window grid: fine vertical mullions along the whole height */}
        {Array.from({ length: 26 }, (_, i) => {
          const x = -10 + i * 10;
          return <polyline key={i} fill="none" stroke="#06101e" strokeWidth="0.9" opacity=".35"
            points={FS.filter((_, j) => j % 10 === 0).map((f) => `${(x - CX) * (0.6 + 0.4 * f * 0) + towerX(f, flex) - 0},${Yf(f)}`).join(" ")} />;
        })}
        <rect x="0" y="0" width="240" height="1000" fill={`url(#${id}V)`} />
        {/* ridge line of the Y */}
        <polyline fill="none" stroke="#07101e" strokeWidth="1.6" opacity=".6" points={FS.filter((f) => f <= HL_F + 0.02).map((f) => `${towerX(f, flex).toFixed(1)},${Yf(f).toFixed(1)}`).join(" ")} />
      </g>
      {rim && (
        <polyline fill="none" stroke={rim} strokeWidth="2.4" strokeLinejoin="round" opacity=".9"
          points={FS.map((f) => `${towerX(f, flex, 1).toFixed(1)},${Yf(f).toFixed(1)}`).join(" ")} />
      )}
      {light && (
        <g>
          <circle cx={topX} cy="4" r="13" fill="#ff3030" opacity={0.35 * blink} />
          <circle cx={topX} cy="4" r="4.5" fill="#ff5a4d" opacity={blink} />
        </g>
      )}
    </svg>
  );
};
