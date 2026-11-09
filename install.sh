#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  ARPXTOOL · installer
#  checks every dependency, reports honestly, installs only what is missing
# ─────────────────────────────────────────────────────────────────────────────
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOL="$HERE/arpxtool.py"
BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin"
OK=0
MISSING=()

# ── palette ──────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  R=$'\033[0m'; B=$'\033[1m'; D=$'\033[2m'
  CY=$'\033[38;5;51m'; VI=$'\033[38;5;141m'; GR=$'\033[38;5;114m'
  AM=$'\033[38;5;214m'; RD=$'\033[38;5;203m'; GY=$'\033[38;5;245m'
else
  R=''; B=''; D=''; CY=''; VI=''; GR=''; AM=''; RD=''; GY=''
fi

W=64
line()  { printf "%s%s%s\n" "$GY" "$(printf '─%.0s' $(seq 1 $W))" "$R"; }
title() { printf "\n%s%s%s\n" "$VI$B" "$1" "$R"; line; }

step() {
  printf "  %s◐%s %-42s" "$CY" "$R" "$1"
}

pass() {
  printf "%s✓%s %s%s%s\n" "$GR" "$R" "$GY" "${1:-}" "$R"
  OK=$((OK + 1))
}

fail() {
  printf "%s✗%s %s%s%s\n" "$RD" "$R" "$GY" "${1:-}" "$R"
  [ -n "${2:-}" ] && MISSING+=("$2")
}

spinner() {
  local pid=$1 msg=$2
  local frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    i=$(( (i + 1) % 10 ))
    printf "\r  %s%s%s %s" "$CY" "${frames:$i:1}" "$R" "$msg"
    sleep 0.12
  done
  printf "\r%*s\r" "$((${#msg} + 4))" ""
}

banner() {
  clear 2>/dev/null || true
  printf "\n"
  printf "  %s%sARPXTOOL%s  %sinstaller%s\n" "$B$CY" "" "$R" "$D" "$R"
  printf "  %sandroid reverse-engineering toolkit · termux · no root%s\n" "$GY" "$R"
  printf "  %s────────────────────────────────────────────────────────────%s\n" "$GY" "$R"
}

# ── checks ───────────────────────────────────────────────────────────────────
check_python() {
  step "python 3"
  if command -v python3 >/dev/null 2>&1; then
    local v; v="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)"
    local ok; ok="$(python3 -c 'import sys;print(1 if sys.version_info>=(3,8) else 0)' 2>/dev/null)"
    if [ "$ok" = "1" ]; then pass "python $v"; else fail "python $v is too old (need 3.8+)" "python"; fi
  else
    fail "not installed" "python"
  fi
}

