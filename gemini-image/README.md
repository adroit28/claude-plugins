# gemini-image

Generates or edits one image per request with the Gemini image API
(`gemini-3.1-flash-image`). Before every generation it asks where to save the image,
and it never overwrites a file without asking.

## Setup

Put your key from Google AI Studio in `~/.config/gemini-image/.env`:

```
GEMINI_API_KEY=...
```

then `chmod 600 ~/.config/gemini-image/.env`. `$GEMINI_API_KEY` or a file named by
`$GEMINI_IMAGE_ENV` also work.

## Use

`/gemini-image:generate a chubby toddler footballer in a blue kit, studio photo`

To edit an existing image, pass it as a reference and say what should change.
The script is `skills/generate/scripts/gen.py` (standard library only).
