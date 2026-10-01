import words from "./words.json";
import { OUTRO_S } from "./kit/Outro";

// Word times (s) from the story's narration.words, copied to src/words.json by anim.py.
// Spoken numbers carry Whisper's own times (tighten.py patches them).
export type Word = { line: string; i: number; w: string; start: number; end: number };
export const WORDS: Word[] = (words as { words?: Word[] }).words ?? (words as unknown as Word[]);
export const FPS = 30;

const clean = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

// A word by 0-based index (negative counts from the end of the line) or by its text
// ("isn't" -> "isnt"); nth picks a later repeat of the same word in that line.
export const word = (line: string, w: number | string, nth = 1): Word => {
  const ws = WORDS.filter((x) => x.line === line);
  if (!ws.length) throw new Error(`no line ${line} in words.json`);
  const hit = typeof w === "number"
    ? ws[w < 0 ? ws.length + w : w]
    : ws.filter((x) => clean(x.w) === clean(w))[nth - 1];
  if (!hit) throw new Error(`word not found: ${line} ${w}${nth > 1 ? ` #${nth}` : ""}`);
  return hit;
};
export const at = (line: string, w: number | string, nth = 1) => word(line, w, nth).start;
export const endOf = (line: string, w: number | string, nth = 1) => word(line, w, nth).end;
export const lineStart = (line: string) => Math.min(...WORDS.filter((x) => x.line === line).map((x) => x.start));
export const lineEnd = (line: string) => Math.max(...WORDS.filter((x) => x.line === line).map((x) => x.end));

// End of the last spoken word, then the like & subscribe badge (its length lives in kit/Outro.tsx),
// while the scene finishes its loop back to the first frame.
export const END = Math.max(...WORDS.map((x) => x.end));
export const OUTRO_AT = END + 0.05;
export const DURATION_S = Math.ceil((OUTRO_AT + OUTRO_S) * FPS) / FPS;
export const LAST_T = DURATION_S - 1 / FPS; // time of the last frame (must match frame 0)
