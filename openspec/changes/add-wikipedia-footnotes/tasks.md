## 1. Cache layer

- [x] 1.1 Add a `wiki_cache.py` module (or top-of-file section in `tools/build_html.py`) defining `load_cache(path) -> dict` and `save_cache(path, data)` using `json` from stdlib, with `ensure_ascii=False` and 2-space indent for stable diffs.
- [x] 1.2 Define cache key format `"{host}/{slug}"` (anchor stripped from slug for cache lookup) and value schema `{title, extract, description, _manual?}`.
- [x] 1.3 Add a `_manual: true` short-circuit in the fetch path so hand-edited entries are never overwritten.

## 2. Wikipedia fetch

- [x] 2.1 Implement `fetch_summary(host, slug) -> dict | None` using `urllib.request` against `https://{host}/api/rest_v1/page/summary/{quoted_slug_without_fragment}`. **Plus**: added an Action API fallback (`/w/api.php?action=query&prop=extracts&redirects=1`) so the build is robust to soft redirects. The two zh.wiki HTTP-500-on-redirect cases that the REST endpoint can't handle are caught here. (Two catalog slugs — `菲利普親王`, `1689年权利法令` — were also corrected to their canonical forms `菲臘親王` and `1689年權利法令`, eliminating the 301 bounce on the inline link too.)
- [x] 2.2 Set `User-Agent: king-charles-iii-bilingual-reader/1.0 (https://github.com/yellowcandle/king-charles-iii-speech)` on every request.
- [x] 2.3 On any error (network, non-200, JSON decode, redirect-to-disambiguation indicated by `type == "disambiguation"`), return `None` and print a stderr warning identifying host + slug + reason.
- [x] 2.4 Add a `time.sleep(0.1)` between sequential fetches inside the build loop.
- [x] 2.5 Add a build-end summary line: `wiki: {cached} cached, {fetched} fetched, {failed} failed`.
- [x] 2.6 Add a `--strict` CLI flag (use `argparse`) that exits non-zero if `failed > 0`.

## 3. Render footnotes

- [x] 3.1 Extend `linkify` (or wrap it) so it returns both the linked HTML AND a list of `(phrase, slug, host)` tuples in source order, deduplicated within the paragraph.
- [x] 3.2 Insert `<sup class="fn-ref"><a href="#p{i}-{lang}-{n}">{n}</a></sup>` immediately after each `</a>` in the linked HTML, where `n` is the 1-based ordinal within the section's column.
- [x] 3.3 Build the per-column `<details class="notes notes-{lang}">` block with `<summary>` `notes ▸` (EN) / `白話注 ▸` (ZH), wrapping an `<ol>` of `<li id="p{i}-{lang}-{n}">` entries.
- [x] 3.4 Format each `<li>` as `<strong>{title}</strong> — {trimmed_extract}{ellipsis_if_truncated} <a href="{wiki_url}" target="_blank" rel="noopener noreferrer" aria-label="Wikipedia article">↗</a>`.
- [x] 3.5 Implement `trim_extract(text, max_chars=250) -> (trimmed, was_truncated)` that prefers first sentence boundary (`. `, `。`, `! `, `? `) and falls back to a word-boundary cut at `max_chars`.
- [x] 3.6 Skip emitting the entire `<details>` element when a column has zero footnotes (e.g. a paragraph with no linked entities, or only entities whose fetches all failed).

## 4. Styles

- [x] 4.1 In `styles.css`, add `.notes` (collapsed-by-default disclosure spacing, marker styling, `<summary>` cursor + hover affordance, top border separating from paragraph).
- [x] 4.2 Add `.fn-ref` (small superscript, slightly muted, no underline, hover/focus underline; `<a>` inside MUST be keyboard-focusable).
- [x] 4.3 Add `.notes ol` reset (no extra left padding, custom counter or `list-style-position: inside`) and `.notes li` paragraph-like rhythm.
- [x] 4.4 Add `.col-zh .notes` overrides: ~92% font-size, lighter foreground, `<summary>` content swap to `白話注 ▸`.
- [x] 4.5 Add `:target` rule so `.notes:has(li:target)` (or fallback `.fn-ref a:focus + …`) opens the drawer when an in-page anchor is followed; smooth-scroll the target. **Design pivot**: CSS cannot toggle `<details open>` via `:target`. Implemented via a 6-line `hashchange` enhancement in `script.js` that opens the parent drawer; the drawer's primary toggle still works without JS. CSS adds a target-highlight (cinnabar tint) + `scroll-margin` for clean scroll anchoring.
- [x] 4.6 Smoke-test print + dark-mode + small-screen layouts (drawer should still collapse cleanly under 600 px column width). Verified via local HTTP server; print stylesheet inherits collapsed `<details>`, dark-mode tokens propagate to `.notes` via existing variables, and at < 820 px the column stack already wraps each drawer under its column.

## 5. End-to-end build

- [x] 5.1 Run `python3 tools/build_html.py` against an empty cache; verify ~100 entries fetch successfully and `tools/wiki_cache.json` is written deterministically (same content on second run). 100 entries cached. md5 of `wiki_cache.json` and `index.html` byte-identical across two consecutive runs.
- [x] 5.2 Run a second build; verify zero network requests (cache hit on every entry). Confirmed: `wiki: 100 cached, 0 fetched, 0 failed`.
- [x] 5.3 Hand-spot-check 5 zh-wiki entries known to redirect oddly (e.g. `Commonwealth` → `大英国协`, `Easter` → `复活节`); set `_manual: true` and override extract where the auto-fetched gloss is misleading. Spot-checked `大英国协`, `复活节`, `無代表，不納稅`, `北大西洋公约`, `兰尼米德`, `菲臘親王`, `1689年權利法令`. All return sensible glosses; no `_manual` overrides needed.
- [x] 5.4 Verify the rendered `index.html` has matching superscript / footnote pairs in each section, and that following a `<sup>` link both scrolls to the `<li>` and opens the drawer. 109 superscript targets, 109 footnote `<li>` IDs, perfect 1:1 set match. Drawer-open verified by inspection of `script.js`.
- [x] 5.5 Verify a forced failure path: temporarily edit one slug to a non-existent title, confirm the build warns, omits the footnote, leaves the `<a>` intact, exits 0 by default and non-zero with `--strict`. Confirmed with `Definitely_Not_A_Real_Article_xyzqwerty1234`: warn + `1 failed`, exit 0 default, exit 2 with `--strict`.

## 6. Documentation

- [x] 6.1 Update `README.md`: regenerate-after-editing section to mention `tools/wiki_cache.json`, the network requirement on first build, and how to refresh (`rm tools/wiki_cache.json`).
- [x] 6.2 Add a brief note in README about the `_manual: true` cache-override mechanism.
- [x] 6.3 Commit `tools/wiki_cache.json` along with the regenerated `index.html`. (File is written; git commit deferred to user per CLAUDE.md guidance — never commit unless explicitly asked.)
