## ADDED Requirements

### Requirement: Build-time Wikipedia summary fetch

The build tool SHALL fetch a short summary for every curated `(phrase, slug)` entry in the entity catalog from the matching Wikipedia language host (`en.wikipedia.org` for `EN_LINKS`, `zh.wikipedia.org` for `ZH_LINKS`) using the REST `page/summary` endpoint, and SHALL persist results to a JSON cache committed to the repository.

#### Scenario: First build populates the cache

- **WHEN** `tools/build_html.py` is run and `tools/wiki_cache.json` does not exist or lacks an entry for a curated slug
- **THEN** the build tool fetches `https://{host}/api/rest_v1/page/summary/{slug}` for that entry
- **AND** stores `extract`, `description`, and `titles.normalized` in the cache keyed by `"{host}/{slug}"`
- **AND** writes the updated cache back to `tools/wiki_cache.json`

#### Scenario: Cached entry skips network

- **WHEN** `tools/build_html.py` is run and `tools/wiki_cache.json` already contains an entry for a curated slug
- **THEN** the build tool reuses the cached `extract` without making a network request

#### Scenario: Manually edited cache entries are preserved

- **WHEN** a cache entry contains `"_manual": true`
- **THEN** the build tool MUST NOT overwrite that entry, even if a fresh fetch would return different content

#### Scenario: HTTP etiquette

- **WHEN** the build tool makes any request to a Wikipedia host
- **THEN** it MUST send a `User-Agent` header identifying this project and a contact URL
- **AND** it MUST sleep at least 100 ms between successive requests within a single build run

### Requirement: Graceful failure on a per-entry basis

The build tool SHALL NOT abort because of a single Wikipedia fetch failure. A failure in fetching one entry MUST leave the rest of the build intact.

#### Scenario: Network error or 404

- **WHEN** a fetch for a single slug fails (network error, HTTP 404, malformed response, or redirect to a disambiguation page)
- **THEN** the build tool prints a warning to stderr identifying the slug and the failure reason
- **AND** omits that entry from the cache (does not write a partial / empty record)
- **AND** continues processing remaining entries
- **AND** still emits the inline `<a>` link for that phrase in the rendered HTML, just without a corresponding footnote entry

#### Scenario: End-of-build summary

- **WHEN** the build completes
- **THEN** the build tool prints a summary line indicating the count of cached entries and the count of failures

#### Scenario: Strict mode opt-in

- **WHEN** `tools/build_html.py` is invoked with `--strict`
- **AND** any single-entry fetch failure occurs during that run
- **THEN** the build tool exits with a non-zero status code after printing the failure summary

### Requirement: Per-section, per-column footnote drawer

The rendered `index.html` SHALL include, inside each `<section class="pair">`, a collapsible footnote drawer for each language column listing every entity referenced in that column of that section. Numbering SHALL reset at the start of each section.

#### Scenario: Collapsed-by-default native disclosure

- **WHEN** `index.html` is rendered
- **THEN** each per-column drawer is a `<details>` element whose `<summary>` reads `notes ▸` (or 文言-side equivalent)
- **AND** the drawer is collapsed by default (no `open` attribute)
- **AND** the implementation MUST NOT depend on JavaScript for the open/close behavior

#### Scenario: Inline superscript markers

- **WHEN** a paragraph contains a linked entity that has a corresponding footnote
- **THEN** the rendered HTML SHALL place a `<sup class="fn-ref">` element immediately after the closing `</a>` of that link
- **AND** the superscript content is the footnote ordinal `1, 2, 3, …` (rendered using the matching numerals: Arabic for the EN column, Arabic in `<sup>` for the ZH column)
- **AND** the superscript MUST be an in-page anchor (`<a href="#p{N}-{lang}-{i}">`) targeting the matching `<li id="p{N}-{lang}-{i}">` inside the drawer

#### Scenario: Per-section numbering reset

- **WHEN** rendering footnotes for two different sections
- **THEN** each section starts numbering at `1`
- **AND** the same entity (e.g. `Magna Carta`) appearing in both §III and §VII receives a separate footnote in each section

#### Scenario: Per-column symmetry

- **WHEN** a section contains linked entities in both columns
- **THEN** the EN column's drawer lists only EN-column entities with EN-wiki summaries
- **AND** the ZH column's drawer lists only ZH-column entities with ZH-wiki summaries
- **AND** drawers are absent (the entire `<details>` element is omitted) for any column that has zero linked entities in that section

### Requirement: Footnote rendering and length

Footnote entries SHALL be derived from the cached Wikipedia `extract` and presented as short, readable glosses.

#### Scenario: Footnote text format

- **WHEN** rendering a footnote `<li>`
- **THEN** the entry begins with the article's normalized title (from cache) followed by an em-dash separator and the trimmed extract
- **AND** the extract is trimmed to the first sentence ending OR to 250 characters at a word boundary, whichever comes first
- **AND** if trimming occurred, an ellipsis (`…`) is appended
- **AND** the entry ends with a permalink anchor (e.g. `↗`) that links to the same Wikipedia URL the inline `<a>` points to

#### Scenario: Anchored slugs gloss the article

- **WHEN** a curated slug contains a `#` fragment (e.g. `North_Atlantic_Treaty#Article_5`)
- **THEN** the footnote entry uses the article-level summary (the cache is keyed by article title without the fragment)
- **AND** the footnote's permalink retains the fragment so the reader lands on the exact section

### Requirement: Visual quietening of 文言-column footnotes

The 文言 (`.col-zh`) footnote drawer SHALL be styled distinctly from the EN drawer to acknowledge the register difference between the body text (文言詔體) and the gloss (modern Mandarin / 白話).

#### Scenario: Differentiated styling

- **WHEN** `.col-zh .notes` is rendered
- **THEN** its font size, color, and `<summary>` label visibly differ from `.col-en .notes`
- **AND** the `<summary>` includes a label such as `白話注` indicating the register switch
