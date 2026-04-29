## Context

The bilingual reader is a static, hand-built artifact: `tools/build_html.py` transforms `CharlesIII-speech.txt` into `index.html` via a curated entity catalog (~50 EN + ~50 ZH phrases, each mapped to a Wikipedia slug). Each phrase becomes an `<a target="_blank">` to either `en.wikipedia.org` or `zh.wikipedia.org`. The page is a one-shot historical artifact — it ships, and the speech text doesn't change. There is no recurring "Wikipedia changed" scenario, and no JavaScript framework — `script.js` is ~60 lines of theme + view-mode toggles.

The proposal adds short summary glosses for every linked entity, surfaced as a per-section, per-column collapsible footnote drawer. This document fixes the technical decisions before tasks.md sequences the work.

## Goals / Non-Goals

**Goals:**
- A reader on a plane or behind a captive portal can read the speech and understand who *Lord Mountbatten* or *Runnymede* is without leaving the page.
- Build remains a single command (`python3 tools/build_html.py`) on Python stdlib only — no new packages.
- Output stays static HTML/CSS, no new JS, no runtime API calls.
- Calm two-column layout is preserved: drawers are collapsed by default and visually quiet.
- Reproducible builds: rerunning the build with no cache changes produces byte-identical output.
- Bilingual symmetry: EN entities → en-wiki summary; ZH entities → zh-wiki summary.

**Non-Goals:**
- No client-side hover popups, no Wikipedia "Page Previews" library, no runtime fetching.
- No live Wikipedia mirroring — we accept that summaries reflect Wikipedia at fetch time, not view time.
- No translation of zh-wiki summaries into 文言 — the gloss stays in modern Mandarin, just styled quieter.
- No automatic disambiguation resolution — the curated slug is authoritative; if it points wrong, fix the slug.
- No graceful degradation for the cache file being absent at build time — we explicitly require either a populated cache or live network access.

## Decisions

### Decision 1: Build-time fetch, committed cache

**Chosen**: `tools/build_html.py` reads/writes a JSON cache (`tools/wiki_cache.json`) keyed by `(host, slug)`. On build, missing entries are fetched from `https://{host}/api/rest_v1/page/summary/{slug}`; existing entries are reused. The cache file is committed to git.

**Why over alternatives:**
- *Runtime client fetch*: would add JS, network dependency at view time, and a CORS surface. Conflicts with "static, calm artifact" goal.
- *Build-time fetch with no cache*: every rebuild hits Wikipedia ~100×, slows iteration, and breaks `--offline` rebuilds. Also makes the build non-deterministic if Wikipedia edits the lead paragraph between runs.
- *Bundled MediaWiki Page Previews JS library*: adds ~30 KB of JS, runtime fetches, and hover-only UX (bad on touch). Doesn't fit the parchment aesthetic.

The committed cache also serves as a hand-edit point: when an extract is misleading (common for redirects, disambiguation pages, or entries where the lead is too biographical), the maintainer edits `wiki_cache.json` directly and the build picks it up. A `_manual: true` marker on edited entries prevents the next fetch pass from overwriting.

### Decision 2: Use REST `page/summary` endpoint, take `extract`

**Chosen**: `GET /api/rest_v1/page/summary/{title}` returns JSON with `extract` (plain-text lead paragraph), `description` (one-line tagline), and `titles.normalized` (canonical title after redirects).

**Why over alternatives:**
- `description` alone is often empty or a Wikidata one-liner that's too terse ("English king") — fine for a tooltip, thin for a footnote.
- MediaWiki Action API `prop=extracts&exintro=1` works but returns HTML and requires extra parsing; REST returns clean plain text.

**Length cap**: We store `extract` as returned (typically 200–600 chars, ≤ ~1200 char hard cap from API) plus `description`. Render-time we trim to the first sentence ending OR 250 chars, whichever comes first, with an ellipsis if truncated. The full extract stays in the cache so a future change to the cap doesn't require re-fetching.

### Decision 3: Anchored slugs (`Foo#Section`) gloss the article, not the section

**Chosen**: For slugs containing `#` (currently only `North_Atlantic_Treaty#Article_5`), the link target retains the anchor, but the cache entry is fetched and keyed by the article title alone. The footnote describes the article as a whole.

**Why**: `page/summary` returns the article lead, not section content; querying section text would require a separate Action API call and extra parsing. The article-level summary is "good enough" for the gloss, while the link still lands the reader at the precise section.

### Decision 4: Per-section, per-column footnote drawer with reset numbering

**Chosen**: Inside each `<section class="pair">`, each column (`.col-en`, `.col-zh`) gains a sibling `<details class="notes">` element listing every linked entity referenced in that paragraph, numbered `¹ ² ³ …` reset per section. Inline links gain a superscript marker (`<sup class="fn-ref">¹</sup>`) immediately after the link text.

**Layout sketch:**
```
<section class="pair">
  <div class="col col-en">
    <p class="col-label">…</p>
    <p>…<a>Magna Carta</a><sup>¹</sup>…<a>Runnymede</a><sup>²</sup>…</p>
    <details class="notes notes-en">
      <summary>notes ▸</summary>
      <ol>
        <li id="p7-en-1">Magna Carta — The 1215 charter…</li>
        <li id="p7-en-2">Runnymede — A water-meadow on the Thames…</li>
      </ol>
    </details>
  </div>
  <div class="col col-zh">… symmetrical …</div>
</section>
```

