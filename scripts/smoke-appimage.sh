#!/usr/bin/env bash
# CI smoke: launch the *packaged* AppImage in Xvfb, inspect its live window and
# reject the all-black/misplaced Flutter surface that widget tests cannot catch.
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: $0 /absolute/path/RedClaw...AppImage" >&2
  exit 2
fi
APPIMAGE="$(realpath "$1")"
[[ -s "$APPIMAGE" ]] || { echo "AppImage missing: $APPIMAGE" >&2; exit 2; }

command -v xdotool >/dev/null || { echo "xdotool required" >&2; exit 2; }
command -v import >/dev/null || { echo "ImageMagick import required" >&2; exit 2; }

WORK="$(mktemp -d)"
child=""
cleanup() {
  if [[ -n "$child" ]]; then
    kill "$child" 2>/dev/null || true
    wait "$child" 2>/dev/null || true
  fi
  rm -rf -- "$WORK"
}
trap cleanup EXIT

# Force X11 and Mesa software GL only inside Xvfb; the *production* AppImage
# preserves native Wayland or X11 according to the user's own desktop session.
export APPIMAGE_EXTRACT_AND_RUN=1
export GDK_BACKEND=x11
export LIBGL_ALWAYS_SOFTWARE=1
export XDG_CONFIG_HOME="$WORK/config"
export XDG_STATE_HOME="$WORK/state"
export XDG_CACHE_HOME="$WORK/cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

"$APPIMAGE" --redclaw-diagnostics > "$WORK/diagnostics.txt"
grep -q 'Skia' "$WORK/diagnostics.txt" || {
  cat "$WORK/diagnostics.txt"
  echo "Renderer diagnostics missing Skia default" >&2
  exit 1
}
"$APPIMAGE" > "$WORK/app.log" 2>&1 &
child=$!

window=""
for attempt in $(seq 1 20); do
  if ! kill -0 "$child" 2>/dev/null; then
    echo "AppImage exited before a UI window became visible" >&2
    cat "$WORK/app.log" >&2
    exit 1
  fi
  window="$(xdotool search --onlyvisible --name 'RedClaw File Tools' 2>/dev/null | head -n1 || true)"
  if [[ -n "$window" ]]; then break; fi
  sleep 1
done
if [[ -z "$window" ]]; then
  echo "No RedClaw File Tools native X11 window opened" >&2
  cat "$WORK/app.log" >&2
  exit 1
fi

sleep 3
import -window "$window" "$WORK/window.png" || {
  echo "Could not capture Flutter window" >&2
  cat "$WORK/app.log" >&2
  exit 1
}
/usr/bin/python3 - "$WORK/window.png" <<'PY'
from PIL import Image
import sys

image = Image.open(sys.argv[1]).convert("RGB")
width, height = image.size
if width < 500 or height < 350:
    raise SystemExit(f"Unexpectedly small Flutter window: {width}x{height}")
# The native titlebar may be black depending on the WM; ignore its upper edge.
pixels = image.crop((8, min(height-1, 65), width-8, height-8)).getdata()
count = 0
black = 0
for red, green, blue in pixels:
    count += 1
    black += max(red, green, blue) <= 12
fraction = black / max(1, count)
print(f"AppImage screenshot: {width}x{height}; truly black pixels: {fraction:.1%}")
# The reported bug blacked out most of the viewport and only painted a
# lower-left rectangle. A real UI has a non-black scaffold throughout.
if fraction > 0.58:
    raise SystemExit("AppImage appears mostly black: native renderer regression")
PY
echo "Packaged AppImage GUI render smoke passed"
