# Where stories come from (no logins, no blocks)

Tested 26 Sep 2026 (report §04 and discover.py). Re-test a source before relying on it.

## Leads

| Source | Access | Use for | Via |
|---|---|---|---|
| BBC Sport, Sky Sports, ESPN football RSS | 200, no key | what happened, fast. Headlines and links only; never read their text aloud | discover.py |
| Reddit r/soccer top-of-day RSS | 200 (the .json endpoint is 403) | what fans argue about; rank stands in for score | discover.py |
| Wikipedia on-this-day REST API | 200 | anniversaries; the featured list is thin on football, so also search | discover.py |
| WebSearch with real dates | — | "on this day 27 September football", "first since", "youngest ever", "record" + this week's dates | WebSearch |
| Club and league sites, governing bodies (FIFA/UEFA/FA documents) | usually open | primary sources for facts and rules | WebFetch |
| Wikimedia Commons API | 200 | CC photos with licence, author, credit | discover.py --commons |
| YouTube view velocity | yt-dlp, no key | whether a story is already moving (optional; do not download) | `yt-dlp -j --no-playlist <url>` |

Avoid: FBref (Cloudflare 403), Understat / FotMob / Sofascore (terms forbid automated access),
X API (paid), NewsAPI free tier (dev only), pytrends (archived), Google News RSS for anything
beyond "is everyone covering this" (personal, non-commercial).

## Verifying a fact

1. Find the claim in the most primary source available and open it (WebFetch). Record the URL
   and the exact figure or date as the page states it.
2. Find a second, independent source. If the only second source quotes the first, say
   "single-source" and lower confidence.
3. Restate facts in your own words. Stats are not copyrightable; wording is. Credit the source
   in the description.
4. Quotes (F11) are copied verbatim from the source page, with the date and setting.
5. Dates and ages: compute them (e.g. "18 months" = Feb 2025 → Aug 2026) and say so in the fact.
   Day names too: `date -j -f %Y-%m-%d 2026-09-24 +%A`. Articles say "on Wednesday" relative to
   their own publish date, so a copied day name can be wrong by a day.
6. Current-world checks: managers, clubs and loans change. Verify today's state instead of
   assuming (the 2026 map differs from older knowledge: Mourinho at Real Madrid, Alonso at
   Chelsea, Salah at Trabzonspor, Maresca at City, as of Sep 2026).
7. Anything not confirmed goes in "Not verified", never into a narration line.

## Photos

`discover.py --commons "<name>"` → rights_guess per file. `cc` with CC BY / BY-SA: credit the
author as the licence requires. `doubtful`: uploader is not the author, or CC0 with no own-work
credit (the Satpayev selfie case): leave it out unless the user decides otherwise. NC/ND
licences are not usable on a monetised channel. Getty/AP/Reuters and broadcast frames need a
licence: never.
