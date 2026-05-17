param(
  [string]$BibPath = "pubs/hcaipub.bib",
  [string]$SoftwarePath = "_pages/software.html",
  [string]$StatsPath = "artifact_stats.json",
  [string]$RepoCachePath = "baltsers_repos.json",
  [string]$GeneratedDataPath = "software_artifacts.generated.json",
  [string]$CentralGitHubOwner = "baltsers",
  [ValidateSet("url_repository", "url_project")]
  [string]$IdentityBy = "url_repository",
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "Collecting publication artifact stats..."
& $Python "artifact-visibility-tools/collect_artifact_stats.py" $BibPath $StatsPath

Write-Host "Fetching central GitHub repositories for $CentralGitHubOwner..."
$repos = @()
$page = 1
do {
  $url = "https://api.github.com/users/$CentralGitHubOwner/repos?per_page=100&page=$page"
  $batch = Invoke-RestMethod -Uri $url -Headers @{ "Accept" = "application/vnd.github+json"; "User-Agent" = "artifact-visibility-tools" }
  if ($batch.Count -gt 0) {
    $repos += $batch
    $page += 1
  }
} while ($batch.Count -eq 100)
$repos | ConvertTo-Json -Depth 8 | Set-Content -Path $RepoCachePath -Encoding UTF8

Write-Host "Appending/updating generated artifact table in $SoftwarePath..."
& $Python "artifact-visibility-tools/build_software_table.py" `
  --bib $BibPath `
  --stats $StatsPath `
  --repos $RepoCachePath `
  --input $SoftwarePath `
  --output $SoftwarePath `
  --generated $GeneratedDataPath `
  --identity-by $IdentityBy

Write-Host "Updated $SoftwarePath"
