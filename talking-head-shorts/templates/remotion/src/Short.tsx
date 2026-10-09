import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useFont } from "./fonts";
import specJson from "./edit.json"; // written by build.py from edit.vN.json: the ONLY per-video input
import blinkJson from "./blink.json"; // per 30 fps frame of the source: 1 = normal picture, 0 = black
import type { Blink, Cutaway as CutawayT, HookLine, Pill as PillT, Spec, W } from "./types";

const S = specJson as unknown as Spec;
const BLINK = blinkJson as unknown as Blink;

export const FPS = 30;
const SW = 1080;
const SH = 1920;
const { source: SRC, style: ST } = S;
const SRC_SEC = SRC.end - SRC.start;
const HOOK_SEC = S.hook.kind === "none" ? 0 : S.hook.kind === "cold" ? S.hook.clip[1] - S.hook.clip[0] : S.hook.seconds;
export const HOOK_FRAMES = Math.round(HOOK_SEC * FPS);
const SRC_FRAMES = Math.ceil(SRC_SEC * FPS);
export const TOTAL_FRAMES = HOOK_FRAMES + SRC_FRAMES;

const FONT = ST.font;
const ACCENT = ST.accent;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const sec = (t: number) => Math.round(t * FPS);
const col = (c?: string) => (c === "accent" ? ACCENT : c || "#fff");
const blinkAt = (t: number) => BLINK.values[Math.round(t * FPS)] ?? 1;

// ---------- captions: word by word, hot words in the accent colour ----------
const HOT = new Set(S.hot.map((w) => w.toUpperCase()));
const PHRASES: W[][] = S.phrases;

