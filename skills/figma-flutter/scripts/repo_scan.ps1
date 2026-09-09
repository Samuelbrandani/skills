# repo_scan.ps1 — Windows wrapper for repo_scan.py (PowerShell 5.1+ / pwsh).
# Usage:  .\scripts\repo_scan.ps1 [repo-root] [feature]
# Finds a Python 3 interpreter (py launcher, python3, python) and runs the
# cross-platform script; the profile printed is identical on every OS.
param(
    [string]$Root = ".",
    [string]$Feature = ""
)
$script = Join-Path $PSScriptRoot "repo_scan.py"
$candidates = @(
    @{ exe = "py";      args = @("-3", $script) },
    @{ exe = "python3"; args = @($script) },
    @{ exe = "python";  args = @($script) }
)
foreach ($c in $candidates) {
    if (Get-Command $c.exe -ErrorAction SilentlyContinue) {
        & $c.exe @($c.args + @($Root) + $(if ($Feature) { @($Feature) } else { @() }))
        exit $LASTEXITCODE
    }
}
Write-Error "repo_scan: Python 3 not found. Install it from python.org or the Microsoft Store, then rerun."
exit 1
