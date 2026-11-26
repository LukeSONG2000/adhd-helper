from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
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
ASSETS = ROOT / "site" / "assets"
ASSET_URLS = {
    name: f"assets/{name}?v={sha256((ASSETS / name).read_bytes()).hexdigest()[:12]}"
    for name in ("site.css", "assessment.css", "guide.css", "appearance.js", "search.js")
}
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


def shell(title, content, groups, start, base="", current=None):
    page_title = f"{title} · ADHD Helper"
    current_section = current.section if current else ""
    section_links = []
    for section, label in (("library", "总览"), ("action", "行动"), ("foundations", "系统"), ("toolbox", "工具箱")):
        target = f"{base}{GUIDE_PAGE}#{section}" if current else f"#{section}"
        active = (current_section or "library") == section
        selected = ' aria-current="location"' if active else ""
        section_links.append(f'<a href="{target}" data-section="{section}"{selected}>{label}</a>')
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="description" content="ADHD 自测入口、生活指南和实用工具。">
  <title>{escape(page_title)}</title>
  <link rel="icon" type="image/png" href="{base}assets/favicon.png">
  <script src="{base}{ASSET_URLS['appearance.js']}"></script>
  <link rel="stylesheet" href="{base}{ASSET_URLS['site.css']}">
  <link rel="stylesheet" href="{base}{ASSET_URLS['guide.css']}">
  <script src="{base}{ASSET_URLS['search.js']}" defer></script>
</head>
<body class="guide-page">
  <a class="skip-link" href="#main">跳到正文</a>
  <header class="site-header">
    <div class="wrap header-line">
      <a class="wordmark" href="{base or './'}"><span class="mark" aria-hidden="true"></span>ADHD Helper</a>
      <div class="header-tools">
        <nav aria-label="主导航"><a href="{base or './'}">自测</a><a href="{base}{GUIDE_PAGE}" aria-current="page">指南</a></nav>
        <button type="button" class="toolbar-button guide-search-button" id="search-trigger" aria-label="搜索指南" hidden><span class="icon icon-search" aria-hidden="true"></span><span class="toolbar-label" aria-hidden="true">搜索</span></button>
        {appearance_button()}
      </div>
    </div>
  </header>
  <nav class="guide-toolbar" aria-label="指南栏目">
    <div class="wrap guide-toolbar-inner">
      <button type="button" class="toolbar-button directory-button" id="directory-button" aria-controls="guide-rail" aria-expanded="true" hidden><span class="icon icon-directory" aria-hidden="true"></span>目录</button>
      <a class="guide-name" href="{base}{GUIDE_PAGE}#library">人生设计指南</a>
      <details class="guide-topics" id="guide-topics" open>
        <summary class="toolbar-button">栏目<span class="chevron" aria-hidden="true"></span></summary>
        <div class="guide-toplinks">{''.join(section_links)}</div>
      </details>
    </div>
  </nav>
  <div class="wrap guide-layout" id="guide-layout" data-search-unit="篇">
    <aside class="guide-rail" id="guide-rail" aria-label="指南目录">
      <div class="rail-sticky" id="rail-sticky">
        {directory_markup(groups, start, base, current)}
      </div>
    </aside>
    {content}
  </div>
  <dialog class="guide-drawer" id="guide-drawer" aria-labelledby="drawer-title">
    <div class="drawer-head"><h2 id="drawer-title">指南目录</h2><form method="dialog"><button type="submit" class="toolbar-button" aria-label="关闭目录" autofocus><span class="icon icon-close" aria-hidden="true"></span></button></form></div>
    <div class="drawer-body" id="drawer-body"></div>
  </dialog>
  <footer class="site-footer">
    <div class="wrap footer-line"><a href="{REPOSITORY}">项目源码</a><a href="{UPSTREAM}">自测题库来源：ZHCstudio/adhd-test</a></div>
  </footer>
