import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_OWNER = "baltsers"

CENTRAL_REPO_ALIASES = {
    "baltsers/PyRTFuzz-demo": "baltsers/PyRTFuzz",
}

KNOWN_FALLBACK_REPOS = {
    "VerLog: Enhancing Release Note Generation for Android Apps using Large Language Models": "baltsers/Verlog",
    "PolyCruise: A Cross-Language Dynamic Information Flow Analysis": "baltsers/polycruise",
}

WORD_STOPS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "by",
    "for",
    "from",
    "in",
    "into",
    "large",
    "of",
    "on",
    "or",
    "the",
    "to",
    "towards",
    "using",
    "via",
    "with",
}


def clean_tex(value):
    if not value:
        return ""
    replacements = {
        "\\`{e}": "e",
        "\\'{e}": "e",
        '\\"{o}': "o",
        "\\&": "&",
        "$^2$": "2",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"\\[{}]", "", value)
    value = re.sub(r"[{}]", "", value)
    value = re.sub(r"\\[a-zA-Z]+\s*", "", value)
    return re.sub(r"\s+", " ", value).strip()


def norm_text(value):
    return re.sub(r"[^a-z0-9]+", " ", clean_tex(value).lower()).strip()


def compact(value):
    return re.sub(r"[^a-z0-9]+", "", clean_tex(value).lower())


def tokens(value):
    return {
        t
        for t in re.findall(r"[a-z0-9]+", norm_text(value))
        if len(t) > 1 and t not in WORD_STOPS
    }


