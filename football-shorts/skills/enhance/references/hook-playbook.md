# Hook playbook

A viewer decides in about one second whether to swipe. The hook is what is on
screen and in text at 0.0–1.5 s. Pick the three that fit the footage, offer them,
recommend one. Channel rules still apply (`../build/references/channel-style.md`,
or `yt-insights/style.md` when it exists): no title card first, no questions in the
title, text changes every 1.5–2.5 s.

| Hook | First 1.5 s | Fits | Spec shape |
|---|---|---|---|
| **Flash-forward** | The payoff frame (the absurd miss, the keeper's save, the player lying in the net), moving, with a context line | any clip with a clear payoff that is not the very first moment | segment 0 = payoff `clip` with a slow `zoom` 1.0→1.12; the payoff reappears later in full |
| **Counter** | Context line + "COUNT THE MISSES" / "HOW MANY?" badge on the first chance | 3+ similar moments (misses, nutmegs, saves, dives) | a badge per moment (`MISS #1 ❌` …), `bass`+`ding` on each; the last one gets the biggest freeze |
| **Stakes line** | The build-up with one line of what is at stake ("LAST MINUTE. 0-0.") | one big moment with context the viewer needs | persistent top line; `riser` into the moment; freeze + `bass` on it |
| **Reaction first** | The player's or bench's reaction face, then cut to what caused it | strong close-up reactions in the footage | reaction `clip` with a `zoom` punch, then `whoosh` into the moment |
| **Verdict challenge** | The moment frozen just before contact with "GOAL OR NOT?" style badge | a close call, VAR, a shot that hits the post | `still` at the instant before, then play out; not for the title (no questions there) |
| **Before/after split** | Two halves: the chance and the reaction, or two similar moments | contrasts, repeats, "same player, same spot" | `split` segment, 1.5–2.5 s |

## Retention craft after the hook

- A change every 1.5–3 s: a cut, a caption change, a zoom or a hit. `check.py --spec` measures the longest stretch without one.
- Real speed for build-ups, factor-2 `slowmo` only on the decisive 0.7–0.8 s; slow-mo on a whole clip kills pace. Show the outcome before the badge: a counter that appears before the ball has missed feels like a spoiler, and one on a moment the viewer never saw clearly feels fake.
- Cut crowd pans, walking back and broadcast graphics. A replay stays when it shows a key moment better (closer, clearer, funnier) than the live angle, which on wide broadcast footage is often the case; drop it only when it repeats a view already shown clearly. Look at the frames before deciding: a replay can score as "low motion" in the analysis.
- Punch-in zoom on reactions, push-in zoom through slow-mo, `shake` only on impacts and freezes.
- White `flash` only on a hard cut into a new chance, never on segment 0.
- End on the payoff or a freeze, and make the last frame lead back into the first so the replay feels continuous.
- Low-resolution sources (under ~540 px on the short side): keep punch-ins at 1.15× or less.

## Sound without source audio

Many user clips have no audio track (`analyse.py` says so). Then every sound comes
from the spec:
- `whoosh` 0.3 s before each hard cut, `riser` over the 1.5–2.5 s before the payoff, `bass` on freezes and verdicts, `ding` or `tick` for counters.
- Tell the user to add a trending sound at upload (Shorts "Add sound"), or give `audio.bed.file` a music file they hold rights to; keep the bed at 0.2–0.3 under the hits.

## Worked example: a 25 s "misses" compilation (letterboxed, silent)

Original: miss 1 → crowd reaction → miss 2 → reaction → miss 3 → miss 4 live (reverse wide angle) → miss 4 aftermath
close-up at the post → miss 4 slow-mo replay from another angle. Four misses, not five or six: the close-up and the
replay share the keeper, the post and the defender with miss 4 live.

First attempts went wrong in instructive ways: trimming to "60-75 % of the original" cut the clearest view of a miss;
slow-mo landed on an aftermath instead of the shot; a replay got its own number; an old badge stayed up during the next
chance. The final 22.5 s cut: flash-forward to the goal-line aftermath with "COUNT THE MISSES" → each miss as build →
slow-mo on the shot → outcome → `MISS #n ❌` badge (cleared before the next chance) → reactions as punch-ins →
goal-line `boomerang` with "NOT LIKE THIS 💀" → replay badged "SLOW-MO REPLAY" at source speed → freeze + shake on
"4 MISSES 💀", which loops into the opening frame.

