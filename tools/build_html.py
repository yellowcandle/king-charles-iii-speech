#!/usr/bin/env python3
"""Generate index.html from CharlesIII-speech.txt with inline Wikipedia anchors.

Run once after editing the source text or the entity catalog. The generated
index.html is the deployable artifact; the build script stays in `tools/` for
transparent regeneration.

On first run (or after `rm tools/wiki_cache.json`), this fetches a short
summary for every curated Wikipedia slug from the matching language host and
caches it to `tools/wiki_cache.json`. Subsequent runs are offline. Cache
entries marked `"_manual": true` are never overwritten — hand-edit them when
the auto-fetched gloss misfires.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "CharlesIII-speech.txt"
OUTPUT = ROOT / "index.html"
CACHE_PATH = ROOT / "tools" / "wiki_cache.json"

USER_AGENT = (
    "king-charles-iii-bilingual-reader/1.0 "
    "(https://github.com/yellowcandle/king-charles-iii-speech)"
)

ROMAN = [
    "", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII", "XXIX", "XXX",
    "XXXI", "XXXII", "XXXIII", "XXXIV", "XXXV", "XXXVI", "XXXVII", "XXXVIII", "XXXIX", "XL",
    "XLI", "XLII", "XLIII", "XLIV", "XLV", "XLVI", "XLVII", "XLVIII", "XLIX", "L", "LI",
]


def cn_num(n: int) -> str:
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + digits[n - 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    raise ValueError(n)


# ---- entity catalog ----
# Phrases are matched as exact substrings (case-sensitive, with word-boundary nuance
# encoded in each phrase). Longest phrases are applied first to avoid being shadowed
# by shorter ones. Each entry: (phrase, wiki-slug). The wiki-slug is *not* URL-encoded
# in the table — we encode at emit time. Slugs may carry a `#section` fragment for the
# inline link; the cache is keyed by the article-only slug.

EN_LINKS: list[tuple[str, str]] = [
    ("incident not far from this great building", "January_6_United_States_Capitol_attack"),
    ("U.S. Supreme Court Historical Society", "Supreme_Court_Historical_Society"),
    ("Queen Elizabeth, the Queen Mother", "Queen_Elizabeth_The_Queen_Mother"),
    ("Prince Philip, Duke of Edinburgh", "Prince_Philip,_Duke_of_Edinburgh"),
    ("life, liberty and the pursuit of happiness", "Life,_Liberty_and_the_pursuit_of_Happiness"),
    ("no taxation without representation", "No_taxation_without_representation"),
    ("Declaration of Rights of 1689", "Bill_of_Rights_1689"),
    ("American Bill of Rights", "United_States_Bill_of_Rights"),
    ("Declaration of Independence", "United_States_Declaration_of_Independence"),
    ("United Nations Security Council", "United_Nations_Security_Council"),
    ("119th Congress", "119th_United_States_Congress"),
    ("Joint Meeting of Congress", "Joint_session_of_the_United_States_Congress"),
    ("Lord Mountbatten", "Louis_Mountbatten,_1st_Earl_Mountbatten_of_Burma"),
    ("General George Marshall", "George_Marshall"),
    ("Marshall Scholarship", "Marshall_Scholarship"),
    ("Henry Kissinger", "Henry_Kissinger"),
    ("Theodore Roosevelt", "Theodore_Roosevelt"),
    ("President Lincoln", "Abraham_Lincoln"),
    ("President John F. Kennedy", "John_F._Kennedy"),
    ("John F. Kennedy", "John_F._Kennedy"),
    ("Gettysburg address", "Gettysburg_Address"),
    ("Buckingham Palace", "Buckingham_Palace"),
    ("Westminster", "Palace_of_Westminster"),
    ("English common law", "English_common_law"),
    ("Magna Carta", "Magna_Carta"),
    ("a tale of two Georges", "A_Tale_of_Two_Cities"),
    ("Charles Dickens", "Charles_Dickens"),
    ("Oscar Wilde", "Oscar_Wilde"),
    ("president George Washington", "George_Washington"),
    ("George Washington", "George_Washington"),
    ("King George the Third", "George_III"),
    ("King George VI", "George_VI"),
    ("King George V", "George_V"),
    ("President Trump", "Donald_Trump"),
    ("River Thames", "River_Thames"),
    ("Runnymede", "Runnymede"),
    ("Royal Navy", "Royal_Navy"),
    ("Appalachia", "Appalachian_Mountains"),
    ("Atlantic", "Atlantic_Ocean"),
    ("Arctic", "Arctic"),
    ("Commonwealth", "Commonwealth_of_Nations"),
    ("9/11", "September_11_attacks"),
    ("article five", "North_Atlantic_Treaty#Article_5"),
    ("AUKUS", "AUKUS"),
    ("F-35", "Lockheed_Martin_F-35_Lightning_II"),
    ("NATO", "NATO"),
    ("Cold War", "Cold_War"),
    ("Afghanistan", "War_in_Afghanistan_(2001%E2%80%932021)"),
    ("Australia", "Australia"),
    ("Easter", "Easter"),
    ("Washington, D.C.", "Washington,_D.C."),
    ("Queen Elizabeth", "Elizabeth_II"),
    ("New York", "New_York_City"),
    ("Statue of Liberty", "Statue_of_Liberty"),
    ("statue of freedom", "Statue_of_Freedom"),
    ("fascism", "Fascism"),
]

ZH_LINKS: list[tuple[str, str]] = [
    ("近於此巍巍殿宇之旁，甫有變故", "2021年美国国会大厦袭击事件"),
    ("愛丁堡公爵菲臘親王", "菲臘親王"),
    ("伊利沙伯王太后", "伊麗莎白·鮑斯-萊昂"),
    ("美國最高法院歷史學會", "美国最高法院"),
    ("一六八九年《權利法案》", "1689年權利法令"),
    ("美利堅《權利法案》", "美国权利法案"),
    ("生命、自由、追求幸福", "生命权、自由权和追求幸福的权利"),
    ("「無代表，毋納稅」", "無代表，不納稅"),
    ("聯合國安理會", "联合国安全理事会"),
    ("第一百十九屆國會", "第119届美国国会"),
    ("國會兩院之會", "美国国会联席会议"),
    ("蒙巴頓勳爵", "路易斯·蒙巴頓"),
    ("喬治·馬歇爾", "乔治·卡特莱特·马歇尔"),
    ("馬歇爾獎學金", "马歇尔奖学金"),
    ("基辛格", "亨利·基辛格"),
    ("西奧多·羅斯福", "西奥多·罗斯福"),
    ("林肯總統", "亚伯拉罕·林肯"),
    ("約翰·甘迺迪總統", "约翰·肯尼迪"),
    ("約翰·甘迺迪", "约翰·肯尼迪"),
    ("蓋茲堡演說", "葛底斯堡演说"),
    ("白金漢宮", "白金汉宫"),
    ("西敏寺", "西敏寺"),
    ("英格蘭普通法", "普通法"),
    ("普通法", "普通法"),
    ("大憲章", "大憲章"),
    ("二喬治記", "雙城記"),
    ("查理・狄更斯", "查尔斯·狄更斯"),
    ("奧斯卡・王爾德", "奥斯卡·王尔德"),
    ("喬治・華盛頓", "乔治·华盛顿"),
    ("喬治三世王", "喬治三世_(英國)"),
    ("喬治六世王", "喬治六世"),
    ("喬治五世王", "喬治五世"),
    ("特朗普總統", "唐納德·特朗普"),
    ("泰晤士河", "泰晤士河"),
    ("蘭尼米德", "兰尼米德"),
    ("皇家海軍", "皇家海军"),
    ("阿巴拉契亞", "阿巴拉契亚山脉"),
    ("英聯邦", "大英国协"),
    ("九一一事件", "九一一袭击事件"),
    ("九一一", "九一一袭击事件"),
    ("大西洋", "大西洋"),
    ("北極", "北极"),
    ("第五條", "北大西洋公约"),
    ("北約", "北大西洋公约组织"),
    ("AUKUS", "AUKUS"),
    ("F-35 戰機", "F-35闪电II战斗机"),
    ("F-35", "F-35闪电II战斗机"),
    ("冷戰", "冷战"),
    ("阿富汗戰爭", "阿富汗战争_(2001年)"),
    ("阿富汗", "阿富汗战争_(2001年)"),
    ("澳洲", "澳大利亚"),
    ("復活節", "复活节"),
    ("華盛頓", "华盛顿哥伦比亚特区"),
    ("伊利沙伯女王", "伊麗莎白二世"),
    ("紐約", "纽约市"),
    ("獨立宣言", "美国独立宣言"),
    ("自由女神像", "自由雕像"),
    ("法西斯", "法西斯主义"),
]


# ---- cache ----

def article_slug(slug: str) -> str:
    return slug.split("#", 1)[0]


def cache_key(host: str, slug: str) -> str:
    return f"{host}/{article_slug(slug)}"


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ---- Wikipedia fetch ----

def _http_json(url: str, host: str) -> dict | None:
    """GET a URL and decode JSON. Returns None and warns on any failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en" if host.startswith("en") else "zh",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def _fetch_via_rest(host: str, slug: str) -> dict | None:
    quoted = urllib.parse.quote(slug, safe="%_,()")
    url = f"https://{host}/api/rest_v1/page/summary/{quoted}"
    data = _http_json(url, host)
    if not data:
        return None
    if data.get("type") == "disambiguation":
        return {"_disambiguation": True}
    extract = (data.get("extract") or "").strip()
    if not extract:
        return None
    titles = data.get("titles") or {}
    return {
        "title": titles.get("normalized") or data.get("title") or slug.replace("_", " "),
        "extract": extract,
        "description": (data.get("description") or "").strip(),
    }


