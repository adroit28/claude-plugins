# Prompt grammar for Kling 3.0 Custom multi-shot

One card per shot. Each card: optional scene line (shot 1 only), one camera
instruction, action with one Element chip per character at first mention,
speaker tags, and on the last shot an out point. Plain lowercase names after
the first mention and inside speaker tags.

## Shot 1 template (opening two-shot, silent)

```
<Location>, photorealistic, <light>, <ambient sound>. Two-shot matching the start frame, static camera. @<a> <gesture>, mouth closed. @<b> <gesture>, mouth closed. No speech in this shot.
```

Speech in a shared frame failed on every rerun. Keep the two-shot silent and
put every line in a solo shot.

## Solo shot template

```
Cut to <medium shot|close-up> of @<a>, <static camera|slow push-in>. <One gesture>. [<a>, <voice tag a>, <delivery>]: "<line>"
```

## Delivery words that work

loud and proud, louder, cracking, flat, quiet, deadpan, small smile, shouting
together. One or two per tag. Do not stack four adjectives.

## Camera instructions, pick exactly one per shot

static camera, slow push-in, slow pull-back, handheld sway. Default to static
for dialogue; movement steals attention from the mouth.

## Things to leave out

- Nods, head turns or head tilts inside a spoken line. Head motion fights
  the lip sync. Gesture with hands and shoulders while speaking.
- Any second description of a character's look. The Element carries it.
- Real people's names in the visual description. Element names only.
- "Cinematic", "8k", "masterpiece" and other filler. They cost characters and
  do nothing.
- Subtitles or on-screen text. Add those in the editor.

## Single-box Auto fallback

Same shots, one box, one paragraph. Keep the scene line, then each shot as
"First N seconds: ... Next N seconds: ... Last N seconds: ...". Chips once per
character in the whole box. End with "Only this dialogue, no other speech."
Expect the cut points to move; this is a fallback, not the plan.

## Still prompt for the start frame

When no still exists, hand the user a prompt for their image pipeline that
composes all characters from their reference images in the opening layout:
same height, heads level, same floor line, full bodies with floor margin below
the feet, camera at the characters' eye level, location and light matching
shot 1, "no other text anywhere". Describe characters by their reference
images ("Image 1 is Boy A: keep his exact face...") and never by a real
person's name, since image classifiers block likeness requests.
