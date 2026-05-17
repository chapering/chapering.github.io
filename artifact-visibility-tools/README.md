# Artifact Visibility Tools

Regenerates the artifact table for `chapering.github.io/_pages/software.html` without removing the original page content.

## What It Does

- Parses `pubs/hcaipub.bib` for papers with `url_repository` by default.
- Fetches public repositories under `https://github.com/baltsers`.
- Uses the validated central GitHub repository from `url_repository` as the artifact identity.
- Skips BibTeX entries without `url_repository`, and skips entries whose `url_repository` is not present under `https://github.com/baltsers`.
- Lists other linked artifacts from `url_figshare`, `url_alternative`, `url_backup`, `url_project`, `url_docker`, and `url_repo2`/`url_repo3`/... as alternative artifacts under the same central repository.
- Totals statistics across the central repository plus all alternative artifacts.
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

To use the older `url_project` grouping behavior explicitly:

```powershell
./artifact-visibility-tools/update_all.ps1 -IdentityBy url_project
```

The first step prints progress for each unique artifact URL. A full run can take a few minutes because public GitHub, Bitbucket, and Zenodo calls are made serially and retry/timeout on slow network responses.

By default, the collector skips per-repository GitHub API calls to avoid the unauthenticated GitHub rate limit. Central `baltsers` repository stars/forks/watchers/issues come from the fetched `baltsers_repos.json` cache instead. To opt back into public GitHub API calls for release downloads/open PR counts, run:

```powershell
./artifact-visibility-tools/update_all.ps1 -GitHubMode public-api
```

If you use `public-api`, setting `$env:GITHUB_TOKEN` first is strongly recommended.

## Add Repository URLs to BibTeX

This separate tool updates a BibTeX file in place by matching each paper title to repositories under `https://github.com/baltsers`. It writes the central repository into `url_repository`; if more than one central repo matches, it writes the remaining links as `url_repo2`, `url_repo3`, and so on. Entries with no match are left unchanged.

Dry run:

```powershell
./artifact-visibility-tools/update_bib_repositories.ps1 -BibPath pubs/hcaipub.bib -DryRun
```

Update the `.bib` file in place:

```powershell
./artifact-visibility-tools/update_bib_repositories.ps1 -BibPath pubs/hcaipub.bib
```

Refresh GitHub repository and README caches before matching:

```powershell
./artifact-visibility-tools/update_bib_repositories.ps1 -BibPath pubs/hcaipub.bib -RefreshRepos -RefreshReadmes
```

## Notes

- GitHub traffic views are not public through unauthenticated APIs, so GitHub-backed artifact views remain `N/A`.
- Figshare `/s/...` private/share links often do not expose public counters through the article API.
- The central artifact name is the validated `baltsers` repository name, not a heuristic slug.