def _fetch_via_action(host: str, slug: str) -> dict | None:
    """Action API fallback. Follows soft redirects (`&redirects=1`)."""
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "extracts|description",
        "exintro": "1",
        "explaintext": "1",
        "redirects": "1",
        "titles": slug.replace("_", " "),
    }
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    data = _http_json(url, host)
    if not data:
        return None
    pages = (data.get("query") or {}).get("pages") or []
    if not pages:
        return None
    page = pages[0]
    if page.get("missing"):
        return None
    extract = (page.get("extract") or "").strip()
    if not extract:
        return None
    return {
        "title": page.get("title") or slug.replace("_", " "),
        "extract": extract,
        "description": (page.get("description") or "").strip(),
    }


def fetch_summary(host: str, slug: str) -> dict | None:
    """REST `page/summary` with Action API fallback (handles redirects)."""
    rest = _fetch_via_rest(host, slug)
    if rest and not rest.get("_disambiguation"):
        return rest
    if rest and rest.get("_disambiguation"):
        print(f"warn: {host}/{slug} resolved to disambiguation page", file=sys.stderr)
        return None
    action = _fetch_via_action(host, slug)
    if action:
        return action
    print(f"warn: {host}/{slug} no summary available (REST + Action both failed)", file=sys.stderr)
    return None


