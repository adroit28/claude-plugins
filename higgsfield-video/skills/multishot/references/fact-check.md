# Fact-check procedure

Run this before writing dialogue whenever a line will state something about
the real world: a count, a record, a trophy, a date, a ranking, a quote. The
script may only assert what this procedure verifies.

## Steps

1. Run `date +%F`. Records change; the brief states the date the facts were
   checked.
2. List every factual claim the idea implies, one row each, before searching.
   Include the implied comparisons ("X has more than Y").
3. For each claim, web-search and open at least one primary or
   near-primary source: the governing body (FIFA, UEFA, France Football for
   the Ballon d'Or), the club or league's official site, or a major
   reference with a dated page. A second source is required for any number
   that decides who wins a round.
4. Record the verified value, the source URL and the source date. If sources
   disagree, record both and mark the claim `disputed`.
5. Anything not verified this run is `unverified`. It cannot appear as a fact
   in dialogue. Options: turn it into an opinion the character holds, or cut
   it.
6. Put the table in the brief and repeat the URLs at the bottom of the brief.

## Table shape

| Claim | Character | Verified value | Status | Source | Source date |
|---|---|---|---|---|---|

Status is one of `verified`, `disputed`, `unverified`.

## Writing rules that follow from the table

- Every number spoken on screen matches the table exactly.
- A claim with status `disputed` is spoken with a hedge or dropped.
- Two characters trading claims: each claim gets a direct answer from the
  table in the next beat, so the audience never hears a number without the
  counter-number.
- Do not round for comedy. "Eight" stays eight.
- Superlatives ("most goals ever") need a source that says most, not a large
  number and an assumption.

## Example (checked 2026-09-23)

| Claim | Character | Verified value | Status | Source | Source date |
|---|---|---|---|---|---|
| Ballon d'Or count | messi | 8 | verified | (add URL at run time) | |
| Ballon d'Or count | ronaldo | 5 | verified | (add URL at run time) | |

Do not reuse example rows as facts. Re-verify every run.
