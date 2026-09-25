# Kling 3.0 on Higgsfield: limits and lessons

Everything here was observed in the Higgsfield web UI on 2026-09-24/25 or paid
for with a wasted generation. Re-verify against the panel if the UI changes;
update this file when it does.

## Where things are

- Video, model Kling 3.0. Left panel: model card, Start frame slot, End frame
  slot (Optional), Multi-shot switch with Auto / Custom, prompt box (Auto) or
  shot cards (Custom), Elements chip, Model, Resolution, Unlimited mode,
  Generate with a credit count.
- There is **no standalone Elements page**. Elements are created and picked
  from the Elements chip under the prompt box or under each shot card. The
  picker lists "My Elements" with `@name` and a type, and has "New Element".
- New Element dialog fields: name, description, Category (Auto, Character,
  Location, Prop), Workspace, Upload media. **No voice field.** Voice Binding
  is a Kling app feature and is not exposed on Higgsfield.

## Hard limits

| Limit | Value | Consequence |
|---|---|---|
| Per-shot duration | 3 s minimum, slider up to the remaining total | No 2 s shots. Five shots means 3 s each, no exceptions. |
| Shots per generation | 5 | Four shots leaves room for one 6 s shot, or 4/3/3/5. |
| Total | 3 to 15 s | Sum of the shot clocks must equal the duration. |
| Per-shot text | roughly 560 stored characters | Text is silently truncated at the end. The payoff line disappears first. |
| Element chip cost | about 50 stored characters each | Chips look like `@ronaldo` but are stored as `@[ronaldo](uuid)`. |
| Resolution | 720p, 1080p, 4K | 4K costs about 3x. Draft at 720p. |

The slider for one shot will not move above 3 s while other cards already use
the whole total. Delete or shorten other cards first, and raise durations in an
order that never exceeds the total mid-edit.

## Character budget rule

Stored length = visible text + 50 x (number of chips). Keep every shot under
560 stored characters, and aim for 450 so a chip added later does not clip it.

- One chip per character per shot, placed at the first mention in the action.
- Plain lowercase names afterwards and inside speaker tags.
- The Elements button also drops chips at the top of the card. Either keep
  those and use plain names in the text, or delete them and keep the inline
  ones. Never both.
- After deleting a chip mid-sentence, check no stray `@` or half chip remains.
- Before generating, scroll to the bottom of every card and confirm the last
  words are the intended last words.

## Elements

- Tag only the characters who appear in that shot. Tagging an absent
  character invites them into the frame.
- Never tag an Element that is not in the script at all.
- Element identity comes from the images on the Element. If a face drifts,
  add a second reference image to the Element rather than adding adjectives
  to the prompt.
- Element description: short and physical, the character's look and shirt
  text. No real names in the body, no voice notes.

## Voice

- Voices are set in the prompt, not on the Element, as `[name, <voice tag>,
  <delivery>]: "line"`.
- The voice tag is copied verbatim from `characters.md` and repeated in every
  shot the character speaks in. Identical wording is the only thing holding
  the voice steady across cuts.
- Within one generation the model keeps a voice across shots. Across two
  generations it does not, so never stitch separate runs.
- Audio: the On toggle is visible only in Auto mode and stays on when you
  switch to Custom. Set it in Auto first.

## Timing and mouths

- Budget 1.5 s per short line, 1 s per gesture or camera move. A 3 s shot
  holds one line and one gesture, or two very short lines and nothing else.
- Three lines in 3 s drops a line. Seen: "Most goals ever!" vanished.
- Shared-frame shots do not lip sync reliably at all. Do not put dialogue in
  them; use them silent for the opener or the closing freeze.
- A shared-frame shot holds at most two spoken beats: one line and one
  reply. Three beats in a two-shot swapped mouths (messi spoke ronaldo's
  line, then each said "Me!" in turn instead of together). Seen 2026-09-25.
