---
name: generate
description: Generate or edit a single image with the paid Gemini image API (gemini-3.1-flash-image) and save it where the user chooses. Use when the user says "generate an image", "make a picture of", "create a photo", "edit this image", "change X in this photo and keep the rest", or wants a character or scene rendered with Gemini. Always asks where to save before generating, every time.
---

# Gemini image

Turn a description (and optionally one or more reference images) into exactly one
JPEG via the Gemini image API, saved to a folder the user picks for that image.

## Paths

| What | Where |
|---|---|
| Generator script | `${CLAUDE_PLUGIN_ROOT}/skills/generate/scripts/gen.py` (stdlib only, `python3`) |
| API key | `$GEMINI_API_KEY`, else file in `$GEMINI_IMAGE_ENV`, else `~/.config/gemini-image/.env` (`GEMINI_API_KEY=...`) |

Never write images, prompts or keys inside the skill directory.

## Rules that do not bend

1. **Ask where to save, every time.** Before each generation — including the second,
   third and tenth in the same session, and edits of an image just made — ask the user
   for the folder and filename with AskUserQuestion. Offer as options: the folder used
   last in this session (if any), the folder of the reference image (for edits), and
   `~/Downloads`; the user can type any other path via "Other". Propose a short
   descriptive filename (e.g. `red-kit-striker.jpg`) and let them change it. Do not
   reuse a previous answer silently, and do not fall back to a default folder.
2. **One image per request.** Each image costs real money (~7 cents at 1K, more at 2K/4K).
   Never fire variants, parallel runs, or a "better" second pass on your own. If the result
   misses the brief, say what is off and offer the change; rerun only when asked.
3. **No silent overwrite.** The script refuses if the file exists. If that happens, ask
   whether to overwrite (`--force`) or pick a new name.
4. **The folder must exist.** If the user names a folder that does not exist, ask before
   creating it.

## Workflow

1. **Pin the brief.** Get subject, style (photoreal / 3D / illustration), aspect ratio
   (default `4:5`; `9:16` for Shorts, `16:9` for thumbnails, `1:1`) and size (default `1K`).
   For edits, find the reference image path(s). Ask only for what is missing.
2. **Write the prompt.** One dense paragraph: subject, look, clothing, pose, setting,
   lighting, camera/lens, style. For edits, say exactly what changes and end with
   "change nothing else".
3. **Ask where to save** (rule 1). Resolve to an absolute path ending in `.jpg`.
4. **Run once:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate/scripts/gen.py" "<prompt>" --out "<abs path>.jpg" \
     [--ratio 4:5] [--size 1K] [--ref ref1.jpg --ref ref2.jpg]
   ```
   Use `--prompt-file file.md --section <heading word>` to reuse a prompt kept as a
   blockquote under a markdown heading.
5. **Show it.** Read the saved file so the user sees it, report the path, size and any
   model note, and state the prompt used so it can be reused. Then wait for feedback.

## Edits vs re-rolls

Re-running a text prompt gives a different person/scene every time. When the user
wants one thing changed and the rest identical, pass the previous image with `--ref`
and describe only the change. Several `--ref` images are numbered in order; refer
to them in the prompt as "image 1", "image 2".

## API facts

- Endpoint `POST /v1beta/interactions`, model `gemini-3.1-flash-image`. Output is JPEG
  only (`image/png` is rejected), so filenames end in `.jpg`.
- `--size` values: `512px`, `1K`, `2K`, `4K` — uppercase K.
- HTTP 400 "blocked for unspecified reasons" is not charged; see below.

## When a request is blocked

- **Real people:** never put a real person's name in the prompt; every model refuses.
  Describe features instead (hair cut, skin tone, eyes, grin, build). Names printed as
  text on clothing can pass; the face description must stay name-free.
- **Too forensic:** blocks also come from over-detailed facial anatomy (hooded or
  deep-set eyes, nostril shape, jaw definition, ethnicity labels, "intense"). Drop two
  or three such details and retry — blocked calls cost nothing, so a retry after a
  block is fine and does not break rule 2.
- **No image, only text:** the script saves the raw reply to `last-response.json` in the
  output folder; read the model's note and adjust the prompt.
- **No key:** tell the user to put `GEMINI_API_KEY=...` in `~/.config/gemini-image/.env`
  (chmod 600), from Google AI Studio. Never ask them to paste the key into chat.
