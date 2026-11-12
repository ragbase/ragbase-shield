# RAGbase Shield for Windows: sheet for the firm's IT

RAGbase Shield installs for one Windows account, without administrator rights, and keeps every client file on the
computer. This sheet lists what the installer writes, what runs, and how to deploy, block or remove it.

## What is installed

| Item | Where | Notes |
|---|---|---|
| Program | `%LOCALAPPDATA%\Programs\RAGbase Shield\` (about 130 MB, 4,247 files) | A private Python 3.12 (python-build-standalone) with Shield inside. Nothing in `Program Files`, `Windows` or `System32`. No PATH change |
| Data (vaults, key, Desk token, journal, models) | `%LOCALAPPDATA%\ragbase-shield\` | Local, never in the roaming profile (SQLite must not sit on a network share). Never removed by the uninstaller |
| Login item | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `RAGbase Shield` = `"%LOCALAPPDATA%\Programs\RAGbase Shield\runtime\RAGbase Shield.exe" -E -s -P -X utf8 -m ragbase_shield service run` | Shown in Task Manager > Startup apps as "RAGbase Shield". The tray item "Lancer à l'ouverture de session" adds or removes it |
| Start menu | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\RAGbase Shield.lnk` | Starts the service when it was stopped |
| Component keys | `HKCU\Software\RAGbase\Shield` | Windows Installer bookkeeping, removed at uninstall |
| Package cache | `%WINDIR%\Installer\<random>.msi` (about 40 MB) | Written by the Windows Installer service for every product, used for the removal, deleted with it |
| Product registration | Windows Installer, per user: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\<user SID>\Products\...`, and the Settings > Apps entry `Software\Microsoft\Windows\CurrentVersion\Uninstall\{ProductCode}` (expected under HKCU for a standard user; a test machine where the installing account is an administrator showed it under HKLM) | Written by the Windows Installer service, not by Shield. Settings > Apps shows "Désinstaller" only |
| ProductCode | `uuid5` of the version (stable per version), `UpgradeCode` `{7143B2B1-CCE6-40A1-9BA0-F244A3ABEBA6}` (never changes) | A newer version replaces the older one (MajorUpgrade); an older one cannot be installed over a newer one |

## What runs

| Process | Program | Role |
|---|---|---|
| Supervisor (with the tray icon) | `runtime\RAGbase Shield.exe` (a copy of `pythonw.exe`, so Task Manager says "RAGbase Shield") | Starts and restarts Shield Desk, shows the icon |
| Shield Desk | `runtime\python.exe ... desk --service` (no window) | The local page and the API of the browser extension, on `127.0.0.1:7878` |
| MCP server (when an AI app uses Shield) | `runtime\python.exe -I -X utf8 -m ragbase_shield mcp` | Started by Claude Desktop, ChatGPT desktop, Codex or VS Code |

Network: none. Every socket is on `127.0.0.1`; no update check, no telemetry, no call at install or start (tested by
`packaging/windows/test_install.ps1`, network checks N1 to N3). The only network step is the optional name-recognition model
(`ragbase-shield ner install`, then `ner download`), started by the user in a terminal.

## Deploy, update, remove (silent)

```bat
rem Install for the signed-in user (no administrator, never a reboot):
msiexec /i RAGbase-Shield-<version>-win64.msi /qn /norestart /l*v "%TEMP%\shield-install.log"
rem Update: the same command with the newer .msi (data and the optional NER packages are kept).
rem Remove (data kept):
msiexec /x {ProductCode} /qn /norestart
"%LOCALAPPDATA%\Programs\RAGbase Shield\uninstall.cmd" /qn
```

The ProductCode is in `%LOCALAPPDATA%\Programs\RAGbase Shield\install_info.json` and in Settings > Apps. Before an
update or a removal, ask the user to close the AI apps that use Shield (Claude Desktop, ChatGPT, VS Code): their MCP
server runs `python.exe` from the same folder. A file in use is moved to `C:\Config.Msi\<id>.rbf` and deleted at
the next reboot; msiexec then returns 0 or 3010 (measured on a Windows Server 2025 test machine, 2026-11-03, review build: a removal with an
MCP server alive returned 0, left the app folder empty and 37 such files for the next reboot; the MCP process kept
running). The package sets `REBOOT=ReallySuppress`: it never reboots and never asks.
Keep `/norestart` on the command line as well (without that property, a `/qn` install with a file in use reboots
the machine at once: that is the Windows Installer default). A package with the same version as the installed
one runs in maintenance mode: the service restarts, no file is replaced. Run the command in the user's own session:
the install is per user, so an administrator running it installs Shield for the administrator's account, not for
the user.

With a window (a double-click), Windows Installer shows the box "fichiers en cours d'utilisation" when its
InstallValidate step finds a process that holds a file to replace or remove. The package stops the installed
service before that step (`ShieldStopEarly`), so Shield's own processes are not listed. Two cases remain: the MCP
server of an AI app (close the app first), and the name match of the built-in check: a program that has a module
of the same name loaded (a `.pyd` or `.dll` of another Python program, seen on a test machine) can be listed although
it holds none of Shield's files; "Ignorer" is then right. Exit codes:

| Exit code | Meaning |
|---|---|
| 0 | Done |
| 3010 | Done; a file was in use, Windows finishes at the next reboot (no reboot was started) |
| 1602 | The user cancelled |
| 1603 | Failed: read the `/l*v` log |
| 1625 | Refused by policy (`DisableUserInstalls`, see below) |
| 1638 | A newer version is installed |

To delete the data too (irreversible: answers masked earlier can no longer be restored), delete
`%LOCALAPPDATA%\ragbase-shield` after the removal. The vault key may also be in Credential Manager
(generic credential `ragbase-shield`, user `vault-key`).

## Policies that block this installer

| Policy | Effect | Answer |
|---|---|---|
| "Prohibit User Installs" (`HKLM\Software\Policies\Microsoft\Windows\Installer`, `DisableUserInstalls` = 1) | The per-user .msi is refused (exit 1625) | A per-machine package (administrator, `Program Files`): follow-up, ask RAGbase |
| AppLocker or WDAC default rules (no program from the user profile) | `RAGbase Shield.exe` and `python.exe` do not start | A publisher rule once the files are signed (signing is pending), or a path rule for `%LOCALAPPDATA%\Programs\RAGbase Shield\` |
| Smart App Control (Windows 11, new installs) | Unsigned programs are blocked | Wait for the signed release |
| "Do not process the legacy run list" (`HKCU` or `HKLM`, `Software\Microsoft\Windows\CurrentVersion\Policies\Explorer`, `DisableCurrentUserRun` = 1) | No start at login; the tray and `doctor` still say "Ouverture de session : oui" (they read the Run value only) | The Task Scheduler fallback below |
| Task Manager > Startup apps, "RAGbase Shield" turned off by the user | Same: no start at login, status still "oui" (Windows keeps the Run value and records the choice under `HKCU\...\Explorer\StartupApproved\Run`) | Turn it on again in Task Manager |

## Fallback login item: Task Scheduler

When the firm's policy ignores the Run key, create a task for the user (Task Scheduler > Create Task):

| Tab | Setting |
|---|---|
| General | Name `RAGbase Shield`; "Run only when user is logged on"; the user's account |
| Triggers | "At log on", "Specific user": the user |
| Actions | Start a program: `%LOCALAPPDATA%\Programs\RAGbase Shield\runtime\RAGbase Shield.exe`, arguments `-E -s -P -X utf8 -m ragbase_shield service run` |
| Conditions | Clear "Start the task only if the computer is on AC power" |
| Settings | Clear "Stop the task if it runs longer than 3 days" |

Command line equivalent (a task for the user's own account, without a highest-privilege flag, normally needs no
administrator; a firm policy can block Task Scheduler for users, which is why the product does not depend on it):

```bat
schtasks /Create /TN "RAGbase Shield" /SC ONLOGON /RU "%USERDOMAIN%\%USERNAME%" /IT /TR "\"%LOCALAPPDATA%\Programs\RAGbase Shield\runtime\RAGbase Shield.exe\" -E -s -P -X utf8 -m ragbase_shield service run"
```

A second start is harmless: the service holds a lock in the data folder, and a second copy exits at once. The
uninstaller does not remove such a task: delete it by hand (`schtasks /Delete /TN "RAGbase Shield" /F`).

## Other notes

- Name recognition (NER, optional) needs the Microsoft Visual C++ 2015-2022 x64 runtime (administrator):
  https://aka.ms/vs/17/release/vc_redist.x64.exe. Without it Shield works with its rules only.
- The port is 7878 on `127.0.0.1`. If another program uses it, the icon says "port 7878 occupé par un autre
  programme" and the browser extension cannot connect.
- Logs for support: `%LOCALAPPDATA%\ragbase-shield\logs\service.log` and `desk.log` (event codes and numbers only:
  no client name, no token).
