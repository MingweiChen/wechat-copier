#!/usr/bin/env python3
"""build-manifest.py — 扫描 wechat-articles 仓库，生成 copier 用的 manifest.json。

只收录标准日期目录（^YYYY-MM-DD$）且含 ranking.json 的天。
每篇文章输出：rank / title / slug / score / rawUrl（raw.githubusercontent 直链）。

用法:
    python3 build-manifest.py --repo /path/to/wechat-articles --out manifest.json
    python3 build-manifest.py --repo ./wechat-articles --owner MingweiChen --name wechat-articles
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RAW_BASE = "https://raw.githubusercontent.com/{owner}/{name}/main/{path}"


def find_day_dirs(repo: Path):
    """返回 [(date_str, month_str, day_dir_path)]，按日期降序。"""
    days = []
    for month_dir in repo.glob("20*-*"):
        if not month_dir.is_dir():
            continue
        # 月份容器 2026-06/，里面是 2026-06-19/
        if re.match(r'^\d{4}-\d{2}$', month_dir.name):
            for day_dir in month_dir.iterdir():
                if day_dir.is_dir() and DATE_RE.match(day_dir.name):
                    days.append((day_dir.name, month_dir.name, day_dir))
    days.sort(key=lambda x: x[0], reverse=True)
    return days


def build_articles(date, month, day_dir, owner, name):
    ranking = day_dir / "ranking.json"
    if not ranking.exists():
        return None
    try:
        data = json.loads(ranking.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN {date} ranking.json parse fail: {e}", file=sys.stderr)
        return None

    html_dir = day_dir / "html"
    has_html_subdir = html_dir.is_dir()

    # 兼容两种格式：{"articles":[...]} 或直接 [...]
    if isinstance(data, list):
        articles = data
    elif isinstance(data, dict):
        articles = data.get("articles", [])
    else:
        articles = []

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

        html_file = None
        if has_html_subdir:
            cand = html_dir / f"{prefix}-{slug}-wechat.html"
            if cand.exists():
                html_file = cand
            else:
                g = sorted(html_dir.glob(f"{prefix}-*-wechat.html"))
                if g:
                    html_file = g[0]
        if html_file is None:
            g = sorted(day_dir.glob(f"{prefix}-*-wechat.html"))
            if g:
                html_file = g[0]
        if html_file is None:
            print(f"  WARN {date} {prefix} html missing, skip", file=sys.stderr)
            continue

        rel_path = str(html_file.relative_to(day_dir.parent.parent))
        raw_url = RAW_BASE.format(owner=owner, name=name, path=rel_path)

        # 封面：优先 covers/ 文件夹对应图（新结构），其次日目录下（旧扁平）
        # 兼容三种命名：{prefix}-{slug}-cover-*、{prefix}-cover-*、{prefix}-{中文标题}-cover-*
        cover_url = None
        cover_dir = day_dir / "covers"
        cover_cands = []
        search_dirs = []
        if cover_dir.is_dir():
            search_dirs.append(cover_dir)
        search_dirs.append(day_dir)
        # 候选 glob 模式：优先 prefix 前缀，再试 slug（最早的天用 slug 命名封面）
        patterns = []
        if prefix:
            patterns.append(f"{prefix}-*cover-*")
        if slug:
            patterns.append(f"{slug}-cover-*")
        for sd in search_dirs:
            for pat in patterns:
                hits = []
                for ext in ("jpg", "png", "jpeg"):
                    hits += list(sd.glob(f"{pat}.{ext}"))
                if hits:
                    cover_cands = hits
                    break
            if cover_cands:
                break
        if cover_cands:
            def _cover_rank(p):
                n = p.name
                for i, kind in enumerate(["-cover-wide", "-cover-square", "-cover-banner"]):
                    if kind in n:
                        return i
                return 9
            best = sorted(cover_cands, key=_cover_rank)[0]
            cover_rel = str(best.relative_to(day_dir.parent.parent))
            cover_url = RAW_BASE.format(owner=owner, name=name, path=cover_rel)

        arts.append({
            "rank": prefix,
            "title": a.get("title", slug),
            "slug": slug,
            "score": a.get("score"),
            "rawUrl": raw_url,
            "coverUrl": cover_url,
        })
    if not arts:
        return None
    return {"date": date, "month": month, "count": len(arts), "articles": arts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="wechat-articles 仓库本地路径")
    ap.add_argument("--owner", default="MingweiChen")
    ap.add_argument("--name", default="wechat-articles")
    ap.add_argument("--out", default="manifest.json")
    ap.add_argument("--limit", type=int, default=0, help="只取最近 N 天（0=全部）")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"❌ 仓库路径不存在: {repo}", file=sys.stderr)
        return 1

    days = find_day_dirs(repo)
    if args.limit > 0:
        days = days[:args.limit]

    out_days = []
    for date, month, day_dir in days:
        entry = build_articles(date, month, day_dir, args.owner, args.name)
        if entry:
            out_days.append(entry)

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": f"{args.owner}/{args.name}",
        "dayCount": len(out_days),
        "days": out_days,
    }
    Path(args.out).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    total = sum(d["count"] for d in out_days)
    print(f"✅ manifest: {len(out_days)} 天 / {total} 篇 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
