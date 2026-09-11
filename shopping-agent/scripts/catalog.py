#!/usr/bin/env python3
"""Turn raw Amazon/Flipkart extractor output into a filtered, ranked HTML catalog.

Reads the JSON emitted by scripts/extract/*.js (saved straight to disk by
chrome-devtools evaluate_script, so the raw rows never pass through the model
context), applies the rules in rules.toml, and writes a self-contained page.

Stdlib only, by design: this plugin should install without a pip step.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tomllib
from datetime import datetime
from pathlib import Path

# Tokens that say nothing about product identity and only add noise to the
# cross-site title match.
STOPWORDS = {
    "with", "and", "for", "the", "in", "up", "to", "of", "ear", "true",
    "wireless", "bluetooth", "black", "white", "blue", "red", "grey", "gray",
    "hours", "hrs", "playtime", "playback", "mic", "calls", "fast", "charging",
    "new", "latest", "pack", "combo", "free", "inch", "cm",
}


# ---------------------------------------------------------------- rules


def load_rules(shipped: Path, base: Path) -> tuple[dict, Path]:
    """Seed the user's editable copy on first run, then read it.

    Lives in the project's shopping/ folder rather than the plugin data dir:
    this is a file the user edits constantly, so it belongs where they work.
    """
    user_copy = base / "rules.toml"
    if not user_copy.exists():
        base.mkdir(parents=True, exist_ok=True)
        shutil.copy(shipped, user_copy)
    with user_copy.open("rb") as fh:
        return tomllib.load(fh), user_copy


def rules_for(query: str, rules: dict) -> tuple[dict, str]:
    """Merge [defaults] with whichever category the query matches."""
    merged = dict(rules.get("defaults", {}))
    q = query.lower()
    for name, cat in rules.get("categories", {}).items():
        if any(re.search(rf"\b{re.escape(k)}", q) for k in cat.get("keywords", [])):
            merged.update({k: v for k, v in cat.items() if k != "keywords"})
            return merged, name
    return merged, "defaults"


def site_rules(base: dict, rules: dict, site: str) -> dict:
    """Layer [sites.<site>] on top of the category-merged rules.

    Precedence runs defaults -> category -> site, most specific last, because
    the two storefronts are not comparable: the same star number means a
    different thing on each, so a single global threshold either lets Flipkart
    junk through or filters out everything it stocks.
    """
    merged = dict(base)
    merged.update(rules.get("sites", {}).get(site, {}))
    return merged


# ------------------------------------------------------- filter / rank


def passes(p: dict, r: dict) -> bool:
    if p.get("rating") is None or p.get("reviews") is None:
        return False
    if r.get("exclude_sponsored") and p.get("sponsored"):
        return False
    if p["rating"] < r.get("min_rating", 0):
        return False
    if p["reviews"] < r.get("min_reviews", 0):
        return False
    price = p.get("price")
    if price is not None:
        lo, hi = r.get("min_price"), r.get("max_price")
        if lo is not None and price < lo:
            return False
        if hi is not None and price > hi:
            return False
    return True


def score(p: dict, rank: dict, cheapest: float | None) -> float:
    """Bayesian-shrunk rating, nudged by price.

    A 5.0 backed by 3 reviews collapses toward the prior; a 4.3 backed by
    49,000 barely moves. This is the whole reason a raw star sort is useless.
    """
    m = rank.get("prior_weight", 800)
    c = rank.get("prior_mean", 3.9)
    v, rt = p["reviews"], p["rating"]
    base = (v / (v + m)) * rt + (m / (v + m)) * c

    penalty = rank.get("price_penalty", 0.0)
    if penalty and cheapest and p.get("price"):
        # Ratio in [0,1]; costing 2x the cheapest surrenders half the penalty.
        base -= penalty * (1 - cheapest / p["price"])
    return base


# ------------------------------------------------------------- dedupe


def tokens(title: str) -> set[str]:
    """Identity-bearing words. Short tokens are dropped EXCEPT numeric ones:
    "4" in "AirPods 4" and "161" in "Airdopes 161" are the whole identity."""
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words
            if w not in STOPWORDS and (len(w) > 2 or any(c.isdigit() for c in w))}


def numeric_tokens(t: set[str]) -> set[str]:
    """Purely numeric tokens — model numbers and headline specs alike."""
    return {w for w in t if w.isdigit()}


def same_product(a: set[str], b: set[str], threshold: float = 0.55) -> bool:
    """Decide whether two listings are the same product.

    Two rules, in order:

    1. If both titles contain numbers and share NONE of them, they are
       different products. Airdopes 161 and 163 differ by a single token and
       are otherwise word-for-word identical; nothing else separates them.
       Sharing even one number (a spec both mention) is enough to pass.

    2. Otherwise compare with the overlap coefficient — intersection over the
       SMALLER set, not the union. Amazon titles are keyword-stuffed while
       Flipkart's are terse, so Jaccard punishes a genuine match for the
       verbosity of one side.

    Tuned to prefer false negatives: listing one product twice is a much
    cheaper mistake than collapsing distinct products into one card.
    """
    na, nb = numeric_tokens(a), numeric_tokens(b)
    if na and nb and not (na & nb):
        return False
    smaller = min(len(a), len(b))
    if smaller < 3:
        return a == b
    return len(a & b) / smaller >= threshold


def dedupe(products: list[dict]) -> list[dict]:
    """Collapse the same product listed on both sites into one card.

    Each group is compared against the tokens of its REPRESENTATIVE, never a
    growing union. Unioning made groups act as magnets: every product absorbed
    widened the token set, so the next comparison matched more easily and one
    card could swallow an entire catalog.
    """
    groups: list[dict] = []
    for p in products:
        t = tokens(p["title"])
        for g in groups:
            if same_product(t, g["_tokens"]):
                g["also"].append(p)
                break
        else:
            groups.append({**p, "also": [], "_tokens": t})
    for g in groups:
        g.pop("_tokens", None)
    return groups


KNOWN_BRANDS = {
    "boat", "noise", "boult", "ptron", "zebronics", "realme", "oneplus",
    "samsung", "sony", "jbl", "apple", "oppo", "vivo", "mi", "redmi",
    "infinity", "skullcandy", "philips", "portronics", "ambrane", "lg",
}


def brand_of(title: str) -> str:
    """Best-effort brand for sorting/display: the first known brand token in
    the title, else its first word — both storefronts lead listings with the
    brand name."""
    words = re.findall(r"[A-Za-z0-9]+", title)
    if not words:
        return "—"
    for w in words[:3]:
        if w.lower() in KNOWN_BRANDS:
            return w.capitalize()
    return words[0].capitalize()


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-") or "search"


# --------------------------------------------------------------- html


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1a1a18;--mut:#6b6b66;--line:#e3e3df;--accent:#0a7c5a;--warn:#b4530a}
@media(prefers-color-scheme:dark){:root{--bg:#16161a;--card:#1e1e23;--ink:#ececea;--mut:#9a9a94;--line:#2e2e35;--accent:#4ecf9f;--warn:#e0913f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding-block:32px;padding-left:20px;padding-right:20px}
.wrap{max-width:940px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}
.meta{color:var(--mut);font-size:13px;margin-bottom:24px}
.meta code{background:var(--line);padding:1px 5px;border-radius:4px}
.grid{display:grid;gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;grid-template-columns:28px 96px 1fr;gap:14px;align-items:start}
.num{font-weight:700;font-size:15px;color:var(--mut);text-align:right;padding-top:4px}
.card img{width:96px;height:96px;object-fit:contain;border-radius:8px;background:#fff}
.t{font-weight:600;margin:0 0 6px;font-size:15px}
.t a{color:inherit;text-decoration:none}.t a:hover{text-decoration:underline}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;color:var(--mut)}
.pill{border:1px solid var(--line);border-radius:999px;padding:2px 9px;font-size:12px}
.stars{color:var(--accent);font-weight:600}
.price{font-weight:700;color:var(--ink);font-size:16px}
.rank{color:var(--mut);font-variant-numeric:tabular-nums;font-size:12px}
.alt{margin-top:8px;font-size:13px}
.alt a{color:var(--accent)}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:28px;text-align:center;color:var(--mut)}
.toolbar{display:flex;gap:8px;align-items:center;margin-bottom:16px;font-size:13px;color:var(--mut)}
.toolbar select{font:inherit;padding:4px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
@media(max-width:520px){.card{grid-template-columns:20px 64px 1fr}.card img{width:64px;height:64px}}
"""

