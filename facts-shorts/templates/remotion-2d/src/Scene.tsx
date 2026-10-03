import { interpolate } from "remotion";
import { WORDS, lineStart, OUTRO_AT, LAST_T } from "./timing";
import { ramp } from "./kit/anim";
import { Bubble, HookProp, Layer, Sfx, Title, clamp } from "./kit/props";

// STARTER scene: replace it with the storyboard (see the plugin's video/references/template.md).
// It works with any script so `anim.py init` renders straight away: the hook prop rings, the
// title shows until line 2, each later line gets a numbered bubble, and the hook comes back
// during the outro so the last frame matches the first. Anchor every change to a word with
// at("L3", "pirates") / lineStart("L4"); never hard-code seconds.

export const BACKGROUND = "radial-gradient(circle at 50% 38%, #4a3320 0%, #1f150d 55%, #0d0906 100%)";

const LINES = [...new Set(WORDS.map((w) => w.line))];
const L2 = LINES.length > 1 ? lineStart(LINES[1]) : OUTRO_AT;

export const Overlays = ({ t }: { t: number }) => {
  const loopIn = ramp(t, OUTRO_AT, OUTRO_AT + 0.4);           // the hook returns under the badge
  const hookOp = (1 - ramp(t, L2 + 0.2, L2 + 0.6)) + loopIn;
  const ringing = t < 0.5 || t > LAST_T - 0.9;
  return (
    <>
      <Sfx at={0} src="ring" vol={0.45} />
      <Sfx at={0.5} src="click" vol={0.7} />
      {LINES.slice(1).map((l) => <Sfx key={l} at={lineStart(l) - 0.15} src="whoosh" vol={0.35} />)}
      <Sfx at={LAST_T - 0.55} src="ring" vol={0.3} />

      <Title t={t} accent="WHY" rest="THIS?" opacity={hookOp} />
      <HookProp t={t} char="☎️" active={ringing} opacity={hookOp}
        scale={t < 0.5 ? 1 : interpolate(t - 0.5, [0, 0.12, 0.3], [1, 0.92, 1], clamp)} />

      {LINES.slice(1).map((l, i) => {
        const a = lineStart(l), b = i + 2 < LINES.length ? lineStart(LINES[i + 2]) : OUTRO_AT;
        return t >= a && t < b ? (
          <Layer key={l}>
            <Bubble t={t} a={a} text={l} x={540} y={760} size={200} />
          </Layer>
        ) : null;
      })}
    </>
  );
};
