# 公众号文章 Copier

一个轻量网页：每天自动从 [`wechat-articles`](https://github.com/MingweiChen/wechat-articles) 仓库拉取每篇文章的**标题**和**正文 HTML**，提供**一键复制**按钮，方便导入微信公众号编辑器。

## 在线访问

GitHub Pages: `https://mingweichen.github.io/wechat-copier/`

## 功能

- 📅 按天列出所有文章（最新在前），可下拉筛选某一天
- 📋 **复制正文** — 把文章 HTML 作为富文本写入剪贴板，粘进微信编辑器保留排版 + 图片
- 🔤 **复制标题** — 单独复制标题文字
- 👁 **预览** — 在网页里渲染文章，确认后再复制
- 🔄 刷新按钮重新拉取最新 manifest

## 工作原理

```
wechat-articles 仓库 (公开)
   └─ {月}/{日}/ranking.json + html/*.html
              │
              │  GitHub Action 每天定时（UTC 15:30）
              │  scripts/build-manifest-remote.py 走 GitHub API 扫描
              ▼
       manifest.json  ← 每篇文章的 title + rawUrl
              │
              ▼
   index.html (GitHub Pages)
   点「复制」→ fetch rawUrl 的 HTML → 写入剪贴板 (text/html)
```

- 文章 HTML 里的图片是 jsDelivr CDN 链接，复制粘贴到微信后微信会自动抓取转存。
- raw.githubusercontent.com 带 CORS（`access-control-allow-origin: *`），网页可直接跨域 fetch。

## 复制粘贴到微信的步骤

1. 打开 Pages 页面，找到要发的文章
2. 点「📋 复制正文」（建议先「预览」确认排版）
3. 打开微信公众号后台 → 新建图文 → 正文区
4. `Ctrl/Cmd + V` 粘贴 → 排版和图片自动带入
5. 标题用「🔤 标题」按钮单独复制粘贴

> ⚠️ 复制功能需要 HTTPS（GitHub Pages 满足）或 localhost；剪贴板富文本 API 在现代 Chrome/Edge/Safari 都支持。

## 本地预览/手动重建

```bash
# 用本地 articles 仓库生成 manifest（开发用）
python3 scripts/build-manifest.py --repo ../wechat-articles --out manifest.json

# 或纯走 GitHub API（CI 用，不依赖本地仓库）
GITHUB_TOKEN=$(gh auth token) python3 scripts/build-manifest-remote.py --out manifest.json

# 本地起服务预览
python3 -m http.server 8899
# 打开 http://127.0.0.1:8899/
```

## 文件

| 文件 | 作用 |
|---|---|
| `index.html` | 主页面：文章列表 + 复制按钮 |
| `preview.html` | 单篇预览页 |
| `manifest.json` | 文章索引（CI 自动刷新） |
| `scripts/build-manifest.py` | 本地仓库版 manifest 生成器 |
| `scripts/build-manifest-remote.py` | GitHub API 版（CI 用） |
| `.github/workflows/deploy.yml` | 每天定时重建 + 部署 Pages |