SORT_JS = """
(function(){
  var sel = document.getElementById("sortSel");
  var grid = document.querySelector(".grid");
  if (!sel || !grid) return;
  function num(v, whenMissing){
    if (v === null || v === undefined || v === "") return whenMissing;
    var n = parseFloat(v);
    return isNaN(n) ? whenMissing : n;
  }
  var comparators = {
    "idx": function(a,b){ return num(a.dataset.idx, 0) - num(b.dataset.idx, 0); },
    "amazon-pos": function(a,b){ return num(a.dataset.amazonPos, Infinity) - num(b.dataset.amazonPos, Infinity); },
    "flipkart-pos": function(a,b){ return num(a.dataset.flipkartPos, Infinity) - num(b.dataset.flipkartPos, Infinity); },
    "price-asc": function(a,b){ return num(a.dataset.price, Infinity) - num(b.dataset.price, Infinity); },
    "price-desc": function(a,b){ return num(b.dataset.price, -Infinity) - num(a.dataset.price, -Infinity); },
    "rating-desc": function(a,b){ return num(b.dataset.rating, -Infinity) - num(a.dataset.rating, -Infinity); },
    "brand": function(a,b){ return (a.dataset.brand||"").localeCompare(b.dataset.brand||""); }
  };
  function applySort(){
    var cards = Array.prototype.slice.call(grid.children);
    cards.sort(comparators[sel.value] || comparators.idx);
    cards.forEach(function(c, i){
      grid.appendChild(c);
      var badge = c.querySelector(".num");
      if (badge) badge.textContent = i + 1;
    });
  }
  sel.addEventListener("change", applySort);
})();
"""


