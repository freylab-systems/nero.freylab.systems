#!/usr/bin/env bash
# Screenshot the built site so theme changes get looked at, not assumed.
#
# Serves the build over HTTP (the pages use absolute asset paths, so file://
# would load without CSS) and drives headless Chrome in a container. Run
# ./tools/build_check.sh first.
#
#   ./tools/screenshot.sh         # PNGs land in /tmp/shots
set -uo pipefail

SITE="${SITE:-/tmp/nerobuild}"
SHOTS="${SHOTS:-/tmp/shots}"
PORT="${PORT:-8000}"

mkdir -p "$SHOTS"
chmod 777 "$SHOTS"
rm -f "$SHOTS"/*.png

pkill -f "http.server $PORT" 2>/dev/null
nohup python3 -m http.server "$PORT" --directory "$SITE" --bind 127.0.0.1 > /tmp/httpd.log 2>&1 &
curl -s --retry 20 --retry-all-errors --retry-delay 1 -o /dev/null "http://127.0.0.1:$PORT/"

shot () {
  local name="$1" size="$2" path="$3"
  docker run --rm --network host -v "$SHOTS":/shots zenika/alpine-chrome \
    --no-sandbox --hide-scrollbars --virtual-time-budget=1500 \
    --window-size="$size" --screenshot=/shots/"$name".png \
    "http://127.0.0.1:$PORT$path" > "$SHOTS/$name.log" 2>&1
  echo "$name -> $SHOTS/$name.png"
}

shot home     960,1500 /
shot post     960,2600 "$(python3 - <<'PY'
import glob, os
posts = sorted(glob.glob('/tmp/nerobuild/[0-9]*/*/*/*.html'))
print(posts[-1].replace('/tmp/nerobuild', '') if posts else '/')
PY
)"
shot mobile   414,1300 /
shot notfound 960,700  /404.html

pkill -f "http.server $PORT" 2>/dev/null
