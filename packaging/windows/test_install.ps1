# Level-1 test of the Windows installer on the build VM (packaging/DESIGN.md section 13.3, W3 to W8).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\shield_pkg\t-<stamp>\test_install.ps1 `
#     -Msi C:\shield_pkg\b-<v>\out\RAGbase-Shield-<v>-win64.msi -UpgradeMsi C:\shield_pkg\b-<v2>\out\RAGbase-Shield-<v2>-win64.msi `
#     -Work C:\shield_pkg\t-<stamp>
#
# Runs as the logged-in SSH user, like a user double-clicking the .msi: msiexec /i ... /qn, no elevation step, the
# product's real folders (%LOCALAPPDATA%\Programs\RAGbase Shield, %LOCALAPPDATA%\ragbase-shield, the HKCU Run key,
# the Start menu) and the default port 7878. It refuses to start when any of them is already in use, and it puts
# back what did not exist before (the data folder, the Run key, %LOCALAPPDATA%\Programs) at the end.
# CLI checks (doctor, verify, MCP) run with RAGBASE_SHIELD_KEYRING=0 (Credential Manager is not reachable over SSH)
# and, for verify and the MCP handshake, a temporary data folder under -Work.
# The Desk token is read from the data folder to call the Desk, never printed or logged; the script checks
# that it appears in no log. Network: net_sampler.ps1 records every socket of the Shield processes and of
# msiexec during the whole test; any non-loopback address fails the test.
# Exit code: 0 when every check passed, 1 otherwise. Output: one PASS / FAIL / INFO line per check, and
# <Work>\logs\test_install.log (same lines) plus the msiexec logs.
# Every msiexec call carries /norestart (review 2026-11-03): with /qn and a file in use, Windows Installer would
# otherwise reboot the machine at once. W7.0 installs the same .msi over itself; W8b removes the product while an
# MCP server of an AI app holds python.exe (expected: exit 3010, no reboot, files left until the next reboot).
param(
  [Parameter(Mandatory = $true)][string]$Msi,
  [Parameter(Mandatory = $true)][string]$UpgradeMsi,
  [Parameter(Mandatory = $true)][string]$Work,
  [string]$Manifest = "",
  [int]$Port = 7878
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8  # the SSH stream carries the French lines of the CLI
$Root = "C:\shield_pkg"

function Under-Root([string]$p) {
  $full = [IO.Path]::GetFullPath($p)
  if (-not $full.StartsWith("$Root\", [StringComparison]::OrdinalIgnoreCase)) { throw "outside $Root : $full" }
  return $full
}
$Work = Under-Root $Work
$Msi = Under-Root $Msi
$UpgradeMsi = Under-Root $UpgradeMsi
if (-not $Manifest) { $Manifest = Join-Path $Work "manifest.json" }
$logs = Join-Path $Work "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$LogFile = Join-Path $logs "test_install.log"
Set-Content -Encoding utf8 $LogFile ""
$TmpHome = Join-Path $Work "tmphome"
$TmpAppData = Join-Path $Work "tmpappdata"

$App = Join-Path $env:LOCALAPPDATA "Programs\RAGbase Shield"
$AppLow = $App.ToLower() + "\"
$Programs = Join-Path $env:LOCALAPPDATA "Programs"
$Data = Join-Path $env:LOCALAPPDATA "ragbase-shield"
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RunValue = "RAGbase Shield"
$ShieldKey = "HKCU:\Software\RAGbase\Shield"
$Lnk = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\RAGbase Shield.lnk"
$ArpCU = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
$ArpLM = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
$Py = Join-Path $App "runtime\python.exe"
$script:Pass = 0
$script:Fail = 0
$script:Pending = 0

function Log([string]$m) { [Console]::Out.WriteLine($m); Add-Content -Encoding utf8 -LiteralPath $LogFile -Value $m }
function Check([string]$id, [bool]$ok, [string]$what, [string]$detail = "") {
  if ($ok) { $script:Pass++; $s = "PASS" } else { $script:Fail++; $s = "FAIL" }
  $tail = ""
  if ($detail) { $tail = " : $detail" }
  Log ("{0,-5} {1,-5} {2}{3}" -f $s, $id, $what, $tail)
}
function Info([string]$id, [string]$what) { Log ("INFO  {0,-5} {1}" -f $id, $what) }

function Quote-Arg([string]$a) {
  if ($a -eq "") { return '""' }
  if ($a -notmatch '[\s"]') { return $a }
  return '"' + (($a -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}
function Run-Proc([string]$Exe, [string[]]$Argv, [hashtable]$EnvSet = @{}, [int]$TimeoutSec = 300) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $Exe
  $psi.Arguments = (@($Argv | ForEach-Object { Quote-Arg $_ })) -join " "
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
  $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
  $psi.WorkingDirectory = $Work
  foreach ($k in $EnvSet.Keys) {
    if ($null -eq $EnvSet[$k]) { $psi.EnvironmentVariables.Remove($k) } else { $psi.EnvironmentVariables[$k] = [string]$EnvSet[$k] }
  }
  $p = [Diagnostics.Process]::Start($psi)
  $o = $p.StandardOutput.ReadToEndAsync()
  $e = $p.StandardError.ReadToEndAsync()
  if (-not $p.WaitForExit($TimeoutSec * 1000)) {
    try { $p.Kill() } catch { }
    return [pscustomobject]@{ Code = -999; Out = ""; Err = "timeout" }
  }
  $p.WaitForExit()
  return [pscustomobject]@{ Code = $p.ExitCode; Out = $o.Result; Err = $e.Result }
}
function Run-Msi([string[]]$Argv, [int]$TimeoutSec = 1200) {
  # /norestart on every call: with /qn and a file in use, msiexec would otherwise REBOOT the machine at once
  # (REBOOT=Prompt with no UI). The package sets REBOOT=ReallySuppress too; this guard holds for any package.
  $Argv = @($Argv) + @("/norestart")
  $p = Start-Process -FilePath (Join-Path $env:SystemRoot "System32\msiexec.exe") -ArgumentList $Argv -PassThru `
         -WorkingDirectory $env:SystemRoot
  $null = $p.Handle
  if (-not $p.WaitForExit($TimeoutSec * 1000)) { return -999 }
  return $p.ExitCode
}
function Http-Status([string]$Url, [hashtable]$Headers = @{}, [string]$HostHeader = "") {
  $req = [System.Net.HttpWebRequest]::Create($Url)
  $req.Timeout = 5000
  $req.Proxy = $null
  foreach ($k in $Headers.Keys) { $req.Headers.Add($k, $Headers[$k]) }
  if ($HostHeader) { $req.Host = $HostHeader }
  try {
    $resp = $req.GetResponse()
    $sr = New-Object IO.StreamReader($resp.GetResponseStream())
    $body = $sr.ReadToEnd()
    $code = [int]$resp.StatusCode
    $resp.Close()
    return [pscustomobject]@{ Code = $code; Body = $body }
  } catch [System.Net.WebException] {
    $r = $_.Exception.Response
    if ($r) { $code = [int]$r.StatusCode; $r.Close(); return [pscustomobject]@{ Code = $code; Body = "" } }
    return [pscustomobject]@{ Code = 0; Body = "" }
  }
}
function Read-Token {
  $f = Join-Path $Data "desk_token"
  if (-not (Test-Path -LiteralPath $f)) { return $null }
  $first = (([IO.File]::ReadAllText($f)) -split "`r?`n")[0].Trim()
  if ($first -match '^[A-Za-z0-9_-]{32,256}$') { return $first }
  return $null
}
function Desk-Status {
  $tok = Read-Token
  if (-not $tok) { return [pscustomobject]@{ Code = -1; Body = "" } }
  return Http-Status "http://127.0.0.1:$Port/api/status" @{ "X-Shield-Token" = $tok }
}
function Wait-Desk([int]$Sec) {
  $end = (Get-Date).AddSeconds($Sec)
  while ((Get-Date) -lt $end) {
    if ((Desk-Status).Code -eq 200) { return $true }
    Start-Sleep -Milliseconds 500
  }
  return $false
}
function Shield-Procs {
  @(Get-CimInstance Win32_Process -Property ProcessId, Name, ExecutablePath, CommandLine |
    Where-Object { $_.ExecutablePath -and $_.ExecutablePath.ToLower().StartsWith($AppLow) })
}
function Sup-Procs { @(Shield-Procs | Where-Object { $_.CommandLine -match "service run" }) }
function Desk-Procs { @(Shield-Procs | Where-Object { $_.CommandLine -match "desk --service" }) }
function Arp-Entries {
  # Settings > Apps entries named "RAGbase Shield". Windows Installer writes the Uninstall key of a per-user
  # product under HKLM (seen on the VM, with the per-user registration under Installer\UserData\<SID>): both
  # hives are read, and the hive is reported.
  @(foreach ($hive in @($ArpCU, $ArpLM)) {
      Get-ChildItem $hive -ErrorAction SilentlyContinue | ForEach-Object {
        $v = Get-ItemProperty -LiteralPath $_.PSPath
        if ($v.DisplayName -eq "RAGbase Shield") {
          [pscustomobject]@{ Code = $_.PSChildName; Version = $v.DisplayVersion; NoModify = $v.NoModify;
                             NoRepair = $v.NoRepair; Uninstall = $v.UninstallString; Hive = $hive.Substring(0, 4) }
        } } })
}
function Read-Shared([string]$p) {
  # The service keeps its log open for writing: open it with FileShare.ReadWrite, as a log viewer does.
  if (-not (Test-Path -LiteralPath $p)) { return ,[byte[]]@() }
  $fs = [IO.File]::Open($p, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
  try { $ms = New-Object IO.MemoryStream; $fs.CopyTo($ms); return ,$ms.ToArray() } finally { $fs.Close() }
}
function Read-SharedText([string]$p) { $b = Read-Shared $p; if ($b.Length -eq 0) { return "" }; return [Text.Encoding]::UTF8.GetString($b) }
function Dump-ServiceLogs([string]$why) {
  # Event codes and integers only (the service never logs the token or a dossier); kept for the report.
  foreach ($n in @("service.log", "desk.log")) {
    $t = Read-SharedText (Join-Path $Data "logs\$n")
    $last = @($t -split "`r?`n" | Where-Object { $_ } | Select-Object -Last 15)
    Info "LOG" "$why, $n ($($last.Count) last lines): $($last -join ' | ')"
  }
}
function Run-Value {
  try { return [string](Get-ItemProperty -LiteralPath $RunKey -Name $RunValue -ErrorAction Stop).$RunValue } catch { return $null }
}
$WI = New-Object -ComObject WindowsInstaller.Installer
function WI-Get($obj, [string]$name, [object[]]$argv) {
  return $obj.GetType().InvokeMember($name, [Reflection.BindingFlags]::GetProperty, $null, $obj, $argv)
}
function Product-State([string]$code) { try { return [int](WI-Get $WI "ProductState" @($code)) } catch { return -99 } }
function Product-Info([string]$code, [string]$prop) { try { return [string](WI-Get $WI "ProductInfo" @($code, $prop)) } catch { return "" } }
function Msi-Summary([string]$path) {
  $db = $WI.GetType().InvokeMember("OpenDatabase", [Reflection.BindingFlags]::InvokeMethod, $null, $WI, @($path, 0))
  $si = WI-Get $db "SummaryInformation" @(0)
  $r = [pscustomobject]@{ Template = [string](WI-Get $si "Property" @(7)); WordCount = [int](WI-Get $si "Property" @(15)) }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($si)
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($db)
  return $r
}
function Read-MsiLog([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return "" }
  $b = [IO.File]::ReadAllBytes($p)
  if ($b.Length -ge 2 -and $b[0] -eq 0xFF -and $b[1] -eq 0xFE) { return [Text.Encoding]::Unicode.GetString($b) }
  return [Text.Encoding]::Default.GetString($b)
}
function Shield-FilesInUse([string]$text) {
  # Client log lines "File In Use: -<name>- Window ...": InstallValidate found a process that holds a file to replace
  # or remove. Shield's own processes must never be there (ShieldStopEarly runs before InstallValidate, review
  # 2026-11-03); other programs are counted only, never named in this log.
  $all = [regex]::Matches($text, "File In Use: -([^\r\n]*?)- Window")
  $ours = @($all | Where-Object { $_.Groups[1].Value -in @("RAGbase Shield", "python") })
  return [pscustomobject]@{ Ours = $ours.Count; Others = ($all.Count - $ours.Count) }
}
function File-Sha([string]$p) { if (Test-Path -LiteralPath $p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash } return "" }
function Token-Leaks([string]$tok) {
  # Names of the files that hold the token (the value itself is never printed).
  if (-not $tok) { return @() }
  $places = @()
  $files = @()
  foreach ($d in @((Join-Path $Data "logs"), $logs)) {
    if (Test-Path -LiteralPath $d) { $files += @(Get-ChildItem -LiteralPath $d -Recurse -File) }
  }
  foreach ($f in @((Join-Path $Data "install.json"))) { if (Test-Path -LiteralPath $f) { $files += @(Get-Item -LiteralPath $f) } }
  foreach ($f in $files) {
    if ($f.FullName -ieq $LogFile) { continue }
    $b = Read-Shared $f.FullName  # UTF-8 / ANSI logs and the UTF-16 msiexec logs, some still open
    if ([Text.Encoding]::UTF8.GetString($b).Contains($tok) -or [Text.Encoding]::Unicode.GetString($b).Contains($tok)) {
      $places += $f.Name
    }
  }
  $rv = Run-Value
  if ($rv -and $rv.Contains($tok)) { $places += "Run key" }
  return $places
}
function Shield-Env([string]$homeDir) {
  $h = @{ "RAGBASE_SHIELD_KEYRING" = "0"; "RAGBASE_SHIELD_PORT" = $null; "PYTHONUTF8" = "1" }
  if ($homeDir) { $h["RAGBASE_SHIELD_HOME"] = $homeDir } else { $h["RAGBASE_SHIELD_HOME"] = $null }
  return $h
}

Log "RAGbase Shield Windows level-1 test  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Log "msi=$Msi"
Log "upgrade msi=$UpgradeMsi"
$os = Get-CimInstance Win32_OperatingSystem
$sess = (Get-Process -Id $PID).SessionId
$elev = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "user=$env:USERNAME session=$sess elevated_token=$elev os=$($os.Caption) $($os.Version) port=$Port"
Log "app=$App"
Log "data=$Data"

# ------------------------------------------------------------------ P: preconditions (refuse to run over a real install)
$pre = [ordered]@{
  app = Test-Path -LiteralPath $App; data = Test-Path -LiteralPath $Data; programs = Test-Path -LiteralPath $Programs
  runkey = Test-Path -LiteralPath $RunKey; runvalue = [bool](Run-Value); shieldkey = Test-Path -LiteralPath $ShieldKey
  ragbasekey = Test-Path -LiteralPath "HKCU:\Software\RAGbase"; lnk = Test-Path -LiteralPath $Lnk; arp = (@(Arp-Entries).Count -gt 0)
  port = [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}
Log ("before: " + (($pre.Keys | ForEach-Object { "$_=$($pre[$_])" }) -join " "))
$clean = -not ($pre.app -or $pre.data -or $pre.runvalue -or $pre.shieldkey -or $pre.lnk -or $pre.arp -or $pre.port)
Check "P1" $clean "no RAGbase Shield install, data folder, Run value, shortcut, product or port $Port in use before the test"
if (-not $clean) { Log "RESULT: refused to run (the machine already has Shield state)"; exit 2 }
foreach ($f in @($Msi, $UpgradeMsi, $Manifest, (Join-Path $Work "net_sampler.ps1"), (Join-Path $Work "mcp_probe.py"))) {
  if (-not (Test-Path -LiteralPath $f)) { Log "RESULT: missing $f"; exit 2 }
}
$sum = Msi-Summary $Msi
Check "P2" (($sum.WordCount -band 8) -eq 8) "package says no elevated privileges are needed (Word Count bit 8)" "Word Count $($sum.WordCount), template $($sum.Template)"
Info "P3" ("msi SHA-256 " + (File-Sha $Msi) + ", " + (Get-Item $Msi).Length + " bytes; upgrade msi SHA-256 " + (File-Sha $UpgradeMsi))
$vars1 = Get-Content (Join-Path (Split-Path (Split-Path $Msi)) "msi_vars.json") -Raw | ConvertFrom-Json
$vars2 = Get-Content (Join-Path (Split-Path (Split-Path $UpgradeMsi)) "msi_vars.json") -Raw | ConvertFrom-Json
Info "P4" "first MSI $($vars1.Version) $($vars1.ProductCode); upgrade MSI $($vars2.Version) $($vars2.ProductCode); UpgradeCode $($vars1.UpgradeCode)"

$stopFile = Join-Path $Work "net.stop"
$netJson = Join-Path $Work "net.json"
Remove-Item -Force -ErrorAction SilentlyContinue $stopFile, $netJson
$sampler = Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -PassThru -ArgumentList @(
  "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$(Join-Path $Work 'net_sampler.ps1')`"",
  "-Out", "`"$netJson`"", "-StopFile", "`"$stopFile`"", "-App", "`"$App`"")
$dnsBefore = @(Get-DnsClientCache -ErrorAction SilentlyContinue | ForEach-Object { $_.Entry }) | Sort-Object -Unique
Start-Sleep -Seconds 3
$tokenSeen = $null

try {
  # ---------------------------------------------------------------- W3: install
  Log "--- W3 install: msiexec /i /qn as $env:USERNAME"
  $t0 = Get-Date
  $rc = Run-Msi @("/i", "`"$Msi`"", "/qn", "/l*v", "`"$(Join-Path $logs 'install.log')`"")
  $secs = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  Check "W3.1" ($rc -eq 0) "msiexec /i /qn exit code 0" "exit $rc, $secs s"
  $files = @(Get-ChildItem -LiteralPath $App -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*\__pycache__\*" })
  $man = Get-Content (Join-Path $App "MANIFEST.json") -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
  $want = @($man.files.PSObject.Properties).Count + 1
  Check "W3.2" ($files.Count -eq $want) "app folder holds the payload" "$($files.Count) files (bytecode caches not counted), MANIFEST.json lists $($want - 1) + itself"
  $ver = Run-Proc $Py @("-I", "-X", "utf8", "-m", "ragbase_shield", "--version") (Shield-Env $TmpHome)
  $expectV = "ragbase-shield " + (Get-Content (Join-Path $App "VERSION") -Raw).Trim()
  Check "W3.3" ($ver.Code -eq 0 -and $ver.Out.Trim() -eq $expectV) "runtime\python.exe -I -X utf8 -m ragbase_shield --version" $ver.Out.Trim()
  $cmdv = Run-Proc (Join-Path $App "bin\ragbase-shield.cmd") @("--version") (Shield-Env $TmpHome)
  Check "W3.4" ($cmdv.Code -eq 0 -and $cmdv.Out.Trim() -eq $expectV) "bin\ragbase-shield.cmd --version" $cmdv.Out.Trim()
  $rv = Run-Value
  $expectRun = "`"$App\runtime\RAGbase Shield.exe`" -E -s -P -X utf8 -m ragbase_shield service run"
  Check "W3.5" ($rv -eq $expectRun) "Run key value 'RAGbase Shield' = the service command" $rv
  $lnkOk = $false; $lnkInfo = "missing"
  if (Test-Path -LiteralPath $Lnk) {
    $l = (New-Object -ComObject WScript.Shell).CreateShortcut($Lnk)
    $lnkInfo = "$($l.TargetPath) $($l.Arguments) (in $($l.WorkingDirectory))"
    $lnkOk = ($l.TargetPath -ieq "$App\runtime\RAGbase Shield.exe") -and ($l.Arguments -eq "-E -s -P -X utf8 -m ragbase_shield service start") -and ($l.WorkingDirectory.TrimEnd("\") -ieq $env:LOCALAPPDATA.TrimEnd("\"))
  }
  Check "W3.6" $lnkOk "Start menu shortcut 'RAGbase Shield'" $lnkInfo
  $arp = @(Arp-Entries)
  $code1 = [string]$vars1.ProductCode
  $a1 = $arp | Where-Object { $_.Code -eq $code1 }
  Check "W3.7" ($arp.Count -eq 1 -and $a1 -and $a1.Version -eq $vars1.Version -and $a1.NoModify -eq 1 -and $a1.NoRepair -eq 1 -and $a1.Uninstall -eq "MsiExec.exe /X$code1") "one Settings > Apps entry, Uninstall only (no Modify, no Repair)" ("$($arp.Count) entry, version $($a1.Version), NoModify $($a1.NoModify), NoRepair $($a1.NoRepair), " + $a1.Uninstall)
  $sid = ([Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
  $udKeys = @(Get-ChildItem "HKLM:\Software\Microsoft\Windows\CurrentVersion\Installer\UserData\$sid\Products" -ErrorAction SilentlyContinue | Where-Object { (Get-ItemProperty -LiteralPath (Join-Path $_.PSPath "InstallProperties") -ErrorAction SilentlyContinue).DisplayName -eq "RAGbase Shield" })
  Info "W3.8" "Uninstall key in $($a1.Hive); per-user registration under Installer\UserData\<this user's SID>: $($udKeys.Count) product"
  $asg = Product-Info $code1 "AssignmentType"
  Check "W3.9" ((Product-State $code1) -eq 5 -and $asg -eq "0") "Windows Installer: product installed for this user only" "state $(Product-State $code1), AssignmentType $asg (0 = per user)"
  $ij = $null
  try { $ij = Get-Content (Join-Path $Data "install.json") -Raw | ConvertFrom-Json } catch { }
  Check "W3.10" ($ij -and $ij.app_dir -ieq $App -and $ij.login_item -eq "run_key" -and $ij.launcher -ieq $Py) "install.json in the data folder (written by the deferred custom action as the user)" $(if ($ij) { "login_item $($ij.login_item), launcher $($ij.launcher) $($ij.launcher_args -join ' ')" } else { "missing" })
  $il = Join-Path $logs "install.log"
  $ilText = Read-MsiLog $il
  Check "W3.11" ($ilText.Contains("Installation success or error status: 0")) "install log: success status 0"
  Info "W3.12" ("install log: ShieldRegister " + $(if ($ilText -match "Doing action: ShieldRegister|Executing op: CustomActionSchedule\(Action=ShieldRegister") { "ran" } else { "NOT seen" }) + ", ShieldStart " + $(if ($ilText -match "Doing action: ShieldStart") { "ran" } else { "NOT seen" }) + ", ALLUSERS " + $(if ($ilText -match "PROPERTY CHANGE: Adding ALLUSERS") { "set" } else { "not set" }))

  # ---------------------------------------------------------------- W4: service up, loopback only, token rules
  Log "--- W4 service"
  $t1 = Get-Date
  $up = Wait-Desk 120
  $ready = [math]::Round(((Get-Date) - $t1).TotalSeconds, 1)
  Check "W4.1" $up "Shield Desk answers 200 with the token on 127.0.0.1:$Port" "$ready s after msiexec returned"
  if (-not $up) { Dump-ServiceLogs "Desk not up after install" }
  $tokenSeen = Read-Token
  $sup = @(Sup-Procs); $desk = @(Desk-Procs)
  $supName = ""; if ($sup.Count) { $supName = (Get-Process -Id $sup[0].ProcessId -ErrorAction SilentlyContinue).ProcessName }
  Check "W4.2" ($sup.Count -eq 1 -and $supName -eq "RAGbase Shield") "one supervisor process named 'RAGbase Shield' (service run)" "$($sup.Count) process(es), name '$supName', pid $($sup.ProcessId -join ',')"
  Check "W4.3" ($desk.Count -eq 1 -and $desk[0].Name -ieq "python.exe" -and $desk[0].CommandLine -match "desk --service --port $Port") "one Shield Desk child (python.exe desk --service)" "$($desk.Count) process(es), pid $($desk.ProcessId -join ',')"
  $st = Desk-Status
  $info = $null; try { $info = $st.Body | ConvertFrom-Json } catch { }
  Info "W4.4" "status: version $($info.version), engine_mode $($info.engine_mode), key_storage $($info.key_storage)"
  $r = Http-Status "http://127.0.0.1:$Port/api/status"
  Check "W4.5" ($r.Code -eq 401) "no token: refused" "HTTP $($r.Code)"
  $r = Http-Status "http://127.0.0.1:$Port/api/status" @{ "X-Shield-Token" = ("A" * 43) }
  Check "W4.6" ($r.Code -eq 401 -or $r.Code -eq 403) "wrong token: refused" "HTTP $($r.Code)"
  $r = Http-Status "http://127.0.0.1:$Port/api/status" @{ "X-Shield-Token" = $tokenSeen } "evil.example:$Port"
  Check "W4.7" ($r.Code -eq 403) "other Host header: refused" "HTTP $($r.Code)"
  $ids = @($sup.ProcessId) + @($desk.ProcessId)
  $socks = @(Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $ids -contains $_.OwningProcess })
  # Allowed: listening on 127.0.0.1, connections between 127.0.0.1 addresses, and "Bound" entries (bound, neither
  # listening nor connected: Windows lists the port of asyncio's socketpair, whose listener is already closed,
  # as 0.0.0.0 "Bound"; netstat shows the pair itself as 127.0.0.1 ESTABLISHED, see N1).
  $nonLoop = @($socks | Where-Object {
      $bound = ($_.State -eq "Bound" -and $_.RemoteAddress -eq "0.0.0.0" -and $_.RemotePort -eq 0)
      -not $bound -and ($_.LocalAddress -ne "127.0.0.1" -or ($_.RemoteAddress -ne "127.0.0.1" -and -not ($_.State -eq "Listen" -and $_.RemoteAddress -eq "0.0.0.0"))) })
  $listen = @($socks | Where-Object { $_.State -eq "Listen" })
  Check "W4.8" ($listen.Count -eq 1 -and $listen[0].LocalAddress -eq "127.0.0.1" -and $listen[0].LocalPort -eq $Port -and $nonLoop.Count -eq 0) "TCP sockets of the supervisor and the Desk: one listener on 127.0.0.1:$Port, every connection 127.0.0.1 to 127.0.0.1" (($socks | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort)>$($_.RemoteAddress):$($_.RemotePort) $($_.State)" } | Sort-Object -Unique) -join "; ")
  $udp = @(Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object { $ids -contains $_.OwningProcess })
  Check "W4.9" ($udp.Count -eq 0) "no UDP socket" "$($udp.Count)"
  $slog = Join-Path $Data "logs\service.log"
  $sl = Read-SharedText $slog
  Check "W4.10" ($sl -match "tray: unavailable \(no_desktop\)") "service.log: tray unavailable (no_desktop) in this session-0 SSH logon, Desk kept running" (($sl -split "`r?`n" | Where-Object { $_ -match "tray:|desk: ready|install:" }) -join " | ")
  foreach ($n in @("service.pid", "service.pid.txt", "desk.pid")) {
    Check "W4.11" (Test-Path (Join-Path $Data $n)) "PID file $n"
  }
  $leak = @(Token-Leaks $tokenSeen)
  Check "W4.12" ($tokenSeen -and $leak.Count -eq 0) "token in no log, not in install.json, not in the Run key" $(if ($leak.Count) { $leak -join ", " } else { "checked logs\, install.json, msiexec logs, Run key" })
  $ss = Run-Proc $Py @("-I", "-X", "utf8", "-m", "ragbase_shield", "service", "status") (Shield-Env "")
  Check "W4.13" ($ss.Code -eq 0) "service status (installed data folder)" (($ss.Out -split "`r?`n" | Where-Object { $_ }) -join " | ")

  # ---------------------------------------------------------------- W5: imports and MCP handshake
  Log "--- W5 MCP"
  $imp = Run-Proc $Py @("-I", "-X", "utf8", "-c", "import win32api, pywintypes, mcp, infi.systray; print('imports ok')") (Shield-Env $TmpHome)
  Check "W5.1" ($imp.Code -eq 0 -and $imp.Out.Trim() -eq "imports ok") "import win32api, pywintypes, mcp, infi.systray (pywin32 without its post-install step)" ($imp.Out.Trim() + $imp.Err.Trim())
  $mcp = Run-Proc $Py @("-I", (Join-Path $Work "mcp_probe.py"), $Py, $Manifest) (Shield-Env $TmpHome) 240
  Check "W5.2" ($mcp.Code -eq 0) "MCP stdio: initialize + tools/list = the 6 tools of the .mcpb manifest" (($mcp.Out -split "`r?`n" | Where-Object { $_ }) -join " | ")
  $envDry = Shield-Env ""  # the installed data folder: install.json names the launcher
  $envDry["APPDATA"] = $TmpAppData
  New-Item -ItemType Directory -Force $TmpAppData | Out-Null
  $dry = Run-Proc (Join-Path $App "bin\ragbase-shield.cmd") @("install", "claude-desktop", "--dry-run") $envDry
  $dryOk = ($dry.Code -eq 0) -and $dry.Out.Contains(($Py -replace "\\", "\\")) -and $dry.Out.Contains('"-I"') -and $dry.Out.Contains('"mcp"')
  Check "W5.3" $dryOk "install claude-desktop --dry-run proposes the installed python.exe -I -X utf8 -m ragbase_shield mcp" (($dry.Out -replace "\s+", " ").Trim())

  # ---------------------------------------------------------------- W6: doctor, verify
  Log "--- W6 doctor and verify"
  $doc = Run-Proc $Py @("-I", "-X", "utf8", "-m", "ragbase_shield", "doctor") (Shield-Env "") 300
  $docLines = @($doc.Out -split "`r?`n" | Where-Object { $_ -match "Installateur|Service Shield Desk|uv / uvx|Python :" })
  Check "W6.1" ($doc.Code -eq 0 -and $doc.Out -match "OK +Installateur : " -and $doc.Out -match "OK +Service Shield Desk : actif, port $Port, ouverture de session : oui") "doctor (installed data folder): installer and service lines, exit 0" ("exit $($doc.Code); " + ($docLines -join " | "))
  New-Item -ItemType Directory -Force $TmpHome | Out-Null
  $doc2 = Run-Proc $Py @("-I", "-X", "utf8", "-m", "ragbase_shield", "doctor") (Shield-Env $TmpHome) 300
  Check "W6.2" ($doc2.Code -eq 0) "doctor in a temporary data folder: exit 0" ("exit $($doc2.Code); " + (($doc2.Out -split "`r?`n" | Where-Object { $_ -match "^(FAIL|WARN)" }) -join " | "))
  $ver2 = Run-Proc $Py @("-I", "-X", "utf8", "-m", "ragbase_shield", "verify") (Shield-Env $TmpHome) 600
  $vline = @($ver2.Out -split "`r?`n" | Where-Object { $_ -match "^R.sultat" }) -join " "
  $vClean = @($ver2.Out -split "`r?`n" | Where-Object { $_ -match "^CLEAN " }).Count
  $vLeak = @($ver2.Out -split "`r?`n" | Where-Object { $_ -match "^(LEAK|ERROR) " }).Count
  Check "W6.3" ($vline -match "CLEAN" -and $vLeak -eq 0) "verify in a temporary data folder: CLEAN" "$vline ($vClean CLEAN lines, $vLeak LEAK or ERROR lines) exit $($ver2.Code)"
  Check "W6.4" ($ver2.Code -eq 0) "verify exit code 0" ("exit $($ver2.Code) " + ($ver2.Err.Trim() -replace "\s+", " "))

  # ---------------------------------------------------------------- W7.0: the same .msi again (maintenance mode)
  Log "--- W7.0 same package again: msiexec /i of the installed $($vars1.Version) msi"
  $supBefore = @((Sup-Procs).ProcessId)
  $t20 = Get-Date
  $rc = Run-Msi @("/i", "`"$Msi`"", "/qn", "/l*v", "`"$(Join-Path $logs 'reinstall.log')`"")
  $secs = [math]::Round(((Get-Date) - $t20).TotalSeconds, 1)
  Check "W7.0a" ($rc -eq 0) "the same .msi over itself: exit 0 (maintenance mode)" "exit $rc, $secs s"
  $upR = Wait-Desk 120
  $supR = @(Sup-Procs)
  Check "W7.0b" ($upR -and (Product-State $code1) -eq 5 -and @(Arp-Entries).Count -eq 1 -and $supR.Count -eq 1 -and ($supBefore -notcontains $supR[0].ProcessId)) "the same .msi over itself: still one product, service restarted, Desk 200" "supervisor $($supBefore -join ',') -> $($supR.ProcessId -join ',')"
  $rlText = Read-MsiLog (Join-Path $logs "reinstall.log")
  Info "W7.0c" ("reinstall log: " + $(if ($rlText -match "Installation success or error status: (\d+)") { "status " + $Matches[1] } else { "no status line" }) + "; file copy operations: " + ([regex]::Matches($rlText, "Executing op: FileCopy")).Count + " (a same-version package replaces no file: a new build needs a new version)")
  $fiu = Shield-FilesInUse $rlText
  Check "W7.0d" ($fiu.Ours -eq 0) "the same .msi over itself: InstallValidate found no Shield process holding a file (ShieldStopEarly ran first)" "Shield processes listed $($fiu.Ours), other programs listed $($fiu.Others)"
  if ($supR.Count) { $sup = $supR }

  # ---------------------------------------------------------------- W7: upgrade keeps the data
  Log "--- W7 upgrade to $($vars2.Version)"
  New-Item -ItemType Directory -Force (Join-Path $App "extras\marker") | Out-Null
  Set-Content -Encoding ascii (Join-Path $App "extras\marker\keep.txt") "NER packages would live here"
  $tokSha = File-Sha (Join-Path $Data "desk_token")
  $dataBefore = @(Get-ChildItem -LiteralPath $Data -Force | Where-Object { $_.Name -notin @("logs", "service.pid", "service.pid.txt", "desk.pid", "install.json", "service.cmd") } | ForEach-Object { $_.Name }) | Sort-Object
  $oldSup = @($sup.ProcessId)
  $ijBefore = $ij
  $t2 = Get-Date
  $rc = Run-Msi @("/i", "`"$UpgradeMsi`"", "/qn", "/l*v", "`"$(Join-Path $logs 'upgrade.log')`"")
  $secs = [math]::Round(((Get-Date) - $t2).TotalSeconds, 1)
  Check "W7.1" ($rc -eq 0) "msiexec /i of the $($vars2.Version) msi: exit 0" "exit $rc, $secs s"
  $fiu = Shield-FilesInUse (Read-MsiLog (Join-Path $logs "upgrade.log"))
  Check "W7.1b" ($fiu.Ours -eq 0) "update: InstallValidate found no Shield process holding a file (ShieldStopEarly ran first)" "Shield processes listed $($fiu.Ours), other programs listed $($fiu.Others)"
  $arp = @(Arp-Entries)
  $code2 = [string]$vars2.ProductCode
  Check "W7.2" ($arp.Count -eq 1 -and $arp[0].Code -eq $code2 -and $arp[0].Version -eq $vars2.Version -and (Product-State $code1) -ne 5) "one product left: $($vars2.Version) (MajorUpgrade removed $($vars1.Version))" (($arp | ForEach-Object { "$($_.Code) $($_.Version)" }) -join "; ")
  Check "W7.3" (Test-Path (Join-Path $App "extras\marker\keep.txt")) "extras\ kept (optional NER packages survive an update)"
  Check "W7.4" ((Run-Value) -eq $expectRun) "Run key kept"
  $up2 = Wait-Desk 120
  if (-not $up2) { Dump-ServiceLogs "Desk not up after the update" }
  $sup2 = @(Sup-Procs); $desk2 = @(Desk-Procs)
  Check "W7.5" ($up2 -and $sup2.Count -eq 1 -and $desk2.Count -eq 1 -and ($oldSup -notcontains $sup2[0].ProcessId)) "service restarted by the new package (new supervisor, one Desk), Desk 200" "supervisor $($oldSup -join ',') -> $($sup2.ProcessId -join ','), desk $($desk2.ProcessId -join ',')"
  $dataAfter = @(Get-ChildItem -LiteralPath $Data -Force | Where-Object { $_.Name -notin @("logs", "service.pid", "service.pid.txt", "desk.pid", "install.json", "service.cmd") } | ForEach-Object { $_.Name }) | Sort-Object
  Check "W7.6" ((File-Sha (Join-Path $Data "desk_token")) -eq $tokSha -and (($dataBefore -join ",") -eq ($dataAfter -join ","))) "data folder untouched (same token, same files)" ($dataAfter -join ", ")
  $info2 = Get-Content (Join-Path $App "install_info.json") -Raw | ConvertFrom-Json
  Check "W7.7" ($info2.product_code -eq $code2) "install_info.json product_code = the installed ProductCode (target of the tray item Desinstaller...)" $info2.product_code
  $ij2 = $null; try { $ij2 = Get-Content (Join-Path $Data "install.json") -Raw | ConvertFrom-Json } catch { }
  Check "W7.8" ($ij2 -and $ijBefore -and $ij2.installed_at -ne $ijBefore.installed_at) "install.json rewritten by the new package" $(if ($ij2) { $ij2.installed_at } else { "missing" })
  $files2 = @(Get-ChildItem -LiteralPath $App -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*\extras\marker\*" -and $_.FullName -notlike "*\__pycache__\*" })
  Info "W7.9" "app folder after the update: $($files2.Count) payload files (+ extras marker), __pycache__ files: $(@(Get-ChildItem -LiteralPath $App -Recurse -File -Filter *.pyc -ErrorAction SilentlyContinue).Count)"

  # ---------------------------------------------------------------- W8: uninstall
  Log "--- W8 uninstall: msiexec /x $code2 /qn"
  $pycBefore = @(Get-ChildItem -LiteralPath $App -Recurse -File -Filter *.pyc -ErrorAction SilentlyContinue).Count
  Info "W8.0" "before uninstall: $pycBefore .pyc files written by Python since the update"
  foreach ($n in @("service.log", "desk.log")) {  # copies for the report (the uninstall removes them)
    $b = Read-Shared (Join-Path $Data "logs\$n")
    if ($b.Length) { [IO.File]::WriteAllBytes((Join-Path $logs "data-$n"), $b) }
  }
  $t3 = Get-Date
  $rc = Run-Msi @("/x", $code2, "/qn", "/l*v", "`"$(Join-Path $logs 'uninstall.log')`"")
  $secs = [math]::Round(((Get-Date) - $t3).TotalSeconds, 1)
  Check "W8.1" ($rc -eq 0) "msiexec /x /qn exit code 0 (no reboot needed)" "exit $rc, $secs s"
  $fiu = Shield-FilesInUse (Read-MsiLog (Join-Path $logs "uninstall.log"))
  Check "W8.1b" ($fiu.Ours -eq 0) "removal: InstallValidate found no Shield process holding a file (ShieldStopEarly ran first)" "Shield processes listed $($fiu.Ours), other programs listed $($fiu.Others)"
  $left = @()
  if (Test-Path -LiteralPath $App) { $left = @(Get-ChildItem -LiteralPath $App -Recurse -Force | ForEach-Object { $_.FullName.Substring($App.Length) }) }
  Check "W8.2" (-not (Test-Path -LiteralPath $App)) "app folder removed entirely (runtime, extras, __pycache__)" $(if ($left.Count) { "$($left.Count) left: " + (($left | Select-Object -First 8) -join ", ") } else { "gone" })
  Check "W8.3" (-not (Run-Value)) "Run key value removed"
  Check "W8.4" (-not (Test-Path -LiteralPath $Lnk)) "Start menu shortcut removed"
  Check "W8.5" ((@(Arp-Entries).Count -eq 0) -and (Product-State $code2) -ne 5) "no product in Settings > Apps"
  Check "W8.6" (-not (Test-Path -LiteralPath $ShieldKey)) "HKCU\Software\RAGbase\Shield removed" $(if (Test-Path "HKCU:\Software\RAGbase") { "HKCU\Software\RAGbase: " + ((Get-ChildItem "HKCU:\Software\RAGbase" | ForEach-Object { $_.PSChildName }) -join ",") } else { "HKCU\Software\RAGbase gone too" })
  Start-Sleep -Seconds 2
  $leftProcs = @(Shield-Procs)
  Check "W8.7" ($leftProcs.Count -eq 0) "no Shield process left" "$($leftProcs.Count)"
  Check "W8.8" (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) "port $Port free"
  $kept = @(Get-ChildItem -LiteralPath $Data -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }) | Sort-Object
  Check "W8.9" ((Test-Path -LiteralPath $Data) -and (File-Sha (Join-Path $Data "desk_token")) -eq $tokSha) "data folder kept (%LOCALAPPDATA%\ragbase-shield, same token)" ($kept -join ", ")
  $gone = @("install.json", "service.pid", "service.pid.txt", "desk.pid", "service.cmd") | Where-Object { Test-Path (Join-Path $Data $_) }
  Check "W8.10" ($gone.Count -eq 0) "installer files removed from the data folder (install.json, PID files)" ($gone -join ", ")
  $leak = @(Token-Leaks $tokenSeen)
  Check "W8.11" ($leak.Count -eq 0) "token in none of the logs (service, desk, msiexec install, upgrade, uninstall)" ($leak -join ", ")

  # ---------------------------------------------------------------- W8b: removal while an AI app holds the runtime
  Log "--- W8b install $($vars1.Version) again, hold python.exe with an MCP server, then msiexec /x /qn"
  $rc = Run-Msi @("/i", "`"$Msi`"", "/qn", "/l*v", "`"$(Join-Path $logs 'install2.log')`"")
  $up3 = Wait-Desk 120
  Check "W8b.1" ($rc -eq 0 -and $up3) "install again after the removal: exit 0, Desk 200" "exit $rc"
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $Py
  $psi.Arguments = "-I -X utf8 -m ragbase_shield mcp"
  $psi.UseShellExecute = $false
  $psi.RedirectStandardInput = $true   # the MCP server waits on stdin: python.exe and its DLLs stay in use
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.WorkingDirectory = $Work
  $psi.EnvironmentVariables["RAGBASE_SHIELD_KEYRING"] = "0"
  $psi.EnvironmentVariables["RAGBASE_SHIELD_HOME"] = $TmpHome
  $mcpProc = [Diagnostics.Process]::Start($psi)
  Start-Sleep -Seconds 8
  $tokSha3 = File-Sha (Join-Path $Data "desk_token")
  $t4 = Get-Date
  $rc = Run-Msi @("/x", $code1, "/qn", "/l*v", "`"$(Join-Path $logs 'uninstall-inuse.log')`"")
  $secs = [math]::Round(((Get-Date) - $t4).TotalSeconds, 1)
  $mcpAlive = -not $mcpProc.HasExited
  $pendingRenames = @()   # not $pending: PowerShell names are case-insensitive, and $script:Pending is the counter
  try {
    $pf = (Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager" -Name PendingFileRenameOperations -ErrorAction Stop).PendingFileRenameOperations
    $pendingRenames = @($pf | Where-Object { $_ -and $_.ToLower().Contains($AppLow) })
  } catch { }
  # Measured on the VM (2026-11-03, review build and final build): msiexec returns 0 here, not 3010, although the files
  # in use are moved to C:\Config.Msi\*.rbf for the next reboot ("1903" lines in the log). Both codes mean "done, no
  # reboot, no prompt"; the IT sheet lists both.
  Check "W8b.2" ($rc -eq 0 -or $rc -eq 3010) "msiexec /x with python.exe in use: exit 0 or 3010 (files in use finish at the next reboot), no reboot, no prompt" "exit $rc, $secs s, MCP server still alive: $mcpAlive"
  Check "W8b.3" ((@(Arp-Entries).Count -eq 0) -and (Product-State $code1) -ne 5 -and -not (Run-Value) -and -not (Test-Path -LiteralPath $Lnk)) "product, Run key and shortcut gone even so"
  $leftInUse = @(Get-ChildItem -LiteralPath $App -Recurse -File -ErrorAction SilentlyContinue)
  Info "W8b.4" "left in the app folder until the next reboot: $($leftInUse.Count) file(s) held by the MCP server; $($pendingRenames.Count) pending delete entries name the app folder"
  Check "W8b.5" ((Test-Path -LiteralPath $Data) -and (File-Sha (Join-Path $Data "desk_token")) -eq $tokSha3) "data folder kept"
  try { $mcpProc.Kill(); $null = $mcpProc.WaitForExit(10000) } catch { }
  Start-Sleep -Seconds 2
  Remove-Item -Recurse -Force -LiteralPath $App -ErrorAction SilentlyContinue
  Check "W8b.6" (-not (Test-Path -LiteralPath $App)) "app folder removable once the AI app has closed (no reboot needed for that)"
  $leak = @(Token-Leaks $tokenSeen)
  Check "W8b.7" ($leak.Count -eq 0) "token in none of the new logs (reinstall, second install, removal in use)" ($leak -join ", ")
} finally {
  # ---------------------------------------------------------------- network evidence
  New-Item -ItemType File -Force $stopFile | Out-Null
  $null = $sampler.WaitForExit(60000)
  $net = $null
  try { $net = Get-Content $netJson -Raw | ConvertFrom-Json } catch { }
  if ($net) {
    $isLoop = { param($a) $a -match '^(127\.0\.0\.1|\[::1\]|0\.0\.0\.0|\[::\]|\*):(\d+|\*)$' }
    $isLocalLoop = { param($a) $a -match '^(127\.0\.0\.1|\[::1\]):\d+$' }
    $shieldProcs = @($net.processes | Where-Object { $_.kind -ne "msiexec" })
    $shieldSocks = @($net.sockets | Where-Object { $_.kind -ne "msiexec" })
    $msiSocks = @($net.sockets | Where-Object { $_.kind -eq "msiexec" })
    $badShield = @($shieldSocks | Where-Object { -not (& $isLoop $_.remote) -or -not (& $isLocalLoop $_.local) })
    $badMsi = @($msiSocks | Where-Object { -not (& $isLoop $_.remote) })
    Info "N0" "net_sampler: $($net.samples) netstat samples and $($net.process_scans) process scans in $($net.seconds) s (every $($net.interval_ms) ms); $($shieldProcs.Count) Shield processes, $(@($net.processes | Where-Object { $_.kind -eq 'msiexec' }).Count) msiexec processes seen"
    Check "N1" ($shieldProcs.Count -ge 4 -and $badShield.Count -eq 0) "Shield processes: no socket to or from a non-loopback address during install, start, update and uninstall" ((($shieldSocks | ForEach-Object { "$($_.kind) $($_.proto) $($_.local)>$($_.remote) $($_.state)" }) | Sort-Object -Unique) -join "; ")
    Check "N2" ($badMsi.Count -eq 0) "msiexec processes: no connection to a remote address" ((($msiSocks | ForEach-Object { "$($_.proto) $($_.local)>$($_.remote) $($_.state)" }) | Sort-Object -Unique) -join "; ")
  } else {
    Check "N1" $false "network sampler produced no result"
  }
  $dnsAfter = @(Get-DnsClientCache -ErrorAction SilentlyContinue | ForEach-Object { $_.Entry }) | Sort-Object -Unique
  $newDns = @($dnsAfter | Where-Object { $dnsBefore -notcontains $_ })
  $suspect = @($newDns | Where-Object { $_ -match "pypi|pythonhosted|github|huggingface|ragbase|anthropic|openai|astral|python\.org" })
  Info "N3" "DNS cache (whole machine, other programs included): $($newDns.Count) new names during the test; names a Shield update or download would use: $(if ($suspect.Count) { $suspect -join ', ' } else { 'none' })"

  # ---------------------------------------------------------------- clean-up: leave the machine as it was
  foreach ($c in @([string]$vars1.ProductCode, [string]$vars2.ProductCode)) {
    if ((Product-State $c) -eq 5) {
      Log "cleanup: uninstalling leftover product $c"
      $null = Run-Msi @("/x", $c, "/qn", "/l*v", "`"$(Join-Path $logs 'cleanup-uninstall.log')`"")
    }
  }
  foreach ($p in @(Shield-Procs)) { try { Stop-Process -Id $p.ProcessId -Force } catch { } }
  if (Test-Path -LiteralPath $App) { Remove-Item -Recurse -Force -LiteralPath $App -ErrorAction SilentlyContinue }
  if (-not $pre.data -and (Test-Path -LiteralPath $Data)) {
    Remove-Item -Recurse -Force -LiteralPath $Data -ErrorAction SilentlyContinue
    Log "cleanup: removed the test's data folder $Data (it did not exist before)"
  }
  if (-not $pre.programs -and (Test-Path -LiteralPath $Programs) -and -not (Get-ChildItem -LiteralPath $Programs -Force)) {
    Remove-Item -Force -LiteralPath $Programs
    Log "cleanup: removed the empty $Programs (it did not exist before)"
  }
  if ((Run-Value)) { Remove-ItemProperty -LiteralPath $RunKey -Name $RunValue -ErrorAction SilentlyContinue }
  if (-not $pre.runkey -and (Test-Path -LiteralPath $RunKey)) {
    $k = Get-Item -LiteralPath $RunKey
    if ($k.ValueCount -eq 0 -and $k.SubKeyCount -eq 0) { Remove-Item -LiteralPath $RunKey; Log "cleanup: removed the empty Run key (it did not exist before)" }
  }
  if (-not $pre.ragbasekey -and (Test-Path "HKCU:\Software\RAGbase")) {
    Remove-Item -Recurse -LiteralPath "HKCU:\Software\RAGbase" -ErrorAction SilentlyContinue
    Log "cleanup: removed HKCU\Software\RAGbase (it did not exist before)"
  }
  if (Test-Path -LiteralPath $TmpHome) { Remove-Item -Recurse -Force -LiteralPath $TmpHome -ErrorAction SilentlyContinue }
  Log "PENDING W9 tray visual check: needs an interactive desktop session of this user (TEST_PLAN_tray.md)"
  $script:Pending++
  Log "RESULT: $($script:Pass) passed, $($script:Fail) failed, $($script:Pending) pending"
}
if ($script:Fail -gt 0) { exit 1 }
exit 0
