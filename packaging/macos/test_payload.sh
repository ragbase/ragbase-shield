#!/bin/bash
# Level-1 test of the macOS installer on this Mac, in a clean temporary HOME (never the real one).
#
# Usage:  packaging/macos/test_payload.sh dist/RAGbase-Shield-<version>.pkg [<work_dir>]
#
# What it does, with HOME=<work>/home and RAGBASE_SHIELD_KEYRING=0 (no keychain prompt, no keychain item):
#   1  expand the .pkg (pkgutil --expand-full), check the tree, the domains and the scripts
#   2  play Installer: copy the payload to <home>/Library/Application Support/RAGbase Shield, run preinstall
#      and postinstall with Installer's arguments and a clean environment (env -i)
#   3  check the LaunchAgent, the .app shell, install.json, launchd
#   4  Shield Desk on 127.0.0.1:<port>: 200 with the token, 401 without, loopback sockets only
#   5  the menu bar item (window of the service process at the menu bar layer) and the tray status line
#   6  the installed command: --version, doctor, verify, MCP handshake, "install claude-desktop --dry-run"
#   7  crash (kill -9): launchd restarts the service; stop and start; restart
#   8  update: run the installer again, data kept
#   9  uninstall (data kept), reinstall, uninstall --purge-data (nothing left)
#   10 the real HOME, ~/Library/LaunchAgents and ~/.ragbase-shield are unchanged
# The launchd job is bootstrapped into this user's GUI session for the test and booted out at the end.
# Every command and result goes to <work>/test.log. Exit 1 when a check fails.
set -u
PKG="$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")"
HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
W="${2:-$(mktemp -d /tmp/shield-pkgtest.XXXXXX)}"
mkdir -p "$W"
W="$(cd "$W" && pwd -P)"
H="$W/home"
APP="$H/Library/Application Support/RAGbase Shield"
DATA="$H/.ragbase-shield"
PORT="${RAGBASE_SHIELD_TEST_PORT:-7878}"
LABEL="ai.ragbase.shield"
UIDN="$(id -u)"
LOG="$W/test.log"
REAL_HOME="$(dscl . -read "/Users/$(id -un)" NFSHomeDirectory | awk '{print $2}')"
# The CPU, as postinstall reads it (not "uname -m", which says x86_64 under Rosetta).
NATIVE_ARCH=x86_64; [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = 1 ] && NATIVE_ARCH=arm64
# Every process of THIS test install runs from here: process checks never count another Shield of this Mac.
OURS="$APP/"
PASS=0
FAIL=0
: > "$LOG"

log() { echo "$@" | tee -a "$LOG"; }
ok() { PASS=$((PASS + 1)); log "PASS  $1"; }
ko() { FAIL=$((FAIL + 1)); log "FAIL  $1"; }
check() { local name="$1"; shift; if "$@" >> "$LOG" 2>&1; then ok "$name"; else ko "$name"; fi; }
# A clean environment like Installer's: no CLAUDECODE, no PYTHON*, HOME = the test home.
cleanenv() { env -i HOME="$H" USER="$(id -un)" LOGNAME="$(id -un)" PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  TMPDIR="${TMPDIR:-/tmp}" LANG=fr_FR.UTF-8 RAGBASE_SHIELD_KEYRING=0 RAGBASE_SHIELD_PORT="$PORT" "$@"; }
shield() { cleanenv "$APP/bin/ragbase-shield" "$@"; }
token() { head -n 1 "$DATA/desk_token" 2>/dev/null | tr -d '\r\n'; }
http_code() { curl -s -o /dev/null -m 5 -w '%{http_code}' "$@" "http://127.0.0.1:$PORT/api/status"; }
wait_desk() {  # wait until /api/status answers 200 with the token (up to $1 s)
  local i=0
  while [ "$i" -lt "$1" ]; do
    [ "$(http_code -H "X-Shield-Token: $(token)")" = 200 ] && return 0
    sleep 1; i=$((i + 1))
  done
  return 1
}
sup_pid() { head -n 1 "$DATA/service.pid" 2>/dev/null | tr -cd '0-9'; }
desk_pid() { head -n 1 "$DATA/desk.pid" 2>/dev/null | tr -cd '0-9'; }
loaded() { launchctl print "gui/$UIDN/$LABEL" >/dev/null 2>&1; }
snapshot_real() {  # names and sizes only, never content
  { ls -la "$REAL_HOME/Library/LaunchAgents" 2>/dev/null | awk '{print $5, $9}';
    find "$REAL_HOME/.ragbase-shield" -maxdepth 2 2>/dev/null | sort;
    ls -d "$REAL_HOME/Library/Application Support/RAGbase Shield" 2>/dev/null;
    ls "$REAL_HOME/Library/Preferences" "$REAL_HOME/Library/Caches" 2>/dev/null | grep -i ragbase; } > "$1"
}
install_pkg() {  # play Installer: preinstall, payload copy, postinstall ($1 = label)
  log "--- install ($1): preinstall, copy payload, postinstall"
  cleanenv /bin/sh "$X/scripts/preinstall" "$PKG" "$APP" "/" "/" >> "$LOG" 2>&1
  mkdir -p "$APP"
  ditto "$X/Payload" "$APP"
  cleanenv /bin/sh "$X/scripts/postinstall" "$PKG" "$APP" "/" "/" >> "$LOG" 2>&1
}