const Captions = ({ t }: { t: number }) => {
  const phrase = PHRASES.find((p) => t >= p[0][1] - 0.04 && t < p[p.length - 1][2] + 0.12);
  if (!phrase) return null;
  const inT = t - (phrase[0][1] - 0.04);
  const pop = interpolate(inT, [0, 0.1], [0.8, 1], clamp);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: ST.captionTop }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: `0 ${ST.captionGap}px`,
          width: ST.captionWidth,
          transform: `scale(${pop})`,
          fontFamily: FONT,
          fontSize: ST.captionSize,
          lineHeight: 1.08,
          textTransform: "uppercase",
        }}
      >
        {phrase.map(([w, s], i) => {
          const active = t >= s;
          const current = active && (i === phrase.length - 1 || t < phrase[i + 1][1]);
          const hot = HOT.has(w.toUpperCase());
          const color = hot ? ACCENT : current ? ST.current : ST.text;
          return (
            <span
              key={i}
              style={{
                color,
                WebkitTextStroke: `${ST.captionStroke}px #000`,
                paintOrder: "stroke fill",
                textShadow: "0 8px 24px rgba(0,0,0,0.7)",
                transform: current ? "scale(1.12)" : "scale(1)",
                display: "inline-block",
                opacity: active ? 1 : 0,
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- picture boxes: where the source (or its matte) sits in the 1080x1920 frame ----------
const coverBox = (w: number, h: number) => {
  const k = Math.max(SW / w, SH / h);
  return { position: "absolute" as const, left: (SW - w * k) / 2, top: (SH - h * k) / 2, width: w * k, height: h * k };
};
const videoBox = () => {
  if (SRC.fit === "crop" && SRC.crop) {
    const [x, y, cw, ch] = SRC.crop;
    const k = Math.max(SW / cw, SH / ch);
    return { position: "absolute" as const, left: (SW - cw * k) / 2 - x * k, top: (SH - ch * k) / 2 - y * k, width: SRC.w * k, height: SRC.h * k };
  }
  return coverBox(SRC.w, SRC.h);
};
const matteBox = () => (SRC.fit === "crop" && SRC.crop ? coverBox(SRC.crop[2], SRC.crop[3]) : coverBox(SRC.w, SRC.h));

// The source video, fitted: cover, crop to the speaker, or the whole frame over its own blur.
const SourceVideo = ({ t0, filter }: { t0: number; filter: string }) => {
  const src = staticFile(SRC.file);
  if (SRC.fit === "blurfill") {
    const fh = Math.round((SW * SRC.h) / SRC.w);
    return (
      <AbsoluteFill>
        <OffthreadVideo src={src} startFrom={sec(t0)} muted style={{ ...coverBox(SRC.w, SRC.h), filter: "blur(40px) brightness(0.5)", transform: "scale(1.25)" }} />
        <OffthreadVideo src={src} startFrom={sec(t0)} muted style={{ position: "absolute", left: 0, top: (SH - fh) / 2, width: SW, height: fh, filter }} />
      </AbsoluteFill>
    );
  }
  return <OffthreadVideo src={src} startFrom={sec(t0)} muted style={{ ...videoBox(), filter }} />;
};

// ---------- person layer: hard punch-in steps, slow drift, optional cut-out over a new background ----------
const Person = ({ t0, steps, drift, shakes, matte }: { t0: number; steps: [number, number][]; drift: number; shakes: Spec["shakes"]; matte: boolean }) => {
  const frame = useCurrentFrame();
  const t = t0 + frame / FPS;
  let base = 1;
  for (const [at, v] of steps) if (t >= at) base = v;
  const dr = 1 + drift * ((t - t0) / SRC_SEC);
  let shake = 0;
  for (const s of shakes) if (t > s.at && t < s.at + s.dur) shake = Math.sin(t * 90) * s.amp * (1 - (t - s.at) / s.dur);
  const M = S.matte;
  const useMatte = matte && !!M && !!S.bg;
  const person = base * dr;
  const vignette = ST.vignette ? (
    <>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.65) 100%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
    </>
  ) : null;
  if (!useMatte || !M || !S.bg) {
    return (
      <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
        <AbsoluteFill style={{ transform: `translate(${shake}px, ${shake * 0.5}px) scale(${person})`, transformOrigin: S.origin }}>
          <SourceVideo t0={t0 + 0} filter={ST.grade} />
        </AbsoluteFill>
        {vignette}
      </AbsoluteFill>
    );
  }
  const B = S.bg;
  const n = Math.min(M.count - 1, Math.max(0, Math.round((t - M.start) * FPS)));
  const dip = 1 - blinkAt(t); // the source blinks to black: dip the WHOLE picture, background too
  const bgZoom = 1 + (person - 1) * B.parallax + B.creep * ((t - t0) / SRC_SEC);
  const bw = Math.round(B.w * B.scale);
  const bh = Math.round(B.h * B.scale);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <AbsoluteFill style={{ transform: `translate(${shake * 0.5}px, ${shake * 0.25}px) scale(${bgZoom})`, transformOrigin: B.origin }}>
        {B.filler && <div style={{ position: "absolute", left: B.left, top: B.top + bh - 12, width: bw, height: 600, background: `linear-gradient(180deg, ${B.filler[0]} 0%, ${B.filler[1]} 60%)` }} />}
        <Img src={staticFile(B.image)} style={{ position: "absolute", left: B.left, top: B.top, width: bw, height: bh, filter: `blur(${B.blur}px) brightness(${B.brightness}) saturate(${B.saturate})` }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ transform: `translate(${shake}px, ${shake * 0.5}px) scale(${person})`, transformOrigin: S.origin }}>
        <Img
          src={staticFile(`${M.dir}/f${String(n).padStart(4, "0")}.png`)}
          style={{ ...matteBox(), filter: `${ST.grade} ${B.grade} drop-shadow(0 0 16px ${B.glow}) drop-shadow(0 0 40px rgba(0,0,0,0.5))` }}
        />
      </AbsoluteFill>
      {vignette}
      <AbsoluteFill style={{ background: "#000", opacity: dip }} />
    </AbsoluteFill>
  );
};

// ---------- cutaway cards ----------
const Blurred = ({ src }: { src: string }) => (
  <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
    <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(36px) brightness(0.45) saturate(1.2)", transform: "scale(1.3)" }} />
  </AbsoluteFill>
);

// Slides in with a spring, holds with a slow push-in, slides out left. ring is a fraction of the picture (0..1).
const Cutaway = ({ c, dur }: { c: CutawayT; dur: number }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inn = spring({ frame, fps, config: { damping: 16, stiffness: 160 } });
  const out = interpolate(frame, [dur - 6, dur], [0, 1], clamp);
  const x = interpolate(inn, [0, 1], [1100, 0]) - out * 1100;
  const push = 1 + 0.06 * (frame / dur);
  const ringPop = spring({ frame: frame - 12, fps, config: { damping: 9, stiffness: 200 } });
  return (
    <AbsoluteFill style={{ transform: `translateX(${x}px)` }}>
      <Blurred src={c.src} />
      <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: c.top ?? 200 }}>
        <div style={{ position: "relative", width: c.w, height: c.h, transform: `scale(${push})`, boxShadow: "0 30px 80px rgba(0,0,0,0.7)", borderRadius: 14, overflow: "hidden" }}>
          <Img src={staticFile(c.src)} style={{ width: c.w, height: c.h }} />
          {c.ring && (
            <div
              style={{
                position: "absolute",
                left: c.ring[0] * c.w - 90,
                top: c.ring[1] * c.h - 90,
                width: 180,
                height: 180,
                borderRadius: "50%",
                border: `12px solid ${ACCENT}`,
                transform: `scale(${interpolate(ringPop, [0, 1], [2.5, 1])})`,
                opacity: ringPop,
                boxShadow: `0 0 40px ${ACCENT}`,
              }}
            />
          )}
        </div>
        {c.label && (
          <div style={{ marginTop: 14, fontFamily: FONT, fontSize: 104, color: "#fff", background: ACCENT, padding: "6px 36px", transform: `rotate(-3deg) scale(${interpolate(ringPop, [0, 1], [1.8, 1])})`, opacity: ringPop }}>
            {c.label}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------- stat pills and counters ----------
const Pill = ({ p, t }: { p: PillT; t: number }) => {
  const { fps } = useVideoConfig();
  const s = spring({ frame: sec(t - p.at), fps, config: { damping: 11, stiffness: 190 } });
  if (t < p.at) return null;
  const big = typeof p.big === "number" ? String(Math.round(interpolate(t, [p.at, p.at + (p.count ?? 0.8)], [0, p.big], clamp))) : p.big;
  return (
    <div style={{ transform: `scale(${s}) rotate(${interpolate(s, [0, 1], [-8, 0])}deg)`, transformOrigin: "left center", display: "flex", alignItems: "baseline", gap: 16, background: p.hot ? ACCENT : "#0b0b0b", border: "5px solid #fff", borderRadius: 18, padding: "4px 26px", fontFamily: FONT, color: "#fff" }}>
      <span style={{ fontSize: 120, lineHeight: 1.1 }}>{big}</span>
      <span style={{ fontSize: 56, color: p.hot ? "#fff" : ST.current }}>{p.small}</span>
    </div>
  );
};

const Pills = ({ t }: { t: number }) => (
  <>
    {S.pills.map((g, i) => {
      if (t < g.from || t > g.to) return null;
      const slideOut = interpolate(t, [g.to - 0.2, g.to], [0, -700], clamp);
      return (
        <AbsoluteFill key={i} style={{ paddingTop: g.top ?? 170, paddingLeft: g.left ?? 50, gap: 18, display: "flex", flexDirection: "column", alignItems: "flex-start", transform: `translateX(${slideOut}px)` }}>
          {g.pills.map((p, k) => (
            <Pill key={k} p={p} t={t} />
          ))}
        </AbsoluteFill>
      );
    })}
  </>
);

const Counters = ({ t }: { t: number }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {S.counters.map((c, i) => {
        if (t < c.from || t > c.to) return null;
        const n = Math.round(interpolate(t, [c.from, c.from + (c.count ?? 0.5)], [0, c.value], clamp));
        const s = spring({ frame: sec(t - c.from), fps, config: { damping: 10, stiffness: 200 } });
        const out = interpolate(t, [c.to - 0.2, c.to], [1, 0], clamp);
        return (
          <AbsoluteFill key={i} style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: c.top ?? 170, opacity: out }}>
            <div style={{ transform: `scale(${interpolate(s, [0, 1], [2.2, 1])})`, textAlign: "center", fontFamily: FONT, color: "#fff", background: ACCENT, padding: "0 50px 10px", border: "6px solid #fff", borderRadius: 20 }}>
              <div style={{ fontSize: 250, lineHeight: 1.05 }}>{n}</div>
              <div style={{ fontSize: 90, marginTop: -20 }}>{c.label}</div>
            </div>
          </AbsoluteFill>
        );
      })}
    </>
  );
};

const Slams = ({ t }: { t: number }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {S.slams.map((m, i) => {
        if (t < m.from || t > m.to) return null;
        const s = spring({ frame: sec(t - m.from), fps, config: { damping: 9, stiffness: 220, mass: 0.7 } });
        const out = interpolate(t, [m.to - 0.15, m.to], [1, 0], clamp);
        return (
          <AbsoluteFill key={i} style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: m.top, opacity: out }}>
            <div style={{ fontFamily: FONT, fontSize: 200, color: col(m.color), WebkitTextStroke: "14px #000", paintOrder: "stroke fill", transform: `scale(${interpolate(s, [0, 1], [3, 1])}) rotate(${interpolate(s, [0, 1], [-10, -4])}deg)`, opacity: s }}>
              {m.text}
            </div>
          </AbsoluteFill>
        );
      })}
    </>
  );
};

