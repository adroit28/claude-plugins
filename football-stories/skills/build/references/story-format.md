# story.v<N>.json

One file per version in `shorts/<slug>/`. It is the single source of truth: facts,
script, voice, cards, captions, audio and publish text. A subset of the
`football-story/1.0` schema (`shorts/narrative-research/story.example.json`), with the same
field names. Never edit a version that has been rendered (`<slug>_v<N>.mp4` exists);
copy it to `story.v<N+1>.json` and bump `version`.

Working example: `shorts/satpayev-rebuild/story.v1.json` (rebuilds `satpayev-fifa-wait_v2.mp4`).

```jsonc
{
 "schema": "football-story/1.0",
 "id": "2026-09-27-keane-haaland",          // date-slug
 "slug": "keane-haaland",                    // folder name, output = <slug>_v<N>.mp4
 "version": 1,
 "format": "F10-it-happened-before",         // F1–F13, see research/references/formats.md
 "canvas": {"width": 1080, "height": 1920, "fps": 30},
 "length": {"max": 30},                      // optional; 40 only when the user asked for a longer cut (validate.py, check.py)

 "facts": [                                  // research writes these; the user signs them off
  {"id": "f1", "claim": "...", "sources": ["https://...", "https://..."], "confidence": "high", "signed_off": "2026-09-27"}
 ],

 "narration": {
  "style": "Fast, punchy football storyteller ...",   // Gemini delivery prompt; ignored by other engines
  "lines": [
   {"id": "L1", "text": "Caption text, also what align.py matches.",
    "tts": "What the voice gets: CAPS for emphasis, ... or <short pause> for pauses.",   // optional
    "facts": ["f1"]},                                  // required unless "no_claim": true
   {"id": "L9", "text": "Remember the name.", "no_claim": true}
  ],
  // written by tts.py / align.py:
  "voice": {"engine": "gemini", "voice": "en-in-tutor-1", "model": "gemini-3.8-flash-tts", "tier": "free"},
  "pace": 0.93, "take": "build/take_en-in-tutor-1.wav", "audio": "build/narration_en-in-tutor-1_p93.wav",
  "words": "build/words_narration_en-in-tutor-1_p93.json"
 },

 "assets": {                                 // every image / music file with its rights
  "photo_key": {"kind": "image", "path": "assets/x.jpg",
   "rights": {"class": "cc", "license": "CC BY 2.0", "author": "...", "source_url": "https://commons...", "check": "..."}},
  "por_wal": {"kind": "video", "path": "src/porwal.mp4",           // downloaded by fetch.py (logged in src/sources.json)
   "rights": {"class": "doubtful", "origin": "broadcaster", "channel": "...", "source_url": "https://www.youtube.com/watch?v=...",
              "accepted": "2026-09-26"}}                              // date of the user's yes for THIS video
 },
 // rights.class: own | cc | licensed | doubtful | unknown. doubtful/unknown are refused by
 // cards.py and validate.py unless the user explicitly accepts (--allow-doubtful) and the
 // hand-over flags it. Paths must be inside the edit folder (copy files into assets/).

 "scenes": [                                 // in spoken order
  {"id": "s1", "template": "calendar_gap", "props": {...},
   "steps": [{"at": {"line": "L1", "word": 0}}, {"at": {"line": "L1", "word": 9}}],   // step k reveals element k
   "photo": "photo_key"}                     // optional background photo
 ],
 "clips": [                                  // optional real footage, rendered by clips.py after compose.py
  {"id": "c1", "asset": "por_wal", "ss": 298.0,                       // source time the window starts at
   "from": {"line": "L1", "word": 0}, "to": {"line": "L2", "word": 0}, // word anchors (or seconds, or "to": "end")
   "crop": "1130:509:450:150", "box": "top",                          // full 1000x900 at y 250 | top | bottom (1000x450) | [x,y,w,h]
   "slow": 2.0, "pre": "delogo=x=2:y=2:w=560:h=118",                 // optional: half speed; filter before the crop
   "note": "Ronaldo celebrating, crop clear of the score bug"}
 ],
 // Clips are muted and sit inside the graphics zone, above the caption band. Crop clear of
 // broadcaster logos, score bugs and watermarks; use "pre" delogo where a crop would cut the subject.
 // Scenes under footage: one scene across back-to-back clips (a whip between two covered
 // scenes flashes card text around the box; clips.py warns).
 // "word" is the 0-based index into the line's text.split(); negative counts from the end.
 // The first step of the first scene is shown from 0 s. Each step appears `motion.lead` s
 // before its word starts. A new scene = whip + whoosh; a new step = crossfade + punch.

 "captions": {"max_words": 3, "max_chars": 18, "y": 1330, "hide_in_scenes": ["s6"]},
 "motion": {"lead": 0.06, "tail": 0.75, "fade": 4, "whip": 6, "punch": 9, "zoom": 0.035},   // optional
 "audio": {
  "whoosh": "scene_change",                  // or "none"
  "hits": [{"at": {"line": "L1", "word": 9}, "volume": 0.7}],   // 48 Hz bass hit on that word
  "bed": {"asset": "music_key", "volume": 0.12, "fade_out": 1.0},   // optional, licensed/cc/own only
  "loudness": {"I": -14, "TP": -1.5, "LRA": 11}
 },
 "disclosure": {"altered_or_synthetic": false, "ai_voice": true, "description_note": "Narration voice is AI-generated."},
 "publish": {"title": "...", "description": "...", "hashtags": ["#football", "#footballshorts"]}
}
```

## Build outputs (all under the edit folder)

| File | From |
|---|---|
| `build/take_<voice>.wav`, `build/narration_<voice>_p<pace>.wav` | tts.py |
| `build/words_<audio>.json`, `build/align_<audio>.json` (flags) | align.py |
| `graphics/v<N>/<scene>_<step>.png` + `.html`, `graphics/v<N>/sheet.png` | cards.py |
| `build/graphics_v<N>.mp4`, `build/voice_fx_v<N>.wav`, `build/timeline_v<N>.json` | compose.py |
| `build/graphics_v<N>_clips.mp4` (timeline `video` repointed, `clips` added) | clips.py |
| `src/*.mp4`, `src/sources.json` | football-shorts fetch.py (footage, after the user's yes) |
| `handoff.md` (prompt for a fresh session once the script is approved) | research skill |
| `<slug>_v<N>.mp4` | finish.py |
| `build/check_<name>.png`, `build/compare_<new>_vs_<ref>.png` | check.py |
