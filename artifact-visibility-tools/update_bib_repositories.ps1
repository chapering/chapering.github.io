param(
  [string]$BibPath = "pubs/hcaipub.bib",
  [string]$RepoCachePath = "baltsers_repos.json",
  [string]$ReadmeCachePath = "baltsers_repo_readmes.json",
  [string]$CentralGitHubOwner = "baltsers",
  [string]$Python = "python",
  [switch]$RefreshRepos,
  [switch]$RefreshReadmes,
  [switch]$SkipReadmes,
  [switch]$DryRun,
  [switch]$Backup
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "artifact-visibility-tools/add_repository_urls.py",
  $BibPath,
  "--owner", $CentralGitHubOwner,
  "--repo-cache", $RepoCachePath,
  "--readme-cache", $ReadmeCachePath
)

if ($RefreshRepos) { $argsList += "--refresh-repos" }
if ($RefreshReadmes) { $argsList += "--refresh-readmes" }
if ($SkipReadmes) { $argsList += "--skip-readmes" }
if ($DryRun) { $argsList += "--dry-run" }
if ($Backup) { $argsList += "--backup" }

& $Python @argsList
