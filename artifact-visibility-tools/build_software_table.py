import base64
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse


START = "<!-- BEGIN AUTO-GENERATED ARTIFACT TABLE -->"
END = "<!-- END AUTO-GENERATED ARTIFACT TABLE -->"

CANONICAL_GITHUB_REPOS = {
    "Daybreak2019/PCA": "awen-li/PCA",
}

CENTRAL_REPO_ALIASES = {
    "baltsers/PyRTFuzz-demo": "baltsers/PyRTFuzz",
}

KNOWN_GITHUB_ALTERNATIVES = {
    "baltsers/PyRTFuzz": ["awen-li/PyRTFuzz"],
    "baltsers/polycruise": ["awen-li/PolyCruise"],
    "baltsers/PolyFuzz": ["awen-li/PolyFuzz"],
    "baltsers/PCA-tool": ["awen-li/PCA"],
    "baltsers/PolyFax": ["awen-li/PolyFax"],
}

KNOWN_FALLBACK_GITHUB_ARTIFACTS = {
    "PolyCruise: A Cross-Language Dynamic Information Flow Analysis": {
        "name": "PolyCruise",
        "full_name": "baltsers/polycruise",
        "html_url": "https://github.com/baltsers/polycruise",
        "description": "Artifact for: PolyCruise: A Cross-Language Dynamic Information Flow Analysis",
        "stars": 0,
        "forks": 0,
        "watchers": 0,
        "issues": 0,
    },
}

KNOWN_GITHUB_STATS = {
    "awen-li/PyRTFuzz": {"stars": 19, "watchers": 5, "forks": 2, "open_issues": 0, "open_prs": 0, "downloads": 0},
    "awen-li/PolyCruise": {"stars": 30, "watchers": 2, "forks": 5, "open_issues": 0, "open_prs": 2, "downloads": 0},
    "awen-li/PolyFuzz": {"stars": 27, "watchers": 3, "forks": 3, "open_issues": 1, "open_prs": 0, "downloads": 0},
    "awen-li/PCA": {"stars": 20, "watchers": 1, "forks": 7, "open_issues": 1, "open_prs": 0, "downloads": 0},
    "awen-li/PolyFax": {"stars": 1, "watchers": 1, "forks": 0, "open_issues": 0, "open_prs": 0, "downloads": 0},
}


def clean_tex(value):
    if not value:
        return ""
    value = value.replace("\\`{e}", "è").replace("\\'{e}", "é")
    value = re.sub(r"\\[{}]", "", value)
    value = re.sub(r"[{}]", "", value)
    value = value.replace("$^2$", "2")
    return re.sub(r"\s+", " ", value).strip()


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
    text = Path(path).read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(r"@\w+\s*\{", text)]
    starts.append(len(text))
    rows = []
    for i in range(len(starts) - 1):
        block = text[starts[i] : starts[i + 1]]
        key = re.search(r"@\w+\s*\{\s*([^,]+),", block, re.S)
        row = {"key": key.group(1) if key else None}
        for field in [
            "title",
            "author",
            "year",
            "booktitle",
            "journal",
            "url_project",
            "doi",
            "note",
        ]:
            row[field] = clean_tex(extract_field(block, field))
        if row.get("url_project"):
            rows.append(row)
    return rows


def normalize_url(url):
    if not url:
        return ""
    u = url.strip().removesuffix(".git").rstrip("/")
    u = re.sub(r"/overview$", "", u)
    u = re.sub(r"/src/master$", "", u)
    return u


def artifact_key(url):
    u = normalize_url(url)
    # Canonicalize known equivalent URLs by repository/homepage.
    replacements = {
        "https://bitbucket.org/wsucailab/iterative-taint-analysis/src/v1.0-Evotaint": "https://bitbucket.org/wsucailab/iterative-taint-analysis",
        "https://bitbucket.org/wsucailab/d2abs": "https://bitbucket.org/wsucailab/d2abs",
        "https://bitbucket.org/wsucailab/d2abs/src/master": "https://bitbucket.org/wsucailab/d2abs",
        "https://github.com/Daybreak2019/PCA": "https://github.com/awen-li/PCA",
        "https://bitbucket.org/wsucailab/icc-visualizer-with-graphstream/src/master": "https://bitbucket.org/wsucailab/icc-visualizer-with-graphstream",
    }
    return replacements.get(u, u)


