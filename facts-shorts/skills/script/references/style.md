# Channel style (facts Shorts, Hinglish)

Channel settings live in `<content root>/channel.json` (promise, length, voice, style, categories);
this file is the writing guide. When the two disagree, channel.json wins.

## Format

- **Promise:** the surprising story behind something viewers see every day. India first, broad topics.
- **Length:** 30–40 s of narration (≈ 85–115 words at pace 1.0), then the 3 s like & subscribe card.
- **Shape:** hook question → twist → payoff. 5–8 lines, one idea per line, and every line must lead
  into the next (a reason, a "but", a consequence). If a line could be removed without the story
  breaking, remove it.
- **Hook (line 1, first 2 s):** a why/how question about something familiar, said like you'd ask a
  friend. It may open with a curious nudge ("Socho...") and the second line may tease ("Iska answer
  bahut interesting hai, kyunki..."). The twist must arrive by about 8 s.
- **Payoff (last line):** short, lands the twist, ideally echoes the hook so the loop back to the
  first frame feels natural ("Aur ahoy? Wo pirates ke paas hi reh gaya.").

## Language

- Hinglish in Roman script: mostly English words, Hindi as glue ("toh", "hi", "matlab", "kyunki",
  "socho", "haan", "par"). Never heavy literal Hindi ("dhwani", "aavishkaar"), never Devanagari.
- Write for the ear: short phrases with natural pause points (commas, "..."). Names and years are
  the anchors viewers remember.
- `text` is the caption (digits are fine: "1877", "10-20 feet"); `tts` is what the voice reads:
  numbers as words ("eighteen seventy-seven", "das-bees feet"), `...` and `<short pause>` before a
  reveal, CAPS on the one surprising word in a line (at most one or two per line).
- Avoid words a viewer could mishear in context: after Alexander Graham Bell, say "ghanti" for a bell.

## Tone

- A friend telling a fun fact: curious, warm, a little playful. Light jokes that come from the story
  itself are good (a pirate wink on "Ahoy").
- Not gimmicky: no fake shock promises ("ye sunke shock ho jaoge", "99% log nahi jaante", "dimaag hil
  jayega"), no invented drama ("he lost an argument"), no clickbait that the video doesn't pay off.
- Not a lecture: no "aaj hum seekhenge", no list of dates, no news-reader voice.

## Facts

- Every claim in the script is verified in `verify.md` (two independent opened sources, or one strong
  primary). Myths can be told as myths ("log kehte hain... par sach ye hai"). Interpretations are said
  as such ("shayad isliye...") or cut.
- Verify from sources, explain in your own words. No stitched quotations. A paraphrase of what someone
  wrote is never in quote marks, on screen or in captions; quote marks only for the exact word someone
  used ("Hello!", "Ahoy!").
- No source citations in the story file: they stay in `verify.md` and in the description.
- Cultural and religious customs: say what people believe and why, never claim the custom works.

## Lessons from Short #1 ("Why do we say hello on the phone?")

- Kept: the hook "Socho... hum phone uthate hi Hello kyun bolte hain?", the tease "Iska answer bahut
  interesting hai", Bell's "Ahoy!" with the pirate joke, Edison's 1877 "Hello" heard 10–20 feet away,
  the hello-girls, and the payoff that ahoy stayed with the pirates.
- Cut as redundant: "What is wanted?" (another greeting that adds nothing), "phone par koi dikhta nahi"
  (an interpretation beat), the 1878 phone-book line (a second proof of the same point).
- Felt wrong: a version with jokes in every line and "he lost an argument" framing (disconnected,
  gimmicky). Preferred: one joke where it fits, each beat causing the next.
- Myth worth knowing: the "Margaret Hello" story (Bell's girlfriend) is false; a debunked myth can
  be a hook, but only if the script then gives the true story.

## Categories (for the 5-Short test)

money/objects · medicine/science · superstitions · words/habits · India history. Spread the test
Shorts across them; `ideas.py coverage` shows what's covered.