</body>
</html>
"""


def appearance_button():
    return """<button type="button" class="toolbar-button theme-control" id="theme-button" aria-label="外观" hidden>
          <span class="icon icon-display" aria-hidden="true"></span><span class="icon icon-sun" aria-hidden="true"></span><span class="icon icon-moon" aria-hidden="true"></span>
        </button>"""


def note_link(note):
    return f'<a href="{note.url}">{escape(note.title)}</a>'


def group_notes(notes):
    groups = defaultdict(lambda: defaultdict(list))
    for note in notes:
        if note.section:
            groups[note.section][note.chapter].append(note)
    return groups, next(note for note in notes if not note.section)


def directory_markup(groups, start, base, current):
    def link(note):
        selected = ' aria-current="page"' if note == current else ""
        return f'<a class="tree-link" href="{base}{note.url}" data-note="{note.url}"{selected}>{escape(note.title)}</a>'

    def branch(label, items, opened):
        state = " open" if opened else ""
        return f'<details class="tree-group"{state}><summary>{escape(label)}</summary><div class="tree-links">{items}</div></details>'

    parts = []
    active_section = current.section if current else next(iter(SECTIONS))
    for section, label in SECTIONS.items():
        chapters = []
        for chapter, matching in groups[section].items():
            if section == "action" and len(matching) > 3:
                chapters.extend(link(note) for note in matching[:3])
                chapters.append(branch("更多行动指南", "".join(link(note) for note in matching[3:]), current in matching[3:]))
            else:
                links = "".join(link(note) for note in matching)
                chapters.append(branch(chapter, links, current in matching) if chapter else links)
        parts.append(branch(label, "".join(chapters), active_section == section))

    return f"""<div class="guide-navigator" id="guide-navigator">
      <div class="guide-filter" id="guide-filter" hidden>
        <span class="icon icon-search" aria-hidden="true"></span>
        <input id="guide-search" type="search" placeholder="搜索指南" aria-label="搜索指南" autocomplete="off" aria-controls="guide-tree">
        <kbd aria-hidden="true">/</kbd>
      </div>
      <p id="search-status" class="filter-status" role="status"></p>
      <nav class="guide-tree" id="guide-tree" aria-label="章节">{link(start)}{''.join(parts)}</nav>
    </div>"""


def build_library(groups, start):

    parts = []
    for section, label in SECTIONS.items():
        group_blocks = []
        for chapter, matching in groups[section].items():
            featured = matching[:3] if section == "action" else []
            cards = "".join(
                f'<a href="{note.url}" class="guide-card"><span class="guide-cover" data-cover="{style}" aria-hidden="true"><span><i></i><i></i><i></i></span></span>{escape(note.title)}</a>'
                for note, style in zip(featured, ("steps", "layout", "layers"))
            )
            links = "\n".join(
                f'<li>{note_link(note)}</li>' for note in matching[len(featured):]
            )
            listing = f"<ul>{links}</ul>" if links else ""
            if cards:
                more = f'<details class="section-more"><summary>更多行动指南</summary>{listing}</details>' if listing else ""
                group_blocks.append(f'<div class="guide-cards">{cards}</div>{more}')
            elif chapter:
                group_blocks.append(f'<details class="section-more"><summary>{escape(chapter)}</summary>{listing}</details>')
            else:
                group_blocks.append(f'<div>{listing}</div>')
        parts.append(f"""
        <section class="part" id="{section}">
          <h2>{label}</h2>
          <div class="part-chapters">{''.join(group_blocks)}</div>
        </section>""")

    content = f"""
  <main id="main" class="guide-library" tabindex="-1">
    <section id="library" class="library" aria-labelledby="library-title">
      <div class="library-header">
        <h1 id="library-title">ADHD <span class="title-word">人生设计指南</span></h1>
        <a class="start-link" href="{start.url}">{escape(start.title)}<span aria-hidden="true"> →</span></a>
      </div>
      {''.join(parts)}
    </section>

    <section id="downloads" class="downloads" aria-labelledby="download-title">
      <h2 id="download-title">下载 Markdown</h2>
      <a class="btn btn-outline" href="downloads/adhd-guide.md" download="{escape(FULL_GUIDE.name)}">全文 Markdown</a>
      <a class="btn btn-outline" href="downloads/adhd-guide-obsidian.zip" download="ADHD人生设计指南 - Obsidian.zip">Obsidian 分篇笔记</a>
    </section>
  </main>
"""
    (DEST / GUIDE_PAGE).write_text(shell("人生设计指南", content, groups, start), encoding="utf-8")


def note_markup(note, base):
    tokens = MARKDOWN.parse(note.body)
    headings = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            anchor = f"section-{len(headings) + 1}"
            token.attrSet("id", anchor)
            headings.append((anchor, tokens[index + 1].content))
        children = token.children or ()
        for position, child in enumerate(children):
            if child.type == "strong_open" and children[position + 1].content == "怎么做":
                child.attrSet("class", "step-label")
            if child.type == "link_open" and unquote(child.attrGet("href") or "").endswith("总目录.md"):
                child.attrSet("href", f"{base}{GUIDE_PAGE}#library")

    markup = MARKDOWN.renderer.render(tokens, MARKDOWN.options, {})
    markup = markup.replace('<table>', '<div class="table-scroll" role="region" tabindex="0" aria-label="表格，可横向滚动"><table>')
    markup = markup.replace('</table>', '</table></div>')
    markup = markup.replace('<li>[ ] ', '<li class="task"><span class="checkbox" aria-hidden="true"></span>')
    return markup, headings


def build_note(note, groups, start):
    base = "../" * note.url.count("/")
    markup, headings = note_markup(note, base)
    outline = ""
    if headings:
        links = "".join(f'<li><a href="#{anchor}">{escape(text)}</a></li>' for anchor, text in headings)
        outline = f'<details class="outline"><summary>本篇目录</summary><ul>{links}</ul></details>'
    section = SECTIONS.get(note.section, "")
    location = f' <span aria-hidden="true">/</span> <a href="{base}{GUIDE_PAGE}#{note.section}">{escape(section)}</a>' if section else ""
    content = f"""
  <main id="main" class="reader" tabindex="-1">
    <article aria-labelledby="article-title">
      <header class="article-header">
        <nav class="article-path" aria-label="当前位置"><a href="{base}{GUIDE_PAGE}#library">总览</a>{location}</nav>
        <h1 id="article-title">{escape(note.title)}</h1>
      </header>
      {outline}
      <div class="prose">{markup}</div>
    </article>
  </main>"""
    output = DEST / note.url
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(shell(note.title, content, groups, start, base=base, current=note), encoding="utf-8")


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
    shutil.copytree(ASSETS, DEST / "assets")
    notes = load_notes()
    groups, start = group_notes(notes)
    build_library(groups, start)
    assessment = (ROOT / "index.html").read_text(encoding="utf-8")
    for name in ("favicon.png", *ASSET_URLS):
        url = ASSET_URLS.get(name, f"assets/{name}")
        assessment = assessment.replace(f'"site/assets/{name}"', f'"{url}"')
    (DEST / "index.html").write_text(assessment, encoding="utf-8")
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
        build_note(note, groups, start)
    searchable = {
        note.url: " ".join((note.title, SECTIONS.get(note.section, ""), note.chapter, note.body))
        for note in notes
    }
    (DEST / "assets" / "search-index.json").write_text(
        json.dumps(searchable, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    build_downloads()
    print(f"Built {len(notes)} guide notes, the guide directory and the assessment in {DEST}")


if __name__ == "__main__":
    main()
