# Artifact Visibility Tools

Regenerates the artifact table for `chapering.github.io/_pages/software.html` without removing the original page content.

## What It Does

- Parses `pubs/hcaipub.bib` for papers with `url_project`.
- Fetches public repositories under `https://github.com/baltsers`.
- Matches papers to central repos by exact repository description text such as `Artifact for: <paper title>`.
- Uses the validated central GitHub repository as the artifact identity; shared Figshare/project links stay as alternative artifacts.
- Appends or replaces only the block between:
  - `<!-- BEGIN AUTO-GENERATED ARTIFACT TABLE -->`
  - `<!-- END AUTO-GENERATED ARTIFACT TABLE -->`
- Keeps original software page content intact.
- Adds browser-side live refresh for GitHub stars/forks/release-downloads and Zenodo views/downloads.

## Run

From the root of `chapering.github.io`:

```powershell
./artifact-visibility-tools/update_all.ps1
```

Optional:

```powershell
./artifact-visibility-tools/update_all.ps1 -Python "C:\path\to\python.exe"
```

The first step prints progress for each unique artifact URL. A full run can take a few minutes because public GitHub, Bitbucket, and Zenodo calls are made serially and retry/timeout on slow network responses.

## Notes

- GitHub traffic views are not public through unauthenticated APIs, so GitHub-backed artifact views remain `N/A`.
- Figshare `/s/...` private/share links often do not expose public counters through the article API.
- The central artifact name is the validated `baltsers` repository name, not a heuristic slug.