def populate_cache(cache: dict) -> tuple[int, int, int]:
    """Ensure every catalog (host, article_slug) has a cache entry. Mutates `cache`.

    Returns (cached_hits, fetched_now, failed).
    """
    needed: list[tuple[str, str]] = []
    seen: set[str] = set()
    for _, slug in EN_LINKS:
        key = cache_key("en.wikipedia.org", slug)
        if key in seen:
            continue
        seen.add(key)
        needed.append(("en.wikipedia.org", article_slug(slug)))
    for _, slug in ZH_LINKS:
        key = cache_key("zh.wikipedia.org", slug)
        if key in seen:
            continue
        seen.add(key)
        needed.append(("zh.wikipedia.org", article_slug(slug)))

    cached = fetched = failed = 0
    for host, slug in needed:
        key = f"{host}/{slug}"
        existing = cache.get(key)
        if existing and (existing.get("_manual") or existing.get("extract")):
            cached += 1
            continue
        result = fetch_summary(host, slug)
        if result is None:
            failed += 1
            continue
        cache[key] = result
        fetched += 1
        time.sleep(0.1)
    return cached, fetched, failed


# ---- text helpers ----

_SENTENCE_END = re.compile(r"[。！？]|[.!?](?=\s|$)")


def trim_extract(text: str, max_chars: int = 250) -> tuple[str, bool]:
    """Trim to first sentence boundary, else word-boundary near max_chars.

    Returns (trimmed, was_truncated). Caller appends an ellipsis if truncated.
    """
    text = text.strip()
    if len(text) <= max_chars:
        m = _SENTENCE_END.search(text)
        if m and m.end() < len(text):
            return text[: m.end()].rstrip(), True
        return text, False
    # Hard cap exceeded — try sentence boundary inside the cap first.
    capped = text[: max_chars + 1]
    m = _SENTENCE_END.search(capped)
    if m and m.end() <= max_chars:
        return text[: m.end()].rstrip(), True
    # Word-boundary fallback. CJK has no spaces, so just hard-cut for those.
    snippet = text[:max_chars]
    if " " in snippet:
        snippet = snippet.rsplit(" ", 1)[0]
    return snippet.rstrip(), True