cleanup() {  # never leave a job, a process or a plist behind, even when a step fails
  launchctl bootout "gui/$UIDN/$LABEL" >/dev/null 2>&1 || true
  pkill -f "$H/Library/Application Support/RAGbase Shield" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "RAGbase Shield macOS level-1 test  $(date '+%Y-%m-%d %H:%M:%S %Z')"
log "pkg=$PKG"
log "work=$W  port=$PORT  arch=$NATIVE_ARCH (uname -m: $(uname -m))  macOS=$(sw_vers -productVersion)"

# 0. Preconditions
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then log "port $PORT is busy: stop"; exit 2; fi
if loaded; then log "a $LABEL job is already loaded in this session: stop"; exit 2; fi
snapshot_real "$W/real-before.txt"

# 1. Expand
X="$W/expanded"
rm -rf "$X"
check "1.1 pkgutil --expand-full" pkgutil --expand-full "$PKG" "$X"
DIST="$W/expanded-flat"
rm -rf "$DIST"
pkgutil --expand "$PKG" "$DIST" >> "$LOG" 2>&1
COMP="$(find "$X" -maxdepth 1 -name '*.pkg' | head -n 1)"
log "component: $COMP"
X="$COMP"
check "1.2 Distribution: home domain only" grep -q 'enable_currentUserHome="true"' "$DIST/Distribution"
check "1.3 Distribution: no system domain" grep -q 'enable_localSystem="false"' "$DIST/Distribution"
check "1.4 Distribution: macOS 13 check" grep -q "compareVersions(system.version.ProductVersion, '13.0')" "$DIST/Distribution"
check "1.5 scripts executable" test -x "$X/Scripts/preinstall" -a -x "$X/Scripts/postinstall"
mv "$X/Scripts" "$X/scripts" 2>/dev/null || true
check "1.6 payload tree" test -d "$X/Payload/bin" -a -f "$X/Payload/VERSION" -a -f "$X/Payload/uninstall.sh" \
  -a -f "$X/Payload/MANIFEST.json" -a -d "$X/Payload/extras"
ls "$X/Payload" >> "$LOG"
if [ -d "$X/Payload/runtime-arm64" ]; then
  BAD=0; N=0
  while IFS= read -r f; do
    N=$((N + 1))
    a="$(lipo -archs "$f" 2>/dev/null)"
    [ "$a" = arm64 ] || { BAD=$((BAD + 1)); echo "arch $a: $f" >> "$LOG"; }
    codesign -v "$f" >/dev/null 2>&1 || { BAD=$((BAD + 1)); echo "signature: $f" >> "$LOG"; }
  done <<EOF2
$(find "$X/Payload/runtime-arm64" -type f \( -name '*.so' -o -name '*.dylib' -o -path '*/bin/python3.12' \))
EOF2
  if [ "$BAD" = 0 ]; then ok "1.7 arm64 runtime: $N Mach-O files, arm64 only, signatures valid"; else ko "1.7 arm64 runtime: $BAD problem(s) in $N files"; fi
  BAD=0; N=0
  while IFS= read -r f; do
    N=$((N + 1)); a="$(lipo -archs "$f" 2>/dev/null)"; [ "$a" = x86_64 ] || BAD=$((BAD + 1))
  done <<EOF2
$(find "$X/Payload/runtime-x86_64" -type f \( -name '*.so' -o -name '*.dylib' -o -path '*/bin/python3.12' \))
EOF2
  if [ "$BAD" = 0 ]; then ok "1.8 x86_64 runtime: $N Mach-O files, x86_64 only"; else ko "1.8 x86_64 runtime: $BAD file(s) not x86_64"; fi
fi
log "installer -pkginfo: $(installer -pkginfo -pkg "$PKG" 2>&1 | tr '\n' ' ')"
log "installer -dominfo: $(installer -dominfo -pkg "$PKG" 2>&1 | tr '\n' ' ')"
log "payload files: $(find "$X/Payload" -type f | wc -l | tr -d ' ')"
# pkgbuild writes auth="root": whether Installer then asks for a password or runs the scripts as root for a
# home-domain install is only seen in the fresh-account test (TEST_PLAN_macos.md steps 4 and 16).
log "INFO  1.9 PackageInfo: $(grep -o 'auth="[a-z]*"' "$X/PackageInfo" 2>/dev/null)"
mkdir -p "$W/other/runtime" && echo keep > "$W/other/runtime/keep.txt"
cleanenv /bin/sh "$X/scripts/preinstall" "$PKG" "$W/other" "/" "/" >> "$LOG" 2>&1
check "1.10 preinstall deletes nothing outside a folder named RAGbase Shield" test -f "$W/other/runtime/keep.txt"

# 2. Install
mkdir -p "$H"
RT0="$X/Payload/runtime-$NATIVE_ARCH"; [ -d "$RT0" ] || RT0="$X/Payload/runtime"
LAYER25_BEFORE="$("$RT0/bin/python3.12" -I "$HERE/menubar_items.py" 2>/dev/null | wc -l | tr -d ' ')"
T0=$(date +%s)
install_pkg "first"
T1=$(date +%s)
log "install scripts took $((T1 - T0)) s"
check "2.1 runtime of this Mac kept ($NATIVE_ARCH), other one removed" test -x "$APP/runtime/bin/python3.12" \
  -a ! -e "$APP/runtime-x86_64" -a ! -e "$APP/runtime-arm64" -a -d "$APP/LICENSES" -a ! -e "$APP/LICENSES-arm64" \
  -a ! -e "$APP/LICENSES-x86_64"
check "2.2 runtime architecture" sh -c "lipo -archs '$APP/runtime/bin/python3.12' | grep -qx '$NATIVE_ARCH'"

# 3. Login item, shell, install.json, launchd
PL="$H/Library/LaunchAgents/$LABEL.plist"
check "3.1 LaunchAgent written in the test HOME" test -f "$PL"
check "3.2 plutil -lint" plutil -lint "$PL"
check "3.3 ProgramArguments[0] is the .app shell" sh -c "/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:0' '$PL' | grep -q 'RAGbase Shield.app/Contents/MacOS/RAGbase Shield'"
check "3.4 plist carries the test HOME (not the real one)" sh -c "/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:HOME' '$PL' | grep -qx '$H'"
check "3.5 .app shell Info.plist" plutil -lint "$APP/RAGbase Shield.app/Contents/Info.plist"
check "3.6 .app shell imports from the runtime" cleanenv "$APP/RAGbase Shield.app/Contents/MacOS/RAGbase Shield" -E -s -c \
  "import sys, ssl, sqlite3, ragbase_shield, rumps, AppKit; assert sys.base_prefix.endswith('/runtime'), sys.base_prefix; print(sys.prefix, sys.base_prefix)"
check "3.7 install.json" test -f "$DATA/install.json"
check "3.8 install.json holds no token" sh -c "! grep -qF '$(token)' '$DATA/install.json' 2>/dev/null || [ -z '$(token)' ]"
check "3.9 launchd job loaded" loaded
launchctl print "gui/$UIDN/$LABEL" 2>/dev/null | grep -E '^\s*(state|pid|program|last exit code) =' >> "$LOG"

# 4. Desk
T2=$(date +%s)
if wait_desk 240; then ok "4.1 Desk answers 200 with the token on 127.0.0.1:$PORT ($(( $(date +%s) - T2 )) s after install)"; else ko "4.1 Desk answers 200 with the token"; fi
check "4.2 401 without the token" test "$(http_code)" = 401
check "4.3 403 for another Host header" test "$(http_code -H 'Host: evil.example:'"$PORT" -H "X-Shield-Token: $(token)")" = 403
STATUS_JSON="$(curl -s -m 5 -H "X-Shield-Token: $(token)" "http://127.0.0.1:$PORT/api/status")"
log "status: $(echo "$STATUS_JSON" | /usr/bin/python3 -c 'import json,sys; d=json.load(sys.stdin); print({k: d.get(k) for k in ("version","engine_mode","network","key_storage")})' 2>&1)"
SP="$(sup_pid)"; DP="$(desk_pid)"
log "supervisor pid=$SP ($(ps -p "$SP" -o comm= 2>/dev/null)), desk pid=$DP ($(ps -p "$DP" -o comm= 2>/dev/null))"
check "4.4 service.pid and desk.pid" test -n "$SP" -a -n "$DP"
SOCKS="$(lsof -nP -a -i -p "$SP,$DP" 2>/dev/null | awk 'NR>1 {print $9}')"
log "sockets: $(echo "$SOCKS" | tr '\n' ' ')"
check "4.5 only 127.0.0.1 sockets" sh -c "[ -n '$SOCKS' ] && ! echo '$SOCKS' | grep -v '^127\.0\.0\.1:'"
check "4.6 the process is named RAGbase Shield" sh -c "ps -p $SP -o command= | grep -q 'RAGbase Shield.app/Contents/MacOS/RAGbase Shield'"

# 5. Menu bar. Since macOS 26 the status item windows belong to Control Centre, not to the app, so the
#    checks are: the app's own report (NSStatusItem visible, icon set), its status line, and, when this
#    terminal has the Accessibility permission, the item seen by System Events. A look at the screen stays a
#    manual step (fresh-account test).
sleep 3
check "5.1 service.log: tray started (rumps)" grep -q "tray: started (rumps)" "$DATA/logs/service.log"
check "5.2 status item created, visible, with the shield icon" grep -q "tray: status item visible=True icon=True" "$DATA/logs/service.log"
check "5.3 tray status line: running, port, version" grep -Eq "tray: status line \"Shield Desk ?: (en marche|running), port $PORT, v$(cat "$APP/VERSION")" "$DATA/logs/service.log"
grep "tray:" "$DATA/logs/service.log" | tail -n 5 >> "$LOG"
AX="$(timeout 30 osascript -e 'tell application "System Events" to tell (first process whose bundle identifier is "ai.ragbase.shield") to get {name, description of every menu bar item of menu bar 2, size of every menu bar item of menu bar 2}' 2>&1)"
log "INFO  5.4 System Events (Accessibility): $AX"
LAYER25="$(cleanenv "$APP/runtime/bin/python3.12" -I "$HERE/menubar_items.py" 2>&1 | wc -l | tr -d ' ')"
log "INFO  5.5 menu bar item windows on screen (all owners): $LAYER25 now, $LAYER25_BEFORE before the install"

# 6. Installed command
check "6.1 --version from the installed location" sh -c "'$APP/bin/ragbase-shield' --version | grep -qx 'ragbase-shield $(cat "$APP/VERSION")'"
shield doctor > "$W/doctor.txt" 2>&1
log "doctor exit=$? ; $(grep -E 'Installateur|Service Shield Desk|uv / uvx|Python :' "$W/doctor.txt" | tr '\n' ';')"
check "6.2 doctor: installer line" grep -q "^OK    Installateur" "$W/doctor.txt"
check "6.3 doctor: service line active" grep -q "^OK    Service Shield Desk : actif, port $PORT, ouverture de session : oui" "$W/doctor.txt"
shield verify > "$W/verify.txt" 2>&1
log "verify: $(tail -n 1 "$W/verify.txt")"
check "6.4 verify: CLEAN" grep -q "CLEAN" "$W/verify.txt"
shield install claude-desktop --dry-run > "$W/install-dry.txt" 2>&1
log "install claude-desktop --dry-run: $(tr '\n' ' ' < "$W/install-dry.txt" | cut -c1-400)"
check "6.5 MCP config uses the installed launcher" grep -qF "$APP/bin/ragbase-shield" "$W/install-dry.txt"
cleanenv "$APP/runtime/bin/python3.12" -I - "$APP/bin/ragbase-shield" "$ROOT/integrations/claude-desktop/manifest.json" > "$W/mcp.txt" 2>&1 <<'PYEOF'
import json, subprocess, sys
launcher, manifest = sys.argv[1], sys.argv[2]
expected = sorted(t["name"] for t in json.load(open(manifest))["tools"])
p = subprocess.Popen([launcher, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
def send(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()
def read(i):
    for line in p.stdout:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("id") == i:
            return m
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pkgtest", "version": "0"}}})
read(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = sorted(t["name"] for t in read(2)["result"]["tools"])
p.stdin.close(); p.wait(timeout=30)
print("server tools:", tools)
print("manifest tools:", expected)
sys.exit(0 if tools == expected else 1)
PYEOF
RC=$?
cat "$W/mcp.txt" >> "$LOG"
if [ "$RC" = 0 ]; then ok "6.6 installed 'ragbase-shield mcp' serves the .mcpb manifest tools"; else ko "6.6 MCP tools match the .mcpb manifest"; fi
check "6.7 .mcpb manifest and plugin unchanged by the installer" git -C "$ROOT" diff --quiet -- integrations/claude-desktop integrations/claude-code integrations/browser-extension

# 7. Crash, stop/start, restart
OLD_SP="$(sup_pid)"
kill -9 "$OLD_SP" 2>/dev/null
log "kill -9 supervisor $OLD_SP"
sleep 12
if wait_desk 240 && [ -n "$(sup_pid)" ] && [ "$(sup_pid)" != "$OLD_SP" ]; then ok "7.1 launchd restarted the service after a crash (new pid $(sup_pid))"; else ko "7.1 restart after crash"; fi
check "7.2 one Desk only after the crash" test "$(pgrep -f "$OURS.*ragbase_shield desk --service" | wc -l | tr -d ' ')" = 1
shield service stop >> "$LOG" 2>&1
sleep 8
check "7.3 service stop: no process left" sh -c "! pgrep -f '$OURS.*ragbase_shield (desk|service)' >/dev/null"
check "7.4 launchd does not relaunch after a clean stop" sh -c "! pgrep -f '$OURS.*ragbase_shield service run' >/dev/null"
shield service start >> "$LOG" 2>&1
if wait_desk 240; then ok "7.5 service start (launchctl kickstart)"; else ko "7.5 service start"; fi
D1="$(desk_pid)"
shield service restart >> "$LOG" 2>&1
sleep 5
if wait_desk 240 && [ "$(desk_pid)" != "$D1" ]; then ok "7.6 service restart gives a new Desk process"; else ko "7.6 service restart"; fi
check "7.7 service status exit 0" shield service status

# 8. Update (run the installer again)
TOK1="$(token)"
mkdir -p "$APP/extras/marker" && echo keep > "$APP/extras/marker/keep.txt"
install_pkg "update"
if wait_desk 240; then ok "8.1 Desk back after the update"; else ko "8.1 Desk back after the update"; fi
check "8.2 token, key and registry kept" sh -c "[ '$(token)' = '$TOK1' ] && [ -f '$DATA/key' ] && [ -f '$DATA/registry.db' ]"
check "8.3 extras kept" test -f "$APP/extras/marker/keep.txt"
check "8.4 one supervisor after the update" test "$(pgrep -f "$OURS.*ragbase_shield service run" | wc -l | tr -d ' ')" = 1

# 9. Uninstall (data kept), reinstall, uninstall --purge-data
cleanenv /bin/sh "$APP/uninstall.sh" >> "$LOG" 2>&1
sleep 3
check "9.1 app folder removed" test ! -e "$APP"
check "9.2 LaunchAgent removed" test ! -e "$PL"
check "9.3 launchd job gone" sh -c "! launchctl print gui/$UIDN/$LABEL >/dev/null 2>&1"
check "9.4 no Shield process left" sh -c "! pgrep -f '$OURS.*ragbase_shield (desk|service)' >/dev/null"
check "9.5 port $PORT free" sh -c "! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null"
check "9.6 installer files removed from the data folder" sh -c "[ ! -e '$DATA/install.json' ] && [ ! -e '$DATA/service.pid' ] && [ ! -e '$DATA/desk.pid' ] && [ ! -e '$DATA/logs' ]"
check "9.7 user data kept (token, key, registry, vaults)" sh -c "[ -f '$DATA/desk_token' ] && [ -f '$DATA/key' ] && [ -f '$DATA/registry.db' ] && [ -d '$DATA/vaults' ]"
log "data folder after uninstall: $(ls -A "$DATA" | tr '\n' ' ')"
install_pkg "reinstall"
wait_desk 240 && ok "9.8 reinstall works" || ko "9.8 reinstall works"
cleanenv /bin/sh "$APP/uninstall.sh" --purge-data >> "$LOG" 2>&1
sleep 3
LEFT="$(find "$H" -mindepth 1 \( -type f -o -type l \) 2>/dev/null | grep -v '/Library/Caches/' )"
log "files left in the test HOME after uninstall --purge-data: ${LEFT:-none}"
check "9.9 uninstall --purge-data leaves no file" test -z "$LEFT"
check "9.10 no process, no job, port free" sh -c "! pgrep -f '$OURS' >/dev/null && ! launchctl print gui/$UIDN/$LABEL >/dev/null 2>&1 && ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null"

# 10. The real HOME was not touched
snapshot_real "$W/real-after.txt"
check "10.1 real ~/Library/LaunchAgents and ~/.ragbase-shield unchanged" cmp -s "$W/real-before.txt" "$W/real-after.txt"

# Safety net: never leave a job loaded
launchctl bootout "gui/$UIDN/$LABEL" >/dev/null 2>&1 || true
log "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
