# RAGbase Shield desktop installers

One installer per platform, no Terminal, no administrator password: a private Python runtime with Shield goes
into the user's own folder, a login item runs Shield Desk in the background, and a menu bar (macOS) or tray
(Windows) icon controls it. User guide: `docs/INSTALL.md`, section 0. Contract: `ARCHITECTURE.md`.

## Status of 0.4.0

| Platform | Installer | State |
|---|---|---|
| macOS 13 or later, Intel and Apple Silicon | `RAGbase-Shield-<version>.pkg` (universal, the default download); `-x86_64.pkg` and `-arm64.pkg` (half size) | **Built, unsigned.** Built from commit fd8662d of the development history (the same Shield code as this release, except two comments and one docstring). Level-1 test on an Intel Mac: 58 of 58 checks (universal), 56 of 56 (Intel only); the Apple Silicon package passed its static checks only. Not done yet: the manual test with a fresh account, a run on an Apple Silicon Mac, signing. |
| Windows 10 and 11, x64 | `RAGbase-Shield-<version>-win64.msi` (per user, no administrator) | **Built, unsigned.** Built from the same commit. Level-1 test on a Windows Server 2025 test machine, two runs (a new install of 0.4.0, and the update from 0.3.1 to 0.4.0): 65 of 65 checks pass in each run; the tray visual check W9 is pending. Not done yet: the tray on a desktop session (W9), a run on a real Windows 10 or 11 PC, an install by an account without administrator rights, signing. |

The version is the one in `pyproject.toml`. The build reads it, so a new version needs only a rebuild.

## What the installers do