const Flashes = ({ t }: { t: number }) => {
  const f = S.flashes.find((a) => t >= a && t < a + 0.14);
  if (f === undefined) return null;
  return <AbsoluteFill style={{ background: "#fff", opacity: interpolate(t, [f, f + 0.14], [0.55, 0], clamp) }} />;
};

// ---------- main: everything after the hook ----------
const Main = () => {
  const frame = useCurrentFrame();
  const t = SRC.start + frame / FPS;
  const at = (a: number) => sec(a - SRC.start);
  return (
    <AbsoluteFill>
      <Person t0={SRC.start} steps={S.steps} drift={S.drift} shakes={S.shakes} matte />
      {S.cutaways.map((c, i) => (
        <Sequence key={i} from={at(c.from)} durationInFrames={sec(c.to - c.from)}>
          <Cutaway c={c} dur={sec(c.to - c.from)} />
        </Sequence>
      ))}
      <Pills t={t} />
      <Counters t={t} />
      <Slams t={t} />
      <Flashes t={t} />
      <Captions t={t} />
    </AbsoluteFill>
  );
};

// ---------- hook: cold open on the user's own line, an image, or a text slam, then the story starts ----------
const HookText = ({ lines }: { lines: HookLine[] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 9, stiffness: 240, mass: 0.7 } });
  return (
    <div style={{ textAlign: "center", fontFamily: FONT, fontSize: 190, lineHeight: 1.0, color: "#fff", WebkitTextStroke: "12px #000", paintOrder: "stroke fill", transform: `scale(${interpolate(s, [0, 1], [2.6, 1])}) rotate(${interpolate(s, [0, 1], [-6, -2])}deg)`, opacity: s }}>
      {lines.map((l, i) => (
        <div key={i} style={{ color: col(l.color) }}>
          {l.text}
        </div>
      ))}
    </div>
  );
};

