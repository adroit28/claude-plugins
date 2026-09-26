# Story cards: gates, score and format

## Gates (a candidate that fails either is dropped, not scored)

1. **Evidence.** The core claim has one primary source (club, league, governing body, the
   official broadcaster's own upload text) or two independent reliable outlets. Two outlets
   repeating the same wire story count as one.
2. **Rights-safe visuals.** The story can be told with our own cards plus own/CC/licensed
   images. Footage is never required.

## Score (0–100, hypothesis from report §04)

| Signal | Weight | How |
|---|---|---|
| Curiosity gap | 20 | 1–5: would a fan say "wait, really?" |
| Evidence strength | 15 | primary = full; two independent = 0.8; one secondary = 0.3 |
| Name recognition for this audience | 15 | Ronaldo, Messi, Yamal, Haaland, Mbappé… plus a Chelsea bonus (see `yt-insights/data/summary.json` top titles if present) |
| Payoff in ≤12 words | 10 | write it; if you can't, score 0 |
| Timeliness | 10 | hours since first report, decaying over 72 h; anniversaries full on the day |
| Momentum | 10 | Reddit rank, views/hour on official uploads |
| Cross-source breadth | 10 | distinct source types (news, Reddit, YouTube, Wikipedia) |
| Visual feasibility | 10 | a template fits; a CC image of the person exists (discover.py --commons) |

Evergreen stories skip timeliness and momentum and renormalise. A controversy raises the bar:
no allegation about a real person beyond what the sources say.

## Card format (shorts/briefs/stories-YYYY-MM-DD.md)

```markdown
# Story cards — YYYY-MM-DD
Research conducted at HH:MM IST / HH:MM UTC. Sources: discover-<date>.json + N searches. Window: ...

## 1. <Short name> · score NN · F6 Hidden Context · Timely|Evergreen|Historical
**Topic** one sentence.
**Hook** "the first line as it would be said"
**Why now** the date or event that makes it timely (or "evergreen").
**Story** 4–6 beats, one line each, in spoken order.
**Facts**
| id | claim | sources | confidence |
|---|---|---|---|
| f1 | ... | [ESPN](url), [club site](url) | high |
**Visuals** templates per beat; CC photo: <Commons URL, licence, rights_guess> or "none".
**Title** 25–45 chars, one CAPS word, emoji pair.
**Length** ~NN s at pace 0.93 (NN words)
**Confidence** high / medium + the weakest fact.
**Not verified** anything you could not confirm (or "nothing").
```

After the cards: a **Rejected** list (one line each, which gate failed) and a **Method and
caveats** section (what was searched, what was blocked, which sources were single-source).
