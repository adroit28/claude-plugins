"""Render data/summary.json + a notes markdown file into a self-contained HTML report.
Usage: report.py --project-dir <dir> --notes <notes.md>
Writes <project>/yt-insights/reports/<channel-slug>-<date>.html and prints the path."""
import argparse, html, json, os, re
from datetime import date
from pathlib import Path

W, H, PAD = 720, 200, {"l": 44, "r": 12, "t": 14, "b": 26}


def esc(s): return html.escape(str(s), quote=True)
def fmt(n):
    if isinstance(n, float) and n.is_integer(): n = int(n)
    return f"{int(n):,}" if abs(n) >= 1000 else f"{n:g}" if isinstance(n, float) else str(n)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def md(text):
    """Tiny markdown: ## headers, paragraphs, - bullets, **bold**, `code`."""
    out, buf, mode = [], [], None
    def flush():
        nonlocal buf, mode
        if not buf: return
        if mode == "ul": out.append("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in buf) + "</ul>")
        else: out.append(f"<p>{inline(' '.join(buf))}</p>")
        buf, mode = [], None
    def inline(s):
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    for line in text.splitlines():
        if line.startswith("## "): flush(); out.append(f"<h3>{inline(line[3:])}</h3>")
        elif line.startswith("# "): flush(); out.append(f"<h2>{inline(line[2:])}</h2>")
        elif line.startswith("- "):
            if mode != "ul": flush(); mode = "ul"
            buf.append(line[2:])
        elif not line.strip(): flush()
        else:
            if mode == "ul": flush()
            mode = "p"; buf.append(line)
    flush()
    return "\n".join(out)


def line_chart(daily):
    n = len(daily)
    if n < 2: return "<p class='muted'>Not enough daily data.</p>"
    xs = [PAD["l"] + i * (W - PAD["l"] - PAD["r"]) / (n - 1) for i in range(n)]
    mx = max(d["views"] for d in daily) or 1
    import math
    raw = mx / 4; mag = 10 ** math.floor(math.log10(raw)); step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    top = math.ceil(mx / step) * step
    y = lambda v: PAD["t"] + (H - PAD["t"] - PAD["b"]) * (1 - v / top)
    pts = " ".join(f"{x:.1f},{y(d['views']):.1f}" for x, d in zip(xs, daily))
    area = f"M{xs[0]:.1f},{y(0):.1f} L" + pts.replace(" ", " L") + f" L{xs[-1]:.1f},{y(0):.1f} Z"
    grid = "".join(f"<line class='grid' x1='{PAD['l']}' x2='{W-PAD['r']}' y1='{y(v):.1f}' y2='{y(v):.1f}'/><text class='tick' x='{PAD['l']-6}' y='{y(v)+4:.1f}' text-anchor='end'>{fmt(v)}</text>" for v in [i * step for i in range(int(top / step) + 1)])
    months, seen = [], set()
    for x, d in zip(xs, daily):
        key = d["day"][:7]
        if key not in seen: seen.add(key); months.append(f"<text class='tick' x='{x:.1f}' y='{H-8}'>{date.fromisoformat(d['day']).strftime('%b %-d')}</text>")
    peak = max(range(n), key=lambda i: daily[i]["views"])
    hit = "".join(f"<rect class='hit' data-i='{i}' x='{x - (xs[1]-xs[0])/2:.1f}' y='0' width='{xs[1]-xs[0]:.1f}' height='{H}'/>" for i, x in enumerate(xs))
    data = json.dumps([{"d": d["day"], "v": d["views"], "s": d["subs"], "x": round(x, 1), "y": round(y(d["views"]), 1)} for x, d in zip(xs, daily)])
    return f"""<figure class="chart" data-series='{esc(data)}'>
<svg viewBox="0 0 {W} {H}" role="img" aria-label="Daily views">
{grid}{''.join(months)}
<path class="area" d="{area}"/><polyline class="line" points="{pts}"/>
<circle class="dot end" cx="{xs[-1]:.1f}" cy="{y(daily[-1]['views']):.1f}" r="4"/>
<circle class="dot peak" cx="{xs[peak]:.1f}" cy="{y(daily[peak]['views']):.1f}" r="4"/>
<text class="label" x="{xs[peak]:.1f}" y="{y(daily[peak]['views'])-9:.1f}" text-anchor="{'end' if peak > n*0.8 else 'middle'}">{fmt(daily[peak]['views'])} on {date.fromisoformat(daily[peak]['day']).strftime('%b %-d')}</text>
<line class="cross" x1="0" x2="0" y1="{PAD['t']}" y2="{H-PAD['b']}" opacity="0"/>
<circle class="dot hover" r="5" opacity="0"/>
{hit}
</svg><div class="tip" hidden></div></figure>"""


def hbars(rows, label_key, val_key, total=None, cap=8, unit="", sub_key=None):
    rows = [r for r in rows if r.get(val_key)][:cap]
    if not rows: return "<p class='muted'>No data.</p>"
    mx = max(r[val_key] for r in rows)
    total = total or sum(r[val_key] for r in rows)
    out = []
    for r in rows:
        v = r[val_key]; pct = 100 * v / total if total else 0
        sub = f"<small>{esc(r[sub_key])}</small>" if sub_key and r.get(sub_key) else ''
        out.append(f"<div class='hb'><span class='hb-l' title='{esc(r[label_key])}'>{esc(r[label_key])}{sub}</span><span class='hb-t'><i style='width:{100*v/mx:.1f}%'></i></span><span class='hb-v'>{fmt(v)}{unit}<small>{pct:.0f}%</small></span></div>")
    return "<div class='hbars'>" + "".join(out) + "</div>"


TRAFFIC = {"SHORTS": "Shorts feed", "YT_SEARCH": "YouTube search", "YT_CHANNEL": "Channel page", "YT_OTHER_PAGE": "Other YouTube pages", "SUBSCRIBER": "Subscriptions feed",
           "HASHTAGS": "Hashtag pages", "EXT_URL": "External links", "PLAYLIST": "Playlists", "SHORTS_CONTENT_LINKS": "Shorts links", "NOTIFICATION": "Notifications",
           "SOUND_PAGE": "Sound page", "RELATED_VIDEO": "Suggested videos", "NO_LINK_OTHER": "Direct / unknown", "END_SCREEN": "End screens", "ADVERTISING": "Ads"}
DEV = {"MOBILE": "Phone", "TV": "TV", "TABLET": "Tablet", "DESKTOP": "Desktop", "GAME_CONSOLE": "Console"}


def retention_chart(rc):
    top, bot = rc.get("top", []), rc.get("bottom", [])
    if not top: return "<p class='muted'>No retention curves yet. They appear once a video has enough views.</p>"
    RW, RH, L, R, T, B = 720, 220, 40, 12, 12, 28
    mx = max(max(y for _, y in c["pts"]) for c in top + bot); mx = max(1.0, mx)
    import math
    ytop = max(1.0, math.ceil(mx / 0.25) * 0.25)
    X = lambda r: L + r * (RW - L - R); Y = lambda v: T + (RH - T - B) * (1 - v / ytop)
    grid = "".join(f"<line class='grid' x1='{L}' x2='{RW-R}' y1='{Y(v):.1f}' y2='{Y(v):.1f}'/><text class='tick' x='{L-6}' y='{Y(v)+4:.1f}' text-anchor='end'>{int(v*100)}%</text>" for v in [i * 0.25 for i in range(int(round(ytop / 0.25)) + 1)])
    xt = "".join(f"<text class='tick' x='{X(r):.1f}' y='{RH-8}' text-anchor='middle'>{int(r*100)}%</text>" for r in (0, .25, .5, .75, 1.0))
    def path(c, cls):
        d = " ".join(f"{X(x):.1f},{Y(min(y, ytop)):.1f}" for x, y in c["pts"])
        t = esc(re.sub(r"\s*#\w+", "", c["title"]).strip()[:60]) + f" · {c['secs']}s · {fmt(c['views'])} views"
        return f"<polyline class='rline {cls}' points='{d}'><title>{t}</title></polyline>"
    lines = "".join(path(c, "bot") for c in bot) + "".join(path(c, "top") for c in top)
    loop = f"<line class='grid loop' x1='{L}' x2='{RW-R}' y1='{Y(1):.1f}' y2='{Y(1):.1f}'/>"
    legend = "<div class='legend'><span><i class='sw top'></i>Top 5 by views</span><span><i class='sw bot'></i>Bottom 5 with enough data</span><span class='muted'>Above 100% = viewers looping. Hover a line for the title.</span></div>"
    return f"<figure class='chart'><svg viewBox='0 0 {RW} {RH}' role='img' aria-label='Audience retention, top vs bottom videos'>{grid}{loop}{xt}<text class='tick' x='{(L+RW-R)/2:.0f}' y='{RH+2}' text-anchor='middle'></text>{lines}</svg></figure>{legend}"


def experiments_html(exps):
    if not exps: return ""
    cards = []
    for e in exps:
        res = e.get("result") or {}; verdict = res.get("verdict", "")
        cls = "signal" if verdict == "signal" else "noise" if verdict == "noise" else "wait"
        rows = "".join(f"<tr><td>{esc(r['label'])}</td>" + (f"<td class='num'>{fmt(r['views'])}</td><td class='num'>{fmt(r['views_per_day'])}</td><td class='num'>{r['retention']:.0f}%</td><td class='num'>{r['secs']}s</td><td class='num'>{r['days_live']}d</td>" if r.get("live") else "<td colspan='5' class='muted'>not live yet</td>") + "</tr>" for r in e.get("scored", []))
        tail = f" · {esc(res['best'])} over {esc(res['worst'])} by {res['ratio']}×" if "ratio" in res else ""
        cards.append(f"""<div class='exp'><div class='exp-h'><span class='pill {cls}'>{esc(verdict)}</span><strong>{esc(e['name'])}</strong><span class='muted small'>{e['id']} · registered {esc(e['created'])}{' · read after ' + esc(e['read_after']) if e.get('read_after') else ''}</span></div>
<p class='muted' style='margin:4px 0 10px'>{esc(e['question'])}{esc(tail)}</p>
<div class='tablewrap'><table><thead><tr><th>Arm</th><th class='num'>Views</th><th class='num'>Views/day</th><th class='num'>Retention</th><th class='num'>Length</th><th class='num'>Live</th></tr></thead><tbody>{rows}</tbody></table></div></div>""")
    return "<h2>Experiments</h2><p class='muted small'>Paired uploads compared on views per day live. A gap under the rule ratio is reported as noise.</p>" + "".join(cards)


def video_table(videos, median):
    mx = max(v["views"] for v in videos) or 1
    has_hook = any(v.get("hook3s") is not None for v in videos)
    has_studio = any(v.get("studio") for v in videos)
    rows = []
    for i, v in enumerate(videos, 1):
        ret = v["avp"]; cls = "loop" if ret >= 100 else "hi" if ret >= 80 else "lo" if ret < 50 else ""
        hook = (f"<td class='num'>{v['hook3s']:.0f}%</td>" if v.get("hook3s") is not None else "<td class='num muted'>–</td>") if has_hook else ""
        st = v.get("studio") or {}
        studio = (f"<td class='num'>{fmt(st['impressions']) if 'impressions' in st else '–'}</td><td class='num'>{str(st['ctr']) + '%' if 'ctr' in st else (str(st['stayed_pct']) + '%' if 'stayed_pct' in st else '–')}</td>") if has_studio else ""
        rows.append(f"""<tr>
<td class="n">{i}</td>
<td class="t"><a href="https://www.youtube.com/shorts/{v['id']}" target="_blank" rel="noopener">{esc(re.sub(r'\s*#\w+', '', v['title']).strip())}</a><small>{date.fromisoformat(v['publishedAt'][:10]).strftime('%-d %b')} · {v['ist_weekday']} {v['ist_hour']:02d}:00 IST · {v['secs']}s</small></td>
<td class="v"><span class="bar"><i style="width:{100*v['views']/mx:.1f}%"></i></span>{fmt(v['views'])}</td>
<td class="r {cls}">{ret:.0f}%</td>{hook}
<td class="num">{v['eng']:.1f}%</td>{studio}
<td class="num">{v['subs']:+d}</td></tr>""")
    return f"""<div class="tablewrap"><table>
<thead><tr><th>#</th><th>Video</th><th>Views</th><th title="Average view percentage; above 100% means viewers looped it">Retention</th>{'<th class="num" title="Share of viewers still watching 3 seconds in">Hook 3s</th>' if has_hook else ''}<th title="(likes + comments + shares) / views">Eng.</th>{'<th class="num">Impr.</th><th class="num" title="Click-through rate, or viewed-vs-swiped for Shorts">CTR / Stayed</th>' if has_studio else ''}<th>Subs</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="muted small">Median video: {fmt(median)} views. Retention above 100% means the Short looped.</p>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--notes", required=True)
    a = ap.parse_args()
    root = Path(a.project_dir) / "yt-insights"
    S = json.load(open(root / "data" / "summary.json"))
    notes = Path(a.notes).read_text()
    c, w = S["channel"], S["window"]
    span = f"{date.fromisoformat(w['start']).strftime('%-d %b')} – {date.fromisoformat(w['end']).strftime('%-d %b %Y')}"
    kpis = [("Views", w["views"], f"{w['days']}-day window"), ("Watch time", round(w["watch_minutes"] / 60), "hours"),
            ("Net subscribers", w["subs_net"], f"{c['subscribers']} total"), ("Likes", w["likes"], f"{w['comments']} comments · {w['shares']} shares"),
            ("Median video", S["median_views"], "lifetime views"), ("Retention", S["mean_avp"], "mean, all videos")]
    kpi_html = "".join(f"<div class='kpi'><span class='k-l'>{esc(l)}</span><span class='k-v'>{fmt(v) if l != 'Retention' else f'{v:g}%'}</span><span class='k-s'>{esc(s)}</span></div>" for l, v, s in kpis)
    traffic = [{"l": TRAFFIC.get(t["insightTrafficSourceType"], t["insightTrafficSourceType"]), "v": t["views"]} for t in S["traffic"]]
    countries = [{"l": t["country"], "v": t["views"]} for t in S["countries"]]
    devices = [{"l": DEV.get(t["deviceType"], t["deviceType"]), "v": t["views"]} for t in sorted(S["devices"], key=lambda d: -d["views"])]
    wd_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekdays = [{"l": d, "n": f"n={S['by_weekday'][d]['n']}", "v": S["by_weekday"][d]["median_views"]} for d in wd_order if d in S["by_weekday"]]
    demo = sorted(S["demographics"], key=lambda d: -d["viewerPercentage"])[:6]
    demo_rows = [{"l": f"{d['ageGroup'].replace('age', '')} {'M' if d['gender']=='male' else 'F' if d['gender']=='female' else '–'}", "v": d["viewerPercentage"]} for d in demo]
    sub_share = next((t["views"] for t in S["subscribedStatus"] if t["subscribedStatus"] == "UNSUBSCRIBED"), 0) / max(w["views"], 1) * 100
    tp = S["title_patterns"]
    pat_rows = "".join(f"<tr><td>{k}</td><td class='num'>{tp['top_quartile'][j]}</td><td class='num'>{tp['bottom_quartile'][j]}</td></tr>" for k, j in
                       [("Median views", "median_views"), ("Length (s)", "avg_secs"), ("Retention %", "avg_avp")] + ([("Still watching at 3s %", "avg_hook3s")] if tp["top_quartile"].get("avg_hook3s") is not None else []) + [ ("Title length (chars)", "avg_title_len"), ("Emoji per title", "avg_emoji"), ("Titles with a question", "pct_with_question")])

    page = f"""<title>{esc(c['title'])} Channel Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">
<style>
:root{{--series-2:#c9561f;--bg:#f3f5f9;--surface:#ffffff;--ink:#0f1a2e;--ink-2:#4b5970;--ink-3:#7e8aa0;--line:#d9dfea;--accent:#034694;--accent-ink:#034694;--accent-soft:#e2ebf8;--area:rgba(3,70,148,.12);--good:#1b7a48;--warn:#a8620c;--bad:#b3261e;--hi:#e6f2ea;--lo:#fbe9e7;--loop:#e2ebf8}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--series-2:#e8804a;--bg:#0b111d;--surface:#121a2b;--ink:#e8edf6;--ink-2:#a9b4c9;--ink-3:#71809b;--line:#243049;--accent:#5d9df2;--accent-ink:#8ebbf7;--accent-soft:#18294a;--area:rgba(93,157,242,.16);--good:#5cc98a;--warn:#e3a34b;--bad:#f0776d;--hi:#173425;--lo:#3a1e1b;--loop:#18294a}}}}
:root[data-theme="dark"]{{--series-2:#e8804a;--bg:#0b111d;--surface:#121a2b;--ink:#e8edf6;--ink-2:#a9b4c9;--ink-3:#71809b;--line:#243049;--accent:#5d9df2;--accent-ink:#8ebbf7;--accent-soft:#18294a;--area:rgba(93,157,242,.16);--good:#5cc98a;--warn:#e3a34b;--bad:#f0776d;--hi:#173425;--lo:#3a1e1b;--loop:#18294a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "Source Sans 3",system-ui,-apple-system,Segoe UI,sans-serif;padding-block:0 48px;padding-inline:clamp(16px,4vw,40px);font-variant-numeric:tabular-nums}}
a{{color:var(--accent-ink)}}
.wrap{{max-width:1080px;margin:0 auto}}
header{{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:8px 24px;padding-block:32px 20px;border-bottom:3px solid var(--accent)}}
h1{{font:700 clamp(36px,6vw,56px)/.95 "Barlow Condensed",Impact,sans-serif;text-transform:uppercase;letter-spacing:.01em;margin:0;text-wrap:balance}}
.eyebrow{{font:600 13px/1 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.14em;color:var(--accent-ink);display:block;margin-bottom:8px}}
.meta{{color:var(--ink-2);font-size:15px;text-align:right}}
.meta b{{color:var(--ink);font-weight:600}}
h2{{font:600 26px/1.1 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.03em;margin:40px 0 14px}}
h3{{font:600 20px/1.2 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.03em;margin:22px 0 8px}}
.kpis{{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin-top:24px}}
.kpi{{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:2px;min-width:0}}
.k-l{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3)}}
.k-v{{font:600 34px/1 "Barlow Condensed",sans-serif;color:var(--ink)}}
.k-s{{font-size:13px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:24px 32px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px 32px}}
.panel h3{{margin-top:0}}
.chart{{margin:0;position:relative}}
.chart svg{{width:100%;height:auto;display:block;overflow:visible}}
.grid{{stroke:var(--line);stroke-width:1}}
.tick{{fill:var(--ink-3);font-size:11px;font-family:"Source Sans 3",sans-serif}}
.area{{fill:var(--area)}}
.line{{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round}}
.dot{{fill:var(--accent);stroke:var(--surface);stroke-width:2}}
.dot.peak{{fill:var(--surface);stroke:var(--accent)}}
.label{{fill:var(--ink-2);font-size:11.5px;font-weight:600}}
.cross{{stroke:var(--ink-3);stroke-dasharray:3 3}}
.hit{{fill:transparent;cursor:crosshair}}
.tip{{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);padding:6px 9px;font-size:13px;line-height:1.35;border-radius:3px;transform:translate(-50%,-100%);white-space:nowrap}}
.tip b{{font-weight:600}}
.hbars{{display:grid;grid-template-columns:minmax(90px,auto) 1fr auto;gap:6px 10px;align-items:center;font-size:14.5px}}
.hb{{display:contents}}
.hb-l{{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.hb-l small{{color:var(--ink-3);font-size:12px;margin-left:4px}}
.hb-t{{height:14px;background:var(--accent-soft);position:relative}}
.hb-t i{{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:0 3px 3px 0}}
.hb-v{{text-align:right;white-space:nowrap}}
.hb-v small{{color:var(--ink-3);margin-left:6px;font-size:12px;display:inline-block;min-width:30px;text-align:right}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-size:14.5px}}
th{{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
td.n{{color:var(--ink-3);width:28px}}
td.t a{{color:var(--ink);text-decoration:none;font-weight:600;display:block;max-width:420px}}
td.t a:hover{{color:var(--accent-ink);text-decoration:underline}}
td.t small{{display:block;color:var(--ink-3);font-size:12.5px;margin-top:2px}}
td.v{{white-space:nowrap;min-width:160px}}
.bar{{display:inline-block;width:88px;height:10px;background:var(--accent-soft);vertical-align:middle;margin-right:8px;position:relative}}
.bar i{{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:0 2px 2px 0}}
td.r{{white-space:nowrap;text-align:right}}
td.r.loop{{background:var(--loop);color:var(--accent-ink);font-weight:600}}
td.r.hi{{background:var(--hi);color:var(--good)}}
td.r.lo{{background:var(--lo);color:var(--bad)}}
td.num,th.num{{text-align:right;white-space:nowrap}}
.compare td:first-child{{color:var(--ink-2)}}
.compare th:not(:first-child){{text-align:right}}
.notes{{max-width:68ch}}
.notes p,.notes li{{color:var(--ink);font-size:16.5px}}
.notes ul{{padding-left:20px;margin:6px 0 14px}}
.notes li{{margin:4px 0}}
.notes code{{font:14px ui-monospace,Menlo,monospace;background:var(--accent-soft);padding:1px 5px;border-radius:2px}}
.muted{{color:var(--ink-3)}}.small{{font-size:13px}}
.rline{{fill:none;stroke-width:2;stroke-linejoin:round}}
.rline.top{{stroke:var(--accent);opacity:.85}}
.rline.bot{{stroke:var(--series-2);stroke-dasharray:5 4;opacity:.8}}
.rline:hover{{stroke-width:3.5;opacity:1}}
.grid.loop{{stroke:var(--ink-3);stroke-dasharray:2 4}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:13.5px;color:var(--ink-2);margin-top:8px;align-items:center}}
.legend .sw{{display:inline-block;width:18px;height:0;border-top:2px solid var(--accent);vertical-align:middle;margin-right:6px}}
.legend .sw.bot{{border-top:2px dashed var(--series-2)}}
.exp{{background:var(--surface);border:1px solid var(--line);padding:14px 16px;margin-bottom:14px}}
.exp-h{{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center}}
.pill{{font:600 11px/1 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.1em;padding:5px 8px;border-radius:2px;color:#fff;background:var(--ink-3)}}
.pill.signal{{background:var(--good)}}.pill.noise{{background:var(--warn)}}
.callout{{border-left:3px solid var(--accent);padding:10px 16px;background:var(--surface);margin:16px 0;font-size:15px;color:var(--ink-2)}}
footer{{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);color:var(--ink-3);font-size:13px;display:flex;flex-wrap:wrap;gap:6px 24px}}
:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
@media (max-width:900px){{.kpis{{grid-template-columns:repeat(3,1fr)}}.grid3{{grid-template-columns:1fr 1fr}}}}
@media (max-width:620px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.grid2,.grid3{{grid-template-columns:1fr}}.meta{{text-align:left}}}}
@media (prefers-reduced-motion:no-preference){{.hb-t i,.bar i{{transition:width .4s ease}}}}
</style>
<div class="wrap">
<header>
<div><span class="eyebrow">Channel report · {esc(span)}</span><h1>{esc(c['title'])}</h1></div>
<div class="meta"><b>{fmt(c['lifetime_views'])}</b> lifetime views · <b>{c['subscribers']}</b> subscribers · <b>{c['public_videos']}</b> public videos<br>Uploading since {date.fromisoformat(c['first_upload']).strftime('%-d %b %Y')} · last upload {c['days_since_last_upload']} days ago</div>
</header>

<div class="kpis">{kpi_html}</div>

<h2>Daily views</h2>
{line_chart(S['daily'])}
<p class="muted small">Hover for the day's views and net subscribers. YouTube analytics lag about 48 hours, so the window ends on {date.fromisoformat(w['end']).strftime('%-d %b')}.</p>

<h2>Every video, ranked</h2>
{video_table(S['all_videos'], S['median_views'])}

<h2>Where viewers leave</h2>
{retention_chart(S.get('retention_curves', {}))}

<h2>Where views come from</h2>
<div class="grid3">
<div class="panel"><h3>Traffic source</h3>{hbars(traffic, 'l', 'v', total=w['views'])}</div>
<div class="panel"><h3>Country</h3>{hbars(countries, 'l', 'v', total=w['views'])}</div>
<div class="panel"><h3>Device</h3>{hbars(devices, 'l', 'v', total=w['views'])}
<p class="muted small" style="margin-top:14px">{sub_share:.1f}% of views came from people not subscribed.</p></div>
</div>

<div class="grid3" style="margin-top:28px">
<div class="panel"><h3>Search terms that found you</h3><ol class="small" style="margin:0;padding-left:20px;color:var(--ink-2);columns:1">{''.join(f"<li>{esc(t['insightTrafficSourceDetail'])} <span class='muted'>· {t['views']}</span></li>" for t in S['search_terms'][:12])}</ol></div>
<div class="panel"><h3>Audience</h3>{hbars(demo_rows, 'l', 'v', total=100, unit='%')}</div>
<div class="panel"><h3>Median views by upload day</h3>{hbars(weekdays, 'l', 'v', total=None, sub_key='n')}<p class="muted small" style="margin-top:14px">Posting times in IST. Small counts per day, so treat as a hint, not a rule.</p></div>
</div>

<h2>What separates the top quarter from the bottom</h2>
<div class="grid2">
<div class="tablewrap"><table class="compare"><thead><tr><th></th><th>Top 25%</th><th>Bottom 25%</th></tr></thead><tbody>{pat_rows}</tbody></table></div>
<div class="callout">Top hashtags across all uploads: {', '.join(f"{h} <span class='muted'>({n})</span>" for h, n in S['hashtags'][:8])}.</div>
</div>

{experiments_html(S.get('experiments'))}

<div class="notes">
{md(notes)}
</div>

<footer><span>Generated {esc(S['generatedAt'][:16].replace('T', ' '))} IST</span><span>Source: YouTube Data API v3 and YouTube Analytics API, read-only</span><span>{('Studio export merged: ' + esc(', '.join(S['studio']['sources']))) if S.get('studio') and S['studio']['videos_matched'] else 'Impressions and click-through rate are not exposed by the API; drop a Studio export in yt-insights/studio/ to add them.'}</span></footer>
</div>
<script>
(function(){{
  var fig=document.querySelector('.chart');if(!fig)return;
  var pts=JSON.parse(fig.dataset.series),svg=fig.querySelector('svg'),cross=svg.querySelector('.cross'),dot=svg.querySelector('.dot.hover'),tip=fig.querySelector('.tip');
  var vb=svg.viewBox.baseVal;
  function show(i){{var p=pts[i];cross.setAttribute('x1',p.x);cross.setAttribute('x2',p.x);cross.setAttribute('opacity',1);dot.setAttribute('cx',p.x);dot.setAttribute('cy',p.y);dot.setAttribute('opacity',1);
    var r=svg.getBoundingClientRect(),sx=r.width/vb.width,sy=r.height/vb.height;
    var d=new Date(p.d+'T00:00:00');tip.innerHTML='<b>'+p.v.toLocaleString()+'</b> views · '+(p.s>=0?'+':'')+p.s+' subs<br>'+d.toLocaleDateString(undefined,{{weekday:'short',day:'numeric',month:'short'}});
    tip.hidden=false;tip.style.left=(p.x*sx)+'px';tip.style.top=(p.y*sy-10)+'px';}}
  function hide(){{cross.setAttribute('opacity',0);dot.setAttribute('opacity',0);tip.hidden=true;}}
  svg.querySelectorAll('.hit').forEach(function(h){{h.addEventListener('mouseenter',function(){{show(+h.dataset.i)}});h.addEventListener('touchstart',function(e){{show(+h.dataset.i)}},{{passive:true}});}});
  svg.addEventListener('mouseleave',hide);
}})();
</script>"""
    out = root / "reports" / f"{slug(c['title'])}-{date.today().isoformat()}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(out)


if __name__ == "__main__":
    main()
