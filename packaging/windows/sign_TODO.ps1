# Sign the Windows installer (packaging/DESIGN.md section 14). NOT RUN YET: no certificate exists.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File sign_TODO.ps1 -Dir C:\shield_pkg\b-<v>
#
# Exits with code 2 ("TODO: certificate not configured") until both are set:
#   $env:SHIELD_SIGN_THUMBPRINT  SHA-1 thumbprint of the code-signing certificate in the user's certificate store
#                                (OV or EV; an EV certificate usually lives on a hardware token), or "trusted-signing"
#   $env:SHIELD_SIGNTOOL         full path of signtool.exe (Windows SDK, "App Certification Kit" folder)
#   For Azure Trusted Signing also: $env:SHIELD_TS_DLIB (Azure.CodeSigning.Dlib.dll), $env:SHIELD_TS_METADATA (metadata.json)
# Steps, after build.sh has left <Dir>\payload and <Dir>\out\*.msi (unsigned) on the build VM:
#   1. sign every PE file of the payload (exe, dll, pyd) that has no valid signature yet (the Microsoft runtime
#      DLLs already carry Microsoft's): python-build-standalone and the wheels ship unsigned binaries, and Smart
#      App Control, WDAC or AppLocker publisher rules check each one;
#   2. write MANIFEST.json again from the signed files (same format as build_payload.py);
#   3. rebuild the .msi from the signed payload (build_msi.ps1 -NoUnpack) and sign the .msi;
#   4. verify: signtool verify /pa on the .msi and Get-AuthenticodeSignature = Valid on every PE file.
# Full explanation, certificate options and checks: packaging/windows/TODO_SIGNING.md.
param([Parameter(Mandatory = $true)][string]$Dir)
$ErrorActionPreference = "Stop"
$thumb = $env:SHIELD_SIGN_THUMBPRINT
$signtool = $env:SHIELD_SIGNTOOL
if (-not $thumb -or -not $signtool -or -not (Test-Path -LiteralPath $signtool)) {
  Write-Output "TODO: certificate not configured (set SHIELD_SIGN_THUMBPRINT and SHIELD_SIGNTOOL, see TODO_SIGNING.md)"
  exit 2
}
$Root = "C:\shield_pkg"
$Dir = [IO.Path]::GetFullPath($Dir)
if (-not $Dir.StartsWith("$Root\", [StringComparison]::OrdinalIgnoreCase)) { throw "outside $Root : $Dir" }
$payload = Join-Path $Dir "payload"
$ts = "http://timestamp.digicert.com"
if ($thumb -eq "trusted-signing") {
  $how = @("/fd", "SHA256", "/tr", "http://timestamp.acs.microsoft.com", "/td", "SHA256",
           "/dlib", $env:SHIELD_TS_DLIB, "/dmdf", $env:SHIELD_TS_METADATA)
} else {
  $how = @("/fd", "SHA256", "/tr", $ts, "/td", "SHA256", "/sha1", $thumb)
}

# 1. PE files without a valid signature, in batches (signtool takes many files per call)
$pe = @(Get-ChildItem -LiteralPath $payload -Recurse -File -Include *.exe, *.dll, *.pyd |
        Where-Object { (Get-AuthenticodeSignature -LiteralPath $_.FullName).Status -ne "Valid" })
Write-Output "sign: $($pe.Count) unsigned PE files"
for ($i = 0; $i -lt $pe.Count; $i += 50) {
  $batch = @($pe[$i..([Math]::Min($i + 49, $pe.Count - 1))] | ForEach-Object { $_.FullName })
  & $signtool sign @how /d "RAGbase Shield" /du "https://ragbase.ai" @batch
  if ($LASTEXITCODE -ne 0) { throw "signtool failed on batch $i" }
}

# 2. MANIFEST.json again (sha256 of every file, the format of packaging/common/build_payload.py)
$py = Join-Path $payload "runtime\python.exe"
$code = @'
import hashlib, json, os, sys
root = sys.argv[1]
files = {}
for dp, dn, fn in os.walk(root):
    for n in fn:
        p = os.path.join(dp, n)
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        if rel != "MANIFEST.json":
            files[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
version = open(os.path.join(root, "VERSION"), encoding="utf-8").read().strip()
data = {"version": version, "files": dict(sorted(files.items())), "count": len(files)}
open(os.path.join(root, "MANIFEST.json"), "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=1, sort_keys=True) + "\n")
'@
& $py -I -c $code $payload
if ($LASTEXITCODE -ne 0) { throw "MANIFEST.json rewrite failed" }

# 3. rebuild the .msi from the signed payload, then sign it
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dir "build_msi.ps1") -Dir $Dir -NoUnpack
if ($LASTEXITCODE -ne 0) { throw "build_msi.ps1 -NoUnpack failed" }
$msi = @(Get-ChildItem (Join-Path $Dir "out") -Filter *.msi)[0].FullName
& $signtool sign @how /d "RAGbase Shield" /du "https://ragbase.ai" $msi
if ($LASTEXITCODE -ne 0) { throw "signtool failed on the msi" }

# 4. verify
& $signtool verify /pa /v $msi
if ($LASTEXITCODE -ne 0) { throw "signtool verify failed" }
$bad = @(Get-ChildItem -LiteralPath $payload -Recurse -File -Include *.exe, *.dll, *.pyd |
         Where-Object { (Get-AuthenticodeSignature -LiteralPath $_.FullName).Status -ne "Valid" })
if ($bad.Count) { throw "$($bad.Count) PE files still without a valid signature" }
Write-Output "sign: OK $msi"
exit 0
