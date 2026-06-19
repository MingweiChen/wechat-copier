#!/usr/bin/env python3
"""build-manifest-remote.py — 纯走 GitHub API 生成 manifest.json，不依赖本地 articles 仓库。
供 GitHub Action 在 copier 仓库里独立运行（每天定时）。
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def gh_get(url, token=None, raw=False):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "wechat-copier-bot")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if not raw:
        req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="MingweiChen")
    ap.add_argument("--name", default="wechat-articles")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--out", default="manifest.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")

    tree_url = (f"https://api.github.com/repos/{args.owner}/{args.name}/"
                f"git/trees/{args.branch}?recursive=1")
    try:
        tree = gh_get(tree_url, token)
    except urllib.error.HTTPError as e:
        print(f"ERROR fetch tree failed: {e}", file=sys.stderr)
        return 1
    paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]

    day_rank = {}
    html_by_day = {}
    cover_by_day = {}
    for p in paths:
        m = re.match(r'^(\d{4}-\d{2})/(\d{4}-\d{2}-\d{2})/ranking\.json$', p)
        if m:
            day_rank[m.group(2)] = (m.group(1), p)
        h = re.match(r'^(\d{4}-\d{2})/(\d{4}-\d{2}-\d{2})/(?:html/)?[^/]*-wechat\.html$', p)
        if h:
            html_by_day.setdefault(h.group(2), []).append(p)
        c = re.match(r'^(\d{4}-\d{2})/(\d{4}-\d{2}-\d{2})/(?:covers/)?[^/]*-cover-[^/]*\.(?:jpg|jpeg|png)$', p)
        if c:
            cover_by_day.setdefault(c.group(2), []).append(p)

    dates = sorted(day_rank.keys(), reverse=True)
    if args.limit > 0:
        dates = dates[:args.limit]

    out_days = []
    for date in dates:
        month, rank_path = day_rank[date]
        raw_rank = (f"https://raw.githubusercontent.com/{args.owner}/{args.name}/"
                    f"{args.branch}/{rank_path}")
        try:
            data = json.loads(gh_get(raw_rank, token, raw=True))
        except Exception as e:
            print(f"  WARN {date} ranking parse fail: {e}", file=sys.stderr)
            continue
        if isinstance(data, list):
            articles = data
        elif isinstance(data, dict):
            articles = data.get("articles", [])
        else:
            articles = []
        day_htmls = html_by_day.get(date, [])

        day_covers = cover_by_day.get(date, [])

        def _cover_rank(path):
            n = path.rsplit("/", 1)[-1]
            for i, kind in enumerate(["-cover-wide", "-cover-square", "-cover-banner"]):
                if kind in n:
                    return i
            return 9

        arts = []
        for a in articles:
            if not isinstance(a, dict):
                continue
            slug = a.get("slug", "")
            prefix = a.get("prefix")
            if not prefix:
                rank = a.get("rank")
                try:
                    prefix = f"{int(rank):02d}" if rank is not None else ""
                except (ValueError, TypeError):
                    prefix = str(rank) if rank is not None else ""
            want = f"{month}/{date}/html/{prefix}-{slug}-wechat.html"
            match = want if want in day_htmls else None
            if not match:
                cands = [h for h in day_htmls
                         if re.search(rf'/{re.escape(prefix)}-[^/]*-wechat\.html$', h)]
                match = sorted(cands)[0] if cands else None
            if not match:
                print(f"  WARN {date} {prefix} html missing, skip", file=sys.stderr)
                continue

            # 封面：优先 covers/ 文件夹对应图。兼容三种命名：
            #   {prefix}-{slug}-cover-*、{prefix}-cover-*、{prefix}-{中文}-cover-*，最早的天用 {slug}-cover-*
            cover_cands = []
            if prefix:
                cover_cands = [c for c in day_covers
                               if re.search(rf'/{re.escape(prefix)}-[^/]*cover-[^/]*\.(?:jpg|jpeg|png)$', c)]
            if not cover_cands and slug:
                cover_cands = [c for c in day_covers
                               if re.search(rf'/{re.escape(slug)}-cover-[^/]*\.(?:jpg|jpeg|png)$', c)]
            cover_url = None
            if cover_cands:
                best = sorted(cover_cands, key=_cover_rank)[0]
                cover_url = (f"https://raw.githubusercontent.com/{args.owner}/"
                             f"{args.name}/{args.branch}/{best}")

            arts.append({
                "rank": prefix,
                "title": a.get("title", slug),
                "slug": slug,
                "score": a.get("score"),
                "rawUrl": (f"https://raw.githubusercontent.com/{args.owner}/"
                           f"{args.name}/{args.branch}/{match}"),
                "coverUrl": cover_url,
            })
        if arts:
            out_days.append({"date": date, "month": month,
                             "count": len(arts), "articles": arts})

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": f"{args.owner}/{args.name}",
        "dayCount": len(out_days),
        "days": out_days,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    total = sum(d["count"] for d in out_days)
    print(f"OK manifest: {len(out_days)} days / {total} articles -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
