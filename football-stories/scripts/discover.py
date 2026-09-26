#!/usr/bin/env python3
"""Collect today's story leads from sources that need no login and do not block scripts.

  discover.py [--out shorts/briefs] [--date 2026-09-27] [--days 3]      news + Reddit + on-this-day
  discover.py --commons "Cole Palmer" [--limit 5]                       CC photo candidates with licence

Sources (all tested 200 OK without a key on 26 Sep 2026): BBC Sport, Sky Sports and ESPN football
RSS (headlines and links only: never read their text aloud), r/soccer top-of-day RSS (rank stands
in for score), Wikipedia on-this-day events for the date and the next --days days, filtered to
football. Writes <out>/discover-<date>.json and prints a compact table. These are leads, not
facts: every claim still needs two independent sources before it goes in a story.

--commons prints licence, author, credit and a rights class guess per file. "CC0" or "own work"
uploaded by someone other than the photographer or subject is flagged doubtful (the Satpayev
case): check the file history before using it. Stdlib only.
"""
import argparse, datetime as dt, html, json, pathlib, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "football-stories/0.1 (personal research script)"}
FEEDS = {"bbc": "https://feeds.bbci.co.uk/sport/football/rss.xml", "sky": "https://www.skysports.com/rss/12040",
         "espn": "https://www.espn.com/espn/rss/soccer/news", "reddit": "https://www.reddit.com/r/soccer/top/.rss?t=day"}
FOOTBALL = re.compile(r"association football|footballer|\bsoccer\b|\bfifa\b|\buefa\b|world cup|premier league|champions league|"
                      r"european cup|fa cup|la liga|serie a|bundesliga|ligue 1|football club|national football team", re.I)
GRIDIRON = re.compile(r"american football|gridiron|\bnfl\b|college football", re.I)


def get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def rss(name, url):
    root = ET.fromstring(get(url)); out = []
    atom = "{http://www.w3.org/2005/Atom}"
    for rank, it in enumerate(root.iter("item"), 1):
        out.append({"source": name, "rank": rank, "title": (it.findtext("title") or "").strip(), "url": (it.findtext("link") or "").strip(),
                    "published": (it.findtext("pubDate") or "").strip()})
    for rank, e in enumerate(root.iter(atom + "entry"), 1):
        link = e.find(atom + "link")
        out.append({"source": name, "rank": rank, "title": html.unescape(e.findtext(atom + "title") or "").strip(),
                    "url": link.get("href") if link is not None else "", "published": e.findtext(atom + "updated") or ""})
    return out

def onthisday(day):
    j = json.loads(get("https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/%02d/%02d" % (day.month, day.day)))
    out = []
    for e in j.get("events", []):
        pages = e.get("pages", [])
        blob = e.get("text", "") + " ".join(p.get("extract", "")[:300] + p.get("description", "") for p in pages)
        if FOOTBALL.search(blob) and not (GRIDIRON.search(blob) and not re.search(r"footballer|soccer|fifa|uefa", blob, re.I)):
            out.append({"source": "wikipedia-onthisday", "date": "%s-%02d-%02d" % (e.get("year"), day.month, day.day),
                        "years_ago": day.year - int(e.get("year", day.year)), "text": e.get("text", ""),
                        "url": pages[0]["content_urls"]["desktop"]["page"] if pages and "content_urls" in pages[0] else ""})
    return out

def commons(query, limit):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": query,
                                "gsrlimit": limit, "prop": "imageinfo", "iiprop": "extmetadata|url|user"})
    pages = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q)).get("query", {}).get("pages", {})
    strip = lambda s: re.sub(r"<[^>]+>", "", html.unescape(s or "")).strip()
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        lic = strip(m.get("LicenseShortName", {}).get("value")); artist = strip(m.get("Artist", {}).get("value"))
        credit = strip(m.get("Credit", {}).get("value")); uploader = ii.get("user", "")
        cls = "cc" if re.search(r"CC|public domain|PD", lic, re.I) else "unknown"
        why = []
        if "NC" in lic or "ND" in lic: cls, why = "unknown", why + ["NC/ND licence: not usable in a monetised Short"]
        if re.search(r"own work", credit, re.I) and uploader and artist and uploader.lower() not in artist.lower():
            cls, why = "doubtful", why + ["'own work' but uploader %r is not the credited author %r" % (uploader, artist)]
        if lic.upper().startswith("CC0") and not re.search(r"own work", credit, re.I):
            cls, why = "doubtful", why + ["CC0 without an own-work credit: check who took the photo"]
        yield {"title": p.get("title"), "url": ii.get("descriptionurl"), "file": ii.get("url"), "license": lic, "author": artist,
               "credit": credit, "uploader": uploader, "rights_guess": cls, "flags": why,
               "attribution": "%s, %s, via Wikimedia Commons" % (artist or uploader, lic)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out"); ap.add_argument("--date"); ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--commons"); ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    if a.commons:
        for r in commons(a.commons, a.limit):
            print("%-10s %-22s %s\n           author %s | uploader %s | %s%s" % (r["rights_guess"], r["license"][:22], r["url"], r["author"][:40],
                  r["uploader"], r["credit"][:60], "".join("\n           FLAG " + f for f in r["flags"])))
        return
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    bundle = {"collected_at": dt.datetime.now().astimezone().isoformat(timespec="minutes"), "date": day.isoformat(), "news": [], "onthisday": [], "errors": []}
    for name, url in FEEDS.items():
        try: bundle["news"] += rss(name, url)
        except Exception as e: bundle["errors"].append("%s: %s" % (name, e))
    for k in range(a.days + 1):
        try: bundle["onthisday"] += onthisday(day + dt.timedelta(days=k))
        except Exception as e: bundle["errors"].append("onthisday +%d: %s" % (k, e))
    out = pathlib.Path(a.out or "shorts/briefs"); out.mkdir(parents=True, exist_ok=True)
    f = out / ("discover-%s.json" % day.isoformat()); f.write_text(json.dumps(bundle, indent=1, ensure_ascii=False))
    for n in bundle["news"]:
        if n["rank"] <= 12: print("%-6s %2d  %s" % (n["source"], n["rank"], n["title"][:110]))
    for o in bundle["onthisday"]:
        print("OTD    %s (%d y)  %s" % (o["date"], o["years_ago"], o["text"][:100]))
    for e in bundle["errors"]: print("error:", e)
    print("%d headlines, %d on-this-day leads -> %s" % (len(bundle["news"]), len(bundle["onthisday"]), f))


if __name__ == "__main__":
    main()
