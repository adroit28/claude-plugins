import { Easing, interpolate } from "remotion";

export const ease = Easing.inOut(Easing.cubic);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// from -> to between times a and b, held outside. If b <= a (a word anchor that lands before the
// previous one) the ramp becomes a near-instant step instead of crashing the render.
const warned = new Set<string>();
export const ramp = (t: number, a: number, b: number, from = 0, to = 1, e = ease) => {
  if (b <= a) {
    const k = `${a}:${b}`;
    if (!warned.has(k)) { warned.add(k); console.warn(`ramp: b (${b}) <= a (${a}); using b = a + 0.001`); }
    b = a + 0.001;
  }
  return interpolate(t, [a, b], [from, to], { ...clamp, easing: e });
};

// 0 -> 1 -> 0: rises at a, holds, falls (highlights, flashes)
export const pulse = (t: number, a: number, up = 0.12, hold = 0.35, down = 0.4) =>
  ramp(t, a, a + up) - ramp(t, a + up + hold, a + up + hold + down);

// visible between a and b with fades (overlays)
export const shown = (t: number, a: number, b: number, fadeIn = 0.3, fadeOut = 0.3) =>
  ramp(t, a, a + fadeIn) * (1 - ramp(t, b, b + fadeOut));

// scale for a pop-in that overshoots and settles
export const pop = (t: number, at: number, over = 0.3, from = 0.6, peak = 1.15) =>
  interpolate(t - at, [0, 0.1, Math.max(over, 0.101)], [from, peak, 1], { ...clamp, easing: Easing.out(Easing.quad) });

// Loop correction: raw(t) plus a smooth offset from `from` to `to`, so the value at `to`
// lands on raw(0) + a whole number of `step`s. With step = the object's symmetry (2π/5 for a
// ball about a pentagon axis, 2π for anything), the last frame matches the first.
export const loopTo = (raw: (t: number) => number, from: number, to: number, step = 2 * Math.PI) => {
  const end = raw(to);
  const target = raw(0) + Math.round((end - raw(0)) / step) * step;
  return (t: number) => raw(t) + (target - end) * ramp(t, from, to);
};