def render(query: str, cat: str, per_site: dict, groups: list[dict], stats: dict) -> str:
    merged = stats["kept"] - stats["shown"]
    merged_note = (
        f" ({merged} merged into other cards as the same product on both sites)"
        if merged > 0 else ""
    )
    cards = []
    for i, g in enumerate(groups, 1):
        alt = ""
        if g["also"]:
            links = " · ".join(
                f'<a href="{html.escape(a["url"])}">{a["site"].title()} '
                f'{"₹{:,}".format(a["price"]) if a.get("price") else "—"}</a>'
                for a in g["also"]
            )
            alt = f'<div class="alt">Also on {links}</div>'
        price = f'₹{g["price"]:,}' if g.get("price") else "—"
        img = (
            f'<img src="{html.escape(g["image"])}" alt="" loading="lazy">'
            if g.get("image")
            else '<div style="width:96px;height:96px"></div>'
        )
        # Positions on whichever storefront(s) this group came from — the
        # group's own listing plus any cross-site "also" duplicate.
        site_rank = {g["site"]: g.get("_site_rank")}
        site_rank.update({a["site"]: a.get("_site_rank") for a in g["also"]})
        amazon_pos = site_rank.get("amazon")
        flipkart_pos = site_rank.get("flipkart")
        brand = brand_of(g["title"])
        raw_price = g.get("price")
        cards.append(f"""<div class="card" data-idx="{i}" data-price="{raw_price if raw_price is not None else ''}" data-rating="{g["rating"]}" data-brand="{html.escape(brand)}" data-amazon-pos="{amazon_pos if amazon_pos is not None else ''}" data-flipkart-pos="{flipkart_pos if flipkart_pos is not None else ''}">
<div class="num">{i}</div>{img}<div>
<p class="t"><a href="{html.escape(g["url"])}" target="_blank" rel="noopener">{html.escape(g["title"])}</a></p>
<div class="row">
  <span class="price">{price}</span>
  <span class="stars">★ {g["rating"]}</span>
  <span>{g["reviews"]:,} ratings</span>
  <span class="pill">{g["site"].title()}</span>
  <span class="rank">{g["site"]} #{g.get("_site_rank", "?")} · score {g["_score"]:.2f}</span>
</div>{alt}</div></div>""")

    body = (
        f'<div class="grid">{"".join(cards)}</div>'
        if cards
        else '<div class="empty">No product cleared your rules. Loosen '
             "<code>min_reviews</code> or <code>min_rating</code> and rerun.</div>"
    )
    toolbar = "" if not groups else """<div class="toolbar"><label for="sortSel">Sort by</label>
<select id="sortSel">
<option value="idx">Catalog order</option>
<option value="amazon-pos">Amazon position</option>
<option value="flipkart-pos">Flipkart position</option>
<option value="price-asc">Price: low to high</option>
<option value="price-desc">Price: high to low</option>
<option value="rating-desc">Rating: high to low</option>
<option value="brand">Brand: A to Z</option>
</select></div>"""

    return f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(query)} — catalog</title><style>{CSS}</style>
