#!/usr/bin/env python3
"""Generate index.html from CharlesIII-speech.txt with inline Wikipedia anchors.

Run once after editing the source text or the entity catalog. The generated
index.html is the deployable artifact; the build script stays in `tools/` for
transparent regeneration.
"""

from __future__ import annotations

import html
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "CharlesIII-speech.txt"
OUTPUT = ROOT / "index.html"

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
# in the table — we encode at emit time.

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
]

ZH_LINKS: list[tuple[str, str]] = [
    ("近於此巍巍殿宇之旁，甫有變故", "2021年美国国会大厦袭击事件"),
    ("愛丁堡公爵菲臘親王", "菲利普親王"),
    ("伊利沙伯王太后", "伊麗莎白·鮑斯-萊昂"),
    ("美國最高法院歷史學會", "美国最高法院"),
    ("一六八九年《權利法案》", "1689年权利法令"),
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
    ("威斯敏斯特", "威斯敏斯特宫"),
    ("英格蘭普通法", "普通法"),
    ("普通法", "普通法"),
    ("大憲章", "大憲章"),
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


def linkify(text: str, table: list[tuple[str, str]], wiki_host: str) -> str:
    """Replace each phrase in `table` with an <a> tag. Longest phrases first.

    Uses placeholder tokens during pass 1 to prevent re-replacement of already-linked
    text on subsequent passes. Pass 2 swaps placeholders for the actual <a> tag.
    """
    # Sort by length descending so "King George the Third" wins before "George".
    sorted_table = sorted(table, key=lambda kv: -len(kv[0]))
    replacements: list[tuple[str, str]] = []  # (placeholder, anchor_html)

    out = text
    for phrase, slug in sorted_table:
        if phrase not in out:
            continue
        url = f"https://{wiki_host}/wiki/{urllib.parse.quote(slug, safe='%#,_()')}"
        token = f"\x00LINK{len(replacements)}\x00"
        anchor = (
            f'<a href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">'
            f"{html.escape(phrase)}</a>"
        )
        replacements.append((token, anchor))
        out = out.replace(phrase, token, 1)  # only the first occurrence per paragraph

    # Now HTML-escape the surrounding plain text without touching placeholders.
    parts = re.split(r"(\x00LINK\d+\x00)", out)
    encoded = []
    for part in parts:
        if part.startswith("\x00LINK") and part.endswith("\x00"):
            idx = int(part[len("\x00LINK") : -1])
            encoded.append(replacements[idx][1])
        else:
            encoded.append(html.escape(part))
    return "".join(encoded)


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
            # Skip front matter / preamble blocks
            continue
        en = m.group(1).strip()
        zh = m.group(2).strip()
        # Collapse runaway whitespace inside the quoted block
        en = re.sub(r"\s+", " ", en)
        zh = re.sub(r"\s+", " ", zh)
        # Strip surrounding straight or curly quotes that wrap the whole quote
        en = re.sub(r'^["“”“”]+', "", en)
        en = re.sub(r'["“”“”]+$', "", en)
        pairs.append((en, zh))
    return pairs


def render(pairs: list[tuple[str, str]]) -> str:
    sections: list[str] = []
    for i, (en, zh) in enumerate(pairs, start=1):
        en_html = linkify(en, EN_LINKS, "en.wikipedia.org")
        zh_html = linkify(zh, ZH_LINKS, "zh.wikipedia.org")
        sections.append(
            f'    <section class="pair" id="p{i}" aria-label="Paragraph {i}">\n'
            f'      <div class="col col-en" lang="en">\n'
            f'        <p class="col-label"><a href="#p{i}" aria-label="Paragraph {i} permalink">§ <span class="num">{ROMAN[i]}</span></a> · English</p>\n'
            f"        <p>{en_html}</p>\n"
            f"      </div>\n"
            f'      <div class="col col-zh" lang="zh-Hant-classical">\n'
            f'        <p class="col-label"><span class="num">第{cn_num(i)}節</span> · 文言</p>\n'
            f"        <p>{zh_html}</p>\n"
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
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Noto+Serif+TC:wght@400;500;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body class="page">
    <header>
      <p class="eyebrow">Address to the 119th Congress  ·  April 2026</p>
      <h1 class="title">King Charles III at the Joint Session of Congress</h1>
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
        <div class="attr">文言詔體 translation drafted with ChatGPT, reviewed by author. Wikipedia anchors curated by hand.</div>
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
    if not SOURCE.exists():
        print(f"Source not found: {SOURCE}", file=sys.stderr)
        return 1
    pairs = parse_pairs(SOURCE.read_text(encoding="utf-8"))
    if not pairs:
        print("No paragraph pairs parsed.", file=sys.stderr)
        return 1
    OUTPUT.write_text(render(pairs), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(pairs)} paragraph pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