**Why over alternatives:**
- *Page-wide ascending numbering*: numbers grow into the hundreds; harder to scan; reset-per-section is the established print-edition convention.
- *One shared notes block per section*: forces EN and ZH glosses into the same column or interleaves them; breaks the bilingual symmetry the rest of the page commits to.
- *Always-visible block*: doubles every paragraph's vertical footprint by default. Collapsed `<details>` keeps default reading flow calm and is zero-JS.
- *Repeat-suppress (gloss only first appearance across the page)*: requires page-wide state and breaks per-section locality. With reset-per-section numbering, a re-gloss is local and cheap.

### Decision 5: Native `<details>` element, no JavaScript

**Chosen**: Use HTML `<details>` / `<summary>` for the drawer. No script changes.

**Why**: Universal browser support, keyboard-accessible by default, touch-friendly, prints expanded if printed. Adding JS for this would violate the "calm static artifact" character of the site.

### Decision 6: Tonal differentiation for 文言 column footnotes

**Chosen**: `.col-zh .notes` gets a slightly smaller font, looser line-height, and a half-step muted color compared to `.col-en .notes`, plus a small italicised label like `白話注` ("vernacular note") on the `<summary>`.

**Why**: The body of `.col-zh` is 文言詔體 — the Wikipedia gloss is modern Mandarin (白話). The register clash is unavoidable given the source, but explicit visual marking ("this annotation speaks in a different register") is more honest than pretending they match. The label also signals to a reader who lands here from the EN side what they're about to read.

### Decision 7: Failure mode — warn and skip, never break

**Chosen**: On any single-entity fetch failure (network error, 404, redirect to disambiguation), `build_html.py` prints a warning to stderr identifying the slug, omits that entry from the cache, and proceeds. The inline link stays in place; only the footnote entry is missing. A summary line at end of build reports `n entries cached, m failures`.

**Why**: This is a one-shot artifact. A single missing gloss for `Easter` should not block shipping the page. If the maintainer wants to enforce completeness, they can run `python3 tools/build_html.py --strict` (a small flag, falls back to the warn-and-skip default).

### Decision 8: HTTP etiquette

**Chosen**: Set `User-Agent: king-charles-iii-bilingual-reader/1.0 (https://github.com/yellowcandle/...)` per Wikimedia API policy. Sleep 100 ms between requests. Sequential, not parallel — total fetch is ~100 entries × ~300 ms ≈ 30 s on first build, zero on subsequent.

**Why**: Wikimedia explicitly requires identifying User-Agent. 100 ms spacing is well below their per-IP rate limits and costs us nothing on a one-shot build. Parallelism is unnecessary at this scale and complicates the stdlib-only constraint.

## Risks / Trade-offs

- **Risk**: Wikipedia edits the lead paragraph after we cache, our gloss drifts from "current Wikipedia."
  → **Mitigation**: Accepted. The cache makes our extract a frozen citation, dated by git history. A maintainer can `rm tools/wiki_cache.json && python3 tools/build_html.py` to refresh wholesale.

- **Risk**: A curated slug points at a redirect or disambiguation page; the extract is wrong or generic ("X may refer to…").
  → **Mitigation**: Maintainer hand-edits the cache entry, sets `_manual: true`. Acceptance test: build runs cleanly; spot-check at least 5 zh-wiki entries (zh has more redirect/translation oddity than en).

- **Risk**: 文言 readers find the modern-Mandarin gloss jarring or dilutive of the imperial-edict register.
  → **Mitigation**: Visual quietening (smaller, lighter, labeled `白話注`); collapsed by default. If feedback is negative, the drawer can be hidden on `.col-zh` via a single CSS rule without rebuilding.

- **Risk**: Build now requires network access on first run; CI/cold-clone breaks if Wikipedia is down.
  → **Mitigation**: Cache is committed to git, so cold clones with the cache rebuild offline. README documents that first-time build with no cache requires network.

- **Trade-off**: Page weight grows by ~30–60 KB of inline footnote prose. Acceptable for a static artifact loaded once; the dominant transfer remains Google Fonts.

- **Trade-off**: Reset-per-section numbering means `Magna Carta` may be footnote ¹ in §III and footnote ² in §VII. We accept the local repetition because the alternative (cross-section refs) needs anchors that pull readers across the page.

## Migration Plan

Not applicable — net-new feature on a static artifact. Rollback is `git revert`.

## Open Questions

- **Anchor on inline `<sup>` markers**: should `<sup>¹</sup>` be a clickable in-page anchor jumping to the open `<details>` block (`<a href="#p7-en-1">`)? Adds discoverability but requires the drawer to open on jump (CSS `:target` selector handles this). Default: yes — it's two extra lines of CSS and a clear UX win.
- **Whether to expose a `--no-fetch` build flag**: pure-cache rebuild for offline iteration. Cheap to add; defer until someone wants it.
