// Amazon.in multi-page search extractor.
// Injected verbatim as the `function` arg of chrome-devtools evaluate_script,
// after navigating to page 1 of the search.
//
// Reads page 1 from the live DOM, then pulls the remaining pages with
// same-origin fetch + DOMParser rather than navigating to each. One tool call
// instead of N, the session cookie rides along, and no assets are re-fetched.
// Verified 2026-09-12: 5 pages -> 122 rows, 93 unique ASINs (page 1 alone: 22).
//
// Selectors anchor on data-component-type and aria-label ("4.3 out of 5 stars",
// "49,541 ratings"); the surrounding class names are hashed and churn.
async () => {
  const PAGES = 5; // ← set from [search].pages in rules.toml

  const num = (s) => (s ? parseInt(String(s).replace(/[^\d]/g, ''), 10) : null);

  const scrape = (root, page) =>
    [...root.querySelectorAll('[data-component-type="s-search-result"]')].map((c) => {
      const labels = [...c.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label'));
      const ratingLabel = labels.find((x) => /out of 5 stars/i.test(x));
      const reviewLabel = labels.find((x) => /^[\d,]+\s+ratings?$/i.test(x));
      const href = c.querySelector('h2 a, a[href*="/dp/"]')?.getAttribute('href') || null;
      return {
        site: 'amazon',
        page,
        id: c.getAttribute('data-asin') || null,
        title: c.querySelector('h2 span')?.textContent?.trim() || null,
        url: href ? new URL(href, location.origin).href.split('/ref=')[0] : null,
        image: c.querySelector('img.s-image')?.getAttribute('src') || null,
        price: num(c.querySelector('.a-price .a-offscreen')?.textContent),
        rating: ratingLabel ? parseFloat(ratingLabel) : null,
        reviews: num(reviewLabel),
        sponsored: /^Sponsored/i.test(c.textContent.trim()),
      };
    });

  const rows = scrape(document, 1);

  const base = location.pathname + location.search.replace(/&page=\d+/g, '');
  const notes = [];

  for (let p = 2; p <= PAGES; p++) {
    try {
      const res = await fetch(`${base}&page=${p}`, { credentials: 'include', cache: 'no-store' });
      if (!res.ok) { notes.push(`page ${p}: HTTP ${res.status}`); break; }
      const html = await res.text();
      // A bot check returns 200 with no results, so detect it explicitly rather
      // than silently recording an empty page.
      if (/Enter the characters you see|api-services-support@amazon/i.test(html)) {
        notes.push(`page ${p}: bot check`); break;
      }
      const got = scrape(new DOMParser().parseFromString(html, 'text/html'), p);
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
