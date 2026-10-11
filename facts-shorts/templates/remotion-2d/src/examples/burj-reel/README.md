# burj-reel: a worked example of "dynamic by default" (Burj Khalifa Reel 1 v2)

Not imported by any Short (the build ignores it, `tsc` still checks it). Copy what you need into `src/` and fix the import paths
(`../../kit` -> `./kit`, `../../timing` -> `./timing`).

| File | Shows |
|---|---|
| `Burj.tsx` | ONE shared hero illustration reused by every beat. Props for each beat's needs: `flex` (progressive bend, top moves most), `lit(f,row)` (per-row lights), `rim`/`glow`, `ghost` (outline only, `ghostFill`), `stretch`. Draw it ONCE, test it on a contact sheet next to the reference photo, then reuse it. |
| `hookbeat.tsx` | A moving open: filmed photo (tilt up the subject on its word), glitch + shake + flash on the hit word, a whip-pan on the turn, a slot-machine counter that explodes on the payoff word, risers into the reveal, frame 0 = last frame. (Generic parts now live in `kit/cinema.tsx`: `CamPhoto`, `SlotCounter`.) |
| `sunbeat.tsx` | A camera ride: one camera (z, f, k) and layers with parallax factors (sun 0.08, far skyline 0.22, mid 0.55, hero 1, clouds 1.2, palms 1.3) = `rigTransform`; lens flare, speed lines, curved horizon. |
| `fact2beat.tsx` | Split screen explained top to bottom: marker rides the hero on the left, a gauge on the right reacts; a bracket joins the two readings; ticks sync to the gauge. |
| `fact3beat.tsx` | Real wind: streamlines that bend around the hero, debris, a hero that flexes progressively, ghost outlines at the extremes, a sound bed whose volume follows the same `wind(t)` as the picture. |
| `bonusbeat.tsx` | The hero again for a different claim (lights go out from the top, a hollow void glow), a riser into the comment ask, a bubble that stays clear of the hero. |

Sound in these files follows the level bands in `references/dynamic.md` (ambience 0.10-0.25, hits 0.20-0.35, voice about 9 LU above the effects).
