# Network sampling for test_install.ps1 (no admin change: no firewall log, no capture driver, no setting).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File net_sampler.ps1 -Out <json> -StopFile <file> -App <app folder>
#
# Until <StopFile> exists: "netstat -ano" about 4 times a second (every TCP connection, listening socket and
# UDP endpoint of the machine, with its PID), and every second the list of processes whose program lies in
# <App> (RAGbase Shield.exe, python.exe of the private runtime) or is msiexec.exe. At the end it writes <Out>:
# the processes seen and every socket row of those processes. test_install.ps1 then fails on any remote address
# that is not loopback. Limit: a connection shorter than one sampling interval can be missed (said in the report).
param(
  [Parameter(Mandatory = $true)][string]$Out,
  [Parameter(Mandatory = $true)][string]$StopFile,
  [Parameter(Mandatory = $true)][string]$App,
  [int]$IntervalMs = 250
)
$ErrorActionPreference = "SilentlyContinue"
$appLow = $App.TrimEnd("\").ToLower() + "\"
$ours = @{}      # pid -> @{ name; kind; first }
$rows = @{}      # "pid|proto|local|remote|state" -> first seen (s)
$checked = @{}   # PIDs looked up when first seen in netstat
$samples = 0
$procScans = 0
$t0 = Get-Date
$nextProc = 0.0

function Classify($p, [double]$now) {
  $path = [string]$p.ExecutablePath
  $kind = $null
  if ($path -and $path.ToLower().StartsWith($script:appLow)) {
    $cl = [string]$p.CommandLine
    if ($cl -match "service run") { $kind = "supervisor" }
    elseif ($cl -match "desk --service") { $kind = "desk" }
    else { $kind = "shield-other" }
  } elseif ($p.Name -ieq "msiexec.exe") { $kind = "msiexec" }
  if ($kind -and -not $script:ours.ContainsKey([int]$p.ProcessId)) {
    $script:ours[[int]$p.ProcessId] = @{ name = [string]$p.Name; kind = $kind; first = [math]::Round($now, 2) }
  }
}

function Scan-Processes {
  $now = ((Get-Date) - $script:t0).TotalSeconds
  foreach ($p in Get-CimInstance Win32_Process -Property ProcessId, Name, ExecutablePath, CommandLine) {
    Classify $p $now
    $script:checked[[string]$p.ProcessId] = $true  # known: no single lookup needed later
  }
  $script:procScans++
}

while (-not (Test-Path -LiteralPath $StopFile)) {
  $elapsed = ((Get-Date) - $t0).TotalSeconds
  if ($elapsed -ge $nextProc) { Scan-Processes; $nextProc = $elapsed + 1.0 }
  $lines = netstat -ano
  $samples++
  foreach ($ln in $lines) {
    $f = ($ln.Trim() -split "\s+")
    if ($f.Count -lt 4) { continue }
    if ($f[0] -eq "TCP" -and $f.Count -ge 5) { $procId = $f[4]; $state = $f[3] }
    elseif ($f[0] -eq "UDP") { $procId = $f[$f.Count - 1]; $state = "" }
    else { continue }
    $key = "$procId|$($f[0])|$($f[1])|$($f[2])|$state"
    if (-not $rows.ContainsKey($key)) {
      $rows[$key] = [math]::Round($elapsed, 2)
      # A PID seen for the first time is looked up at once: a short-lived Shield process (a custom action
      # runs for 1 to 3 s) is caught even between two process scans.
      if (-not $checked.ContainsKey($procId)) {
        $checked[$procId] = $true
        $one = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -Property ProcessId, Name, ExecutablePath, CommandLine
        if ($one) { Classify $one $elapsed }
      }
    }
  }
  Start-Sleep -Milliseconds $IntervalMs
}
Scan-Processes
$dur = ((Get-Date) - $t0).TotalSeconds
$procs = @()
foreach ($k in $ours.Keys) { $procs += [pscustomobject]@{ pid = $k; name = $ours[$k].name; kind = $ours[$k].kind; first = $ours[$k].first } }
$sockets = @()
foreach ($k in $rows.Keys) {
  $parts = $k -split "\|"
  $procId = [int]$parts[0]
  if ($ours.ContainsKey($procId)) {
    $sockets += [pscustomobject]@{ pid = $procId; kind = $ours[$procId].kind; proto = $parts[1]; local = $parts[2];
                                   remote = $parts[3]; state = $parts[4]; first = $rows[$k] }
  }
}
$result = [pscustomobject]@{ samples = $samples; process_scans = $procScans; seconds = [math]::Round($dur, 1);
                             pids_looked_up = $checked.Count;
                             interval_ms = $IntervalMs; processes = $procs; sockets = $sockets }
$result | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $Out
