#!/bin/sh
# RAGbase Shield uninstaller for macOS (copied into the app folder by the installer).
#
#   "~/Library/Application Support/RAGbase Shield/uninstall.sh"               remove the app, keep your data
#   "~/Library/Application Support/RAGbase Shield/uninstall.sh" --purge-data  also delete the data folder
#
# Removes: the login item (LaunchAgent ai.ragbase.shield), the running service, the app folder, the package
# receipt, and the installer's own files in the data folder (install.json, PID files, service logs).
# Keeps: the data folder with your dossiers, vaults, key and Desk token, unless --purge-data is given
# (then old answers can no longer be restored). Runs as the user, no administrator password.
set -u
PURGE=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --purge-data) PURGE=1 ;;
    --quiet|--from-tray) QUIET=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $a" >&2; exit 2 ;;
  esac
done
say() { [ "$QUIET" = 1 ] || echo "$@"; }

APP="$(cd "$(dirname "$0")" && pwd -P)"
case "$APP" in
  */"RAGbase Shield") ;;
  *) echo "uninstall.sh : dossier inattendu ($APP), rien n'est supprimé." >&2; exit 1 ;;
esac
[ -f "$APP/VERSION" ] || { echo "uninstall.sh : $APP n'est pas une installation de RAGbase Shield." >&2; exit 1; }

LABEL="ai.ragbase.shield"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
plist_env() { /usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:$1" "$PLIST" 2>/dev/null; }

# Data folder and keychain setting of THIS install: the login item's settings, else the environment.
DATA=""
KEYRING="${RAGBASE_SHIELD_KEYRING:-1}"
if [ -f "$PLIST" ]; then
  DATA="$(plist_env RAGBASE_SHIELD_HOME)"
  k="$(plist_env RAGBASE_SHIELD_KEYRING)"; [ -n "$k" ] && KEYRING="$k"
fi
[ -n "$DATA" ] || DATA="${RAGBASE_SHIELD_HOME:-$HOME/.ragbase-shield}"

# 1. Stop the service (launchd first, then the PID files as a fallback: no orphan survives).
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
for f in service.pid desk.pid; do
  pid="$(cat "$DATA/$f" 2>/dev/null | head -n 1)"
  case "$pid" in ''|*[!0-9]*) continue ;; esac
  if ps -p "$pid" -o command= 2>/dev/null | grep -q "ragbase_shield"; then
    kill "$pid" 2>/dev/null || true
  fi
done
sleep 1
for f in service.pid desk.pid; do
  pid="$(cat "$DATA/$f" 2>/dev/null | head -n 1)"
  case "$pid" in ''|*[!0-9]*) continue ;; esac
  if ps -p "$pid" -o command= 2>/dev/null | grep -q "ragbase_shield"; then
    kill -9 "$pid" 2>/dev/null || true
  fi
done

# 2. Login item.
rm -f "$PLIST"

# 3. Package receipt (home domain).
pkgutil --volume "$HOME" --forget ai.ragbase.shield >/dev/null 2>&1 || true
rm -f "$HOME/Library/Receipts/ai.ragbase.shield."* 2>/dev/null || true

# 4. The installer's own files in the data folder.
if [ -d "$DATA" ]; then
  rm -f "$DATA/install.json" "$DATA/service.pid" "$DATA/desk.pid" "$DATA/service.cmd" "$DATA/.service.cmd.tmp"
  rm -f "$DATA/logs/service.log"* "$DATA/logs/desk.log"* "$DATA/logs/launchd.out.log" "$DATA/logs/launchd.err.log"
  rmdir "$DATA/logs" 2>/dev/null || true
  # Copies of uploaded files left by a Desk stopped during a request (the Desk removes them after each request
  # and at its next start; after an uninstall nothing starts it again).
  rm -rf "$DATA/desk-uploads"
fi

# True when a folder holds nothing but Shield's own files. A custom RAGBASE_SHIELD_HOME (copied into the login
# item at install time) may point at a folder such as Documents, where Shield also wrote desk_token and
# registry.db: --purge-data must never delete the user's other files there.
only_shield_files() {
  for e in "$1"/* "$1"/.[!.]* "$1"/..?*; do
    [ -e "$e" ] || [ -L "$e" ] || continue
    case "${e##*/}" in
      desk_token|key|registry.db|registry.db-*|.registry.lock|vaults|imported|models|logs|desk-uploads) ;;
      install.json|.install.json.tmp|service.pid|service.pid.txt|desk.pid|service.cmd|.service.cmd.tmp|.DS_Store) ;;
      *) return 1 ;;
    esac
  done
  return 0
}

# 5. Optional: the data folder itself (vaults, key, token, models) and the keychain item.
if [ "$PURGE" = 1 ] && [ -d "$DATA" ]; then
  case "$DATA" in
    /|"$HOME"|"$HOME/") echo "uninstall.sh : dossier de données refusé ($DATA)." >&2; PURGE=0 ;;
    *)
      # A custom RAGBASE_SHIELD_HOME read from the login item must hold only Shield's own files.
      if [ "$DATA" != "$HOME/.ragbase-shield" ] && ! only_shield_files "$DATA"; then
        echo "uninstall.sh : $DATA contient d'autres fichiers que ceux de Shield, rien n'y est supprimé." >&2
        PURGE=2   # the closing message must not advise deleting that folder
      else
        rm -rf "$DATA"
        # The keychain item is shared by every Shield of this account: only for the default data folder,
        # and never when the install ran with the keychain switched off (RAGBASE_SHIELD_KEYRING=0).
        case "$KEYRING" in 0|false|no|off) ;; *)
          if [ "$DATA" = "$HOME/.ragbase-shield" ]; then
            security delete-generic-password -s ragbase-shield -a vault-key >/dev/null 2>&1 || true
          fi ;;
        esac
        say "RAGbase Shield est désinstallé. Le dossier de données a été supprimé."
      fi
      ;;
  esac
fi

# 6. The app folder last (this script lives in it).
rm -rf "$APP"
if [ "$PURGE" != 1 ]; then
  say "RAGbase Shield est désinstallé. Vos dossiers et vos coffres restent dans $DATA."
  [ "$PURGE" = 2 ] || case "$KEYRING" in
    0|false|no|off) say "Pour tout effacer : supprimez ce dossier (les anciennes réponses ne pourront plus être restaurées)." ;;
    *) say "Pour tout effacer : supprimez ce dossier et l'élément « ragbase-shield » du Trousseau d'accès (les"
       say "anciennes réponses ne pourront plus être restaurées)." ;;
  esac
fi
exit 0
