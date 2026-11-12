# Build the RAGbase Shield .msi on the Windows build VM (packaging/DESIGN.md sections 7.1 and 13.3, W1 and W2).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\shield_pkg\b-<v>\build_msi.ps1 -Dir C:\shield_pkg\b-<v>
#
# <Dir> holds what packaging/windows/build.sh sent: payload.zip, payload.sha256, Package.wxs, Components.wxs,
# msi_vars.json. Output: <Dir>\out\RAGbase-Shield-<v>-win64.msi and <Dir>\logs\*.log.
#
# Build tools, user level, only under C:\shield_pkg (nothing in Program Files, no PATH change, no admin step):
# - .NET SDK (channel 8.0) from Microsoft's dotnet-install.ps1 into C:\shield_pkg\dotnet;
# - WiX Toolset as a dotnet tool, pinned version, into C:\shield_pkg\tools (WiX is MS-RL, never shipped).
# Their caches and settings are sent to C:\shield_pkg too (process environment only), and .NET telemetry is off.
param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [string]$WixVersion = "5.0.2",
  [string]$DotnetChannel = "8.0",
  [switch]$NoUnpack  # sign_TODO.ps1: build from the signed <Dir>\payload (its MANIFEST.json written again)
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = "C:\shield_pkg"

function Under-Root([string]$p) {
  $full = [IO.Path]::GetFullPath($p)
  if (-not $full.StartsWith("$Root\", [StringComparison]::OrdinalIgnoreCase)) { throw "outside $Root : $full" }
  return $full
}
function Run-Logged([string]$Log, [string]$Exe, [string[]]$Argv) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  "`$ $Exe $($Argv -join ' ')" | Out-File -Append -Encoding utf8 $Log
  & $Exe @Argv *>&1 | ForEach-Object { "$_" } | Out-File -Append -Encoding utf8 $Log
  $code = $LASTEXITCODE
  $ErrorActionPreference = $old
  return $code
}
function Say([string]$m) { $line = "build_msi: $m"; Write-Output $line; $line | Out-File -Append -Encoding utf8 $script:Summary }

$Dir = Under-Root $Dir
$logs = Join-Path $Dir "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
Get-ChildItem $logs -Filter *.log -ErrorAction SilentlyContinue | Remove-Item -Force  # one build, one set of logs
$script:Summary = Join-Path $logs "build_msi.log"
Set-Content -Encoding utf8 $script:Summary "build_msi.ps1 $(Get-Date -Format s) on $env:COMPUTERNAME as $env:USERNAME"

# Process environment of the build tools: everything under C:\shield_pkg, no telemetry, no first-run steps.
$env:DOTNET_ROOT = "$Root\dotnet"
$env:DOTNET_CLI_HOME = "$Root\dotnet_home"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = "1"
$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = "0"
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = "0"
$env:DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = "1"
$env:DOTNET_ROLL_FORWARD = "Major"
$env:NUGET_PACKAGES = "$Root\nuget\packages"
$env:NUGET_HTTP_CACHE_PATH = "$Root\nuget\http"
$env:NUGET_PLUGINS_CACHE_PATH = "$Root\nuget\plugins"
$env:APPDATA = "$Root\appdata"
$env:LOCALAPPDATA = "$Root\localappdata"
$env:TEMP = "$Root\tmp"
$env:TMP = "$Root\tmp"
foreach ($d in @($env:DOTNET_CLI_HOME, $env:NUGET_PACKAGES, $env:NUGET_HTTP_CACHE_PATH, $env:NUGET_PLUGINS_CACHE_PATH,
                 $env:APPDATA, $env:LOCALAPPDATA, $env:TEMP, "$Root\tools", "$Root\dl")) {
  New-Item -ItemType Directory -Force $d | Out-Null
}

# 1. .NET SDK, user level
$dotnet = "$Root\dotnet\dotnet.exe"
if (-not (Test-Path $dotnet)) {
  $dl = "$Root\dl\dotnet-install"
  New-Item -ItemType Directory -Force $dl | Out-Null
  $inst = Join-Path $dl "dotnet-install.ps1"
  Invoke-WebRequest -UseBasicParsing -Uri "https://dot.net/v1/dotnet-install.ps1" -OutFile $inst
  Say ("dotnet-install.ps1 downloaded, SHA-256 " + (Get-FileHash $inst -Algorithm SHA256).Hash)
  $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  & $inst -Channel $DotnetChannel -InstallDir "$Root\dotnet" -NoPath *>&1 | ForEach-Object { "$_" } |
    Out-File -Append -Encoding utf8 (Join-Path $logs "dotnet-install.log")
  $ErrorActionPreference = $old
  if (-not (Test-Path $dotnet)) { throw "dotnet-install.ps1 did not install $dotnet (see logs\dotnet-install.log)" }
}
$sdk = (& $dotnet --version) | Select-Object -Last 1
Say "dotnet SDK $sdk at $Root\dotnet (telemetry off)"

# 2. WiX, pinned, as a dotnet tool in C:\shield_pkg\tools
$wix = "$Root\tools\wix.exe"
if (-not (Test-Path $wix)) {
  $rc = Run-Logged (Join-Path $logs "wix-install.log") $dotnet @("tool", "install", "wix", "--version", $WixVersion,
                                                                 "--tool-path", "$Root\tools")
  if ($rc -ne 0) { throw "dotnet tool install wix failed ($rc), see logs\wix-install.log" }
}
$wixv = ((& $wix --version) | Select-Object -Last 1).Trim()
if (-not $wixv.StartsWith($WixVersion)) { throw "WiX $wixv found in $Root\tools, $WixVersion pinned" }
Say "WiX $wixv"

# 3. Payload: unpack, then check every file against the payload's own MANIFEST.json
$payload = Join-Path $Dir "payload"
if (-not $NoUnpack) {
  $zip = Join-Path $Dir "payload.zip"
  $want = ((Get-Content (Join-Path $Dir "payload.sha256") -Raw).Trim() -split "\s+")[0].ToUpper()
  $got = (Get-FileHash $zip -Algorithm SHA256).Hash
  if ($got -ne $want) { throw "payload.zip SHA-256 $got differs from the sent $want" }
  if (Test-Path $payload) { Remove-Item -Recurse -Force $payload }
  New-Item -ItemType Directory $payload | Out-Null
  $rc = Run-Logged (Join-Path $logs "unpack.log") "tar.exe" @("-xf", $zip, "-C", $payload)
  if ($rc -ne 0) { throw "tar -xf failed ($rc)" }
}
$manifest = Get-Content (Join-Path $payload "MANIFEST.json") -Raw | ConvertFrom-Json
$bad = 0; $n = 0
foreach ($p in $manifest.files.PSObject.Properties) {
  $n++
  $f = Join-Path $payload ($p.Name -replace "/", "\")
  if (-not (Test-Path -LiteralPath $f) -or (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLower() -ne $p.Value) { $bad++ }
}
$extra = (Get-ChildItem -Recurse -File $payload | Measure-Object).Count - $n - 1
if ($bad -or $extra) { throw "payload differs from MANIFEST.json ($bad changed or missing, $extra extra)" }
Say "payload ($(if ($NoUnpack) { 'kept, -NoUnpack' } else { 'payload.zip SHA-256 OK' })): $n files match MANIFEST.json"

# 4. wix build + ICE validation
$vars = Get-Content (Join-Path $Dir "msi_vars.json") -Raw | ConvertFrom-Json
$out = Join-Path $Dir "out"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory $out | Out-Null
$msi = Join-Path $out ("RAGbase-Shield-" + $vars.Version + "-win64.msi")
$t0 = Get-Date
$rc = Run-Logged (Join-Path $logs "wix-build.log") $wix @("build", "-arch", "x64", "-nologo",
  "-d", ("Version=" + $vars.Version), "-d", ("ProductCode=" + $vars.ProductCode),
  "-d", ("UpgradeCode=" + $vars.UpgradeCode), "-d", ("ShortcutGuid=" + $vars.ShortcutGuid),
  "-d", ("PayloadDir=" + $payload), "-o", $msi,
  (Join-Path $Dir "Package.wxs"), (Join-Path $Dir "Components.wxs"))
$secs = [int]((Get-Date) - $t0).TotalSeconds
if ($rc -ne 0 -or -not (Test-Path $msi)) {
  Get-Content (Join-Path $logs "wix-build.log") -Tail 40
  throw "wix build failed ($rc)"
}
$bw = @(Select-String -Path (Join-Path $logs "wix-build.log") -Pattern "warning WIX" -SimpleMatch).Count
Say "wix build OK in $secs s, $bw warning line(s): $msi"
$rc = Run-Logged (Join-Path $logs "wix-validate.log") $wix @("msi", "validate", "-nologo", $msi)
$ve = @(Select-String -Path (Join-Path $logs "wix-validate.log") -Pattern "error WIX").Count
$vw = @(Select-String -Path (Join-Path $logs "wix-validate.log") -Pattern "warning WIX").Count
Say "wix msi validate exit $rc : $ve error line(s), $vw warning line(s) (logs\wix-validate.log)"
$item = Get-Item $msi
Say ("msi " + $item.Name + " " + $item.Length + " bytes SHA-256 " + (Get-FileHash $msi -Algorithm SHA256).Hash)
if ($rc -ne 0) { exit 3 }
exit 0
