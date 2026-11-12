@echo off
rem RAGbase Shield: remove the program for this Windows account. Same as Settings, Apps, RAGbase Shield,
rem Uninstall, or the tray icon menu "Desinstaller...". No administrator rights are needed (per-user install).
rem Your dossiers, vaults and key stay in the folder LOCALAPPDATA\ragbase-shield. To erase them too, delete that
rem folder afterwards (old answers can then no longer be restored).
rem Silent removal for IT: uninstall.cmd /qn    (any msiexec option is passed on)
rem Never a reboot (/norestart): exit code 3010 means a file was still in use (an AI app ran Shield); Windows
rem finishes the removal at the next reboot. Close Claude Desktop, ChatGPT, Codex and VS Code first.
rem The working folder moves out of the app folder first: a process whose working folder is inside it would
rem keep it from being removed.
cd /d "%SystemRoot%"
start "" /wait msiexec.exe /x __PRODUCT_CODE__ /norestart %* & exit /b
