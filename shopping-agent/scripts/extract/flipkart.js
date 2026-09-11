// Flipkart multi-page search extractor.
// Injected verbatim as the `function` arg of chrome-devtools evaluate_script,
// after navigating to page 1 of the search.
//
// Page 1 comes from the live DOM; later pages via same-origin fetch +
// DOMParser. Flipkart server-renders its search results, so the fetched HTML
// carries products without needing the SPA to boot.
// Verified 2026-09-12: 3 pages -> 120 rows, 91 unique ids.
//
// Flipkart ships hashed class names (CjyrHS, MKiFS6, ...) that change on every
// redesign, so nothing anchors on them. Two stable footholds:
//   * div[data-id]  — the product card wrapper
//   * "4.3(1,234)"  — the rating badge's exact own-text shape
// Scoping the rating to that badge matters: a naive innerText regex reads
// "Bluetooth 5.3" as a 5.3-star rating.
async () => {
  const PAGES = 5; // ← set from [search].pages in rules.toml

  // The decimal is OPTIONAL: Flipkart prints a flat 4.0 as "4(14,844)".
  // Requiring \d\.\d silently dropped every whole-star product, including the
  // single best-reviewed item on page 1 (boAt Airdopes Alpha, 793,084 ratings).
  const BADGE = /^([1-5](?:\.\d)?)\s*\(([\d,]+)\)$/;
  const num = (s) => (s ? parseInt(String(s).replace(/[^\d]/g, ''), 10) : null);

  const scrape = (root, page) =>
    [...root.querySelectorAll('div[data-id]')]
      .filter((c) => c.querySelector('a[href*="/p/itm"]'))
      .map((c) => {
        const badge = [...c.querySelectorAll('div,span')]
          .map((e) => e.textContent.trim())
          .find((t) => BADGE.test(t));
        const m = badge ? badge.match(BADGE) : null;
        const a = c.querySelector('a[href*="/p/itm"]');
        // The product name lives in the thumbnail's alt text, which is more
        // reliable than any text node on the card.
        const img = [...c.querySelectorAll('img')].find((i) => (i.alt || '').trim().length > 10);
        const text = c.textContent || '';
        return {
          site: 'flipkart',
          page,
          id: c.getAttribute('data-id'),
          title: img?.alt?.trim() || a?.getAttribute('title') || null,
          url: a ? new URL(a.getAttribute('href').split('?')[0], location.origin).href : null,
          image: img?.getAttribute('src') || null,
          price: num((text.match(/₹[\d,]+/) || [null])[0]),
          rating: m ? parseFloat(m[1]) : null,
          reviews: m ? num(m[2]) : null,
          sponsored: /\bAd\b|Sponsored/i.test(text.slice(0, 120)),
        };
      });

  const rows = scrape(document, 1);

  const base = location.pathname + location.search.replace(/&page=\d+/g, '');
  const notes = [];

  for (let p = 2; p <= PAGES; p++) {
    try {
      const res = await fetch(`${base}&page=${p}`, { credentials: 'include', cache: 'no-store' });
      if (!res.ok) { notes.push(`page ${p}: HTTP ${res.status}`); break; }
      const got = scrape(new DOMParser().parseFromString(await res.text(), 'text/html'), p);
      if (!got.length) { notes.push(`page ${p}: no cards`); break; }
      rows.push(...got);
    } catch (e) {
      notes.push(`page ${p}: ${e.message}`); break;
    }
  }

  // `pos` is the product's place in this site's own result order, which is
  // what the catalog sorts by: the storefront's ranking encodes sales and
  // relevance signals no star average can reconstruct.
  const kept = rows.filter((r) => r.id && r.title && r.url);
  kept.forEach((r, i) => { r.pos = i; });
  return { rows: kept, notes };
};
