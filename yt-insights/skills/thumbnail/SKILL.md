---
name: thumbnail
description: Suggest thumbnail concepts for a Short and render the chosen one as an exact 9:16 image (1080x1920, or 2160x3840 with --hd) from text alone or over a frame the user supplies as an image or a video plus timestamp. Use when the user says "thumbnail for my short", "make a thumbnail", "cover image", "which frame should I use", "thumbnail ideas", or asks to generate a thumbnail.
---

# Shorts thumbnail

Propose three concepts, render the one the user picks, check it at grid size,
hand back the file. Nothing is uploaded; the user sets it in Studio.

## Inputs

1. `${CLAUDE_PROJECT_DIR}/yt-insights/style.md` — voice and colours. Read it every time.
2. From the user: the clip (topic, culprit or hero, the one moment worth
   freezing), length, and whether they have a frame to use. Ask in one line
   for anything missing. Two forms of frame are accepted:
   - an image file (screenshot or exported frame), or
   - a video file plus a timestamp in seconds (needs `ffmpeg`, or a
     headless-Chrome fallback that may fail on some codecs; if it fails, ask
     for a screenshot).
   With no frame, the script draws the channel's blue-or-red gradient and
   pitch lines; that is fine for reaction and roast clips.
   A **person photo** is a third input, separate from the frame: the user's
   own face for a reaction thumbnail, or a player. Pass it with `--photo` and
   pick a shape: `cutout` (background removed with Apple Vision on macOS, or
   rembg if installed; falls back to `card` and says so), `circle` (round
   frame in the accent colour) or `card` (tilted polaroid). With a photo the
   text moves to the top by default. Cutouts are trimmed to the visible
   pixels and sit on a baseline above the wordmark, so crop the source to
   head-and-shoulders when the face should be big, or leave the torso in
   when it should match a second person. `--photo2` adds a second person:
   both become cutouts, `--photo` on the left and `--photo2` on the right.
   `--photo-filter "grayscale(.55) contrast(1.08) brightness(.92)"` drains
   the colour for a gloomy look (baked into the pixels for cutouts, CSS for
   circle and card). If the photo is a phone screenshot of a video player,
   crop away the app bars first; the black bands otherwise become part of
   the subject. Player photos: ask the user to supply a broadcast screenshot
   or a photo they have rights to; do not fetch press or agency images from
   the web. If a supplied photo shows a club crest, say so in the hand-over:
   the crest is the user's call, the style guide avoids them.
3. Draft metadata in `${CLAUDE_PROJECT_DIR}/yt-insights/drafts/` for the same
   clip, if it exists, so the thumbnail and title do not repeat each other.

## Step 1: three concepts

A short table in chat, one row per concept:

| # | Frame to freeze | Headline (≤2 lines, 1-3 words each) | Sub-line (≤4 words) | Emoji | Style | Why |

Vary the angle: the culprit's face or body language, the moment of impact, a
stat card. Rules:

- Headline says the moment; the title says the take. Never the same words.
- Punch word first and in caps. Two lines maximum, three words per line.
- One emoji pair, the same family as the title.
- Style presets: `roast` (dark red), `hype` (channel blue), `sad` (desaturated
  blue), `neutral` (black). Chelsea-negative clips are `roast`; Chelsea-positive
  and any other club's clip are `hype`.
- No club crests, league logos or broadcaster graphics in the frame; they get
  fan channels flagged. Crop them out with `--focus` or pick another frame.
- Faces sell. If the frame has one, keep it in the top 40% with
  `--focus "50% 15%"` and let the text sit at the bottom.

Mark the concept you would pick and say why in one line.

## Step 2: render

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/thumbnail.py" \
  --project-dir "${CLAUDE_PROJECT_DIR}" --slug <slug> \
  --headline "LINE ONE|LINE TWO" --sub "sub line" --emoji "💀😭" --style roast \
  [--image frame.jpg | --video clip.mp4 --at 12.5] [--focus "50% 20%"] \
  [--photo me.jpg --photo-shape cutout|circle|card --photo-focus "50% 15%"] \
  [--photo2 player.png] [--photo-filter "grayscale(.55) contrast(1.08) brightness(.92)"] [--text-pos top] [--hd]
```

If `${CLAUDE_PLUGIN_ROOT}` is unset, the script is at
`<project>/.claude/skills/yt-insights/scripts/thumbnail.py`.

Output goes to `<project>/yt-insights/thumbnails/<slug>-<date>.png`, with a
`-grid.png` preview at 216x384 (the channel grid tile) and an editable
`.html` source next to it. The script verifies the exact pixel size and the
2 MB cap (it drops to JPEG if a photo frame pushes a PNG over) and prints a
JSON line with `"ok": true`.

Sizes: default 1080x1920 matches the video frame exactly, which is what you
need for the frame-bake workaround below. `--hd` renders 2160x3840, the size
YouTube's help page recommends for Shorts thumbnails; use it when the user can
upload a custom image on desktop.

## Step 3: check the render

Open both the full PNG and the `-grid.png` with the Read tool and confirm:

- Every headline word is readable in the 216 px grid preview. If not, cut
  words before shrinking type.
- No line is clipped or auto-shrunk below the others (the script shrinks any
  line wider than 960 px; uneven sizes mean a line is too long).
- Text sits inside the centre 4:5 area (roughly y 285 to 1635 on a 1080x1920
  canvas). Home, Explore and Subscriptions crop Shorts tiles to 4:5.
- Nothing important in the bottom 260 px; the view count overlays there.
- Emoji rendered as colour glyphs, not boxes.
- With a cutout, the subject's edges are clean (no halo of old background)
  and the face is not covered by text. If the cutout clipped hair or hands,
  switch to `circle`.

Fix and re-render once at most before handing over; further tweaks are the
user's call.

## Step 4: hand over

Give the file path and how to apply it. As of September 2026, custom image
uploads for Shorts live in YouTube Studio on desktop (upload time or after,
under the video's Thumbnail section) and are rolling out account by account,
Partner Program channels first. If the option is missing on desktop, the
mobile app only lets you pick a frame from the video. Workaround: drop the
1080x1920 PNG into the edit as the first one or two frames (under 0.1 s, not
visible to viewers), export, upload from the phone and pick that frame with
the slider. Thumbnails never show in the swipe feed, so this only affects the
channel grid, search, subscriptions and the home shelf.

## Constraints

- This skill does not write to YouTube. If the user wants the image set on the video, hand off to `/yt-insights:publish`.
- Keep the wordmark unless the user asks for `--no-brand`.
- Say when the frame came from the Chrome fallback rather than ffmpeg; the
  seek can land a few frames off.