# ---- linking + footnote collection ----

def linkify(
    text: str,
    table: list[tuple[str, str]],
    wiki_host: str,
    cache: dict,
    section_id: int,
    lang: str,
) -> tuple[str, list[dict]]:
    """Replace each phrase with `<a>…</a><sup>n</sup>` and return matching footnote data.

    Numbering is assigned in source order, deduped by article slug, and only includes
    entities whose summaries are present in `cache`. Phrases without a cache entry still
    get an inline `<a>` (no `<sup>`).
    """
    sorted_table = sorted(table, key=lambda kv: -len(kv[0]))
    out = text
    # EN catalog phrases use title case but the body sometimes lowercases them
    # (e.g. "joint meeting of Congress" mid-sentence vs catalog "Joint Meeting
    # of Congress"). Match case-insensitively for EN to keep footnote numbering
    # aligned with the parallel ZH side; render the body's actual casing while
    # the footnote head shows the catalog's canonical form. ZH has no case so
    # the simpler path applies.
    case_insensitive = lang == "en"
    matches: list[tuple[str, str, str, str]] = []  # (actual_phrase, canonical_phrase, slug, url)
    for phrase, slug in sorted_table:
        # Treat U+00B7 (·) and U+30FB (・) as equivalent — Chinese
        # transliteration sources mix them and they look identical in the
        # serif fonts we use.
        pattern_chars = ["[·・]" if c in "·・" else re.escape(c) for c in phrase]
        pattern = re.compile("".join(pattern_chars), re.IGNORECASE if case_insensitive else 0)
        mx = pattern.search(out)
        if not mx:
            continue
        actual_phrase = mx.group(0)
        url = f"https://{wiki_host}/wiki/{urllib.parse.quote(slug, safe='%#,_()')}"
        token = f"\x00LINK{len(matches)}\x00"
        matches.append((actual_phrase, phrase, slug, url))
        out = pattern.sub(token, out, count=1)

    # Walk placeholders in source order; assign footnote numbers.
    fn_for_match: dict[int, int | None] = {}
    seen: dict[str, int | None] = {}  # article_slug -> assigned n (None if cache miss)
    footnotes: list[dict] = []
    placeholder_re = re.compile(r"\x00LINK(\d+)\x00")
    for m in placeholder_re.finditer(out):
        idx = int(m.group(1))
        _, canonical_phrase, slug, url = matches[idx]
        art = article_slug(slug)
        if art in seen:
            fn_for_match[idx] = seen[art]
            continue
        entry = cache.get(f"{wiki_host}/{art}")
        if not entry or not entry.get("extract"):
            seen[art] = None
            fn_for_match[idx] = None
            continue
        n = len(footnotes) + 1
        seen[art] = n
        fn_for_match[idx] = n
        # Footnote head uses the catalog's canonical phrase — what the reader
        # saw in the body (case-normalised) — not the Wikipedia title, so the
        # ¹ in the body and the entry head align by name, not by article slug.
        footnotes.append({
            "n": n,
            "phrase": canonical_phrase,
            "slug": slug,
            "url": url,
            "title": entry.get("title") or canonical_phrase,
            "extract": entry["extract"],
        })

    # Render: substitute placeholders, escape surrounding plaintext.
    # Wikipedia links live in the footnote drawer, not inline. Body keeps the
    # phrase as plain text and emits a numbered superscript that jumps to the
    # matching footnote. Phrases whose summary couldn't be cached become plain
    # text with no marker.
    parts = re.split(r"(\x00LINK\d+\x00)", out)
    rendered: list[str] = []
    for part in parts:
        m = re.fullmatch(r"\x00LINK(\d+)\x00", part)
        if m:
            idx = int(m.group(1))
            actual_phrase, _, _, _ = matches[idx]
            piece = html.escape(actual_phrase)
            n = fn_for_match[idx]
            if n is not None:
                fid = f"p{section_id}-{lang}-{n}"
                piece += f'<sup class="fn-ref"><a href="#{fid}">{n}</a></sup>'
            rendered.append(piece)
        else:
            rendered.append(html.escape(part))
    return "".join(rendered), footnotes


