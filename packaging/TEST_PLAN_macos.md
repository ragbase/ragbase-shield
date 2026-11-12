# macOS manual test with a fresh account

Needs an administrator of the Mac (password to create and delete the test account). About 15 minutes. Target: under
2 minutes from the double-click to the menu bar icon.

| # | Step | Expected | Record |
|---|---|---|---|
| 1 | `sudo sysadminctl -addUser shieldtest -fullName "Shield Test" -password <generated>` (the administrator types the password) | account created | |
| 2 | Fast User Switching to `shieldtest`; download `RAGbase-Shield-<v>.pkg` with Safari from the release page | file in Downloads, quarantined | |
| 3 | Double-click the `.pkg` | macOS 15+: refusal dialog; System Settings > Privacy & Security > "Open Anyway" | screenshots |
| 4 | Installer: Continue, licence, "Install for me only", Install | no administrator password asked (`build.sh` sets `auth="none"` in the component's PackageInfo: a password prompt here is a blocking defect) | password asked? yes / no |
| 5 | Conclusion page, then look at the menu bar | shield icon within 10 s; "Background Items Added: RAGbase Shield" notification | name shown in the notification; if no icon: notch hiding it? `launchctl print gui/$(id -u)/ai.ragbase.shield` state |
| 6 | Click the icon | status line "Shield Desk : en marche, port 7878, v<v>, règles" (or English on an English system) | |
| 7 | "Ouvrir Shield Desk" | Safari opens `http://127.0.0.1:7878/`, the `?t=` token disappears from the address bar, page works | |
| 8 | Add a dossier in the Desk | keychain prompt names "RAGbase Shield": choose "Always Allow" | name in the prompt |
| 8b | Make `~/Documents/Clients/Test` with one `.docx`, add it as a dossier in the Desk | macOS asks "RAGbase Shield" for access to Documents: Allow; the document is listed | prompt shown? name? A silent refusal or "Ce dossier n'existe pas" is a defect (the service is a launchd agent) |
| 8c | Desk > Extension navigateur > Copier le jeton; paste it in the extension options; "Tester la connexion" | connection OK, no Terminal used | |
| 9 | Icon > Dossiers | the new dossier title is listed; clicking it opens the folder in the Finder | |
| 10 | Wi-Fi off, log out and in | icon back, Desk answers (offline start) | |
| 11 | System Settings > General > Login Items | "RAGbase Shield" listed under "Allow in the Background" | |
| 11b | Switch that entry off, log out and in, open the icon menu if it shows | known gap: the menu check mark reads the plist, not this switch | does the service start? what does the check mark say? |
| 12 | Icon > "Lancer à l'ouverture de session" off, log out and in | no icon; turn it on again from Terminal: `"~/Library/Application Support/RAGbase Shield/bin/ragbase-shield" service enable` | |
| 13 | Icon > Quitter > confirm | icon gone, Desk stops; log out and in brings it back | |
| 14 | Re-run the same `.pkg` (update path) | service restarts, the dossier is still there | |
| 15 | Icon > Désinstaller... > Désinstaller | icon gone, `~/Library/Application Support/RAGbase Shield` gone, `~/.ragbase-shield` kept | |
| 15b | System Settings > Login Items; Keychain Access, search "ragbase-shield" | no "RAGbase Shield" entry left; the keychain item is kept (documented) | stale entry? |
| 16 | In Terminal as `shieldtest`: `ls -l ~/Library/Application\ Support/` before step 15 and `pkgutil --volume ~ --pkgs \| grep ragbase` | files owned by `shieldtest` (not root); receipt `ai.ragbase.shield` listed | owner, receipt path |
| 17 | Log out; `sudo sysadminctl -deleteUser shieldtest` | account removed | |

Also record: the `id -u` seen by `postinstall` (add `id -u >> /tmp/shield-postinstall-uid.txt` to a test build,
or read `~/.ragbase-shield/logs/service.log` first line "install: ... start launchd"), and whether Installer
asked for a password at any point.

Apple Silicon (same steps, plus): use a Mac where Rosetta is not installed (`/usr/bin/pgrep -q oahd` finds
nothing). The universal `.pkg` must install with no Rosetta prompt, and
`file ~/Library/Application\ Support/RAGbase\ Shield/runtime/bin/python3.12` must say `arm64`. Then run
`packaging/macos/test_payload.sh dist/RAGbase-Shield-<v>.pkg` there (level-1 test, temporary HOME).
