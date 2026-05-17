import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict


BIB = sys.argv[1] if len(sys.argv) > 1 else "hcaipub.bib"
OUT = sys.argv[2] if len(sys.argv) > 2 else "artifact_stats.json"
UA = "Mozilla/5.0 artifact-stats-script/1.0"
LAST_HOST_CALL = defaultdict(float)


def log(message):
    print(message, flush=True)


def request_json(url, method="GET", body=None):
    host = urllib.parse.urlparse(url).netloc
    if host == "api.bitbucket.org":
        elapsed = time.time() - LAST_HOST_CALL[host]
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
    data = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                LAST_HOST_CALL[host] = time.time()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            LAST_HOST_CALL[host] = time.time()
            if e.code == 429 and attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            raise


def extract_field(block, name):
    m = re.search(r"(?im)^\s*" + re.escape(name) + r"\s*=\s*", block)
    if not m:
        return None
    i = m.end()
    while i < len(block) and block[i].isspace():
        i += 1
    if i >= len(block):
        return None
    if block[i] == "{":
        depth = 0
        start = i + 1
        for j in range(i, len(block)):
            if block[j] == "{":
                depth += 1
            elif block[j] == "}":
                depth -= 1
                if depth == 0:
                    return block[start:j].strip()
    if block[i] == '"':
        j = i + 1
        while j < len(block) and block[j] != '"':
            j += 1
        return block[i + 1 : j].strip()
    j = i
    while j < len(block) and block[j] not in ",\n":
        j += 1
    return block[i:j].strip()


def parse_bib(path):
    text = open(path, encoding="utf-8").read()
    starts = [m.start() for m in re.finditer(r"@\w+\s*\{", text)]
    starts.append(len(text))
    rows = []
    for i in range(len(starts) - 1):
        block = text[starts[i] : starts[i + 1]]
        key = re.search(r"@\w+\s*\{\s*([^,]+),", block, re.S)
        row = {"key": key.group(1) if key else None}
        for field in ["title", "year", "booktitle", "journal", "url_project", "doi"]:
            row[field] = extract_field(block, field)
        if row.get("url_project"):
            row["title"] = re.sub(r"\s+", " ", re.sub(r"[{}]", "", row.get("title") or "")).strip()
            row["venue"] = re.sub(r"\s+", " ", re.sub(r"[{}]", "", row.get("booktitle") or row.get("journal") or "")).strip()
            rows.append(row)
    return rows