<div class="wrap">
<h1>{html.escape(query)}</h1>
<div class="meta">
{stats['shown']} shown &middot; {stats['kept']} of {stats['scraped']} listings cleared the rules{merged_note}
&nbsp;·&nbsp; rules: <code>{cat}</code> — {" · ".join(f"{s} ★{r.get('min_rating')}+/{r.get('min_reviews'):,}+" for s, r in per_site.items())}
&nbsp;·&nbsp; amazon {stats['amazon']} / flipkart {stats['flipkart']}
&nbsp;·&nbsp; order: <code>{stats['order']}</code>
&nbsp;·&nbsp; {datetime.now():%d %b %Y, %H:%M}
</div>{toolbar}{body}<script>{SORT_JS}</script></div>"""


# --------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--amazon", type=Path, nargs="*", default=[])
    ap.add_argument("--flipkart", type=Path, nargs="*", default=[])
    ap.add_argument("--rules", type=Path, required=True, help="shipped rules.default.toml")
    ap.add_argument("--project-dir", type=Path, required=True, help="${CLAUDE_PROJECT_DIR}")
    ap.add_argument("--out", type=Path, help="override the computed catalog path")
    ap.add_argument("--relax", action="store_true", help="halve thresholds and retry")
    args = ap.parse_args()

    raw: list[dict] = []
    counts = {"amazon": 0, "flipkart": 0}
    seen: set[tuple[str, str]] = set()
    dupes = 0
    notes: list[str] = []
    for site, paths in (("amazon", args.amazon), ("flipkart", args.flipkart)):
        for path in sorted(paths):
            if not path.exists():
                continue
            try:
                rows = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                print(f"warn: {path.name} unreadable ({e})", file=sys.stderr)
                continue
            # Extractors return {rows, notes}; notes record why a page loop
            # stopped early (bot check, HTTP error) so a short scan is visible
            # rather than silently passing as a full one.
            if isinstance(rows, dict):
                for n in rows.get("notes", []):
                    notes.append(f"{site}: {n}")
                rows = rows.get("rows", next((v for v in rows.values()
                                              if isinstance(v, list)), []))
            for r in rows:
                key = (site, str(r.get("id")))
                # Both sites repeat listings across pages — Flipkart heavily.
                if key in seen:
                    dupes += 1
                    continue
                seen.add(key)
                counts[site] += 1
                raw.append(r)

    if not raw:
        print("error: no listings extracted from either site", file=sys.stderr)
        return 2

    base = args.project_dir / "shopping"
    all_rules, user_copy = load_rules(args.rules, base)

    # Catalogs land beside the rules unless the user redirected them.
    configured = all_rules.get("output", {}).get("dir")
    catalogs = Path(configured).expanduser() if configured else base / "catalogs"
    out_path = args.out or catalogs / f"{slugify(args.query)}-{datetime.now():%Y-%m-%d}.html"
    active, cat = rules_for(args.query, all_rules)
    def loosen(r: dict) -> dict:
        return {**r,
                "min_reviews": max(10, int(r.get("min_reviews", 500) * 0.4)),
                "min_rating": round(max(3.5, r.get("min_rating", 4.0) - 0.3), 1)}

    per_site = {s: site_rules(active, all_rules, s) for s in ("amazon", "flipkart")}
    if args.relax:
        per_site = {s: loosen(r) for s, r in per_site.items()}
        cat += " (relaxed)"
    kept = [p for p in raw if passes(p, per_site.get(p["site"], active))]
    prices = [p["price"] for p in kept if p.get("price")]
    cheapest = min(prices) if prices else None
    rank_cfg = all_rules.get("ranking", {})
    for p in kept:
        p["_score"] = score(p, rank_cfg, cheapest)

    order = rank_cfg.get("order", "site")
    if order == "site":
        # Preserve each storefront's own ranking, then interleave the two so
        # neither site monopolises the top of the catalog: A#1, F#1, A#2, F#2...
        by_site: dict[str, list[dict]] = {}
        for prod in sorted(kept, key=lambda x: x.get("pos", 10**6)):
            by_site.setdefault(prod["site"], []).append(prod)
        for rows_ in by_site.values():
            for i, prod in enumerate(rows_):
                prod["_site_rank"] = i + 1
        kept.sort(key=lambda x: (x.get("_site_rank", 10**6), x["site"]))
    else:
        kept.sort(key=lambda p: p["_score"], reverse=True)

    groups = dedupe(kept)[: active.get("max_results", 8)]

    stats = {"scraped": len(raw), "kept": len(kept), "shown": len(groups),
             "order": order, **counts}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(args.query, cat, per_site, groups, stats), encoding="utf-8")

    floor = all_rules.get("behaviour", {}).get("relax_if_fewer_than", 3)
    print(json.dumps({
        "out": str(out_path),
        "rules_file": str(user_copy),
        "category": cat,
        "order": order,
        "rules_applied": {s: {"min_rating": r.get("min_rating"),
                              "min_reviews": r.get("min_reviews")}
                          for s, r in per_site.items()},
        "scraped": len(raw),
        "cross_page_dupes_dropped": dupes,
        "extractor_notes": notes,
        "pages_read": {s: len({r.get("page") for r in raw if r["site"] == s})
                       for s in ("amazon", "flipkart")},
        "kept": len(kept),
        "shown": len(groups),
        "per_site": counts,
        "should_relax": len(groups) < floor and not args.relax,
        "top": [
            {"title": g["title"][:70], "site": g["site"], "site_rank": g.get("_site_rank"),
             "price": g.get("price"),
             "rating": g["rating"], "reviews": g["reviews"],
             "also": [a["site"] for a in g["also"]], "url": g["url"]}
            for g in groups
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
