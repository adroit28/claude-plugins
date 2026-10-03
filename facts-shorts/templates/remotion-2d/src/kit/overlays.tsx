import { Easing, interpolate } from "remotion";
import { WORDS } from "../timing";
import { pop } from "./anim";

// Overlay layout (1080x1920): numbers and tags sit in the top band (y 200-560), captions at y 1330,
// the picture in between (y ~300-1280). Keep anything new out of the subject's box.
export const STROKE = (px: number) => ({ WebkitTextStroke: `${px}px #000`, paintOrder: "stroke fill" }) as const;
export const CAPTION_Y = 1330;

// Caption chunks: up to `max` words, broken after punctuation, held until the next chunk
// (at most 0.5 s past the last word), never past `until`.
const chunks = (max: number, until: number) => {
  const out: { text: string; start: number; end: number }[] = [];
  for (const l of [...new Set(WORDS.map((w) => w.line))]) {
    let g: typeof WORDS = [];
    const flush = () => {
      if (g.length) out.push({ text: g.map((w) => w.w.replace(/[.,!?:;]+$/, "")).join(" "), start: g[0].start, end: g[g.length - 1].end });
      g = [];
    };
    for (const w of WORDS.filter((x) => x.line === l)) {
      g.push(w);
      if (g.length === max || /[.,!?:;]$/.test(w.w)) flush();
    }
    flush();
  }
  return out.map((c, i) => ({ ...c, end: Math.min(until, Math.max(c.end, Math.min(out[i + 1]?.start ?? c.end + 0.5, c.end + 0.5))) }));
};

let cache: { key: string; list: ReturnType<typeof chunks> } | null = null;

export const Caption = ({ t, until = Infinity, max = 2, y = CAPTION_Y }: { t: number; until?: number; max?: number; y?: number }) => {
  const key = `${max}:${until}`;
  if (cache?.key !== key) cache = { key, list: chunks(max, until) };
  const c = cache.list.find((k) => t >= k.start && t < k.end);
  if (!c) return null;
  const s = interpolate(t - c.start, [0, 0.12], [0.85, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.back(2)) });
  return (
    <div style={{ position: "absolute", top: y, width: "100%", textAlign: "center", fontFamily: "Barlow", fontSize: 92,
      color: "#fff", textTransform: "uppercase", letterSpacing: 1, transform: `scale(${s})`,
      ...STROKE(10), textShadow: "0 8px 24px rgba(0,0,0,.45)" }}>
      {c.text}
    </div>
  );
};

// Big number with a label under it. `hitAt`: the moment the final value lands (scale punch + colour).
export const Counter = ({ value, label, opacity, t, hitAt, hitColor = "#ffc400", top = 230 }: {
  value: number | string; label: string; opacity: number; t: number; hitAt?: number; hitColor?: string; top?: number;
}) => {
  if (opacity <= 0) return null;
  const hit = hitAt !== undefined && t >= hitAt;
  const s = hit ? interpolate(t - hitAt!, [0, 0.15, 0.4], [1, 1.25, 1], { extrapolateRight: "clamp" }) : 1;
  return (
    <div style={{ position: "absolute", top, width: "100%", textAlign: "center", opacity }}>
      <div style={{ fontFamily: "Anton", fontSize: 260, lineHeight: 1, color: hit ? hitColor : "#fff", transform: `scale(${s})`, ...STROKE(8) }}>{value}</div>
      <div style={{ fontFamily: "Barlow", fontSize: 64, color: "#fff", letterSpacing: 6, ...STROKE(6) }}>{label}</div>
    </div>
  );
};

// Tag card: small line on top (a year), big value popping in on its word, label under it.
export const Tag = ({ t, at, over, value, under, color = "#fff", opacity = 1, top = 210 }: {
  t: number; at: number; over?: string | number; value: string | number; under?: string; color?: string; opacity?: number; top?: number;
}) => {
  if (t < at || opacity <= 0) return null;
  return (
    <div style={{ position: "absolute", top, width: "100%", textAlign: "center", opacity }}>
      {over !== undefined && <div style={{ fontFamily: "Barlow", fontSize: 76, color: "#ffffffcc", letterSpacing: 8, ...STROKE(8) }}>{over}</div>}
      <div style={{ fontFamily: "Anton", fontSize: 250, lineHeight: 1, color, transform: `scale(${pop(t, at)})`, ...STROKE(8) }}>{value}</div>
      {under && <div style={{ fontFamily: "Barlow", fontSize: 64, color: "#fff", letterSpacing: 6, ...STROKE(8) }}>{under}</div>}
    </div>
  );
};
