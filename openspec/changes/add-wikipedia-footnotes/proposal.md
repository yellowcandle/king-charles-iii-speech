## Why

The bilingual reader links curated entities (people, events, documents, places) directly to Wikipedia, but a reader who doesn't already recognise *Runnymede*, *Lord Mountbatten*, or *第五條* gains nothing from a bare link without leaving the page. A short build-time gloss under each section turns the reader into a self-contained scholarly edition — readable on a plane or behind a captive portal — while keeping the calm two-column parchment layout intact.

## What Changes

- Add a build-time Wikipedia summary fetch step in `tools/build_html.py` that resolves each curated slug against the matching `en.wikipedia.org` / `zh.wikipedia.org` REST `page/summary` endpoint.
- Cache fetched summaries in a new `tools/wiki_cache.json` checked into git — reproducible builds, hand-editable when an extract misfires, no network dependency on rebuilds.
- Render a per-section, per-column collapsible footnote drawer (`<details><summary>notes ▸</summary>…</details>`) listing every entity referenced in that column of that section, numbered `¹ ² ³` reset per section.
- Add inline superscript markers next to each linked entity (`Magna Carta¹`) tied to the matching footnote.
- Style 文言 column footnotes one tonal step quieter than the body to soften the 文言 / 白話 register clash.
- On fetch failure (network down, 404, redirect): warn to stderr, skip that note, leave the inline link intact — never break the build over one entity.

## Capabilities

### New Capabilities

- `wikipedia-footnotes`: Build-time enrichment of curated Wikipedia anchors with a short summary footnote drawer per section per language column.

### Modified Capabilities

<!-- None — no prior specs exist; this is the first capability formalised. -->

## Impact

- **Code**: `tools/build_html.py` (new fetch + render functions), `styles.css` (footnote drawer + superscript markers), `index.html` (regenerated output, larger). No changes to `script.js` — drawers use native `<details>` so JS stays out of it.
- **New file**: `tools/wiki_cache.json` (~30–60 KB; ~100 entries × ~250 char extract).
- **Build dependency**: `tools/build_html.py` gains a network requirement on first build / cache miss. Stays on Python stdlib (`urllib.request`) — no new package dependencies.
- **External**: Polite use of Wikipedia REST API at build time; honour `User-Agent` per Wikimedia API etiquette. Cache prevents re-fetching on every build.
- **Aesthetic**: Page weight grows; collapsed-by-default drawer keeps default visual density unchanged.
