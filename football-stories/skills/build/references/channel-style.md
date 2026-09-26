# Channel fit for story Shorts (The Football Adda, @footballaddaclub)

If `${CLAUDE_PROJECT_DIR}/yt-insights/style.md` exists, read it: it is the live
rulebook, built from the channel's own analytics, and it wins over this summary.

**Length.** 20–30 s. The channel's Shorts over 40 s never cleared 100 views. If the
narration runs long, cut words from the script; do not speed the voice up (the
user prefers it slightly slower than Gemini's natural read: pace 0.93). When the
user asks for a longer cut (a story with footage, more beats to hold retention), up
to 40 s is fine: set `"length": {"max": 40}` and keep the script to about 90 words
(97 words with pauses read as 38.6 s at pace 1.0). Never over 40 s.

**Hook.** The first line is the constraint or the number, said in the first 1.5 s
over the first card. No title card, no "in this video".

**Pace.** A visual change every 1.5–2.5 s: a reveal step inside a scene or a new
scene. No card static for more than 2.5 s.

**Ending.** A short payoff line on its own card ("Remember the name."), captions
hidden, so it reads as the end and loops back into the hook.

**Titles.** 25–45 characters, player name, one claim + one emotion, CAPS on one
punch word, an emoji pair (💀😂 / 😭❤️ / 🤯😭 / 🇰🇿⚡️), no questions, no
transfer-fee talk. Full player names in the description for search.

**Description.** One or two plain sentences, the sources in short form, and always
the line "Narration voice is AI-generated." when the voice is not the user's own.

**Hashtags.** `#football #footballshorts` always; `#chelsea #cfc` only on Chelsea
stories, otherwise player + club tags. 4–6 total.

**Slots (IST).** Tue/Wed/Thu 17:30–20:00, Sat 18:00. Never 13:00.

**Footage.** Real clips (via `clips`) make a story feel live, but broadcast footage
carries a High Content ID risk that no crop removes: Content ID matches the pictures,
not the logo. Crop broadcaster logos, score bugs and watermarks off anyway, so their
branding isn't on the channel. Clips are muted: the voice tells the story.

**Sound.** Voice + synthesised whooshes and bass hits. No music is baked in by
default; the user adds a low bed at upload (Shorts "Add sound" or the YouTube
Audio Library) or supplies a licensed track as an asset.
