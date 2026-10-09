---
name: build
description: Build stage of a talking-head Short - generate the Remotion project from the plugin's own data-driven template (the edit spec edit.vN.json is the only per-video input: captions, punch-in steps, cutaways, pills, counters, slams, hook, background swap), typecheck, preview a still or a short range, and render at 30 fps with 4 workers to a new raw_vN.mp4. Use after the plan is approved (and the background, if any), when the user says "build it", "render it", "show me a still at 12 s", or invokes /talking-head-shorts:build.
---

# Build and render

The Remotion template (`${CLAUDE_PLUGIN_ROOT}/templates/remotion`) reads `src/edit.json`; `build.py` writes that from the spec. **Never edit TSX per
video.** If a look cannot be expressed in the spec, change the template in the plugin (and bump the plugin version), not the project copy: the
project's `src/*.tsx` is overwritten from the template on every build.

## Steps

1. `$PY -I $S/spec.py validate shorts/<slug>`: no ERRORs; read the warns.
2. Preview before a full render, one still at a moment that stresses the layout (a pill + caption, a cutaway + label, a slam, the hook):
   `$PY -I $S/build.py shorts/<slug> --still <OUTPUT seconds>` (output seconds = hook + source seconds - window start) and look at it.
   A few seconds only: `--frames 0-120`. Fix the spec (ops), not the project.
3. Full render: `$PY -I $S/build.py shorts/<slug> --render` (4 workers, jpeg frames, a few seconds per second of video).
   It creates `anim/` on first use, refreshes the template files, hard-links the source and matte frames into `public/`, copies images,
   fills missing cutaway sizes from the picture, typechecks with tsc, renders to `anim/out/raw_v<N>.mp4`. An existing `raw_v<N>.mp4` is
   never overwritten: bump the spec for a new version.
4. node_modules: `--node-modules <dir>` or `$THS_NODE_MODULES` or `~/.cache/talking-head-shorts/node_modules` (`setup.sh --node` installs it
   once with a LOCAL `.npmrc` -> registry.npmjs.org because `~/.npmrc` points at a dead private registry; a download, needs the user's yes).
   Remotion pinned at 4.0.530. Remotion's static server 404s on symlinked files, which is why build.py hard-links.

## What the template can do (spec keys)

hook (cold / image / slam / none) - person layer with hard punch-in `steps`, slow `drift`, `shakes` - `cutaways` (spring in, push-in, ring, label,
blurred card background) - `pills` groups (counting numbers) - `counters` - `slams` - `flashes` - word-by-word `phrases` with `hot` words - `bg` + `matte`
(background swap with parallax, grade, glow, blink dip) - `fit` cover / crop / blurfill. The mixer and outro run in `finish`.

Report: the stills you checked, the render time, the path of `raw_v<N>.mp4`. `notes.md` State, cost (`cost.py --step build`), fresh-session offer
(finish is small; continue here unless the user prefers otherwise).

Multi-clip slugs: `build.py <slug> --timeline` renders the `Multi` composition from `timeline.json` (T9 in `timeline/SKILL.md`).
