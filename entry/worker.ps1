# Start one background Claude job from a brief file (Windows PowerShell 5.1+ / PowerShell 7).
#
#   .\worker.ps1 -Brief C:\path\to\brief.md [-Name job1] [-Model sonnet] [-Effort medium]
#                [-ConfigDir C:\Users\me\.claude-second] [-Chrome] [-DryRun]
#
# -ConfigDir  use a different Claude account: the folder where that account is logged in
#             (it sets CLAUDE_CONFIG_DIR). Leave it out to use your normal account.
# -Chrome     the job needs the Claude in Chrome extension; that extension belongs to the
#             account signed in to it, and a setup-token in the environment would disable it.
# -DryRun     print the command instead of running it.
#
# Splitting work between two accounts is for spreading tasks over two quotas that you each
# own. It is not a way to carry on after one account hits its limit: do not wire this up as an
# automatic fallback.
param(
  [Parameter(Mandatory = $true)][string]$Brief,
  [string]$Name = "job",
  [string]$Model = "sonnet",
  [string]$Effort = "medium",
  [string]$ConfigDir = "",
  [switch]$Chrome,
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Brief)) { throw "Brief not found: $Brief" }

$sbk = if ($env:SBK_HOME) { $env:SBK_HOME } elseif ((-not (Test-Path (Join-Path $HOME ".sbk"))) -and (Test-Path (Join-Path $HOME ".claude\sbk"))) { Join-Path $HOME ".claude\sbk" } else { Join-Path $HOME ".sbk" }
$logDir = Join-Path $sbk "logs"
$log = Join-Path $logDir ("worker-" + $Name + ".log")
$prompt = "Read $Brief in full and carry it out to the end. Work autonomously."
$cliArgs = @("-p", "--model", $Model, "--effort", $Effort, "--permission-mode", "acceptEdits",
             "--name", $Name, "--output-format", "stream-json", "--verbose")
if ($Chrome) { $cliArgs += "--chrome" }
$cliArgs += @("--", $prompt)

if ($ConfigDir) { $env:CLAUDE_CONFIG_DIR = $ConfigDir }
# A token or key in the environment would override the login of the chosen account.
Remove-Item Env:CLAUDE_CODE_OAUTH_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

if ($DryRun) {
  Write-Output ("CLAUDE_CONFIG_DIR=" + $env:CLAUDE_CONFIG_DIR)
  Write-Output ("claude " + ($cliArgs -join " "))
  Write-Output ("log: " + $log)
  exit 0
}
New-Item -ItemType Directory -Force $logDir | Out-Null
& claude @cliArgs *> $log
exit $LASTEXITCODE
