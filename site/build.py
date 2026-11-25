from collections import defaultdict
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote
from zipfile import ZIP_DEFLATED, ZipFile

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "guide" / "ADHD人生设计指南"
FULL_GUIDE = ROOT / "guide" / "ADHD人生设计指南 - 全文.md"
DEST = ROOT / "_site"
REPOSITORY = "https://github.com/LukeSONG2000/adhd-helper"
GUIDE_PAGE = "guide.html"
UPSTREAM = "https://github.com/ZHCstudio/adhd-test"
SECTIONS = {
    "action": "行动指南运用篇",
    "foundations": "底层系统构建篇",
    "toolbox": "ADHD 实用工具箱",
}
MARKDOWN = MarkdownIt("gfm-like", {"html": False, "linkify": False})


@dataclass(frozen=True)
class Note:
    source: Path
    title: str
    url: str
    section: str
    chapter: str
    body: str


def load_notes():
    notes = []
    for source in sorted(NOTES.rglob("*.md")):
        path = source.relative_to(NOTES)
        if path.name == "总目录.md":
            continue
        heading, body = source.read_text(encoding="utf-8").split("\n", 1)
        if not heading.startswith("# "):
            raise ValueError(f"Missing title in {path}")
        if len(path.parts) == 1:
            notes.append(Note(source, heading[2:], "guide/start.html", "", "", body))
            continue

        section = tuple(SECTIONS)[int(path.parts[0][:2]) - 1]
        number = path.stem.split(" ", 1)[0]
        chapter = path.parts[1].split(" ", 1)[1] if len(path.parts) == 3 else ""
        if chapter:
            chapter_number = re.search(r"\d+", path.parts[1])[0]
            number = f"{chapter_number}-{number}"
        url = f"guide/{section}/{number}.html"
        notes.append(Note(source, heading[2:], url, section, chapter, body))

    if len({note.url for note in notes}) != len(notes):
        raise ValueError("Two notes use the same URL")
    return notes


def shell(title, content, base=""):
    page_title = f"{title} · ADHD Helper"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="ADHD 自测入口、生活指南和实用工具。">
  <title>{escape(page_title)}</title>
  <link rel="icon" type="image/png" href="{base}assets/favicon.png">
  <link rel="stylesheet" href="{base}assets/site.css">
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <header class="site-header">
    <div class="wrap header-line">
      <a class="wordmark" href="{base or './'}"><span class="mark" aria-hidden="true"></span>ADHD Helper</a>
      <nav aria-label="主导航">
        <a href="{base or './'}">自测</a>
        <a href="{base}{GUIDE_PAGE}" aria-current="page">指南</a>
      </nav>
    </div>
  </header>
  {content}
  <footer class="site-footer">
    <div class="wrap footer-line"><a href="{REPOSITORY}">项目源码</a><a href="{UPSTREAM}">自测题库来源：ZHCstudio/adhd-test</a></div>
  </footer>
</body>
</html>
"""


def note_link(note):
    return f'<a href="{note.url}">{escape(note.title)}</a>'


def build_library(notes):
    groups = defaultdict(lambda: defaultdict(list))
    for note in notes:
        if note.section:
            groups[note.section][note.chapter].append(note)
    start = next(note for note in notes if not note.section)

    parts = []
    for section, label in SECTIONS.items():
        group_blocks = []
        for chapter, matching in groups[section].items():
            links = "\n".join(
                f'<li data-note="{note.url}">{note_link(note)}</li>' for note in matching
            )
            heading = f"<h3>{escape(chapter)}</h3>" if chapter else ""
            group_blocks.append(f'<div data-chapter>{heading}<ul>{links}</ul></div>')
        parts.append(f"""
        <section class="part" id="{section}" data-part>
          <div class="part-heading"><span class="part-mark" aria-hidden="true"></span><h2>{label}</h2></div>
          <div class="part-chapters">{''.join(group_blocks)}</div>
        </section>""")

    content = f"""
  <main id="main" class="wrap">
    <section id="library" class="library" aria-labelledby="library-title">
      <div class="library-header">
        <div>
          <h1 id="library-title">人生设计指南</h1>
          <div class="library-links">
            {note_link(start)}
            <a href="#downloads">下载 Markdown</a>
          </div>
        </div>
        <div class="search" hidden>
          <label for="guide-search">搜索指南</label>
          <input id="guide-search" type="search" placeholder="例如：起床、时间盲、过载" autocomplete="off" aria-controls="guide-sections">
          <p id="search-status" role="status" aria-live="polite" hidden></p>
        </div>
      </div>
      <nav class="part-nav" aria-label="指南分类">
        {''.join(f'<a href="#{section}">{label}</a>' for section, label in SECTIONS.items())}
      </nav>
      <div id="guide-sections">{''.join(parts)}</div>
      <p id="no-results" hidden>没有找到匹配的文章。可以换个关键词。</p>
    </section>

    <section id="downloads" class="downloads" aria-labelledby="download-title">
      <h2 id="download-title">下载 Markdown</h2>
      <a href="downloads/adhd-guide.md" download="{escape(FULL_GUIDE.name)}">全文 Markdown</a>
      <a href="downloads/adhd-guide-obsidian.zip" download="ADHD人生设计指南 - Obsidian.zip">Obsidian 分篇笔记</a>
    </section>
  </main>
  <script src="assets/search.js" defer></script>