def classify(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc.lower()
    path = u.path.strip("/")
    if host == "github.com":
        parts = path.split("/")
        if len(parts) >= 2:
            repo = parts[1].removesuffix(".git")
            return "github", f"{parts[0]}/{repo}"
    if host == "bitbucket.org":
        parts = path.split("/")
        if len(parts) >= 2:
            return "bitbucket", f"{parts[0]}/{parts[1]}"
    if "zenodo.org" in host:
        m = re.search(r"/(?:record|records)/(\d+)", u.path)
        if m:
            return "zenodo", m.group(1)
    if "figshare.com" in host:
        return "figshare-share", path
    if "4open.science" in host:
        return "4open", path
    if host == "chapering.github.io":
        return "project-page", path.rstrip("/")
    if "sites.google.com" in host:
        return "google-sites", path
    if host == "dx.doi.org" or host == "doi.org":
        return "doi", path
    return "other", host + "/" + path


def github_stats(repo):
    base = f"https://api.github.com/repos/{repo}"
    meta = request_json(base)
    stats = {
        "platform": "GitHub",
        "artifact": f"https://github.com/{repo}",
        "views": "N/A",
        "downloads": 0,
        "stars": meta.get("stargazers_count"),
        "watchers": meta.get("subscribers_count"),
        "forks": meta.get("forks_count"),
        "open_issues": None,
        "open_prs": None,
        "notes": "",
    }
    # GitHub traffic views are auth-only; public release asset downloads are available.
    try:
        releases = request_json(base + "/releases?per_page=100")
        stats["downloads"] = sum(
            asset.get("download_count", 0)
            for rel in releases
            for asset in rel.get("assets", [])
        )
    except Exception:
        stats["downloads"] = "N/A"
    for kind, label in [("issue", "open_issues"), ("pr", "open_prs")]:
        q = urllib.parse.urlencode({"q": f"repo:{repo} type:{kind} state:open"})
        try:
            data = request_json(f"https://api.github.com/search/issues?{q}")
            stats[label] = data.get("total_count")
            time.sleep(0.7)
        except Exception:
            stats[label] = "N/A"
    return stats


def bitbucket_stats(repo):
    base = f"https://api.bitbucket.org/2.0/repositories/{repo}"
    meta = request_json(base)
    stats = {
        "platform": "Bitbucket",
        "artifact": meta.get("links", {}).get("html", {}).get("href", f"https://bitbucket.org/{repo}"),
        "views": "N/A",
        "downloads": "N/A",
        "stars": "N/A",
        "watchers": None,
        "forks": None,
        "open_issues": "N/A",
        "open_prs": None,
        "notes": "stars unavailable; Bitbucket exposes watchers",
    }
    for name, endpoint in [("watchers", "watchers"), ("forks", "forks")]:
        try:
            data = request_json(f"{base}/{endpoint}?pagelen=1")
            stats[name] = data.get("size")
        except Exception:
            stats[name] = "N/A"
    try:
        data = request_json(f"{base}/pullrequests?state=OPEN&pagelen=1")
        stats["open_prs"] = data.get("size")
    except Exception:
        stats["open_prs"] = "N/A"
    if meta.get("has_issues"):
        try:
            data = request_json(f"{base}/issues?state=new&state=open&state=on%20hold&pagelen=1")
            stats["open_issues"] = data.get("size")
        except urllib.error.HTTPError as e:
            stats["open_issues"] = f"N/A ({e.code})"
    return stats


def zenodo_stats(record):
    data = request_json(f"https://zenodo.org/api/records/{record}")
    s = data.get("stats", {})
    return {
        "platform": "Zenodo",
        "artifact": data.get("links", {}).get("self_html", f"https://zenodo.org/records/{record}"),
        "views": s.get("views"),
        "downloads": s.get("downloads"),
        "stars": "N/A",
        "watchers": "N/A",
        "forks": "N/A",
        "open_issues": "N/A",
        "open_prs": "N/A",
        "notes": f"unique views {s.get('unique_views')}; unique downloads {s.get('unique_downloads')}",
    }


def unavailable(kind, ident, url):
    notes = {
        "figshare-share": "private/share URL; metrics not exposed by public API here; page fetch returns AWS WAF challenge",
        "4open": "anonymous artifact page behind Cloudflare challenge; no public repo counters found",
        "project-page": "GitHub Pages project page; no public view/download counters",
        "google-sites": "Google Sites project page; no public counters available",
        "doi": "publisher DOI page, not an artifact counter source",
        "other": "no public counter source identified",
    }.get(kind, "no public counter source identified")
    return {
        "platform": kind,
        "artifact": url,
        "views": "N/A",
        "downloads": "N/A",
        "stars": "N/A",
        "watchers": "N/A",
        "forks": "N/A",
        "open_issues": "N/A",
        "open_prs": "N/A",
        "notes": notes,
    }


def collect():
    papers = parse_bib(BIB)
    cache = {}
    errors = {}
    unique_keys = []
    seen_keys = set()
    for p in papers:
        kind, ident = classify(p["url_project"])
        cache_key = (kind, ident)
        if cache_key not in seen_keys:
            seen_keys.add(cache_key)
            unique_keys.append(cache_key)

    log(f"Found {len(papers)} papers with artifact links and {len(unique_keys)} unique artifact URLs.")
    completed = 0
    for p in papers:
        kind, ident = classify(p["url_project"])
        cache_key = (kind, ident)
        if cache_key in cache:
            continue
        completed += 1
        log(f"[{completed}/{len(unique_keys)}] {kind}: {ident}")
        try:
            if kind == "github":
                cache[cache_key] = github_stats(ident)
            elif kind == "bitbucket":
                cache[cache_key] = bitbucket_stats(ident)
            elif kind == "zenodo":
                cache[cache_key] = zenodo_stats(ident)
            else:
                cache[cache_key] = unavailable(kind, ident, p["url_project"])
            log(f"  done")
        except Exception as e:
            errors[str(cache_key)] = repr(e)
            cache[cache_key] = unavailable(kind, ident, p["url_project"])
            cache[cache_key]["notes"] = "fetch error: " + repr(e)
            log(f"  failed: {repr(e)}")

    out = []
    for p in papers:
        kind, ident = classify(p["url_project"])
        s = dict(cache[(kind, ident)])
        s.update({"year": p.get("year"), "paper": p.get("title"), "key": p.get("key"), "project_link": p["url_project"]})
        out.append(s)
    return out, errors


if __name__ == "__main__":
    rows, errors = collect()
    open(OUT, "w", encoding="utf-8").write(json.dumps({"rows": rows, "errors": errors}, indent=2))
    print(json.dumps({"count": len(rows), "errors": errors}, indent=2))
