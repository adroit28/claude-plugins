// The edit spec (schema talking-head-shorts/1). Every time is in SOURCE seconds unless noted.
export type W = [string, number, number]; // word, start, end

export type Source = {
  file: string; // in public/
  start: number;
  end: number;
  w: number;
  h: number;
  fit: "cover" | "crop" | "blurfill";
  crop?: [number, number, number, number]; // x, y, w, h in source pixels (fit = crop)
};

export type Style = {
  font: string;
  fontFile: string;
  accent: string; // hot words, slam highlights, pills
  current: string; // the word being spoken
  text: string;
  captionSize: number;
  captionTop: number;
  captionWidth: number;
  captionStroke: number;
  captionGap: number;
  grade: string; // css filter on the person
  vignette: boolean;
};

export type HookLine = { text: string; color?: string }; // color: "accent" | css colour | omitted = white
export type Hook =
  | { kind: "none" }
  | { kind: "image"; seconds: number; image: string; box?: [number, number, number]; lines: HookLine[] } // box = left, top, height
  | { kind: "slam"; seconds: number; lines: HookLine[]; bg?: string }
  | { kind: "cold"; clip: [number, number]; lines: HookLine[] }; // cold open from the user's own best line

export type Cutaway = { src: string; from: number; to: number; w: number; h: number; ring?: [number, number]; label?: string; top?: number };
export type Pill = { big: string | number; small: string; at: number; hot?: boolean; count?: number };
export type PillGroup = { from: number; to: number; top?: number; left?: number; pills: Pill[] };
export type Counter = { from: number; to: number; value: number; count?: number; label: string; top?: number };
export type Slam = { from: number; to: number; text: string; color?: string; top: number };
export type Shake = { at: number; dur: number; amp: number };

export type Bg = {
  image: string;
  w: number; // natural size
  h: number;
  scale: number;
  left: number;
  top: number;
  blur: number;
  brightness: number;
  saturate: number;
  origin: string; // transform origin, e.g. "540px 1000px"
  parallax: number; // 0.5 = background zooms half as much as the person
  creep: number; // extra slow push-in over the clip
  filler?: [string, string] | null; // dark strip below the picture when placement exposes the bottom edge
  grade: string; // css filter on the person over this background
  glow: string; // outer glow colour (inner rim light is an optional upgrade)
};
export type Matte = { dir: string; start: number; count: number };

export type Spec = {
  schema: string;
  slug: string;
  version: number;
  source: Source;
  style: Style;
  hook: Hook;
  phrases: W[][];
  hot: string[];
  steps: [number, number][];
  drift: number;
  origin: string;
  shakes: Shake[];
  flashes: number[];
  cutaways: Cutaway[];
  pills: PillGroup[];
  counters: Counter[];
  slams: Slam[];
  bg: Bg | null;
  matte: Matte | null;
  sfx: [string, number, number][]; // [name, source seconds, volume] (the mixer uses these, not Remotion)
  hook_sfx: [string, number, number][]; // [name, seconds into the hook, volume]
  music: { drone: boolean; vol?: number };
  outro: { seconds: number };
};

export type Blink = { fps: number; values: number[] };