- Joint lines ("Me!" together) go in their own 3 s two-shot with no other
  dialogue, then a freeze. Never as the third beat of a shot.
- Use `Immediately,` before a reply to kill the pause.

## Gestures

- Never count on fingers. "Four fingers" came back as five.
- Reliable: hands on hips, chest out, flex both arms, thumb to own chest,
  point at own chest, shrug, turn to camera.
- No head movement while a character speaks. Nods and head turns fight the
  lip sync and produce half-motions (reported across Kling and Seedance
  guides). Put a nod before or after the line, or drop it.
- Freeze on the last frame gives the editor a clean out point.

## Start frame

- Start frame = composition, one still with all the characters placed as the
  first shot needs them. Leave End frame empty.
- Do not add the still as an Element. Elements are single subjects.
- Shot 1 text must match the still ("Two-shot matching the start frame").
- Switching between Auto and Custom can clear the Start frame slot. Check it
  before every Generate.

## Credits

- Auto 15 s at 1080p showed 30 credits. One 3 s Custom shot at 1080p showed 6.
- Test at 720p. Rerun identical settings once at 1080p or 4K only when the
  720p result is one the user would post.
- Unlimited mode: if flipping it on does not change the Generate count, the
  plan does not include it. Leave it off.

## Auto vs Custom

- Auto: Kling picks the cuts. Fine for a single-speaker clip or a cheap 6 s
  comparison. Do not use it for two-character dialogue: a 15 s Auto run with
  explicit "Cut to X alone" beats and a chip per cut still put both boys in
  frame and swapped their lines throughout (2026-09-25).
- Rule that survived every run: **no speech in a shared frame.** Even a
  one-line-plus-reply two-shot failed on rerun (messi spoke ronaldo's line
  tail, and the unspoken reply leaked into messi's next solo shot). Solo
  shots kept their own lines every time.
- Dialogue layout: shot 1 is the start-frame two-shot with "mouth closed" on
  both and "No speech in this shot"; every spoken line is a solo shot with one
  gesture; the clip ends on a solo freeze. Five cards means four lines. Put
  joint beats or extra rounds in the editor or in a part two.
- Custom: pinned cut points and durations, per-shot Elements. Use it for any
  dialogue piece. The main prompt box does not exist in Custom; the scene
  line goes at the top of shot 1.

## Model choice (checked 2026-09-25)

- Kling 3.0 on Higgsfield lacks Kling's Voice Binding and per-character audio
  tracks, so speaker routing in a shared frame is guesswork. Cheapest option
  (about 6 credits per 3 s card at 1080p).
- Seedance 2.0: best audio leaderboard scores and phoneme-level lip sync, but
  ByteDance lists multi-person lip sync as an open problem. Full tier needs
  Plus on Higgsfield. Worth one test only for a shared-frame exchange.
- Veo 3.1: cleanest dialogue, 8 s maximum, roughly 58 credits per clip.
- Sora: discontinued (app April 2026, API 2026-09-24).
- Every model's guidance converges on one speaker per shot. Changing model
  does not remove the shared-frame rule.
- Native lip sync stays loose on Kling 3.0 via Higgsfield even when the
  structure is right (confirmed 2026-09-25 on the silent-opener, solo-shot
  build). Resolution sharpens mouths but does not fix timing. Fixes in order
  of cost: burned-in subtitles; re-sync the finished clip in Lipsync Studio
  with one ElevenLabs voice per character (solo shots make this one face per
  pass); a single Seedance 2.0 test with the same cards.

## Connecting from Claude Code

Higgsfield has no API key. It offers a hosted MCP server
(`https://mcp.higgsfield.ai/mcp`, OAuth with the normal account) and a CLI
with long-lived tokens for non-interactive use. Higgsfield recommends the CLI
for Claude Code. Generations spend normal plan credits. Connecting reportedly
grants a short 100-credit trial. The MCP advertises 30+ tools, so enable it
only when generating.
