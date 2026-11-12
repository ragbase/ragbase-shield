# Windows signing: what is needed and the exact steps (not done yet)

Status: the `.msi` and every program inside it are **unsigned**. Nothing here was run: there is no certificate yet.
`packaging/windows/sign_TODO.ps1` exits with code 2 ("TODO: certificate not configured") until the two settings of
section 3 exist. Nothing is faked: no self-signed certificate, no test certificate.

## 1. What the unsigned build costs today

| Where | What the user sees | Who can get past it |
|---|---|---|
| Download in Edge or Chrome | "RAGbase-Shield-...msi isn't commonly downloaded", "Keep" hidden under "..." | The user |
| Double-click (SmartScreen) | "Windows a protégé votre ordinateur": "Informations complémentaires", then "Exécuter quand même" | The user, unless a policy hides the button |
| Windows 11 Smart App Control (on for new installs) | Blocks unsigned programs and DLLs, with no button to go on | Nobody: Smart App Control must be turned off (it cannot be turned on again without a reset) |
| Firm policy: AppLocker or WDAC (Windows Defender Application Control) | The .msi or `RAGbase Shield.exe` does not start | IT, with a publisher rule: needs a signature |
| Settings > Apps | Publisher "RAGbase" (from the MSI), no signature check | Nobody needs to |

## 2. Certificate: the three choices

| Choice | SmartScreen | Cost and constraint | Fits |
|---|---|---|---|
| Azure Trusted Signing (Microsoft) | Trusted from the first download | Monthly fee per account; the organisation must pass Microsoft's identity validation (company registration, 3 years of history for some regions) | The simplest if RAGbase qualifies: no hardware token, works from any build machine with `signtool` + the Trusted Signing dlib |
| EV code-signing certificate (DigiCert, Sectigo, GlobalSign...) | Trusted from the first download | Yearly fee; the key lives on a hardware token (USB) or a cloud HSM: the token must be plugged into the build machine, or the CA's cloud signing service used | Good when Trusted Signing is not open to RAGbase |
| OV code-signing certificate | Warnings until the file builds reputation (weeks, many downloads) | Lower yearly fee; since 2023 also on a token or HSM | Second choice |

The publisher supplies one of them. The rest is ready.

## 3. Settings on the Windows build machine (before `sign_TODO.ps1`)

| Setting | Value |
|---|---|
| `signtool.exe` | Windows SDK, "Signing Tools for Desktop Apps" component. User-level: install the SDK on another machine and copy the `x64` folder of `signtool.exe` (with `signtool.exe.manifest`, `wintrust.dll` is part of Windows) to `C:\shield_pkg\signtool\`. `$env:SHIELD_SIGNTOOL = "C:\shield_pkg\signtool\signtool.exe"` |
| OV or EV certificate | Import it into the current user's store (`certmgr.msc`, "Personal"), or plug in the token. `$env:SHIELD_SIGN_THUMBPRINT = "<40 hex characters>"` (`Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert`) |
| Azure Trusted Signing | `$env:SHIELD_SIGN_THUMBPRINT = "trusted-signing"`, `$env:SHIELD_TS_DLIB = "<path>\Azure.CodeSigning.Dlib.dll"` (NuGet package Microsoft.Trusted.Signing.Client), `$env:SHIELD_TS_METADATA = "<path>\metadata.json"` with `{"Endpoint": "https://<region>.codesigning.azure.net", "CodeSigningAccountName": "...", "CertificateProfileName": "..."}`; sign in with `az login` (or a service principal in `AZURE_*` variables) |

## 4. The exact steps (what `sign_TODO.ps1` does)

Run on the Windows build machine, after `build_msi.ps1` (which leaves `C:\shield_pkg\b-<v>\payload` and the unsigned
`out\RAGbase-Shield-<v>-win64.msi`):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\shield_pkg\b-<v>\sign_TODO.ps1 -Dir C:\shield_pkg\b-<v>
```

1. Sign every PE file of the payload that has no valid signature yet: the payload holds 137 PE files (`python.exe`,
   `pythonw.exe`, `RAGbase Shield.exe`, `python312.dll`, `python3.dll`, the `DLLs\*.pyd` of the runtime, and the
   `.pyd` / `.dll` files of the wheels: cryptography, lxml, pydantic-core, pypdfium2, pywin32, pillow, rpds-py,
   charset-normalizer, and the `.exe` launchers kept inside pip and setuptools). The Microsoft runtime DLLs (`vcruntime140.dll`, `vcruntime140_1.dll`) already carry a
   valid Microsoft signature and are left as they are. Command per batch of 50 files:

   ```powershell
   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /sha1 <THUMBPRINT> /d "RAGbase Shield" /du "https://ragbase.ai" <files...>
   # Trusted Signing instead of /sha1:  /tr http://timestamp.acs.microsoft.com /td SHA256 /dlib <dlib> /dmdf <metadata.json>
   ```

2. Write `MANIFEST.json` again from the signed files (same format as `packaging/common/build_payload.py`; the
   signed tree is then the reproducibility unit of the release).
3. Rebuild the `.msi` from the signed payload: `build_msi.ps1 -Dir C:\shield_pkg\b-<v> -NoUnpack` (same WiX,
   same `msi_vars.json`, ICE validation again), then sign the `.msi` itself:

   ```powershell
   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /sha1 <THUMBPRINT> /d "RAGbase Shield" /du "https://ragbase.ai" out\RAGbase-Shield-<v>-win64.msi
   ```

4. Verify, and stop on any failure:

   ```powershell
   signtool verify /pa /v out\RAGbase-Shield-<v>-win64.msi
   Get-ChildItem payload -Recurse -Include *.exe,*.dll,*.pyd | Get-AuthenticodeSignature | Where-Object Status -ne Valid   # must print nothing
   ```

Then copy the signed `.msi` to `dist/`, write `dist/SHA256SUMS`, and run `packaging/windows/test_install.ps1` again
on the signed files.

## 5. Checks after the first signed build

| Check | How | Expected |
|---|---|---|
| Signature of the .msi | Explorer > Properties > Digital Signatures, or `Get-AuthenticodeSignature` | "RAGbase", timestamped, Valid |
| SmartScreen | Download from a web page in Edge on a clean Windows 11, double-click | No blue SmartScreen screen (EV or Trusted Signing); OV: may still warn for a while |
| Smart App Control | A Windows 11 machine with Smart App Control "On": install, then let Shield Desk start | Install and start work; nothing in "Protection history" |
| Programs after install | `Get-AuthenticodeSignature "$env:LOCALAPPDATA\Programs\RAGbase Shield\runtime\RAGbase Shield.exe"` | Valid |
| Bytecode | Python writes `.pyc` files at the first start (not signed, not executables) | No effect on the checks above |
| NER extras | `ragbase-shield ner install` downloads torch and others later: their DLLs are signed by their makers or not at all | Smart App Control may block NER on an unsigned wheel: test once and note it in the install guide |

## 6. Not covered by signing

- A firm that forbids per-user installs (`DisableUserInstalls`) or programs under the user profile (AppLocker
  default rules) still needs the per-machine variant (`Scope="perUserOrMachine"`, administrator, `%ProgramFiles%`),
  a follow-up item.
- The Start menu shortcut and the Run key start `RAGbase Shield.exe`, a copy of `pythonw.exe`: once signed with
  RAGbase's certificate, AppLocker and WDAC publisher rules can allow it by name.