def venue_abbrev(row):
    venue = row.get("booktitle") or row.get("journal") or ""
    if not venue:
        return ""
    known = [
        ("Foundations of Software Engineering", "ACM FSE"),
        ("International Conference on Software Engineering", "IEEE/ACM ICSE"),
        ("Symposium on Software Testing and Analysis", "ACM ISSTA"),
        ("IEEE Symposium on Security and Privacy", "IEEE S&P"),
        ("USENIX Security", "USENIX Security"),
        ("Computer and Communications Security", "ACM CCS"),
        ("The Web Conference", "WWW"),
        ("Network and Distributed System Security Symposium", "NDSS"),
        ("Software Analysis, Evolution, and Reengineering", "SANER"),
        ("Mobile Software Engineering and Systems", "MobileSoft"),
        ("Software Security and Reliability", "SERE"),
        ("Source Code Analysis and Manipulation", "SCAM"),
        ("Software Quality, Reliability, and Security", "QRS"),
        ("International Symposium on Visual Computing", "ISVC"),
        ("Software Engineering for Adaptive and Self-Managing Systems", "SEAMS"),
        ("Mining Software Repositories", "MSR"),
        ("Software Engineering in Society", "ICSE-SEIS"),
        ("Transactions on Software Engineering and Methodology", "ACM TOSEM"),
        ("ACM Computing Surveys", "ACM CSUR"),
        ("IEEE Transactions on Software Engineering", "IEEE TSE"),
        ("IEEE Transactions on Information Forensics and Security", "IEEE TIFS"),
        ("IEEE Transactions on Dependable and Secure Computing", "IEEE TDSC"),
        ("Journal of Systems and Software", "JSS"),
        ("IEEE Transactions on Reliability", "IEEE TR"),
        ("Information and Software Technology", "IST"),
        ("IEEE Transactions on Mobile Computing", "IEEE TMC"),
        ("IEEE Transactions on Parallel and Distributed Systems", "IEEE TPDS"),
        ("IEEE Transactions on Visualization and Computer Graphics", "IEEE TVCG"),
        ("International Journal of Image and Graphics", "IJIG"),
        ("Journal of Computer Science and Technology", "JCST"),
    ]
    for needle, abbr in known:
        if needle.lower() in venue.lower():
            return abbr
    m = re.search(r"\(([^()]{2,40})\)", venue)
    return m.group(1) if m else venue


def paper_info(row):
    authors = clean_tex(row.get("author", "")).replace(" and ", ", ")
    title = row.get("title", "")
    venue = venue_abbrev(row)
    year = row.get("year", "")
    doi = row.get("doi", "")
    text = f"{authors}. \"{title}.\" {venue}, {year}."
    if doi:
        text += f" doi:{doi}"
    return text


def badges(row):
    note = row.get("note", "")
    return [b for b in ["Available", "Functional", "Reusable", "Reproduced"] if b in note]


def load_baltsers(path):
    repos = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for repo in repos:
        desc = clean_tex(repo.get("description") or "")
        out.append(
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "description": desc,
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "watchers": repo.get("watchers_count", 0),
                "issues": repo.get("open_issues_count", 0),
            }
        )
    return out


def find_central_repo(row, repos):
    title = row["title"].lower()
    exact = [r for r in repos if title and title in r["description"].lower()]
    if exact:
        return exact[0]
    return None


def parse_platform(url):
    host = urlparse(url).netloc.lower()
    if "figshare.com" in host:
        return "Figshare"
    if "zenodo.org" in host:
        return "Zenodo"
    if "github.com" in host:
        return "GitHub"
    if "bitbucket.org" in host:
        return "Bitbucket"
    if "chapering.github.io" in host:
        return "Project page"
    if "sites.google.com" in host:
        return "Google Sites"
    if "doi.org" in host:
        return "DOI"
    return host or "Artifact"