const Hook = () => {
  const frame = useCurrentFrame();
  const h = S.hook;
  if (h.kind === "none") return null;
  const push = 1 + 0.12 * (frame / HOOK_FRAMES);
  const flash = interpolate(frame, [0, 4], [0.9, 0], clamp);
  const shade = <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.85) 100%)" }} />;
  const text = (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
      <HookText lines={h.lines} />
    </AbsoluteFill>
  );
  const white = <AbsoluteFill style={{ background: "#fff", opacity: flash }} />;
  if (h.kind === "image") {
    const [bl, bt, bh] = h.box ?? [0, 150, 1500];
    return (
      <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
        <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: "50% 40%" }}>
          <Blurred src={h.image} />
          <Img src={staticFile(h.image)} style={{ position: "absolute", height: bh, left: bl, top: bt }} />
        </AbsoluteFill>
        {shade}
        {text}
        {white}
      </AbsoluteFill>
    );
  }
  if (h.kind === "slam") {
    return (
      <AbsoluteFill style={{ background: h.bg ?? `radial-gradient(circle at 50% 45%, ${ACCENT} 0%, #120000 75%)`, overflow: "hidden" }}>
        {text}
        {white}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: S.origin }}>
        <Person t0={h.clip[0]} steps={[[0, 1.12]]} drift={0} shakes={[]} matte={false} />
      </AbsoluteFill>
      {shade}
      {text}
      {white}
    </AbsoluteFill>
  );
};

export const Short = () => {
  useFont(FONT, ST.fontFile);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {HOOK_FRAMES > 0 && (
        <Sequence durationInFrames={HOOK_FRAMES}>
          <Hook />
        </Sequence>
      )}
      <Sequence from={HOOK_FRAMES}>
        <Main />
      </Sequence>
    </AbsoluteFill>
  );
};