"""
    (DEST / GUIDE_PAGE).write_text(shell("人生设计指南", content), encoding="utf-8")


def note_markup(note, base):
    tokens = MARKDOWN.parse(note.body)
    headings = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            anchor = f"section-{len(headings) + 1}"
            token.attrSet("id", anchor)
            headings.append((anchor, tokens[index + 1].content))
        for child in token.children or ():
            if child.type == "link_open" and unquote(child.attrGet("href") or "").endswith("总目录.md"):
                child.attrSet("href", f"{base}{GUIDE_PAGE}#library")

    markup = MARKDOWN.renderer.render(tokens, MARKDOWN.options, {})
    markup = markup.replace('<table>', '<div class="table-scroll" role="region" tabindex="0" aria-label="表格，可横向滚动"><table>')
    markup = markup.replace('</table>', '</table></div>')
    markup = markup.replace('<li>[ ] ', '<li class="task"><span class="checkbox" aria-hidden="true"></span>')
    return markup, headings


def build_note(note):
    base = "../" * note.url.count("/")
    markup, headings = note_markup(note, base)
    outline = ""
    if headings:
        links = "".join(f'<li><a href="#{anchor}">{escape(text)}</a></li>' for anchor, text in headings)
        outline = f'<details class="outline"><summary>本篇目录</summary><ul>{links}</ul></details>'
    section = SECTIONS.get(note.section, "")
    location = f'<p class="location">{escape(" / ".join(x for x in (section, note.chapter) if x))}</p>' if section else ""
    content = f"""
  <main id="main" class="wrap reader">
    <a class="back" href="{base}{GUIDE_PAGE}#library">返回指南目录</a>
    <article aria-labelledby="article-title">
      <header class="article-header">
        {location}
        <h1 id="article-title">{escape(note.title)}</h1>
      </header>
      {outline}
      <div class="prose">{markup}</div>
    </article>
  </main>"""
    output = DEST / note.url
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(shell(note.title, content, base=base), encoding="utf-8")


def build_downloads():
    downloads = DEST / "downloads"
    downloads.mkdir()
    shutil.copyfile(FULL_GUIDE, downloads / "adhd-guide.md")
    with ZipFile(downloads / "adhd-guide-obsidian.zip", "w", compression=ZIP_DEFLATED) as archive:
        for note in sorted(NOTES.rglob("*.md")):
            archive.writestr(note.relative_to(NOTES.parent).as_posix(), note.read_bytes())


def main():
    if DEST.is_dir():
        shutil.rmtree(DEST)
    shutil.copytree(ROOT / "site" / "assets", DEST / "assets")
    notes = load_notes()
    build_library(notes)
    assessment = (ROOT / "index.html").read_text(encoding="utf-8")
    (DEST / "index.html").write_text(assessment.replace('href="site/assets/', 'href="assets/'), encoding="utf-8")
    (DEST / "test.html").write_text("""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=./">
  <title>打开 ADHD 自测</title>
</head>
<body><a href="./">打开 ADHD 自测</a></body>
</html>
""", encoding="utf-8")
    for note in notes:
        build_note(note)
    searchable = {
        note.url: " ".join((note.title, SECTIONS[note.section], note.chapter, note.body))
        for note in notes if note.section
    }
    (DEST / "assets" / "search-index.json").write_text(
        json.dumps(searchable, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    build_downloads()
    print(f"Built {len(notes)} guide notes, the guide directory and the assessment in {DEST}")


if __name__ == "__main__":
    main()