def render_notes(footnotes: list[dict], section_id: int, lang: str) -> str:
    if not footnotes:
        return ""
    summary = "notes ▸" if lang == "en" else "白話注 ▸"
    items: list[str] = []
    for fn in footnotes:
        trimmed, truncated = trim_extract(fn["extract"])
        if truncated:
            trimmed = trimmed.rstrip() + "…"
        fid = f"p{section_id}-{lang}-{fn['n']}"
        items.append(
            f'            <li id="{fid}"><strong>{html.escape(fn["phrase"])}</strong> — '
            f"{html.escape(trimmed)} "
            f'<a href="{html.escape(fn["url"], quote=True)}" target="_blank" '
            f'rel="noopener noreferrer" aria-label="Wikipedia article">'
            f'<span class="ext-mark">↗︎</span></a></li>'
        )
    items_html = "\n".join(items)
    return (
        f'        <details class="notes notes-{lang}">\n'
        f"          <summary>{summary}</summary>\n"
        f"          <ol>\n{items_html}\n          </ol>\n"
        f"        </details>\n"
    )


# ---- text parsing ----

def parse_pairs(src: str) -> list[tuple[str, str]]:
    chunks = [c.strip() for c in src.split("\n---\n") if c.strip()]
    pairs: list[tuple[str, str]] = []
    for chunk in chunks:
        m = re.search(
            r"\*\*Original\*\*\s*\n+>\s*(.+?)\n+\*\*文言詔體譯\*\*\s*\n+>\s*(.+?)$",
            chunk,
            re.DOTALL,
        )
        if not m:
            continue
        en = m.group(1).strip()
        zh = m.group(2).strip()
        en = re.sub(r"\s+", " ", en)
        zh = re.sub(r"\s+", " ", zh)
        en = re.sub(r'^["“”“”]+', "", en)
        en = re.sub(r'["“”“”]+$', "", en)
        pairs.append((en, zh))
    return pairs


