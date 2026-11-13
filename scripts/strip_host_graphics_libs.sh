#!/usr/bin/env bash
# Remove copies of libraries that must match the running host GPU/Wayland stack.
# linuxdeploy can otherwise ship Ubuntu 22.04 EGL/Wayland libraries ahead of
# CachyOS/Arch Mesa or NVIDIA libraries via LD_LIBRARY_PATH.
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: $0 APPDIR" >&2
  exit 2
fi
APPDIR="$1"
[[ -d "$APPDIR/usr" ]] || {
  echo "Invalid AppDir: $APPDIR" >&2
  exit 2
}

# Keep libflutter_linux_gtk.so and other Flutter runtime libraries.
# Remove ONLY driver / display-server interfaces, not GTK or Flutter itself.
PATTERNS=(
  'libGL.so*' 'libGLX*.so*' 'libGLdispatch.so*'
  'libOpenGL.so*' 'libEGL*.so*' 'libGLES*.so*'
  'libgbm.so*' 'libdrm*.so*' 'libglapi.so*'
  'libwayland-*.so*' 'libvulkan.so*'
)
for libdir in "$APPDIR/usr/lib" "$APPDIR/usr/bin/lib"; do
  [[ -d "$libdir" ]] || continue
  for pattern in "${PATTERNS[@]}"; do
    while IFS= read -r -d '' entry; do
      printf 'Leaving host graphics library out of AppImage: %s\n' \
        "${entry#"$APPDIR"/}"
      rm -f -- "$entry"
    done < <(find "$libdir" -maxdepth 3 \
      \( -type l -o -type f \) -name "$pattern" -print0)
  done
done
# Fail-closed regression check, including symbolic links.
for libdir in "$APPDIR/usr/lib" "$APPDIR/usr/bin/lib"; do
  [[ -d "$libdir" ]] || continue
  for pattern in "${PATTERNS[@]}"; do
    if [[ -n "$(find "$libdir" -maxdepth 3 \( -type l -o -type f \) \
       -name "$pattern" -print -quit)" ]]; then
      echo "Forbidden bundled driver library remains: $pattern" >&2
      exit 1
    fi
  done
done
