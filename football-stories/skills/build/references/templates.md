# Card templates (scripts/cards.py)

Every template renders a full 1080×1920 frame: dark navy gradient, faint pitch lines,
fonts Anton (headlines), Barlow Condensed (labels), with graphics inside x 80–930,
y 250–1180. Captions (Montserrat ExtraBold, drawn by compose.py) sit in the band centred
at y 1330. Nothing goes below y 1470 or right of x 930 (Shorts UI).

Text props: HTML-escaped; `\n` = line break; `**x**` = emphasis (gold by default).
Colour props: a token (`ink muted line gold red green cfc claret sky card`) or any CSS
colour. Emoji render from Apple Color Emoji (flags like 🇰🇿, ⏳, ★).
`steps` in the scene decide how many states render (capped at the template's maximum).

See every template with sample props: `$PY scripts/cards.py --demo /tmp/fs-demo`, then Read
`/tmp/fs-demo/sheet.png`. Sample props: `template-demo.json`.

| Template | Steps | Props | Fits |
|---|---|---|---|
| `calendar_gap` | 3: start card + empty slot → gap label + stamp → end card | `kicker, start{month, year, label, sub, color, title_color}, end{…}, gap_label, stamp` | F6 waits, F9 anniversaries, "X then Y" |
| `name_plate` | 2: name → flag + country | `kicker, first, last, flag, country, country_color`; with `photo`: photo top, name below | who-is-this reveal |
| `rule_card` | 1–2: rule → footer line | `pill, title, big, unit, note, footer{icon, text}` | rules, laws, "the catch" |
| `stat_stack` | items+1: heading → one card per item (≤4) | `heading, items[{stat, unit, title, sub, gold}]` | 3 quick facts, achievements |
| `transfer_path` | 3: milestone → club card → arrow + second card | `top{pill, pill_color, text, tick}, first{kicker, club, line, bg, border, kicker_color, text_color}, arrow, second{…}` | signing → loan, sale, return |
| `headline_card` | 1 | `lines[], flag, name, name_color` | closing line, series tag |
| `stat_compare` | 3: left number → right number → verdict | `kicker, title, left{value, label, color}, right{…}, verdict, sub` | F1 hidden number, F10 then vs now |
| `timeline` | events (≤4), one per step | `kicker, events[{date, title, sub, color}]` | F4 myth vs record, F9, F10 |
| `quote_card` | 2: quote → speaker, date, source | `kicker, quote, speaker, role, date, source` | F11 quote unpacked (quote verbatim from the source) |

Any template accepts `"photo": "<asset key>"` on the scene: a dimmed background image in
the top two thirds (name_plate uses its own photo layout). Photos need a rights class of
own, cc or licensed.

## Adding a template

A function `name(x, p, step)` in cards.py returning `x.page(inner_html, extra_css, bg=x.photo_bg())`,
plus an entry in `TEMPLATES` with its step count, plus a row here and a sample in
`template-demo.json`. Reuse the CSS classes (`box card kicker pill big t1 t2 stat stamp`).
Run `--demo` and check the sheet against the safe-zone rectangles before using it.