check_java() {
  step "java runtime"
  if command -v java >/dev/null 2>&1; then
    local v; v="$(java -version 2>&1 | head -1 | sed 's/.*version "\([^"]*\)".*/\1/')"
    pass "java $v"
  else
    fail "not installed (apktool and apksigner need it)" "openjdk-17"
  fi
}

check_tool() {
  local label="$1" bin="$2" pkg="${3:-}"
  step "$label"
  if command -v "$bin" >/dev/null 2>&1; then
    pass "$(command -v "$bin")"
  else
    fail "not found" "$pkg"
  fi
}

check_disk() {
  step "free space"
  local free
  free="$(df -m "$HOME" 2>/dev/null | awk 'NR==2{print $4}')"
  if [ -n "$free" ] && [ "$free" -gt 500 ] 2>/dev/null; then
    pass "${free} MB free"
  else
    fail "${free:-0} MB free · a build needs ~500 MB" ""
  fi
}

check_net() {
  step "network"
  if python3 - <<'PY' >/dev/null 2>&1
import urllib.request, ssl
ctx = ssl.create_default_context()
urllib.request.urlopen("https://raw.githubusercontent.com/Impact-I/reFlutter/main/enginehash.csv",
                       timeout=8, context=ctx).read(64)
PY
  then
    pass "refluter table reachable"
  else
    printf "%s!%s %soptional · engine auto-download will be skipped%s\n" "$AM" "$R" "$GY" "$R"
  fi
}

check_toolfile() {
  step "arpxtool.py"
  if [ -f "$TOOL" ]; then
    pass "$(du -h "$TOOL" | cut -f1)"
  else
    fail "missing next to install.sh" ""
    printf "\n  %scannot continue without arpxtool.py%s\n" "$RD" "$R"; exit 1
  fi
}

install_missing() {
  [ ${#MISSING[@]} -eq 0 ] && return 0
  local uniq; uniq="$(printf '%s\n' "${MISSING[@]}" | sort -u | tr '\n' ' ')"
  title "installing: $uniq"
  printf "  %s(this can take a few minutes on a phone)%s\n\n" "$D" "$R"
  if ! command -v pkg >/dev/null 2>&1; then
    printf "  %s!%s pkg not found · this installer is meant for termux\n" "$AM" "$R"
    printf "    install by hand: apt install %s\n" "$uniq"
    return 0
  fi
  # shellcheck disable=SC2086
  pkg install -y $uniq >/tmp/arp_install.log 2>&1 &
  local pid=$!
  spinner $pid "pkg install $uniq"
  if wait $pid; then
    printf "  %s✓%s installed · %s\n" "$GR" "$R" "$uniq"
    MISSING=()
  else
    printf "  %s✗%s pkg failed · see /tmp/arp_install.log\n" "$RD" "$R"
  fi
}

run_tests() {
  title "test suites"
  local total=0 failed=0
  for t in test_cli test_dex_integrity test_netsec test_flutter_patch; do
    [ -f "$HERE/tests/$t.py" ] || continue
    total=$((total + 1))
    step "$t"
    if python3 "$HERE/tests/$t.py" >/tmp/arp_test_$t.log 2>&1; then
      pass "pass"
    else
      fail "fail · /tmp/arp_test_$t.log" ""
      failed=$((failed + 1))
    fi
  done
  [ "$total" -eq 0 ] && printf "  %s! no test files found%s\n" "$AM" "$R"
  return $failed
}

self_check() {
  title "self check"
  local out; out="$(python3 "$TOOL" --self-check 2>&1)"
  local ticks; ticks="$(printf '%s' "$out" | grep -c '✓' || true)"
  local cross; cross="$(printf '%s' "$out" | grep -c '✗' || true)"
  printf "  %s%d passed%s · %s%d failed%s\n" "$GR" "${ticks:-0}" "$R" \
         "$([ "${cross:-0}" -gt 0 ] && printf '%s' "$RD" || printf '%s' "$GY")" "${cross:-0}" "$R"
  if [ "${cross:-0}" -gt 0 ]; then
    printf "%s" "$out" | grep '✗' | sed 's/^/    /'
    return 1
  fi
  return 0
}

launcher() {
  title "launcher"
  step "writing $BIN/arpxtool"
  if [ ! -d "$BIN" ]; then
    fail "no $BIN on this system" ""
    printf "    use instead:  alias arpxtool='python3 %s'\n" "$TOOL"
    return 0
  fi
  cat > "$BIN/arpxtool" 2>/dev/null <<LAUNCH
#!/bin/sh
exec python3 "$TOOL" "\$@"
LAUNCH
  if chmod +x "$BIN/arpxtool" 2>/dev/null; then
    pass "arpxtool"
  else
    fail "could not write to $BIN" ""
    printf "    run:  alias arpxtool='python3 %s'\n" "$TOOL"
  fi
}

summary() {
  title "summary"
  if [ ${#MISSING[@]} -eq 0 ]; then
    printf "  %s✓ everything present%s\n" "$GR$B" "$R"
  else
    printf "  %s! missing:%s %s\n" "$AM$B" "$R" "$(printf '%s\n' "${MISSING[@]}" | sort -u | tr '\n' ' ')"
  fi
  printf "\n  %sready · try:%s\n" "$GY" "$R"
  printf "    %sarpxtool -i app.apk%s\n" "$CY" "$R"
  printf "    %sarpxtool --self-check%s\n" "$CY" "$R"
  printf "    %sarpxtool -i app.apk -m security --bypass-protection%s\n\n" "$CY" "$R"
}

# ── run ──────────────────────────────────────────────────────────────────────
banner
title "environment"
check_python
check_java
check_toolfile
check_disk

title "toolchain"
check_tool "apktool"    apktool    apktool
check_tool "zipalign"   zipalign   zipalign
check_tool "apksigner"  apksigner  apksigner
check_tool "keytool"    keytool    openjdk-17
check_tool "unzip"      unzip      unzip

title "network"
check_net

install_missing
launcher

self_check
RC=$?
run_tests || RC=1

summary
exit $RC
