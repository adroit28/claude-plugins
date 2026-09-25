# Character registry

Each entry is an Element that exists in the user's Higgsfield workspace. Use
the Element name exactly. Copy the voice tag verbatim into every speaker tag.
Image paths are relative to `~/Documents/ai-learning/`.

When the user introduces a new character, add an entry here in the same
shape before writing shots for it, and remind them to create the Element on
Higgsfield with the same name and description.

## ronaldo

| Field | Value |
|---|---|
| Element | `ronaldo` (Character) |
| Reference image | `ai videos/character sheet/football cartoon/rnd fat 1 tan.jpg` |
| Description | 4-year-old boy, chubby build, warm golden-bronze tan skin, near-black hair in a swept-back quiff, big toothy grin. Plain bright-red short-sleeve football shirt with white text SIUUUU RONALDO on two lines, white shorts, white knee socks, white football boots. |
| Voice tag | `high squeaky boy voice` |
| Personality | loud, proud, boastful, voice cracks when losing |
| Reliable gestures | chest out, hands on hips, flex both arms, thumb to own chest |

## messi

| Field | Value |
|---|---|
| Element | `messi` (Character) |
| Reference image | `ai videos/character sheet/football cartoon/msi lean 1.jpg` (bearded); clean-shaven variant `msi lean 1 no beard.jpg` |
| Description | 4-year-old boy, compact sturdy build, light-medium olive skin, chestnut-brown hair swept back with a side part, short ginger-brown beard and moustache, calm shy closed-lip smile. Plain light sky-blue short-sleeve football shirt with black text ANKARA MESSI on two lines, white shorts, white knee socks, bright pink boots. Black-and-grey floral sleeve tattoo with a pink flower on his right arm. |
| Voice tag | `soft low calm boy voice` |
| Personality | deadpan, few words, one-word answers land the joke |
| Reliable gestures | small shrug, small smile, stands calmly mouth closed (nod only before or after a line, never during) |

## mbappe

| Field | Value |
|---|---|
| Element | `mbappe` (Character) |
| Reference image | `ai videos/character sheet/football cartoon/mbp lean 1.jpg` |
| Description | 4-year-old boy, lean build, medium-brown skin, short dark hair, wide bright smile. Plain blue short-sleeve football shirt with white text TURTLE MBAPPE on two lines, white shorts, white knee socks, orange boots. (Confirm shirt colour and boots against the image before use.) |
| Voice tag | `bright quick boy voice` (unverified in a generation; adjust after first use) |
| Personality | cheerful, fast, celebratory |
| Reliable gestures | arms raised, bouncing, pointing and laughing |

## angry baby (korean)

| Field | Value |
|---|---|
| Element | not yet created on Higgsfield |
| Reference image | `ai videos/character sheet/google cartoon/angry baby - korean clean.jpg` (cleaned); original screenshot kept at `ai videos/character sheet/real images/angry baby - korean.jpeg` |
| Description | Real (non-fictional) toddler, deeply angry/annoyed frown with furrowed eyebrows and downward pursed mouth, short dark hair, light blue sleeveless top. Cleaned via a `--ref` edit on `personal projects/characters/gen.py`: sharpened, background replaced with a plain soft warm-gray backdrop, and only a very faint painterly/photoreal-preserving stylization (deliberately kept subtle after a v1 draft was rejected as too illustrated). |
| Voice tag | not yet chosen |
| Personality | perpetually annoyed/grumpy |
| Reliable gestures | not yet established |

Generated with (v2, the kept version — lighter stylization than v1):

    python3 gen.py "Edit this photo of the baby. Keep the same baby, the same exact face and identity, the same deeply angry/annoyed frown expression with furrowed eyebrows and a downward pursed mouth, the same hairstyle, the same light blue outfit, and the same head pose and framing. Make only these changes: (1) clean up the image quality: sharpen the face and hair, remove blur, noise and JPEG artifacts, improve clarity and lighting, keep it looking like a real photograph; (2) completely replace the cluttered background with a clean, simple, softly out-of-focus plain warm-gray studio backdrop, removing the people and clutter currently behind him; (3) apply only the faintest, most subtle touch of stylization -- barely perceptible, just a hint of smoothness to skin texture -- it should still read as a real photograph at a glance, NOT as a painting or illustration. Prioritize photorealism over stylization; the cartoon effect should be extremely minimal, much lighter than a typical AI portrait filter. Do not make him smile or look happy, do not change his pose, clothing or age, do not add exaggerated proportions or oversized eyes -- he must still look angry." --ref "../../ai videos/character sheet/real images/angry baby - korean.jpeg" --out "angry baby korean clean v2.jpg" --ratio 1:1 --size 2K

## Existing stills

| Still | Path | Layout |
|---|---|---|
| GOAT tunnel two-shot 9:16 | `ai videos/character sheet/stills/goat tunnel two-shot 9x16.jpg` | ronaldo left, messi right, hands on hips, same height, players' tunnel, pitch glow behind |
