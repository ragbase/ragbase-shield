# Optional check W10: the .msi installs and starts with a standard-user token (no administrator right at all).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\shield_pkg\t-<stamp>\test_basic_user.ps1 `
#     -Msi C:\shield_pkg\b-<v>\out\RAGbase-Shield-<v>-win64.msi -Work C:\shield_pkg\t-<stamp>
#
# The SSH account of the build VM is an administrator, so test_install.ps1 runs msiexec with an elevated token.
# Here msiexec runs under "runas /trustlevel:0x20000" (Basic User: the Administrators group is deny-only, no
# privilege, medium integrity), as a lawyer without admin rights would run it. Checks: exit status 0 in the msiexec
# log, the AdminUser and Privileged properties absent, the product registered for this user, Shield Desk answers.
# Then the product is removed with msiexec /x (data folder, Run key and folders that did not exist before are put
# back as they were). Same refusal rule as test_install.ps1: it does not run over an existing install.
param(
  [Parameter(Mandatory = $true)][string]$Msi,
  [Parameter(Mandatory = $true)][string]$Work,
  [int]$Port = 7878
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Root = "C:\shield_pkg"
foreach ($p in @($Msi, $Work)) {
  $full = [IO.Path]::GetFullPath($p)
  if (-not $full.StartsWith("$Root\", [StringComparison]::OrdinalIgnoreCase)) { throw "outside $Root : $full" }
}
$logs = Join-Path $Work "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$LogFile = Join-Path $logs "test_basic_user.log"
Set-Content -Encoding utf8 $LogFile ""
$App = Join-Path $env:LOCALAPPDATA "Programs\RAGbase Shield"
$Programs = Join-Path $env:LOCALAPPDATA "Programs"
$Data = Join-Path $env:LOCALAPPDATA "ragbase-shield"
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$script:Pass = 0; $script:Fail = 0
function Log([string]$m) { [Console]::Out.WriteLine($m); Add-Content -Encoding utf8 -LiteralPath $LogFile -Value $m }
function Check([string]$id, [bool]$ok, [string]$what, [string]$detail = "") {
  if ($ok) { $script:Pass++; $s = "PASS" } else { $script:Fail++; $s = "FAIL" }
  $tail = ""; if ($detail) { $tail = " : $detail" }
  Log ("{0,-5} {1,-6} {2}{3}" -f $s, $id, $what, $tail)
}
function Read-MsiLog([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return "" }
  $fs = [IO.File]::Open($p, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
  try { $ms = New-Object IO.MemoryStream; $fs.CopyTo($ms); $b = $ms.ToArray() } finally { $fs.Close() }
  if ($b.Length -ge 2 -and $b[0] -eq 0xFF -and $b[1] -eq 0xFE) { return [Text.Encoding]::Unicode.GetString($b) }
  return [Text.Encoding]::Default.GetString($b)
}
function Run-Value { try { return [string](Get-ItemProperty -LiteralPath $RunKey -Name "RAGbase Shield" -ErrorAction Stop)."RAGbase Shield" } catch { return $null } }
$WI = New-Object -ComObject WindowsInstaller.Installer
function WI-Get($obj, [string]$name, [object[]]$argv) { return $obj.GetType().InvokeMember($name, [Reflection.BindingFlags]::GetProperty, $null, $obj, $argv) }
function Product-State([string]$code) { try { return [int](WI-Get $WI "ProductState" @($code)) } catch { return -99 } }
$vars = Get-Content (Join-Path (Split-Path (Split-Path $Msi)) "msi_vars.json") -Raw | ConvertFrom-Json
$code = [string]$vars.ProductCode

$pre = @{ data = Test-Path $Data; programs = Test-Path $Programs; runkey = Test-Path $RunKey; ragbase = Test-Path "HKCU:\Software\RAGbase" }
$clean = -not ((Test-Path $App) -or $pre.data -or (Run-Value) -or ((Product-State $code) -eq 5))
Log "W10 Basic User install  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  msi=$Msi"
Check "W10.0" $clean "no RAGbase Shield install or data folder before the check"
if (-not $clean) { Log "RESULT: refused to run"; exit 2 }
try {
  $mlog = Join-Path $logs "basic-install.log"
  $cmd = "`"$env:SystemRoot\System32\msiexec.exe`" /i `"$Msi`" /qn /norestart /l*v `"$mlog`""
  Log "runas /trustlevel:0x20000 $cmd"
  $out = & runas.exe /trustlevel:0x20000 $cmd 2>&1
  Log ("runas: " + (($out | ForEach-Object { "$_" }) -join " "))
  $end = (Get-Date).AddSeconds(600)
  $text = ""
  while ((Get-Date) -lt $end) {
    $text = Read-MsiLog $mlog
    if ($text -match "MainEngineThread is returning (\d+)") { break }
    Start-Sleep -Seconds 2
  }
  $ret = if ($text -match "MainEngineThread is returning (\d+)") { $Matches[1] } else { "none" }
  Check "W10.1" ($text.Contains("Installation success or error status: 0")) "msiexec under a Basic User token: success status 0" "engine returned $ret"
  $admin = [regex]::Match($text, "Property\(S\): AdminUser = (\S+)").Groups[1].Value
  $priv = [regex]::Match($text, "Property\(S\): Privileged = (\S+)").Groups[1].Value
  Check "W10.2" (-not $admin -and -not $priv) "the install ran without administrator rights (AdminUser and Privileged not set)" "AdminUser '$admin', Privileged '$priv'"
  $asg = ""; try { $asg = [string](WI-Get $WI "ProductInfo" @($code, "AssignmentType")) } catch { }
  Check "W10.3" ((Product-State $code) -eq 5 -and $asg -eq "0" -and (Test-Path (Join-Path $App "runtime\python.exe"))) "product installed for this user, files in %LOCALAPPDATA%\Programs" "state $(Product-State $code), AssignmentType $asg"
  Check "W10.4" ([bool](Run-Value)) "Run key written by the custom action"
  $ok = $false
  $end = (Get-Date).AddSeconds(120)
  while ((Get-Date) -lt $end -and -not $ok) {
    $tf = Join-Path $Data "desk_token"
    if (Test-Path $tf) {
      $tok = (([IO.File]::ReadAllText($tf)) -split "`r?`n")[0].Trim()
      try {
        $req = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$Port/api/status"); $req.Proxy = $null; $req.Timeout = 5000
        $req.Headers.Add("X-Shield-Token", $tok)
        $resp = $req.GetResponse(); $ok = ([int]$resp.StatusCode -eq 200); $resp.Close()
      } catch { }
    }
    if (-not $ok) { Start-Sleep -Milliseconds 500 }
  }
  Check "W10.5" $ok "Shield Desk answers 200 (service started by the restricted install)"
} finally {
  if ((Product-State $code) -eq 5) {
    $p = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -ArgumentList @("/x", $code, "/qn", "/norestart", "/l*v", "`"$(Join-Path $logs 'basic-uninstall.log')`"") -PassThru -WorkingDirectory $env:SystemRoot
    $null = $p.Handle; $null = $p.WaitForExit(600000)
    Check "W10.6" ($p.ExitCode -eq 0 -and (Product-State $code) -ne 5 -and -not (Test-Path $App)) "msiexec /x removes it" "exit $($p.ExitCode)"
  }
  if (-not $pre.data -and (Test-Path $Data)) { Remove-Item -Recurse -Force $Data -ErrorAction SilentlyContinue; Log "cleanup: removed the data folder (it did not exist before)" }
  if (-not $pre.programs -and (Test-Path $Programs) -and -not (Get-ChildItem $Programs -Force)) { Remove-Item -Force $Programs }
  if (-not $pre.runkey -and (Test-Path $RunKey)) { $k = Get-Item $RunKey; if ($k.ValueCount -eq 0 -and $k.SubKeyCount -eq 0) { Remove-Item $RunKey } }
  if (-not $pre.ragbase -and (Test-Path "HKCU:\Software\RAGbase")) { Remove-Item -Recurse "HKCU:\Software\RAGbase" -ErrorAction SilentlyContinue }
  Log "RESULT: $($script:Pass) passed, $($script:Fail) failed"
}
if ($script:Fail -gt 0) { exit 1 }
exit 0
