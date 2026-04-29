# King Charles III · Joint Session of Congress — Bilingual Reader

A static reader for King Charles III's address to the Joint Session of the U.S.
Congress (April 2026, semi-quincentennial of the Declaration of Independence).
Each English paragraph appears side-by-side with a 文言詔體 (Classical Chinese
imperial-edict) rendering written in the voice of an ancient Chinese sovereign
(朕…詔曰…).

Linked entities — persons, events, documents, places — open the matching
Wikipedia article: **English column → en.wikipedia.org**, **文言 column →
zh.wikipedia.org**.

## Sources

- English original: [CTV News full transcript](https://www.ctvnews.ca/canada/royal-family/article/full-speech-king-charles-addresses-us-congress-highlights-uk-us-bond/) — local copy in `CharlesIII-speech.txt`.
- 文言詔體 translation drafted with ChatGPT, reviewed by author. Wikipedia anchors curated by hand.

## Project layout

```
.
├── index.html            # built output — the deployable artifact
├── styles.css            # parchment palette, EB Garamond + Noto Serif TC, two-column responsive grid
├── script.js             # ~70 lines: theme + view-mode toggles with localStorage
├── CharlesIII-speech.txt # source of truth for the parallel text
├── webui.pen             # Pencil design source (regal, parchment-paper direction)
├── tools/
│   └── build_html.py     # one-shot generator that turns the .txt + entity catalog into index.html
└── README.md
```

## Local preview

The site is plain static files — any HTTP server works:

```bash
python3 -m http.server --bind 127.0.0.1 8765
# open http://127.0.0.1:8765/
```

Or with Node:

```bash
npx serve .
```

Loading `file://.../index.html` directly works in most browsers but Google
Fonts may be blocked by file-protocol CORS — prefer a real HTTP server.

## Regenerating after editing the text

If you edit `CharlesIII-speech.txt` or the entity catalog inside
`tools/build_html.py`, regenerate `index.html`:

```bash
python3 tools/build_html.py
```

The generator parses the `**Original** > … **文言詔體譯** > …` blocks, applies
the curated phrase-to-Wikipedia-slug catalog (longest match first, once per
paragraph), and writes the full HTML.

## Verifying Wikipedia links

```bash
grep -oE 'href="https://(en|zh)\.wikipedia\.org/wiki/[^"]+"' index.html \
  | sed -E 's/^href="//; s/"$//' | sort -u \
  | while read -r u; do printf '%s  %s\n' "$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 8 "$u")" "$u"; done
```

Expected: every URL returns `200`. The generator does not auto-fix slugs —
broken links are surfaced here for manual correction in the catalog.

## Deployment

The build artifact is just three files: `index.html`, `styles.css`,
`script.js`. The `CharlesIII-speech.txt` source is also linked from the
footer, so include it in the deploy.

### Cloudflare Pages (recommended)

1. Push the repo to GitHub.
2. Cloudflare dashboard → **Workers & Pages → Pages → Connect to Git** → select the repo.
3. Build settings — **Build command: (leave blank)**, **Build output directory: `/`**, **Branch: `main`**.
4. First deploy in ~30 s. Auto-deploys on every push.

### GitHub Pages

1. Push to GitHub.
2. Repo **Settings → Pages → Source: Deploy from a branch**, **Branch: `main` / `(root)`**.
3. URL: `https://<user>.github.io/king-charles-iii-speech/`.

Both serve the same artifact; the choice is operational.

## Design

![Desktop mockup](docs/desktop-mockup.png)

Direction: regal, parchment paper. Palette is `#faf6ee` ground, `#1f1a14` ink,
`#8b1a1a` cinnabar accents, `#d9d1bd` rules. EB Garamond for English, Noto
Serif TC for 文言. Two-column at desktop, stacks at &lt; 820 px. Dark-mode
toggle persists in `localStorage`. View-mode segmented control switches
between English-only, Both, or 文言-only. Print stylesheet linearises the
layout and hides the toolbar.

The Pencil source lives in `webui.pen` — open with [Pencil](https://pencil.io)
to edit. Re-export the PNG with the Pencil MCP `export_nodes` tool or via the
Pencil GUI.

> **Note:** the `.pen` file persists to disk only when Pencil's GUI processes
> a save event. If you only ever drove Pencil through the MCP, save once from
> the Pencil app to commit the design data to disk.