| Step | macOS | Windows |
|---|---|---|
| Install | Double-click the `.pkg`. Installer, "Install for me only" (home domain, `auth="none"`): no administrator password | Double-click the per-user `.msi` (`Scope="perUser"`): no UAC prompt |
| App folder | `~/Library/Application Support/RAGbase Shield/` | `%LOCALAPPDATA%\Programs\RAGbase Shield\` |
| Payload | Private Python 3.12.15 (python-build-standalone) with Shield and its dependencies inside, `bin/ragbase-shield` launcher, icons, licences. No pip and no network at install time | Same, plus `bin\ragbase-shield.cmd` and `runtime\RAGbase Shield.exe` (a copy of `pythonw.exe`, for the process name) |
| Registration | `postinstall` keeps the runtime of this Mac (CPU read with `sysctl hw.optional.arm64`, correct under Rosetta), then runs `ragbase-shield service install` | MSI custom actions run `service install --no-start`, then `service start` |
| Login item | LaunchAgent `~/Library/LaunchAgents/ai.ragbase.shield.plist` that runs the `RAGbase Shield.app` shell | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\RAGbase Shield`; Task Scheduler "at log on" is the manual fallback for firms whose policy ignores the Run key |
| Service | One supervisor (the icon) and one Shield Desk child on `127.0.0.1:7878`, restarted after a crash, started at each login, stopped for good by "Quitter" | Same code |
| Menu | Status line, Ouvrir Shield Desk, Dossiers, Redémarrer, Lancer à l'ouverture de session, Ouvrir le journal, Désinstaller..., Quitter (French, or English on an English system) | Same items; status in "Statut..." and in the hover text |
| Update | Run a newer installer: the service stops, the runtime is replaced, `<home>` and `extras/` stay | `MajorUpgrade`: same rule |
| Uninstall | Icon > Désinstaller..., or `uninstall.sh` (data kept), `uninstall.sh --purge-data` (data deleted too, only Shield's own files in a custom data folder) | Icon > Désinstaller..., or Settings > Apps; the data folder is never removed by the MSI |
| Data folder | Unchanged: `~/.ragbase-shield` | Unchanged: `%LOCALAPPDATA%\ragbase-shield` |

Privacy rules (ARCHITECTURE.md section 2): no network call at install or at start, no telemetry, no update
check. Every socket goes to `127.0.0.1`. The only network step stays the optional NER download, started by the
user. The service only reads the Desk token, never logs or shows it. The `.mcpb`, the Claude Code plugin and the
browser extension are not changed and keep working.

Interpreter flags: service processes and install scripts run with `-E -s -P -X utf8`; the terminal and MCP
launchers run with `-I -X utf8`. `-P` and `-I` keep the current folder out of `sys.path` (a planted `json.py`
in a project folder must never run). The Windows custom actions and Run key must use the same flags.

## Build

### macOS (on a Mac, from a clean checkout)

Needs: Xcode command line tools (`pkgbuild`, `productbuild`, `pkgutil`, `lipo`, `iconutil`), uv 0.6.2 or later
(0.6.2 is the tested version), network once (python-build-standalone and wheels; later builds use
`build/cache`). Python 3.11+ with Pillow: the repo `.venv`, or `build.sh` makes `build/tools-venv` with
`pillow==13.0.0` (icons only, never shipped).

```sh
cd ragbase-shield
packaging/common/relock.sh               # only when pyproject.toml or build-constraints.in change; commit the locks
packaging/macos/build.sh                 # -> dist/RAGbase-Shield-<version>.pkg (universal) + .sha256
packaging/macos/build.sh --arch x86_64   # -> dist/RAGbase-Shield-<version>-x86_64.pkg
packaging/macos/build.sh --arch arm64    # -> dist/RAGbase-Shield-<version>-arm64.pkg
```

Every input is pinned by SHA-256: `common/pins.json` (runtime archives), `common/requirements-*.lock` (wheels),
`common/build-constraints.txt` (build backends). A wrong hash stops the build. `build.sh` warns when `src/`,
`pyproject.toml` or `packaging/` differ from the commit (`install_info.json` then records `<commit>+dirty`), and
holds `build/.build-lock` so that two builds in one checkout cannot overwrite each other.

Never link the Intel-only package for lawyers: on Apple Silicon, Installer asks for Rosetta, which can need an
administrator. The universal package needs no question.

### Windows (payload on a Mac or Linux machine, `.msi` on a Windows machine)

The payload builds on the build machine with the same inputs and pins as macOS. The `.msi` is built by WiX on a
Windows machine, in `C:\shield_pkg` only (user level, no administrator step).

```sh
packaging/windows/build.sh                                       # payload, staged copy, Components.wxs, payload.zip -> build/windows/msi-<version>/
packaging/windows/build.sh --msi-version 0.4.1 --reuse-payload   # same payload, higher MSI version (for the upgrade test)
```

Then, on the Windows machine:

```powershell
# copy build/windows/msi-<version>/ to C:\shield_pkg\b-<version>\
powershell -NoProfile -ExecutionPolicy Bypass -File C:\shield_pkg\b-<version>\build_msi.ps1 -Dir C:\shield_pkg\b-<version>
# -> C:\shield_pkg\b-<version>\out\RAGbase-Shield-<version>-win64.msi and logs\*.log; copy the .msi back to dist/
```

Steps of `build.sh`: icons, wheel (`uv build` with the hashed build constraints), `build_payload.py windows-x64`
(python-build-standalone 3.12, the wheels of `requirements-windows-x64.lock`, `bin\ragbase-shield.cmd`,
`runtime\RAGbase Shield.exe` as a copy of `pythonw.exe`), `stage_payload.py` (MSI version, `ProductCode`,
`uninstall.cmd`, `MANIFEST.json` again), `check_payload.py`, `gen_components.py`, a deterministic `payload.zip`
(sorted entries, commit time); then on the Windows machine `build_msi.ps1`: .NET SDK 8.0 from `dotnet-install.ps1` into
`C:\shield_pkg\dotnet` and WiX 5.0.2 as a dotnet tool in `C:\shield_pkg\tools` (user level, installed once, never
on the PATH, telemetry off), SHA-256 check of the zip, every file checked against `MANIFEST.json`,
`wix build -arch x64`, `wix msi validate`, and the SHA-256 of the `.msi` in its log. No build tool is shipped.

`ProductCode` = uuid5 of the version under `shield_ns`; `UpgradeCode` is fixed in `pins.json` and must never
change. The Windows Installer compares only the first three fields of `Version`: an upgrade test uses `0.4.1`,
not `0.4.0.1`.

Every `.msi` handed to anyone must carry a new version: `ProductCode` follows the version, so a package with the
same version as the installed one runs in maintenance mode (the service restarts, no file is replaced; W7.0 of
`test_install.ps1` checks it). A rebuild of the same version from a newer commit is invisible on a machine that
holds the first build: bump the version, or have the tester uninstall first. The package sets
`REBOOT=ReallySuppress` and the silent commands carry `/norestart`: with a file in use (an AI app runs the MCP
server from `runtime\`), msiexec moves the file to `C:\Config.Msi` for the next reboot and returns 0 (measured on
a test machine) or 3010, instead of rebooting a `/qn` install at once (the Windows Installer default; W8b checks it: no
reboot, no prompt, product gone, data kept).

### Build scripts

| Script | Role |
|---|---|
| `common/pins.json` | Runtime release, file names, SHA-256, prune lists, bundle ids, minimum macOS, Windows `UpgradeCode` and uuid5 namespace |
| `common/relock.sh` | `uv pip compile --generate-hashes` for macOS arm64, macOS x86_64, Windows x64, and the build backends |
| `common/build-constraints.in`, `build-constraints.txt` | hatchling, setuptools and wheel pinned with hashes: the Shield wheel and the rumps / infi.systray sdists are built with the same backend every time |
| `common/fetch.py` | Downloads and verifies a runtime archive (fails on a hash change unless `--repin`) |
| `common/prune_runtime.py` | Removes Tcl/Tk, IDLE, tests, headers, `libpython3.12.dylib` (unused: the binary is static), `.dSYM` |
| `common/build_payload.py` | One payload per target; `merge-macos` makes the universal payload; drops `uv_cache.json`, `direct_url.json` and their `RECORD` lines (reproducible manifests) |
| `common/licenses.py` | `LICENSES/` tree and table; fails on GPL, LGPL, AGPL or a missing licence |
| `common/check_payload.py` | Licences, no build-machine or repo path, no Tcl/Tk, `MANIFEST.json` matches the tree, every `RECORD` line ships, no em dash, no group- or world-writable file, no setuid bit, no link out of the payload, sizes |
| `common/make_tray_icons.py` | Menu bar template (44 px), `.ico`, `.icns` from `integrations/assets/icon-512.png` |
| `macos/build.sh` | The whole macOS build (`build_pkg.sh` is the same script under another name) |
| `macos/Distribution.xml`, `macos/resources/` | Home domain only, macOS 13 check (French and English message), French welcome and conclusion pages with an English summary, Apache-2.0 licence |
| `macos/scripts/preinstall`, `postinstall` | Stop the old service, keep the right runtime, `service install`; both refuse an install folder not named "RAGbase Shield" |
| `macos/uninstall.sh` | Copied into the app folder |
| `macos/ai.ragbase.shield.plist` | Reference copy of the LaunchAgent (a unit test checks that the code renders exactly this) |
| `macos/test_payload.sh` | Level-1 test in a temporary HOME |
| `macos/menubar_items.py` | Test helper: counts menu bar item windows (no screen capture) |
| `macos/compare_pkgs.sh` | Compares two `.pkg` files part by part (Payload, Bom, PackageInfo, Scripts, Distribution, Resources) |
| `macos/TODO_SIGNING.md`, `macos/sign_and_notarize_TODO.sh`, `macos/python.entitlements` | Signing and notarisation, not run |
| `windows/build.sh` | The build-machine part of the Windows build: payload, staging, `Components.wxs`, deterministic zip |
| `windows/Package.wxs` | WiX 5 source: `Scope="perUser"`, `MajorUpgrade`, Start menu shortcut, Settings > Apps entry with Uninstall only, custom actions that run `runtime\RAGbase Shield.exe -E -s -P -X utf8 -m ragbase_shield service ...` from `%LOCALAPPDATA%` (never from the app folder) |
| `windows/gen_components.py` | `Components.wxs` from the staged payload: one component per folder, HKCU `KeyPath`, `RemoveFolder`, `*.pyc` clean-up of the `__pycache__` folders Python writes at first start |
| `windows/stage_payload.py` | MSI version and `ProductCode` into `install_info.json` and `uninstall.cmd`, `MANIFEST.json` again, `msi_vars.json` for `wix build -d` |
| `windows/build_msi.ps1` | On the Windows machine: user-level dotnet and pinned WiX, zip and manifest checks, `wix build`, `wix msi validate`, SHA-256 of the `.msi` |
| `windows/uninstall.cmd` | Copied into the app folder: `msiexec /x {ProductCode}` run from `%SystemRoot%` (data folder kept; `/qn` for IT) |
| `windows/test_install.ps1`, `windows/net_sampler.ps1`, `windows/mcp_probe.py` | Level-1 test on a Windows machine (W3 to W8 and the network sampling); `windows/test_basic_user.ps1` is the optional W10 check with a Basic User token |
| `windows/TEST_PLAN_tray.md` | The manual tray check W9 (needs an interactive session) |
| `windows/IT_SHEET.md` | For the firm's IT: paths, registry, silent commands, blocking policies, the Task Scheduler fallback |
| `windows/TODO_SIGNING.md`, `windows/sign_TODO.ps1` | Windows signing, not run (the script exits 2 without a certificate) |

## Test

| Level | Command | Where |
|---|---|---|
| Unit tests of the service and the packaging rules | `.venv/bin/python -m pytest -q tests/test_service_login_item.py tests/test_packaging_safety.py tests/test_local_only.py` | Dev venv; no launchd, no real HOME, no network |
| Level 1, macOS | `packaging/macos/test_payload.sh dist/RAGbase-Shield-<version>.pkg [<work_dir>]` | A Mac. Temporary HOME, `RAGBASE_SHIELD_KEYRING=0`, port 7878 must be free. It plays Installer (expanded payload, then the package's own pre/postinstall in a clean environment), bootstraps the LaunchAgent into the current GUI session for the test and removes it at the end, and checks that the real `~/Library/LaunchAgents`, `~/.ragbase-shield` and `~/Library/Application Support/RAGbase Shield` did not change. Do not run two at once (same launchd label, same port) |
| Level 2, macOS | `packaging/TEST_PLAN_macos.md` | A fresh macOS test account; Installer double-click, Gatekeeper, keychain and folder prompts, menu clicks; same steps on an Apple Silicon Mac without Rosetta |
| Unit tests of the Windows packaging rules | `.venv/bin/python -m pytest -q tests/test_packaging_windows.py` | Dev venv, any OS: `Package.wxs`, `gen_components.py`, `stage_payload.py`, `uninstall.cmd`, the signing TODO, the Windows fixes in `desk/` |
| Level 1, Windows | `test_install.ps1` on a Windows test machine, with two `.msi` files (the release version and a higher upgrade version): W3 to W8, the same package over itself (W7.0), a removal with the runtime in use (W8b), the network sampling | A test account with the product's real folders (`%LOCALAPPDATA%\Programs\RAGbase Shield`, `%LOCALAPPDATA%\ragbase-shield`, the HKCU Run key) and port 7878: it refuses to run over an existing install and puts back what did not exist before. The tray visual check (W9) needs an interactive session: `windows/TEST_PLAN_tray.md` |
| Reproducibility | Build the same commit in two clean clones, then `packaging/macos/compare_pkgs.sh a.pkg b.pkg` | Every part "same"; the `.pkg` SHA-256 always differs (xar creation time) |

## Sign (TODO; nothing is faked)

### macOS

Needs the Apple Developer Program (organisation account for the Team ID), the "Developer ID Application" and
"Developer ID Installer" certificates in the build keychain, and a notary profile. Full steps and checks:
`macos/TODO_SIGNING.md`. The script `macos/sign_and_notarize_TODO.sh` exits with code 2 until the identities exist.

```sh
xcrun notarytool store-credentials ragbase-notary --apple-id <apple-id> --team-id <TEAMID> --password <app-specific-password>
export SHIELD_APP_IDENTITY="Developer ID Application: RAGbase (TEAMID)"
export SHIELD_INSTALLER_IDENTITY="Developer ID Installer: RAGbase (TEAMID)"
export SHIELD_NOTARY_PROFILE=ragbase-notary
packaging/macos/build.sh
packaging/macos/sign_and_notarize_TODO.sh universal
#   1. codesign every Mach-O of both runtimes, leaves first: --options runtime --timestamp --entitlements python.entitlements
#   2. rebuild the component and product packages from the signed payload (build.sh --reuse-payload)
#   3. productsign --timestamp --sign "$SHIELD_INSTALLER_IDENTITY"
#   4. xcrun notarytool submit --wait ; xcrun stapler staple ; spctl --assess --type install -vv (expect "Notarized Developer ID")
```

The menu bar app shell is written at install time from the signed `python3.12`. Check its behaviour on the first
signed build (`macos/TODO_SIGNING.md`, section 3).

### Windows

Needs an OV or EV code-signing certificate, or an Azure Trusted Signing account (EV and Trusted Signing avoid the
SmartScreen warning from the first day; OV builds reputation over weeks). `packaging/windows/sign_TODO.ps1` exits
with code 2 until a certificate is configured. Steps (`windows/TODO_SIGNING.md`):

```powershell
# 1. sign what the login item and the launchers run (python-build-standalone binaries carry no Authenticode signature)
signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /sha1 <THUMBPRINT> `
  "payload\runtime\python.exe" "payload\runtime\pythonw.exe" "payload\runtime\RAGbase Shield.exe" `
  "payload\runtime\python312.dll" "payload\runtime\python3.dll"
# 2. rebuild the MSI from the signed payload (wix build ...), then sign it
signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /sha1 <THUMBPRINT> /d "RAGbase Shield" dist\RAGbase-Shield-<version>-win64.msi
signtool verify /pa /v dist\RAGbase-Shield-<version>-win64.msi
```

## Release checklist

| # | Step | Command or check |
|---|---|---|
| 1 | Version | `pyproject.toml` holds the release version; the `.mcpb` is built from the same commit and has the same version |
| 2 | Clean commit | `git status --porcelain -- src pyproject.toml packaging LICENSE NOTICE integrations/assets` prints nothing |
| 3 | Clean build account | Build from Terminal.app in a clean macOS account: an agent or IDE session adds `com.apple.provenance` attributes (`._` entries in the package; `build.sh` warns) |
| 4 | Locks | `packaging/common/relock.sh` only when the dependencies changed; commit the locks |
| 5 | macOS packages | `packaging/macos/build.sh`, then `--arch x86_64` and `--arch arm64`; each prints `check: OK` |
| 6 | Reproducibility | A second build in another clone; `packaging/macos/compare_pkgs.sh` says "same" for every part |
| 7 | Level-1 test | `packaging/macos/test_payload.sh dist/RAGbase-Shield-<version>.pkg`: every check PASS |
| 8 | Level-2 test | `packaging/TEST_PLAN_macos.md` on Intel and on Apple Silicon (no Rosetta) |
| 9 | Sign and notarise | Section "Sign" above; `spctl` says "accepted, source=Notarized Developer ID" |
| 10 | Windows build | From the same clean commit: `packaging/windows/build.sh` and `build_msi.ps1` (the `.msi` of the release version), then the same with `--msi-version <next> --reuse-payload` (the upgrade-test package only); both print `check: OK`, `wix build` 0 warnings, `wix msi validate` 0 errors |
| 10b | Windows test | `test_install.ps1`: every check PASS (W3 to W8, W8b, N1 to N3; W9 pending); then the tray check W9 of `windows/TEST_PLAN_tray.md` in a desktop session, then one run on a Windows 10 or 11 PC without administrator rights; then sign (`windows/TODO_SIGNING.md`) and run `test_install.ps1` once more on the signed file |
| 11 | Sums | `(cd dist && shasum -a 256 *.pkg *.msi *.mcpb > SHA256SUMS)`; publish the SHA-256 also on a separate HTTPS page |
| 12 | Publish | GitHub Release: the `.pkg`, the `.msi`, `SHA256SUMS`, the `.mcpb`. Then replace the screenshot placeholders of `docs/INSTALL.md` section 0 and update the download links |
| 13 | Updates | Users re-run the newer installer. There is no update check (it would be a network call at start) |

Release rule: once signing exists, the public download links point at signed builds only. Until then, every
release says clearly that the installers are unsigned.

### Screenshots for `docs/INSTALL.md` section 0

Take them during the level-2 tests, in French (and English for part 2), then remove the "à venir" / "to come"
lines.

| File | What it shows |
|---|---|
| `docs/img/install/mac-01-refus.png` | macOS refuses the unsigned `.pkg` |
| `docs/img/install/mac-02-ouvrir-quand-meme.png` | System Settings > Privacy & Security, "Open Anyway" |
| `docs/img/install/mac-03-installation.png` | Installer, "Install for me only", no password |
| `docs/img/install/mac-04-icone-et-menu.png` | The shield icon and its menu |
| `docs/img/install/win-01-smartscreen.png` | SmartScreen, "More info" then "Run anyway" |
| `docs/img/install/win-02-installation.png` | The MSI screens |
| `docs/img/install/win-03-icone-et-menu.png` | The tray icon and its menu |

## Release files of 0.4.0 (unsigned)

The four installers were built from commit fd8662d of the development history (`install_info.json` says
`"version": "0.4.0"` and `"source": "fd8662d120de"`, no `+dirty`). Their Shield code is the `src/` tree of this
repository, except one code comment in `cli.py`, one docstring in `config.py` and one comment line in
`engine/lexicon/en_first_names.txt` (text only, no change of
behaviour). The Claude Desktop extension (`ragbase-shield-0.4.0.mcpb`), the wheel and the source archive are built
from this repository at the tag `v0.4.0`: their SHA-256 are in the `SHA256SUMS` file of the release.

| File | Size | SHA-256 |
|---|---|---|
| `RAGbase-Shield-0.4.0.pkg` (macOS, universal, the default download) | 85,105,096 bytes | `82dc068f25ec4cd118d75b231802cf1c89284e1022edaf25e50c756902d9aa60` |
| `RAGbase-Shield-0.4.0-x86_64.pkg` (macOS, Intel only) | 43,296,258 bytes | `a25e610f9f4c9d929103f89ef9aced4a94c1e4d08f18f10fb6c87b11344c01c9` |
| `RAGbase-Shield-0.4.0-arm64.pkg` (macOS, Apple Silicon only) | 41,881,997 bytes | `be0cb929b884855a4298759ee9b7eba1fa87df867998f818b60e3c2b8c606eb4` |
| `RAGbase-Shield-0.4.0-win64.msi` (Windows x64, per user) | 40,294,731 bytes | `a9007a2950c0a73251926c0f2c7dc6dd6fd9242ef546e2e9e0c7d494146e423d` |

Minimum macOS: 13.0 (pypdfium2 5.x wheels). The `.app` shell uses the `pyvenv.cfg` variant (the
python-build-standalone `python3.12` is statically linked, so there is no `libpython` lookup).

## Licences of what ships (macOS)

All permissive. No GPL, LGPL or AGPL (checked by `licenses.py` at every build). `certifi` (MPL-2.0) is no longer
pulled: mcp 2.3 uses httpx2 with `truststore` (MIT). pystray (LGPL-3.0) is not used.

| Package | Licence | Package | Licence |
|---|---|---|---|
| CPython 3.12 runtime (PBS) | PSF-2.0 (+ OpenSSL Apache-2.0, libffi MIT, SQLite public domain, zlib, bzip2, xz 0BSD, expat MIT, mpdecimal BSD-2) | ragbase-shield | Apache-2.0 |
| mcp, mcp-types | MIT | pydantic, pydantic-core, annotated-types, typing-inspection | MIT |
| starlette, uvicorn, sse-starlette, click, h11 | BSD-3-Clause | anyio, jsonschema(-specifications), referencing, rpds-py, attrs | MIT |
| httpx2, httpcore2, idna | BSD-3-Clause | truststore, PyJWT, more-itertools, keyring, jaraco.* | MIT |
| cryptography | Apache-2.0 OR BSD-3-Clause | cffi / pycparser | MIT-0 / BSD-3-Clause |
| pypdf | BSD-3-Clause | pdfplumber, pdfminer.six, charset-normalizer | MIT |
| pypdfium2 | BSD-3-Clause, Apache-2.0 (PDFium and its bundled libraries, notices in `LICENSES/pypdfium2`) | pillow | MIT-CMU |
| python-docx | MIT | lxml | BSD-3-Clause |
| python-multipart, opentelemetry-api | Apache-2.0 | typing_extensions | PSF-2.0 |
| rumps (menu bar) | BSD-3-Clause | pyobjc-core, pyobjc-framework-Cocoa | MIT |
| pip (kept for the optional NER extra) | MIT | | |

Windows adds infi.systray (BSD-3-Clause, tray icon) and pywin32 (PSF-2.0, pulled by mcp). Build tools, not
shipped: uv (MIT or Apache-2.0), Apple pkgbuild / productbuild / lipo / iconutil, Pillow (icons only), WiX
(MS-RL) or msitools (LGPL-2.1) for the `.msi`.

## Known limits

| # | Severity | Item | What is needed |
|---|---|---|---|
| 1 | High | Windows: the tray icon has not been checked on a desktop session (the level-1 test runs in session 0, without a desktop), and the `.msi` ran on Windows Server 2025 only | The W9 check of `windows/TEST_PLAN_tray.md` in an interactive session, then one run on a Windows 10 or 11 PC |
| 2 | High | Unsigned packages: macOS "Open Anyway"; Windows SmartScreen, and Smart App Control or firm policy can block unsigned files entirely | Signing |
| 3 | High | No relaunch after "Quitter" except log out and in (no app in Applications or Launchpad) | A small launcher app in `~/Applications` |
| 4 | High | Adding a dossier needs a typed full path (no folder picker) | A menu item "Ajouter un dossier..." with the system folder picker |
| 5 | High | NER is not available to installed users (`ner install` into `extras/` not built) | Engine and CLI work |
| 6 | High | Not proved yet: no password prompt in the real Installer, the service start from Installer's script context, the macOS prompt for Documents access | Level-2 test |
| 7 | Medium | The service sends the Desk token to whatever listens on 127.0.0.1:7878 before it knows it is Shield (risk on shared machines) | A challenge answer from the Desk before the token is sent |
| 8 | Medium | Keychain "Always Allow" is given to a plain Python copy that any program can run; up to three keychain prompts (Desk, MCP launcher, `.mcpb`) | One signed program for every Shield process |
| 9 | Medium | The "Lancer à l'ouverture de session" check mark reads the plist only, not the System Settings switch | Read the real state |
| 10 | Medium | Windows: an install by an account without administrator rights is declared by the package (per-user scope) but not proven | A standard-user account during the W9 session, or a Windows 10 or 11 PC without administrator rights |
| 11 | Medium | Windows: "Ouvrir Shield Desk" hands the Desk token to the browser on its command line (visible for an instant in Task Manager, and recorded by process-creation auditing on a managed laptop) | A link without the token (a one-time code, or a cookie set by the Desk) |
| 12 | Low | Uninstall leaves the MCP entries in Claude Desktop, Claude Code, Codex and VS Code, and the NER models | Remove them, or keep saying so (INSTALL.md does) |
| 13 | Low | An update turns the login item back on and restarts a service the user had quit; an older package can be installed over a newer one | Small code change |
| 14 | Low | The `?t=` token goes into browser history and "Copier le jeton" into the clipboard (both can sync off the machine) | Desk and extension change |
| 15 | Low | Windows: the login toggle, `service status` and `doctor` read the Run value only, not `StartupApproved\Run` or the `DisableCurrentUserRun` policy | Read them in `login_item_enabled()` |
| 16 | Low | Windows: the tray's Désinstaller... runs `msiexec /x` with the full UI after its own confirmation, so Windows Installer asks a second time | `/passive` on that call |
| 17 | Low | Windows: the Error and ActionText strings WiX puts into the package are English | A French `.wxl` and `-culture fr-FR`, then re-test |
| 18 | Low | Windows build: `build_msi.ps1` fetches `dotnet-install.ps1` and the newest .NET 8.0 SDK patch without a pinned hash; WiX 5.0.2 is version-pinned only (build tools, never shipped) | Pin the SDK version and the script hash |
| 19 | Info | Claude Desktop's `.mcpb` runs a bundled copy of Shield with uv (one download of its dependencies, INSTALL.md section 2), not the installed runtime; both share the data folder | Unchanged by design |
