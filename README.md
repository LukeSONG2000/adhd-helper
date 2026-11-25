# ADHD Helper

- [GitHub Pages](https://lukesong2000.github.io/adhd-helper/)，可在线自测、搜索指南并下载 Markdown 或 Obsidian 笔记。
- [分篇 Markdown](guide/ADHD人生设计指南/总目录.md) 与 [全文 Markdown](guide/ADHD人生设计指南%20-%20全文.md)。
- 量表、计分和报告源自 [ZHCstudio/adhd-test](https://github.com/ZHCstudio/adhd-test)。作答、计分和报告在当前浏览器内处理。

## 本地预览

```sh
python3 -m pip install -r requirements.txt
python3 site/build.py
python3 -m http.server 8000 --directory _site
```

指南笔记位于 `guide/ADHD人生设计指南/`。更新笔记后同步更新全文 Markdown。推送到 `main` 后，GitHub Actions 会构建并发布更新。
