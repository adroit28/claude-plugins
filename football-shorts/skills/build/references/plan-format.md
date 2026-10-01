# Beat plan format (plan.py) and spec ops (spec.py)

The model writes a short plan; `plan.py` writes the JSON. Every spec field in
`spec-format.md` is reachable from a plan line, so hand-written spec JSON should
never be needed. Later versions are not re-planned: `spec.py` applies small ops
to the previous spec and prints what moved.

```
PY=<shorts dir>/.venv/bin/python   S=${CLAUDE_PLUGIN_ROOT}/skills/build/scripts
$PY $S/plan.py shorts/<slug>/plan.v1.md              -> shorts/<slug>/spec.v1.json + timeline
$PY $S/spec.py shorts/<slug>/spec.v1.json bump -- shift fan-angle +0.6 -- caption set ov:"TWO SHORT" to=@fan-angle.end
```

## plan.vN.md

Plain text. `#` starts a comment (a whole line, or ` # note` after a space).
Header lines are `key value`; then three sections `beats`, `overlays`, `hits`
(headings may carry `##`). A `.json` plan with the same keys also works.

```
slug messi-fk-76
version 7
fps 25                          # default 25; size 1080x1920; max_duration 30
source fk src/fk.mp4            # one line per source key
source quotes src/quotes.mp4
fill box=478,254,0,298 cy=0.47 dark=0.12 blur=6     # optional, or `fill none`
audio clip_volume=1.0 loudnorm=I=-15:TP=-3:LRA=11   # optional (these are the defaults)
bed file=src/crowd.wav volume=0.4                   # optional
spine question="3 LEGENDS. 1 NAME." turn=10 button=13   # REQUIRED (hook-playbook: spine before cuts)
bpm 128 offset=0.0              # optional: cuts snap to the beat grid (±0.25 s, via the previous beat)
end none                        # default `end loop`: adds a 0.4 s still of the opening frame when
                                # the last beat is not already on the opening source

beats
# src   in     out     effect        caption            hit         extras (any spec key=value, JSON allowed)
quotes  37.46  +1.48   clip          -                  bass+0.02   label=mbappe-world crop=[608,1080,0,0] hit.volume=0.5
fk      25.8   26.72   clip          -                  -           mute=true zoom={"from":1.0,"to":1.1,"ease":"out"}
fk      28.88  +0.64   still         "text:THIS CLOSE"  bass        cap.y=900 cap.size=110 cap.emoji=🤏 zoom=0
alt     11.56  +2.16   clip:1.6667x  -                  -           crop={"w":492,"h":875,"x_from":90,"x_to":116,"y":0}
fk      26.5   +0.8    ramp:26.72:x3 -                  impact      label=strike        # slows 3x around source 26.72
v       24.4   +0.72   slowmo:x2     "small:REPLAY"     -           cap.from=+0.2 cap.to=@G10
-       -      +1.2    card          -                  -           lines=[{"text":"14 GOALS","size":120}] bg=#000000
```

Beat columns: `src` key (or `-` for cards/splits) · `in` source seconds (`ss`, or `at`
for a still) · `out` absolute source seconds or `+length` · `effect` · `caption` ·
`hit` · extras. Lengths of `clip`/`still`/`card`/`split` are snapped to whole
frames; other types get `t` as written and `render.py` pins the frame count.

| effect | spec | notes |
|---|---|---|
| `clip`, `clip:1.6667x` | `clip` with `speed` | |
| `still` | `still` with `at` | `in` is the frozen frame |
| `slowmo:x2` | `slowmo` factor 2 | length = t × factor |
| `reverse:x1.25` | `reverse` slow 1.25 | |
| `boomerang:x2` | `boomerang` loops 2 | length = t × 2 × loops |
| `split`, `card` | as named | give `top=`/`bottom=`/`lines=` in extras |
| `ramp:<slow_at>:x<factor>` | `ramp` | real speed → eased slow-down around source `slow_at` → back out; `hold=` (0.16 s) `ease=` (0.2 s) in extras |

Caption column: `"TEXT"` → `big` overlay for the whole beat, `|` splits lines;
prefixes `small:`, `badge:` (dark pill, y 1240, size 64), `text:` (plain, y 900).
`cap.y`, `cap.size`, `cap.from=+0.2`, `cap.to=@seg` and any overlay key as `cap.<key>`.

Hit column: `bass`, `whoosh-0.3` (offset from the beat start), `riser:0.74` (dur),
`hit.volume=` and other hit keys via `hit.<key>`. Kinds are whatever `render.py`
knows (sample pack or synth).

Extras: any segment key from `spec-format.md`. Values are JSON when they parse
(`[608,1080,940,0]`, `{"to":1.1}`, `true`), `a,b,c` numbers become a list,
everything else is a string; quote strings with spaces.

`overlays` lines: `<from> <to> key=value…` where a time is seconds, `end`,
`@<seg>` (start of that beat, index or label), `@<seg>.end`, each with `±offset`.
Keys: `big="A|B"`, `small=`, `badge=`, `text=` (plus `y`, `size`, `bg`, `emoji`),
`png=`, `video=`, or raw overlay keys.

`hits` lines: `<at> <kind[:dur]> [key=value…]` or `<at> file=<wav> volume=`.

Output: `spec.vN.json` in the plan's folder (`--out` elsewhere), the timeline,
the overlay list with safe-zone warnings (y_big < 250), hit summary, length
warnings. A version whose render exists is never overwritten: bump `version`.

## spec.py ops

`spec.py <spec> [--fx fx.vN.json] [--ops file|-] [--dry] op… -- op…`. Ops print
`== op` then a diff: `- + ~` segment rows with new times, moved overlays/hits
with old → new, new total. A rendered version is frozen: the first op must be
`bump`. Segment selectors: index or label (a unique part is enough). Overlays:
`ov:<index>` or `ov:"text start"`. Hits: `hit:<index>` or `hit@<at>[:kind]`.

| op | effect |
|---|---|
| `bump [--fx fx.vN.json]` | spec.vN → spec.vN+1 (and fx.vN → fx.vN+1); refuses if the target exists |
| `set <path>=<value> …` | `seg:fan-angle.zoom.to=1.3`, `segments[8].crop=[608,1080,900,0]`, `audio.clip_volume=0.8`, `hit@36.33:riser.at=35.8`, `ov:"TWO SHORT".y_big=450` |
| `unset <path>` | remove a key |
| `shift <seg> <±delta> [--head]` | longer/shorter beat (output seconds; `--head` moves the in-point instead of the out-point); everything after the old end ripples; warns about captions/hits in a trimmed part |
| `slide <seg> <±delta>` | move the source window, length unchanged |
| `drop <seg\|ov:…\|hit…> …` | remove; dropping a beat ripples later times back and drops what sat inside it |
| `insert <after:seg\|before:seg\|start\|end> <beat line>` | new beat in plan grammar; later times ripple forward; its caption/hit come with it |
| `replace <a-b \| "lab1".."lab2" \| a,b,c> with <beat line>` | several beats become one: overlays strictly inside go, one that starts on the range refits to the new beat, hits inside are re-placed by their source time (or dropped with a note), `key=@` copies a value (e.g. `crop=@`) from the first replaced beat |
| `hit add <at> <kind[:dur]\|file=…> [k=v]` / `hit remove <sel>` | audio hits |
| `caption set <ov> [text="A\|B"] [from=] [to=] [k=v]` | edit an overlay in place |

`--fx` keeps a `fx.vN.json` (track.py layers) in step: layer `seg` indices are
renumbered on insert/drop and their `from`/`to`/`values` times ripple.