def parse_github_repo(url):
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", normalize_url(url))
    if not m:
        return None
    return canonical_github_repo(f"{m.group(1)}/{m.group(2)}")


def canonical_github_repo(repo):
    return CANONICAL_GITHUB_REPOS.get(repo, repo)


def merge_metric(current, value):
    if value in (None, "N/A", ""):
        return current
    if current in (None, "N/A", ""):
        return value
    try:
        return max(int(current), int(value))
    except (TypeError, ValueError):
        return current


def numeric_metric(value):
    if value in (None, "N/A", ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def add_source_metric(stats, field, value):
    value = numeric_metric(value)
    if value is None:
        return
    stats[field] = max(int(stats.get(field, 0) or 0), value)


def build_artifacts(bib_rows, stats_rows, repos):
    stats_by_key = {r["key"]: r for r in stats_rows}
    repos_by_full_name = {r["full_name"]: r for r in repos}
    artifacts = {}

    groups = {}
    for row in bib_rows:
        groups.setdefault(artifact_key(row["url_project"]), []).append(row)

    def choose_repo(matches):
        # If multiple central repos mention papers that share the same artifact URL,
        # prefer the latest paper's repo and avoid import-like names when possible.
        def score(item):
            repo, paper = item
            try:
                year = int(paper.get("year") or 0)
            except ValueError:
                year = 0
            friendly = 0 if repo["name"].lower().startswith("wsucailab-") else 1
            return (year, friendly, -len(repo["name"]))
        return sorted(matches, key=score, reverse=True)[0][0]

    def fallback_match(row):
        return KNOWN_FALLBACK_GITHUB_ARTIFACTS.get(row["title"])

    def add_github_repo(art, repo_full_name, url=None, as_alternative=True):
        repo_full_name = canonical_github_repo(repo_full_name)
        if repo_full_name not in art["githubRepos"]:
            art["githubRepos"].append(repo_full_name)
        url = url or f"https://github.com/{repo_full_name}"
        if as_alternative and url.rstrip("/") != art["centralUrl"].rstrip("/"):
            art["alternativeArtifacts"][url] = "GitHub"

    for group_key, group_rows in groups.items():
        matches = []
        seen = set()
        for row in group_rows:
            repo = find_central_repo(row, repos)
            if repo and repo["full_name"] not in seen:
                matches.append((repo, row))
                seen.add(repo["full_name"])
        if not matches:
            for row in group_rows:
                repo = fallback_match(row)
                if repo:
                    matches.append((repo, row))
                    break
        if not matches:
            continue
        chosen_repo = choose_repo(matches)
        canonical_name = CENTRAL_REPO_ALIASES.get(chosen_repo["full_name"], chosen_repo["full_name"])
        repo = repos_by_full_name.get(canonical_name, chosen_repo)
        key = repo["full_name"]
        if key not in artifacts:
            artifacts[key] = {
                "id": re.sub(r"[^a-z0-9]+", "-", repo["name"].lower()).strip("-"),
                "name": repo["name"],
                "centralRepo": repo["full_name"],
                "githubRepos": [repo["full_name"]],
                "centralUrl": repo["html_url"],
                "cached": {
                    "views": "N/A",
                    "downloads": "N/A",
                    "stars": repo["stars"],
                    "forks": repo["forks"],
                    "watchers": repo.get("watchers", 0),
                    "open_issues": repo.get("issues", 0),
                    "open_prs": "N/A",
                },
                "alternativeArtifacts": {},
                "badges": [],
                "papers": [],
            }
        art = artifacts[key]
        for matched_repo, _ in matches:
            add_github_repo(
                art,
                matched_repo["full_name"],
                matched_repo["html_url"],
                as_alternative=matched_repo["full_name"] != art["centralRepo"],
            )

        for row in group_rows:
            alt = normalize_url(row["url_project"])
            gh_alt = parse_github_repo(alt)
            if gh_alt:
                alt = f"https://github.com/{gh_alt}"
            if alt and alt != art["centralUrl"].rstrip("/"):
                art["alternativeArtifacts"][alt] = parse_platform(alt)
            if gh_alt and gh_alt not in art["githubRepos"]:
                add_github_repo(art, gh_alt, f"https://github.com/{gh_alt}")
            for b in badges(row):
                if b not in art["badges"]:
                    art["badges"].append(b)
            info = paper_info(row)
            if info not in art["papers"]:
                art["papers"].append(info)
            stat = stats_by_key.get(row["key"], {})
            for field in ["views", "downloads", "stars", "forks"]:
                value = stat.get(field)
                if value not in (None, "N/A"):
                    art["cached"][field] = merge_metric(art["cached"][field], value)

    repo_stats = {}
    for repo in repos:
        repo_stats[canonical_github_repo(repo["full_name"])] = {
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "watchers": repo.get("watchers", 0),
            "open_issues": repo.get("issues", 0),
            "open_prs": "N/A",
            "downloads": 0,
        }
    url_stats = {}
    for row in stats_rows:
        artifact_url = row.get("artifact", "") or row.get("project_link", "")
        repo = parse_github_repo(artifact_url)
        if not repo:
            source = artifact_key(artifact_url)
            existing = url_stats.setdefault(source, {})
            for field in ["views", "downloads", "stars", "watchers", "forks", "open_issues", "open_prs"]:
                add_source_metric(existing, field, row.get(field))
            continue
        existing = repo_stats.setdefault(repo, {})
        for field in ["stars", "watchers", "forks", "open_issues", "open_prs", "downloads"]:
            add_source_metric(existing, field, row.get(field))
    for repo, stats in KNOWN_GITHUB_STATS.items():
        existing = repo_stats.setdefault(repo, {})
        for field, value in stats.items():
            add_source_metric(existing, field, value)

    for art in artifacts.values():
        for repo in KNOWN_GITHUB_ALTERNATIVES.get(art["centralRepo"], []):
            add_github_repo(art, repo, f"https://github.com/{repo}")
        if not art["centralRepo"].startswith("baltsers/"):
            art["alternativeArtifacts"][art["centralUrl"]] = "GitHub"
        unique_repos = []
        for repo in art["githubRepos"]:
            repo = canonical_github_repo(repo)
            if repo not in unique_repos:
                unique_repos.append(repo)
        art["githubRepos"] = unique_repos
        totals = {}
        for field in ["views", "downloads", "stars", "watchers", "forks", "open_issues", "open_prs"]:
            totals[field] = {"value": 0, "seen": False}
        non_github_totals = {field: {"value": 0, "seen": False} for field in totals}

        for repo in art["githubRepos"]:
            for field, value in repo_stats.get(repo, {}).items():
                value = numeric_metric(value)
                if value is None:
                    continue
                totals.setdefault(field, {"value": 0, "seen": False})
                totals[field]["value"] += value
                totals[field]["seen"] = True

        for url in art["alternativeArtifacts"]:
            if parse_github_repo(url):
                continue
            for field, value in url_stats.get(artifact_key(url), {}).items():
                value = numeric_metric(value)
                if value is None:
                    continue
                totals.setdefault(field, {"value": 0, "seen": False})
                totals[field]["value"] += value
                totals[field]["seen"] = True
                non_github_totals.setdefault(field, {"value": 0, "seen": False})
                non_github_totals[field]["value"] += value
                non_github_totals[field]["seen"] = True

        for field, total in totals.items():
            if total["seen"]:
                art["cached"][field] = total["value"]
        art["cachedNonGithub"] = {
            field: total["value"]
            for field, total in non_github_totals.items()
            if total["seen"]
        }

        # Keep host-level download/view totals, such as Zenodo, instead of
        # replacing them with zero release downloads from GitHub mirrors.
        for field in ["views", "downloads"]:
            host_total = {"value": 0, "seen": False}
            for url in art["alternativeArtifacts"]:
                if parse_github_repo(url):
                    continue
                value = url_stats.get(artifact_key(url), {}).get(field)
                value = numeric_metric(value)
                if value is None:
                    continue
                host_total["value"] += value
                host_total["seen"] = True
            if host_total["seen"]:
                art["cached"][field] = host_total["value"]

        for field in ["stars", "forks", "watchers", "open_issues", "open_prs"]:
            total = 0
            seen_value = False
            for repo in art["githubRepos"]:
                value = repo_stats.get(repo, {}).get(field)
                value = numeric_metric(value)
                if value is None:
                    continue
                total += value
                seen_value = True
            for url in art["alternativeArtifacts"]:
                if parse_github_repo(url):
                    continue
                value = url_stats.get(artifact_key(url), {}).get(field)
                value = numeric_metric(value)
                if value is None:
                    continue
                total += value
                seen_value = True
            if seen_value:
                art["cached"][field] = total
        if art["cached"].get("downloads") in (None, "N/A", ""):
            total = 0
            seen_value = False
            for repo in art["githubRepos"]:
                value = repo_stats.get(repo, {}).get("downloads")
                if value not in (None, "N/A", ""):
                    total += int(value)
                    seen_value = True
            if seen_value:
                art["cached"]["downloads"] = total

    return sorted(artifacts.values(), key=lambda a: a["name"].lower())


def render_table(artifacts):
    data = json.dumps(artifacts).replace("</", "<\\/")
    rows = []
    for art in artifacts:
        alt_links = []
        for url, label in sorted(art["alternativeArtifacts"].items(), key=lambda x: (x[1], x[0])):
            alt_links.append(f'<a href="{html.escape(url)}">{html.escape(label)}</a>')
        badge_html = " ".join(f'<span class="artifact-badge">{html.escape(b)}</span>' for b in art["badges"]) or "N/A"
        paper_html = "".join(f"<li>{html.escape(p)}</li>" for p in art["papers"])
        rows.append(
            f'''<tr data-artifact-id="{html.escape(art["id"])}">
  <td data-sort="artifact"><a class="artifact-name" href="{html.escape(art["centralUrl"])}">{html.escape(art["name"])}</a></td>
  <td data-sort="badges">{badge_html}</td>
  <td data-sort="alternatives">{", ".join(alt_links) if alt_links else "N/A"}</td>
  <td class="metric" data-sort="views" data-stat="views">{html.escape(str(art["cached"]["views"]))}</td>
  <td class="metric" data-sort="downloads" data-stat="downloads">{html.escape(str(art["cached"]["downloads"]))}</td>
  <td class="metric" data-sort="stars" data-stat="stars">{html.escape(str(art["cached"]["stars"]))}</td>
  <td class="metric" data-sort="forks" data-stat="forks">{html.escape(str(art["cached"]["forks"]))}</td>
  <td class="metric" data-sort="watchers" data-stat="watchers">{html.escape(str(art["cached"].get("watchers", "N/A")))}</td>
  <td class="metric" data-sort="open_issues" data-stat="open_issues">{html.escape(str(art["cached"].get("open_issues", "N/A")))}</td>
  <td class="metric" data-sort="open_prs" data-stat="open_prs">{html.escape(str(art["cached"].get("open_prs", "N/A")))}</td>
  <td data-sort="papers"><ul class="artifact-papers">{paper_html}</ul></td>
</tr>'''
        )

    return f'''{START}
<style>
.artifact-tools-wrap {{ margin-top: 2rem; }}
.artifact-tools-meta {{ color: #5f6671; font-size: 0.9rem; line-height: 1.45; margin-bottom: 0.9rem; }}
.artifact-table-scroll {{ border: 1px solid #d9dee7; border-radius: 8px; box-shadow: 0 8px 22px rgba(20, 35, 55, 0.08); overflow-x: auto; }}
.artifact-tools-table {{ border-collapse: separate; border-spacing: 0; width: 100%; font-size: 0.86rem; background: #fff; }}
.artifact-tools-table th, .artifact-tools-table td {{ border-bottom: 1px solid #e5e9f0; padding: 0.55rem 0.62rem; vertical-align: top; }}
.artifact-tools-table th {{ background: #f6f8fb; color: #253044; font-weight: 700; position: sticky; top: 0; z-index: 1; }}
.artifact-tools-table tbody tr:nth-child(even) {{ background: #fbfcfe; }}
.artifact-tools-table tbody tr:hover {{ background: #f2f7ff; }}
.artifact-tools-table td.metric, .artifact-tools-table th.metric {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.artifact-tools-table .artifact-name {{ color: #1f5f9f; font-weight: 700; }}
.artifact-tools-table .artifact-badge {{ display: inline-block; border: 1px solid #b6c6e6; border-radius: 999px; padding: 0.08rem 0.42rem; margin: 0.08rem; font-size: 0.75rem; background: #eef4ff; color: #28446c; }}
.artifact-tools-table .artifact-papers {{ margin: 0; padding-left: 1.1rem; }}
.artifact-tools-table .artifact-papers li {{ margin-bottom: 0.25rem; }}
.artifact-sort-button {{ align-items: center; background: transparent; border: 0; color: inherit; cursor: pointer; display: inline-flex; font: inherit; font-weight: 700; gap: 0.32rem; justify-content: inherit; margin: 0; padding: 0; text-align: inherit; width: 100%; }}
.artifact-sort-button:hover {{ color: #1f5f9f; }}
.artifact-sort-indicator {{ color: #667085; font-size: 0.68rem; min-width: 2.1rem; text-transform: uppercase; }}
.artifact-sort-button[aria-pressed="true"] .artifact-sort-indicator {{ color: #1f5f9f; }}
@media (max-width: 900px) {{ .artifact-table-scroll {{ border-radius: 6px; }} }}
</style>
<div class="artifact-tools-wrap" id="artifact-tools">
<h2>Artifact Index</h2>
<p class="artifact-tools-meta">Artifact links point to validated GitHub repositories, preferring the <a href="https://github.com/baltsers">baltsers</a> mirror when one is available. Public counters refresh in the browser when GitHub/Zenodo APIs are reachable. GitHub traffic views are not publicly exposed, so repository views remain N/A unless an alternative artifact host exposes views.</p>
<div class="artifact-table-scroll">
<table class="artifact-tools-table">
  <thead>
    <tr>
      <th scope="col"><button class="artifact-sort-button" type="button" data-sort-key="artifact" data-sort-type="text">Artifact <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col"><button class="artifact-sort-button" type="button" data-sort-key="badges" data-sort-type="text">Badges <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col"><button class="artifact-sort-button" type="button" data-sort-key="alternatives" data-sort-type="text">Alternative artifacts <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="views" data-sort-type="number">#Views <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="downloads" data-sort-type="number">#Downloads <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="stars" data-sort-type="number">#Stars <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="forks" data-sort-type="number">#Forks <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="watchers" data-sort-type="number">#Watchers <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="open_issues" data-sort-type="number">#Open Issues <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col" class="metric"><button class="artifact-sort-button" type="button" data-sort-key="open_prs" data-sort-type="number">#Open PRs <span class="artifact-sort-indicator"></span></button></th>
      <th scope="col"><button class="artifact-sort-button" type="button" data-sort-key="papers" data-sort-type="text">Associated papers <span class="artifact-sort-indicator"></span></button></th>
    </tr>
  </thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>
</div>
</div>
<script>window.LAB_ARTIFACTS = {data};</script>
<script>
(function () {{
  const fmt = value => (value === null || value === undefined || value === "" ? "N/A" : String(value));
  const isKnownNumber = value => Number.isFinite(Number(value));
  const sumKnown = values => {{
    const nums = values.map(Number).filter(Number.isFinite);
    return nums.length ? nums.reduce((a, b) => a + b, 0) : "N/A";
  }};
  const sumNumbers = values => sumKnown(values);
  const addNumbers = (a, b) => sumKnown([a, b]);
  const sortState = {{ key: null, type: null, direction: null }};
  let sortRefreshTimer = null;

  function sortValue(row, key, type) {{
    const el = row.querySelector('[data-sort="' + key + '"]');
    const raw = el ? el.textContent.trim() : "";
    if (type === "number") {{
      const value = Number(raw.replace(/,/g, ""));
      return {{ known: Number.isFinite(value), value }};
    }}
    return {{ known: true, value: raw.toLowerCase() }};
  }}

  function artifactName(row) {{
    const el = row.querySelector('[data-sort="artifact"]');
    return el ? el.textContent.trim().toLowerCase() : "";
  }}

  function compareRows(a, b, key, type, direction) {{
    const av = sortValue(a, key, type);
    const bv = sortValue(b, key, type);
    if (type === "number") {{
      if (av.known !== bv.known) return av.known ? -1 : 1;
      const delta = av.value - bv.value;
      if (delta !== 0) return direction === "asc" ? delta : -delta;
      return artifactName(a).localeCompare(artifactName(b));
    }}
    const delta = av.value.localeCompare(bv.value);
    if (delta !== 0) return direction === "asc" ? delta : -delta;
    return artifactName(a).localeCompare(artifactName(b));
  }}

  function updateSortButtons(key, direction) {{
    document.querySelectorAll("#artifact-tools .artifact-sort-button").forEach(button => {{
      const active = button.dataset.sortKey === key;
      button.setAttribute("aria-pressed", active ? "true" : "false");
      const indicator = button.querySelector(".artifact-sort-indicator");
      if (indicator) indicator.textContent = active ? direction : "";
      const th = button.closest("th");
      if (th) th.setAttribute("aria-sort", active ? (direction === "asc" ? "ascending" : "descending") : "none");
    }});
  }}

  function sortTable(key, type, direction) {{
    const tbody = document.querySelector("#artifact-tools tbody");
    if (!tbody) return;
    Array.from(tbody.querySelectorAll("tr"))
      .sort((a, b) => compareRows(a, b, key, type, direction))
      .forEach(row => tbody.appendChild(row));
    sortState.key = key;
    sortState.type = type;
    sortState.direction = direction;
    updateSortButtons(key, direction);
  }}

  function scheduleCurrentSort() {{
    if (!sortState.key) return;
    window.clearTimeout(sortRefreshTimer);
    sortRefreshTimer = window.setTimeout(() => sortTable(sortState.key, sortState.type, sortState.direction), 80);
  }}

  function setupSorting() {{
    document.querySelectorAll("#artifact-tools .artifact-sort-button").forEach(button => {{
      button.addEventListener("click", () => {{
        const key = button.dataset.sortKey;
        const type = button.dataset.sortType || "text";
        const sameColumn = sortState.key === key;
        const direction = sameColumn
          ? (sortState.direction === "asc" ? "desc" : "asc")
          : (type === "number" ? "desc" : "asc");
        sortTable(key, type, direction);
      }});
    }});
  }}

  async function getJSON(url) {{
    const res = await fetch(url, {{ headers: {{ "Accept": "application/json" }} }});
    if (!res.ok) throw new Error(res.status + " " + url);
    return res.json();
  }}
  async function githubStats(repo) {{
    const info = await getJSON("https://api.github.com/repos/" + repo);
    let downloads = 0;
    try {{
      const releases = await getJSON("https://api.github.com/repos/" + repo + "/releases?per_page=100");
      downloads = releases.reduce((total, rel) => total + (rel.assets || []).reduce((n, a) => n + (a.download_count || 0), 0), 0);
    }} catch (_) {{}}
    let openIssues = null;
    let openPRs = null;
    try {{
      const issues = await getJSON("https://api.github.com/search/issues?q=" + encodeURIComponent("repo:" + repo + " type:issue state:open"));
      openIssues = issues.total_count;
      const prs = await getJSON("https://api.github.com/search/issues?q=" + encodeURIComponent("repo:" + repo + " type:pr state:open"));
      openPRs = prs.total_count;
    }} catch (_) {{}}
    return {{ stars: info.stargazers_count, forks: info.forks_count, watchers: info.subscribers_count, open_issues: openIssues, open_prs: openPRs, downloads }};
  }}
  async function zenodoStats(urls) {{
    const ids = (urls || []).map(u => (u.match(/zenodo\\.org\\/(?:record|records)\\/(\\d+)/) || [])[1]).filter(Boolean);
    const rows = await Promise.all(ids.map(async id => {{
      try {{ return (await getJSON("https://zenodo.org/api/records/" + id)).stats || {{}}; }} catch (_) {{ return null; }}
    }}));
    const ok = rows.filter(Boolean);
    return {{ views: sumNumbers(ok.map(r => r.views)), downloads: sumNumbers(ok.map(r => r.downloads)) }};
  }}
  function setCell(id, key, value) {{
    const el = document.querySelector('[data-artifact-id="' + id + '"] [data-stat="' + key + '"]');
    if (el) el.textContent = fmt(value);
  }}
  function setCellIfKnown(id, key, value) {{
    if (isKnownNumber(value)) setCell(id, key, value);
  }}
  document.addEventListener("DOMContentLoaded", function () {{
    setupSorting();
    (window.LAB_ARTIFACTS || []).forEach(async artifact => {{
      try {{
        const repos = artifact.githubRepos || [artifact.centralRepo];
        const [gh, zen] = await Promise.all([
          Promise.all(repos.map(repo => githubStats(repo).catch(() => null))),
          zenodoStats(Object.keys(artifact.alternativeArtifacts || {{}}))
        ]);
        const githubRows = gh.filter(Boolean);
        const allGithubOK = githubRows.length === repos.length;
        const nonGithub = artifact.cachedNonGithub || {{}};
        const ghDownloads = allGithubOK ? sumNumbers(githubRows.map(r => r.downloads)) : "N/A";
        if (allGithubOK) {{
          setCellIfKnown(artifact.id, "stars", addNumbers(nonGithub.stars, sumNumbers(githubRows.map(r => r.stars))));
          setCellIfKnown(artifact.id, "forks", addNumbers(nonGithub.forks, sumNumbers(githubRows.map(r => r.forks))));
          setCellIfKnown(artifact.id, "watchers", addNumbers(nonGithub.watchers, sumNumbers(githubRows.map(r => r.watchers))));
          setCellIfKnown(artifact.id, "open_issues", addNumbers(nonGithub.open_issues, sumNumbers(githubRows.map(r => r.open_issues))));
          setCellIfKnown(artifact.id, "open_prs", addNumbers(nonGithub.open_prs, sumNumbers(githubRows.map(r => r.open_prs))));
        }}
        if (zen.views !== "N/A") setCell(artifact.id, "views", zen.views);
        const nonGithubDownloads = zen.downloads !== "N/A" ? zen.downloads : nonGithub.downloads;
        setCellIfKnown(artifact.id, "downloads", sumKnown([nonGithubDownloads, ghDownloads]));
        scheduleCurrentSort();
      }} catch (_) {{}}
    }});
  }});
}})();
</script>
{END}'''


def append_or_replace(original, table):
    if START in original and END in original:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: table, original, flags=re.S)
    statcounter = re.search(r"\n<script type=\"text/javascript\">\s*var sc_project=", original)
    if statcounter:
        return original[: statcounter.start()] + "\n\n" + table + "\n" + original[statcounter.start() :]
    return original.rstrip() + "\n\n" + table + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bib", default="hcaipub.bib")
    parser.add_argument("--stats", default="artifact_stats.json")
    parser.add_argument("--repos", default="baltsers_repos.json")
    parser.add_argument("--input", default="software.original.html")
    parser.add_argument("--output", default="software.html")
    parser.add_argument("--generated", default="software_artifacts.generated.json")
    args = parser.parse_args()

    bib = parse_bib(args.bib)
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))["rows"]
    repos = load_baltsers(args.repos)
    artifacts = build_artifacts(bib, stats, repos)
    table = render_table(artifacts)
    original = Path(args.input).read_text(encoding="utf-8")
    updated = append_or_replace(original, table)
    Path(args.output).write_text(updated, encoding="utf-8")
    Path(args.generated).write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
    print(json.dumps({"artifacts": len(artifacts), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