def entry_ranges(text):
    starts = [m.start() for m in re.finditer(r"@\w+\s*\{", text)]
    for idx, start in enumerate(starts):
        brace = text.find("{", start)
        if brace < 0:
            continue
        depth = 0
        pos = brace
        while pos < len(text):
            char = text[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield start, pos + 1
                    break
            pos += 1


def extract_field(block, name):
    match = re.search(r"(?im)^\s*" + re.escape(name) + r"\s*=\s*", block)
    if not match:
        return None
    i = match.end()
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
        while j < len(block):
            if block[j] == '"' and block[j - 1] != "\\":
                return block[i + 1 : j].strip()
            j += 1
    j = i
    while j < len(block) and block[j] not in ",\n":
        j += 1
    return block[i:j].strip()


def parse_entry(block):
    key_match = re.search(r"@\w+\s*\{\s*([^,]+),", block, re.S)
    fields = {}
    for field in [
        "title",
        "author",
        "year",
        "booktitle",
        "journal",
        "doi",
        "url",
        "url_project",
        "url_docker",
        "url_repository",
        "note",
    ]:
        value = extract_field(block, field)
        if value is not None:
            fields[field] = clean_tex(value)
    return {
        "key": key_match.group(1).strip() if key_match else "",
        "title": fields.get("title", ""),
        "fields": fields,
        "block": block,
    }


def github_request(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "artifact-visibility-tools",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_repos(owner):
    repos = []
    page = 1
    while True:
        print(f"Fetching {owner} repositories page {page}...", file=sys.stderr)
        batch = github_request(
            f"https://api.github.com/users/{owner}/repos?per_page=100&page={page}"
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def load_or_fetch_repos(cache_path, owner, refresh):
    path = Path(cache_path)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    repos = fetch_repos(owner)
    path.write_text(json.dumps(repos, indent=2), encoding="utf-8")
    return repos


def fetch_readme(full_name):
    try:
        data = github_request(f"https://api.github.com/repos/{full_name}/readme")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"  README unavailable for {full_name}: {exc}", file=sys.stderr)
        return ""
    content = data.get("content") or ""
    if not content:
        return ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except ValueError:
        return ""


def load_or_fetch_readmes(cache_path, repos, refresh, skip):
    path = Path(cache_path)
    readmes = {}
    if path.exists() and not refresh:
        readmes = json.loads(path.read_text(encoding="utf-8"))
    if skip:
        return readmes
    changed = False
    for index, repo in enumerate(repos, start=1):
        full_name = repo["full_name"]
        if full_name in readmes and not refresh:
            continue
        print(f"Fetching README {index}/{len(repos)}: {full_name}", file=sys.stderr)
        readmes[full_name] = fetch_readme(full_name)
        changed = True
    if changed or not path.exists():
        path.write_text(json.dumps(readmes, indent=2, ensure_ascii=False), encoding="utf-8")
    return readmes


def repo_record(repo, readmes):
    full_name = repo["full_name"]
    html_url = repo.get("html_url") or f"https://github.com/{full_name}"
    return {
        "name": repo.get("name") or full_name.split("/", 1)[-1],
        "full_name": full_name,
        "html_url": html_url,
        "description": repo.get("description") or "",
        "readme": readmes.get(full_name, ""),
        "topics": " ".join(repo.get("topics") or []),
    }


def fallback_repo(full_name):
    name = full_name.split("/", 1)[-1]
    return {
        "name": name,
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "description": "",
        "readme": "",
        "topics": "",
    }


def score_repo(entry, repo):
    title = entry["title"]
    if not title:
        return 0, []
    title_norm = norm_text(title)
    title_compact = compact(title)
    artifact_prefix = title.split(":", 1)[0].strip()
    artifact_compact = compact(artifact_prefix)
    repo_name_compact = compact(repo["name"])
    repo_full_compact = compact(repo["full_name"].split("/", 1)[-1])
    corpus = "\n".join([repo["name"], repo["full_name"], repo["description"], repo["readme"], repo["topics"]])
    corpus_norm = norm_text(corpus)
    repo_url = repo["html_url"].rstrip("/")

    score = 0
    reasons = []
    for field_name, field_value in entry["fields"].items():
        if field_name.startswith("url") and repo_url.lower() in field_value.lower().rstrip("/"):
            score += 1200
            reasons.append(f"{field_name} already names repo")

    if title_norm and title_norm in corpus_norm:
        score += 1000
        reasons.append("exact title in repo text")

    if artifact_compact and artifact_compact == repo_name_compact:
        score += 900
        reasons.append("title prefix equals repo name")
    elif artifact_compact and artifact_compact == repo_full_compact:
        score += 900
        reasons.append("title prefix equals repo basename")
    elif artifact_compact and (
        artifact_compact in repo_name_compact or repo_name_compact in artifact_compact
    ):
        score += 500
        reasons.append("title prefix overlaps repo name")

    title_tokens = tokens(title)
    corpus_tokens = tokens(corpus)
    if title_tokens and corpus_tokens:
        overlap = title_tokens & corpus_tokens
        ratio = len(overlap) / max(1, len(title_tokens))
        if len(overlap) >= 4 and ratio >= 0.55:
            score += int(350 + ratio * 250 + len(overlap) * 4)
            reasons.append(f"title token overlap {len(overlap)}/{len(title_tokens)}")

    return score, reasons


def matches_for_entry(entry, repos, min_score):
    fallback = KNOWN_FALLBACK_REPOS.get(entry["title"])
    scored = []
    repos_by_full_name = {repo["full_name"]: repo for repo in repos}
    for repo in repos:
        score, reasons = score_repo(entry, repo)
        if score >= min_score:
            scored.append((score, repo, reasons))
    if fallback and all(repo["full_name"] != fallback for _, repo, _ in scored):
        scored.append((950, fallback_repo(fallback), ["known central repository fallback"]))
    if not scored:
        return []
    scored.sort(key=lambda item: (-item[0], item[1]["full_name"].lower()))
    strong = [item for item in scored if item[0] >= 900]
    chosen = strong if strong else [item for item in scored if item[0] >= scored[0][0] - 35]

    expanded = []
    seen = set()
    for score, repo, reasons in chosen:
        canonical = CENTRAL_REPO_ALIASES.get(repo["full_name"])
        if canonical and canonical not in seen:
            expanded.append(
                (
                    score + 1,
                    repos_by_full_name.get(canonical) or fallback_repo(canonical),
                    ["canonical central repository for matched repo"],
                )
            )
            seen.add(canonical)
        if repo["full_name"] not in seen:
            expanded.append((score, repo, reasons))
            seen.add(repo["full_name"])
    expanded.sort(key=lambda item: (-item[0], item[1]["full_name"].lower()))
    return expanded


def field_indent(block):
    match = re.search(r"\n([ \t]*)[A-Za-z_][A-Za-z0-9_]*\s*=", block)
    return match.group(1) if match else "  "


def remove_repo_fields(block):
    pattern = re.compile(
        r"\n[ \t]*(?:url_repository|url_repo\d+)\s*=\s*(?:\{(?:[^{}]|\{[^{}]*\})*\}|\"(?:\\.|[^\"])*\"|[^,\n}]*),?",
        re.I,
    )
    return pattern.sub("", block)


def insert_repo_fields(block, urls):
    if not urls:
        return block
    block = remove_repo_fields(block)
    close = block.rfind("}")
    if close < 0:
        return block
    indent = field_indent(block)
    existing_body = block[:close].rstrip()
    suffix = block[close:]
    if not existing_body.endswith(","):
        existing_body += ","
    fields = []
    for index, url in enumerate(urls, start=1):
        field = "url_repository" if index == 1 else f"url_repo{index}"
        comma = "," if index < len(urls) else ""
        fields.append(f"{indent}{field} = {{{url}}}{comma}")
    return existing_body + "\n" + "\n".join(fields) + "\n" + suffix


def update_bib_text(text, repos, min_score, dry_run):
    output = []
    cursor = 0
    changes = []
    for start, end in entry_ranges(text):
        output.append(text[cursor:start])
        block = text[start:end]
        entry = parse_entry(block)
        matches = matches_for_entry(entry, repos, min_score)
        if matches:
            urls = [repo["html_url"].rstrip("/") for _, repo, _ in matches]
            changes.append(
                {
                    "key": entry["key"],
                    "title": entry["title"],
                    "urls": urls,
                    "scores": [
                        {
                            "score": score,
                            "repo": repo["full_name"],
                            "reasons": reasons,
                        }
                        for score, repo, reasons in matches
                    ],
                }
            )
            output.append(block if dry_run else insert_repo_fields(block, urls))
        else:
            output.append(block)
        cursor = end
    output.append(text[cursor:])
    return "".join(output), changes


def main():
    parser = argparse.ArgumentParser(
        description="Add or update url_repository fields in a BibTeX file by matching papers to GitHub repos."
    )
    parser.add_argument("bib", help="BibTeX file to update in place")
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="central GitHub owner or organization")
    parser.add_argument("--repo-cache", default="baltsers_repos.json", help="GitHub repository cache JSON")
    parser.add_argument("--readme-cache", default="baltsers_repo_readmes.json", help="GitHub README cache JSON")
    parser.add_argument("--refresh-repos", action="store_true", help="refresh repository cache from GitHub")
    parser.add_argument("--refresh-readmes", action="store_true", help="refresh README cache from GitHub")
    parser.add_argument("--skip-readmes", action="store_true", help="do not fetch missing README files")
    parser.add_argument("--min-score", type=int, default=650, help="minimum semantic match score")
    parser.add_argument("--dry-run", action="store_true", help="print matches without rewriting the BibTeX file")
    parser.add_argument("--backup", action="store_true", help="write a .bak copy before modifying the BibTeX file")
    args = parser.parse_args()

    bib_path = Path(args.bib)
    text = bib_path.read_text(encoding="utf-8")
    raw_repos = load_or_fetch_repos(args.repo_cache, args.owner, args.refresh_repos)
    readmes = load_or_fetch_readmes(args.readme_cache, raw_repos, args.refresh_readmes, args.skip_readmes)
    repos = [repo_record(repo, readmes) for repo in raw_repos if repo.get("full_name", "").startswith(f"{args.owner}/")]

    updated, changes = update_bib_text(text, repos, args.min_score, args.dry_run)
    for change in changes:
        urls = ", ".join(change["urls"])
        print(f"{change['key']}: {urls}")
    if args.dry_run:
        print(f"Dry run: {len(changes)} entries would be updated.")
        return
    if args.backup:
        bib_path.with_suffix(bib_path.suffix + ".bak").write_text(text, encoding="utf-8")
    bib_path.write_text(updated, encoding="utf-8")
    print(f"Updated {bib_path} with {len(changes)} repository link field set(s).")


if __name__ == "__main__":
    main()
