#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All-in-one, "all baked in" extractor for working .m3u8 links from http://172.31.169.169

- Pure Python standard library (no external dependencies)
- Concurrent using ThreadPoolExecutor
- Scrapes token.php pages and limited child resources for m3u8 URLs
- Validates candidates by fetching first ~8KB and checking for #EXTM3U
- Saves CSV and M3U files

Usage:
  python extract_m3u8_all_baked_in.py --base http://172.31.169.169 --concurrency 30 --timeout 10
"""
import re
import csv
import sys
import time
import html
import json
import argparse
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Set, Tuple

DEFAULT_BASE = "http://172.31.169.169"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": DEFAULT_BASE + "/",
}

M3U8_RE = re.compile(r'https?://[^\s\'"]+?\.m3u8(?:\?[^\s\'"]*)?', re.I)
SRC_RE = re.compile(r'<(?:iframe|script|source)[^>]+?(?:src|data-src)\s*=\s*["\']([^"\']+)["\']', re.I)
TVARRAY_PARSE_RE_1 = re.compile(r'tvChannelArray\s*=\s*JSON\.parse\(`(.+?)`\)', re.S)
TVARRAY_PARSE_RE_2 = re.compile(r'tvChannelArray\s*=\s*(\[[\s\S]+?\])\s*;', re.S)

def absolutize(base_url: str, maybe_url: str) -> str:
    if maybe_url.startswith("//"):
        return "http:" + maybe_url
    if maybe_url.startswith("http"):
        return maybe_url
    return urllib.parse.urljoin(base_url, maybe_url)

def http_get(url: str, timeout: float = 10.0, headers: Optional[Dict[str,str]] = None, range_bytes: Optional[Tuple[int,int]] = None) -> Tuple[int, bytes, str]:
    """Return (status_code, content_bytes, text_or_empty)."""
    req = urllib.request.Request(url)
    for k, v in (headers or HEADERS).items():
        req.add_header(k, v)
    if range_bytes is not None:
        start, end = range_bytes
        req.add_header("Range", f"bytes={start}-{end}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            status = getattr(resp, "status", 200)
            ct = resp.headers.get_content_charset() or "utf-8"
            text = ""
            try:
                text = data.decode(ct, errors="ignore")
            except Exception:
                text = data.decode("utf-8", errors="ignore")
            return status, data, text
    except urllib.error.HTTPError as e:
        try:
            data = e.read()
        except Exception:
            data = b""
        return e.code, data, data.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[WARN] GET failed {url}: {e}", file=sys.stderr)
        return 0, b"", ""

def extract_tv_channel_array(html_text: str) -> List[Dict]:
    m = TVARRAY_PARSE_RE_1.search(html_text)
    if not m:
        m = TVARRAY_PARSE_RE_2.search(html_text)
        if not m:
            raise RuntimeError("Could not find tvChannelArray JSON on homepage")
        json_text = m.group(1)
    else:
        json_text = m.group(1)
    json_text = html.unescape(json_text)
    return json.loads(json_text)

def scrape_candidates(token_url: str, html_text: str) -> Tuple[Set[str], Set[str]]:
    m3u8s = set(M3U8_RE.findall(html_text) or [])
    child_srcs = set()
    for src in SRC_RE.findall(html_text):
        child_srcs.add(absolutize(token_url, src))
    return m3u8s, child_srcs

def validate_m3u8(url: str, timeout: float = 10.0) -> bool:
    status, data, _ = http_get(url, timeout=timeout, range_bytes=(0, 8191))
    if status and status >= 400:
        return False
    # If server ignored range and returned nothing, try small non-range get
    if not data:
        status2, data2, _ = http_get(url, timeout=timeout)
        if status2 and status2 >= 400:
            return False
        data = data2
    try:
        text = (data or b"").decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    return "#EXTM3U" in text

def fetch_child_html(url: str, timeout: float) -> str:
    status, _, text = http_get(url, timeout=timeout)
    return text if status == 200 and text else ""

def process_channel(base: str, name: str, timeout: float, exec_children: ThreadPoolExecutor, visited: Set[str]) -> Dict[str, str]:
    qs = urllib.parse.quote(name, safe="")
    tok_url = f"{base}/token.php?stream={qs}"
    status, _, text = http_get(tok_url, timeout=timeout)
    if status != 200 or not text:
        return {"channel": name, "m3u8": "", "status": "token_fetch_failed"}

    m3u8s, child_srcs = scrape_candidates(tok_url, text)

    # Fetch limited number of child pages concurrently
    child_srcs_limited = []
    for u in child_srcs:
        if u not in visited:
            visited.add(u)
            child_srcs_limited.append(u)
        if len(child_srcs_limited) >= 40:
            break

    futures = {exec_children.submit(fetch_child_html, u, timeout): u for u in child_srcs_limited}
    for fut in as_completed(futures):
        html_text = fut.result()
        if html_text:
            m3u8s.update(M3U8_RE.findall(html_text) or [])

    if not m3u8s:
        return {"channel": name, "m3u8": "", "status": "no_m3u8_found"}

    # Validate candidates concurrently and short-circuit on first OK
    with ThreadPoolExecutor(max_workers=8) as validator_pool:
        vfuts = {validator_pool.submit(validate_m3u8, u, timeout): u for u in list(m3u8s)}
        winner = None
        for vf in as_completed(vfuts):
            ok = False
            try:
                ok = vf.result()
            except Exception:
                ok = False
            u = vfuts[vf]
            print(f"   - check {name}: {u} -> {'OK' if ok else 'BAD'}")
            if ok:
                winner = u
                break
        # Cancel remaining (best-effort)
        for vf in vfuts:
            if vf is not None and not vf.done():
                try:
                    vf.cancel()
                except Exception:
                    pass

    if winner:
        return {"channel": name, "m3u8": winner, "status": "ok"}
    else:
        return {"channel": name, "m3u8": next(iter(m3u8s)), "status": "none_valid"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE, help="Base site, e.g. http://172.31.169.169")
    ap.add_argument("--concurrency", type=int, default=30, help="Max concurrent channels")
    ap.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds")
    ap.add_argument("--csv", default="m3u8_dump.csv")
    ap.add_argument("--m3u", default="playlist.m3u")
    args = ap.parse_args()

    homepage = f"{args.base}/"
    status, _, text = http_get(homepage, timeout=args.timeout)
    if status != 200 or not text:
        print(f"[FATAL] Could not load homepage {homepage}. Are you on the same network?", file=sys.stderr)
        sys.exit(2)

    try:
        channels = extract_tv_channel_array(text)
    except Exception as e:
        print(f"[FATAL] Could not parse tvChannelArray: {e}", file=sys.stderr)
        sys.exit(2)

    names = [c.get("ch_name") for c in channels if str(c.get("active")) == "1"]
    print(f"[INFO] Found {len(names)} channels")

    t0 = time.time()
    results: List[Dict[str,str]] = []
    visited: Set[str] = set()

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool, ThreadPoolExecutor(max_workers=64) as child_pool:
        futs = {pool.submit(process_channel, args.base, n, args.timeout, child_pool, visited): n for n in names}
        for f in as_completed(futs):
            try:
                res = f.result()
            except Exception as e:
                ch = futs[f]
                print(f"[WARN] Channel {ch} failed: {e}", file=sys.stderr)
                res = {"channel": futs[f], "m3u8": "", "status": "error"}
            results.append(res)

    # Save CSV
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["channel", "m3u8", "status"])
        w.writeheader()
        w.writerows(results)

    # Save M3U (only ok)
    with open(args.m3u, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for row in results:
            if row["status"] == "ok" and row["m3u8"]:
                f.write(f'#EXTINF:-1,{row["channel"]}\n{row["m3u8"]}\n')

    ok_count = sum(1 for r in results if r["status"] == "ok")
    dt = time.time() - t0
    print("\n[DONE]")
    print(f"- CSV: {args.csv}")
    print(f"- M3U: {args.m3u}")
    print(f"- Working: {ok_count}/{len(results)}")
    print(f"- Elapsed: {dt:.1f}s with concurrency={args.concurrency}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
