# Channel style (facts Shorts, Hinglish)

Channel settings live in `<content root>/channel.json` (promise, length, voice, style, categories);
this file is the writing guide. When the two disagree, channel.json wins.

## Format

- **Promise:** the surprising story behind something viewers see every day. India first, broad topics.
- **Length:** aim 40–45 s of narration (≈ 120–135 words at pace 1.0), hard max 60 s (≈ 175 words), then the 3 s like & subscribe card.
- **Shape:** hook question → twist → payoff. 5–8 lines, one idea per line, and every line must lead
  into the next (a reason, a "but", a consequence). If a line could be removed without the story
  breaking, remove it.
- **Hook (line 1, first 2 s)** (myth-buster topics: see Myth-buster mode below): a why/how question about something familiar, said like you'd ask a
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

## Myth-buster mode ("you're doing it wrong")

Use when the topic is a habit or belief many viewers practise and it is wrong or harmful (earbuds after a
bath, brushing right after eating, cracking knuckles). Ask the user if the topic is borderline. The viewer
should feel "main ye galti kar raha hoon" and stay to the last word to learn the fix. Same length, same
facts rules; only the shape changes.

Shape: accusation hook -> why it feels right -> twist -> stakes -> (1-2 short context lines or none) -> bridge
that opens the fix -> fix -> payoff that sends the viewer's hand back to the habit.

- **Hook (first 2 s):** tells the viewer they are doing it now ("Ruko. Nahaane ke baad kaan mein earbud
  daalte ho? Ye ek badi galti hai."). Not a neutral why-question. Must be paid off by the twist inside ~8 s.
- **Why it feels right:** one line naming the sensation or belief that keeps people doing it. Without it
  the viewer thinks "main toh nahi karta" and swipes.
- **Stakes:** one beat that reframes the thing they think is harmless or helpful (e.g. the wax is a
  protector, removing it is the harm). A short analogy is fine ("kaan ka bodyguard"); the claim under it
  must be VERIFIED.
- **Open loop:** tease the fix before the middle ("iska jawab itna simple hai ki hans padoge") and pay it
  off only in the last two beats. History/market/context beats get 1-2 lines or go, whichever keeps the
  loop tight.
- **Fix:** free, easy, specific, and VERIFIED. A myth-buster with no fix is just scary; find the fix or
  pick another topic.
- **Payoff:** short, lands the fix, sends the hand back to the habit ("agli baar haath earbud ki taraf
  jaaye... ye video yaad kar lena").
- **Drama comes from structure, not claims.** Allowed: accusation, "ruko", contrast, short sentences,
  pauses before the reveal, one CAPS word, an analogy. Not allowed: attributing to "doctors"/"studies"
  unless verify.md has that wording, invented danger or numbers, "99% log", "shock ho jaoge", anything the
  video does not pay off. Do not claim harm beyond what verify.md says ("kaan ke parde ke kareeb" stays
  as worded; no "behre ho jaoge" unless verified).
- Health topics: end with the safe version of the fix, and keep "agar dard ya blockage ho toh doctor ko
  dikhao" if verify.md supports it; never replace medical advice.

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