def render(pairs: list[tuple[str, str]], cache: dict) -> str:
    sections: list[str] = []
    for i, (en, zh) in enumerate(pairs, start=1):
        en_html, en_notes = linkify(en, EN_LINKS, "en.wikipedia.org", cache, i, "en")
        zh_html, zh_notes = linkify(zh, ZH_LINKS, "zh.wikipedia.org", cache, i, "zh")
        sections.append(
            f'    <section class="pair" id="p{i}" aria-label="Paragraph {i}">\n'
            f'      <div class="col col-en" lang="en">\n'
            f'        <p class="col-label"><a href="#p{i}" aria-label="Paragraph {i} permalink">§ <span class="num">{ROMAN[i]}</span></a> · English</p>\n'
            f"        <p>{en_html}</p>\n"
            f"{render_notes(en_notes, i, 'en')}"
            f"      </div>\n"
            f'      <div class="col col-zh" lang="zh-Hant-classical">\n'
            f'        <p class="col-label"><span class="num">第{cn_num(i)}節</span> · 文言</p>\n'
            f"        <p>{zh_html}</p>\n"
            f"{render_notes(zh_notes, i, 'zh')}"
            f"      </div>\n"
            f"    </section>\n"
        )
    body = "".join(sections)

    return f"""<!doctype html>
<html lang="en" data-view="both">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>King Charles III · Joint Session of Congress · A Bilingual Reader</title>
    <meta name="description" content="King Charles III's address to the U.S. Congress on the 250th anniversary of the Declaration of Independence — the original English alongside a 文言詔體 (Classical Chinese imperial-edict) rendering, with inline Wikipedia annotations." />
    <meta property="og:title" content="King Charles III at the Joint Session of Congress" />
    <meta property="og:description" content="A bilingual reader: the original English alongside a 文言詔體 Classical Chinese rendering." />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Noto+Serif+TC:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body class="page">
    <header>
      <p class="eyebrow">Address to the 119th Congress  ·  April 2026</p>
      <h1 class="title">King Charles III at the Joint Session of Congress<span class="zh" lang="zh-Hant">英皇查理斯三世於美國參眾兩院聯席會議致辭</span></h1>
      <p class="subtitle">Original English  ·  <span class="zh">文言詔體</span> — A Bilingual Reader</p>

      <div class="toolbar" role="toolbar" aria-label="Display options">
        <div class="segmented" role="group" aria-label="Language view">
          <button type="button" data-view-set="english" aria-pressed="false">English</button>
          <button type="button" data-view-set="both" aria-pressed="true">Both</button>
          <button type="button" data-view-set="classical" aria-pressed="false"><span class="label-zh">文言</span></button>
        </div>
        <button type="button" class="theme-toggle" data-theme-toggle aria-label="Toggle dark mode">
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
          <span data-theme-label>Dark</span>
        </button>
      </div>
    </header>

    <hr class="rule-double" />

    <main class="body">
{body}    </main>

    <hr class="rule-double rule-double--reverse" />

    <footer class="footer">
      <div>
        <div>English original · <a href="https://www.ctvnews.ca/canada/royal-family/article/full-speech-king-charles-addresses-us-congress-highlights-uk-us-bond/" target="_blank" rel="noopener noreferrer">CTV News full transcript</a> · local copy <a href="CharlesIII-speech.txt">CharlesIII-speech.txt</a></div>
        <div class="attr">文言詔體 translation drafted with ChatGPT, reviewed by author. Wikipedia anchors curated by hand. Footnote glosses sourced from Wikipedia summaries at build time.</div>
        <div class="attr">More writing · <a href="https://www.threads.com/@lemon.talks.ai" target="_blank" rel="noopener noreferrer" lang="zh-Hant">檸檬的 AI 筆記簿</a></div>
      </div>
      <div class="sig">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 4l3 14h14l3-14-5 5-5-7-5 7-5-5z"/><path d="M5 18h14"/></svg>
        <span>yellowcandle · 2026</span>
      </div>
    </footer>

    <script src="script.js"></script>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any Wikipedia fetch fails.",
    )
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"Source not found: {SOURCE}", file=sys.stderr)
        return 1
    pairs = parse_pairs(SOURCE.read_text(encoding="utf-8"))
    if not pairs:
        print("No paragraph pairs parsed.", file=sys.stderr)
        return 1

    cache = load_cache(CACHE_PATH)
    cached, fetched, failed = populate_cache(cache)
    save_cache(CACHE_PATH, cache)
    print(
        f"wiki: {cached} cached, {fetched} fetched, {failed} failed",
        file=sys.stderr,
    )

    OUTPUT.write_text(render(pairs, cache), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(pairs)} paragraph pairs.")

    if args.strict and failed:
        print(f"--strict: {failed} fetch failure(s); exiting non-zero.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
