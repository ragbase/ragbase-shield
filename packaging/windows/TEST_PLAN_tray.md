# Windows tray: manual test (W9, pending)

The level-1 test (`test_install.ps1`) runs over SSH, in session 0, where Windows has no desktop: the service logs
`tray: unavailable (no_desktop)` and keeps Shield Desk running without an icon (checked, W4.10). The icon, its
menu and its dialogs can only be checked in an interactive desktop session. This plan is that check.

Needs: an interactive desktop session of a test user on a Windows 10 or 11 machine (or a new Remote Desktop session
on a Windows Server test machine). Do not use a session that belongs to someone else. Before step 1: no RAGbase
Shield installed, no `%LOCALAPPDATA%\ragbase-shield` folder (write down if it exists).

| # | Do | Expected | Screenshot |
|---|---|---|---|
| 1 | Copy `RAGbase-Shield-<v>-win64.msi` to the Desktop. In PowerShell: `Set-Content -Path .\RAGbase-Shield-<v>-win64.msi -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"` (marks it as downloaded), then double-click it | SmartScreen "Windows a protégé votre ordinateur" (unsigned). "Informations complémentaires", "Exécuter quand même" | `win-01-smartscreen.png` |
| 2 | Let the installer run | A small Windows Installer progress window, no UAC prompt, no question; it closes by itself in under a minute | `win-02-installation.png` |
| 3 | Look at the notification area (click ^ if needed) | The shield icon within 10 s. Hover text: `Shield Desk : en marche, port 7878, v<v>, règles` (English system: `Shield Desk: running, ...`) | `win-03-icone-et-menu.png` (with step 4) |
| 4 | Right-click the icon | Items, in order: Statut..., Ouvrir Shield Desk, Dossiers (Shield Desk), Dossier de données Shield, Redémarrer, Lancer à l'ouverture de session, Ouvrir le journal, Réessayer, Désinstaller..., Quitter. Accents right (no `Ã©`) | |
| 5 | Statut... | A box with the status line and `Ouverture de session : oui` | |
| 6 | Double-click the icon, then Ouvrir Shield Desk | The default browser opens Shield Desk; the `?t=` part disappears from the address bar | |
| 7 | Dossiers (Shield Desk) | Shield Desk on its Dossiers page | |
| 8 | Dossier de données Shield, then Ouvrir le journal | Explorer opens `%LOCALAPPDATA%\ragbase-shield`, then its `logs` folder | |
| 9 | Redémarrer | Hover text `démarrage`, then `en marche` within about 10 s | |
| 10 | Lancer à l'ouverture de session, then Statut... | `Ouverture de session : non`; Task Manager > Startup apps no longer lists RAGbase Shield. Click it again: `oui`, listed again | |
| 10b | Task Manager > Startup apps > RAGbase Shield > Disable, then Statut..., then sign out and in | Known limit to record: Statut says `Ouverture de session : oui` but the icon does not come back (Windows ignores the Run value). Enable it again | |
| 11 | Task Manager > Processes > Windows Explorer > Restart | The icon comes back within a few seconds (TaskbarCreated fix of 2026-10-27) | |
| 12 | Sign out of this test session and sign in again | The icon is back within 10 s (Run key) | |
| 13 | Quitter, then Annuler | Confirmation box; after Annuler the icon stays | |
| 14 | Quitter, then OK | The icon goes; `http://127.0.0.1:7878` no longer answers. Start menu > RAGbase Shield: the icon is back | |
| 15 | Settings > Apps > Installed apps > RAGbase Shield, "..." | Only "Désinstaller" (no Modifier, no Réparer) | |
| 15b | With the icon present, double-click the `.msi` of a higher version (the upgrade-test package), then let it run | No box "fichiers en cours d'utilisation" names RAGbase Shield or python (ShieldStopEarly stops the service before Windows Installer looks); the icon goes, then comes back within 10 s of the end; same check again on step 16 | `win-04-mise-a-jour.png` |
| 16 | Icon > Désinstaller..., then OK, then "Oui" in the Windows Installer box | The box names the data folder; the icon goes; `%LOCALAPPDATA%\Programs\RAGbase Shield` is gone; `%LOCALAPPDATA%\ragbase-shield` is still there | |
| 17 | Clean up | If `%LOCALAPPDATA%\ragbase-shield` did not exist before step 1, delete it. Sign out of the test session only | |

Record in the test report of the release: pass or fail per row, the Windows version and language, the time from
step 2 to the icon, and the screenshots for `docs/INSTALL.md` section 0.
