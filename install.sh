#!/usr/bin/env bash
#
# install.sh — Nautilus Extensions multi-distro installer
# Repo: https://github.com/zonaro/RedClaw-File-Tools (fork of ToFpon/Nautilus-Extensions)
#
# Installs selected extensions per-user into
#   ~/.local/share/nautilus-python/extensions
# and auto-detects the package manager, installing only the dependencies
# required by the extensions you pick. Detection order:
#   apt (Debian/Ubuntu) · dnf (Fedora) · pacman (Arch/CachyOS) · zypper (openSUSE)
#   apk (Alpine) · xbps-install (Void) · eopkg (Solus)
# On anything else the extensions are still copied; nothing is installed
# automatically, and a verification report at the end lists exactly what is
# missing and the probable package names to look for.
# Packages that were renamed across distros are tried under several names
# (e.g. p7zip -> 7zip), and a single failing candidate never aborts the install.
#
# One-liner (installs everything, same as before):
#   curl -fsSL https://raw.githubusercontent.com/zonaro/RedClaw-File-Tools/main/install.sh | bash
#
# Local usage:
#   ./install.sh                              # install all extensions (default)
#   ./install.sh --all                        # same as above
#   ./install.sh --list                       # list available extensions and exit
#   ./install.sh --only dual-panel,edit-with  # install just these
#   ./install.sh --exclude hidden-dim-all     # install all but these
#   ./install.sh --all --yes --no-optional    # non-interactive, no extras
#
# Flags:
#   --all            install every extension (default)
#   --only LIST      comma-separated slugs to install (see --list)
#   --exclude LIST   comma-separated slugs to skip (installs the rest)
#   --list           show available extensions and exit
#   --yes, -y        assume "yes" for prompts (non-interactive)
#   --no-optional    skip optional extras (unrar)
#   --help, -h       show this help and exit
#
set -euo pipefail

REPO_URL="https://github.com/zonaro/RedClaw-File-Tools.git"
EXT_DIR="$HOME/.local/share/nautilus-python/extensions"
PPA_DIR="/usr/share/zonaro-nautilus-extensions"

# Directory holding the media conversion core (needed by a few extensions).
MEDIA_CORE_DIR="media_core"

# ---------------------------------------------------------------------------
# Extension catalog
# ---------------------------------------------------------------------------
SLUGS=(
  archive-browser
  audio-tools
  clone-repository
  column-browser
  comic-tools
  compress-pdf
  cut-dim
  deb-installer
  dev-tools-minify
  dual-panel
  duration-column
  edit-with

  extract-here
  file-tools
  folder-color-revival
  hidden-dim-all
  hidden-dim-icon
  move-and-symlink
  image-tools
  media-converter
  merge-pdf
  paste-into-file
  preview-panel
  progress-mirror
  search-content
  terminal-tools
  video-to-audio
  video-tools
  watermark-pdf
)

slug_desc() {
  case "$1" in
    archive-browser)      echo "Browse, extract and create archives";;
    audio-tools)          echo "Convert audio files (ffmpeg)";;
    clone-repository)     echo "Clone git repos and Git submenu";;
    column-browser)       echo "Miller-columns folder browser (F9)";;
    comic-tools)          echo "Open comics (cbz/cbr/cb7/cbt) page by page";;
    compress-pdf)         echo "Compress PDF files via Ghostscript";;
    cut-dim)              echo "Dim items cut with Ctrl+X";;
    deb-installer)        echo "Visual .deb package installer";;
    dev-tools-minify)     echo "Minify .js/.css files";;
    dual-panel)           echo "Dual-pane file manager (F3)";;
    duration-column)      echo "Duration column for audio/video";;
    edit-with)            echo "Open text files with any installed editor";;
    extract-here)         echo "Fast archive extraction (7z, rar, zip...)";;
    file-tools)           echo "Friendly rename, copy path, symlinks...";;
    folder-color-revival) echo "Folder color & emblem tagging";;
    hidden-dim-all)       echo "Dim icon + label of hidden files";;
    hidden-dim-icon)      echo "Dim only the icon of hidden files";;
    move-and-symlink)     echo "Move items and leave a symlink behind";;
    image-tools)          echo "Grayscale, crop, annotate, convert...";;
    media-converter)      echo "FFmpeg-powered media conversion UI";;
    merge-pdf)            echo "Merge multiple PDFs into one";;
    paste-into-file)      echo "Save clipboard as .txt/.png/.zip";;
    preview-panel)        echo "Dynamic file preview panel (F4)";;
    progress-mirror)      echo "Mirror copy/move progress in a window";;
    search-content)       echo "Text search & replace via grep/ripgrep (F8)";;
    terminal-tools)       echo "Run scripts in the terminal + open a terminal that follows the folder";;
    video-to-audio)       echo "Extract audio from videos (legacy shim, see video-tools)";;
    video-tools)          echo "Convert videos + extract audio (ffmpeg)";;
    watermark-pdf)        echo "Text/image PDF watermarking";;
    *)                    echo "";;
  esac
}

# Files to copy for a given slug.
slug_files() {
  case "$1" in
    edit-with)            echo "nautilus_edit_ext.py";;
    folder-color-revival) echo "folder-color-revival.py folder_icon_editor.py folder_icon_theme.py folder_icon_project.py folder_icon_catalog.py name_to_color.py color_database.json";;
    audio-tools|video-tools|media-converter)
                          echo "$1.py media_dialogs.py";;
    terminal-tools)       echo "terminal-tools.py follow-shell.py";;
    *)                    echo "$1.py";;
  esac
}

# Logical dependency keys for a given slug (always plus the shared base keys).
slug_deps() {
  case "$1" in
    archive-browser|extract-here) echo "libarchive-c p7zip unrar";;
    comic-tools)                  echo "p7zip unrar";;
    clone-repository)             echo "git";;
    compress-pdf)                 echo "ghostscript pypdf";;
    dual-panel)                   echo "rsync";;
    duration-column)              echo "ffmpeg";;
    file-tools|paste-into-file)   echo "pillow";;
    folder-color-revival)         echo "pillow cairo pangocairo";;
    image-tools)                  echo "pillow ffmpeg";;
    audio-tools)                  echo "ffmpeg mutagen";;
    video-tools)                  echo "ffmpeg";;
    media-converter)              echo "ffmpeg pillow";;
    merge-pdf)                    echo "pypdf";;
    preview-panel)                echo "pillow cairo ffmpeg ffmpegthumbnailer poppler";;
    search-content)               echo "ripgrep";;
    video-to-audio)               echo "ffmpeg";;
    watermark-pdf)                echo "ghostscript pypdf cairo";;
    *)                            echo "";;
  esac
}

# Shared base dependencies (needed by any GTK/Nautilus extension).
BASE_KEYS=(nautilus-python gobject gtk4 libadwaita nautilus-extensions)

# Extensions that need the media_core/ package on disk.
needs_media_core() {
  case "$1" in
    media-converter|video-to-audio|video-tools|audio-tools|image-tools|dual-panel) return 0;;
    *) return 1;;
  esac
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARNING: $*" >&2; }

usage() {
  sed -n '3,30p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//' || true
}

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------
MODE="all"
ONLY=""
EXCLUDE=""
ASSUME_YES=0
NO_OPTIONAL=0
WANT_LIST=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all)          MODE="all";;
    --list)         WANT_LIST=1;;
    -h|--help)      usage; exit 0;;
    --only)         [ "$#" -ge 2 ] || die "--only requires an argument (see --help)"; ONLY="$2"; shift;;
    --only=*)       ONLY="${1#--only=}";;
    --exclude)      [ "$#" -ge 2 ] || die "--exclude requires an argument (see --help)"; EXCLUDE="$2"; shift;;
    --exclude=*)    EXCLUDE="${1#--exclude=}";;
    -y|--yes)       ASSUME_YES=1;;
    --no-optional)  NO_OPTIONAL=1;;
    *)              die "Unknown option: '$1' (see --help)";;
  esac
  shift
done

if [ "$WANT_LIST" -eq 1 ]; then
  echo "Available extensions (${#SLUGS[@]}):"
  echo
  printf '  %-22s %s\n' "SLUG" "DESCRIPTION"
  printf '  %-22s %s\n' "----------------------" "-----------------------------------"
  for slug in "${SLUGS[@]}"; do
    printf '  %-22s %s\n' "$slug" "$(slug_desc "$slug")"
  done
  exit 0
fi

if [ -n "$ONLY" ] && [ -n "$EXCLUDE" ]; then
  die "--only and --exclude are mutually exclusive."
fi
if [ -n "$ONLY" ]; then MODE="only"; fi
if [ -n "$EXCLUDE" ]; then MODE="exclude"; fi

is_slug() {
  local s
  for s in "${SLUGS[@]}"; do
    if [ "$s" = "$1" ]; then return 0; fi
  done
  return 1
}

# Resolve SELECTED[] from MODE/ONLY/EXCLUDE.
SELECTED=()
case "$MODE" in
  all)
    SELECTED=("${SLUGS[@]}")
    ;;
  only)
    IFS=',' read -ra _parts <<< "$ONLY"
    for _part in "${_parts[@]}"; do
      _slug="${_part// /}"
      [ -n "$_slug" ] || continue
      is_slug "$_slug" || die "Unknown extension slug: '$_slug' (see --list)"
      SELECTED+=("$_slug")
    done
    [ "${#SELECTED[@]}" -gt 0 ] || die "--only requires at least one slug (see --list)"
    ;;
  exclude)
    IFS=',' read -ra _parts <<< "$EXCLUDE"
    declare -A _EX=()
    for _part in "${_parts[@]}"; do
      _slug="${_part// /}"
      [ -n "$_slug" ] || continue
      is_slug "$_slug" || die "Unknown extension slug to exclude: '$_slug' (see --list)"
      _EX["$_slug"]=1
    done
    for slug in "${SLUGS[@]}"; do
      if [ -z "${_EX[$slug]:-}" ]; then SELECTED+=("$slug"); fi
    done
    [ "${#SELECTED[@]}" -gt 0 ] || die "--exclude removed every extension"
    ;;
esac

# ---------------------------------------------------------------------------
# Package manager detection
# ---------------------------------------------------------------------------
PKG_MANAGER=""
if command -v apt-get >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PKG_MANAGER="pacman"
elif command -v zypper >/dev/null 2>&1; then
  PKG_MANAGER="zypper"
elif command -v apk >/dev/null 2>&1; then
  PKG_MANAGER="apk"
elif command -v xbps-install >/dev/null 2>&1; then
  PKG_MANAGER="xbps"
elif command -v eopkg >/dev/null 2>&1; then
  PKG_MANAGER="eopkg"
else
  # Unknown distro: nothing is installed automatically, but the extensions
  # are still copied and the final verification reports exactly what is
  # missing and the probable package name to look for.
  PKG_MANAGER="unknown"
fi

# Map a logical dependency key to distro package name(s) — space-separated,
# best candidate first, empty = not needed. Several candidates serve as
# fallback because distros rename packages (p7zip -> 7zip everywhere, for
# example). The maps for apk, xbps and eopkg are best-effort: the final
# verification step prints whatever is still missing.
pkg_candidates() {
  case "$PKG_MANAGER" in
    apt)
      case "$1" in
        nautilus-python)     echo "python3-nautilus";;
        gobject)             echo "python3-gi";;
        gtk4)                echo "gir1.2-gtk-4.0";;
        libadwaita)          echo "gir1.2-adw-1";;
        nautilus-extensions) echo "gir1.2-nautilus-4.0";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python3-pypdf";;
        cairo)               echo "python3-cairo";;
        pangocairo)          echo "gir1.2-pangocairo-1.0";;
        pillow)              echo "python3-pil";;
        mutagen)             echo "python3-mutagen";;
        libarchive-c)        echo "python3-libarchive-c";;
        p7zip)               echo "7zip p7zip-full p7zip";;
        poppler)             echo "poppler-utils";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    dnf)
      case "$1" in
        nautilus-python)     echo "nautilus-python";;
        gobject)             echo "python3-gobject python3-gobject3";;
        gtk4)                echo "gtk4";;
        libadwaita)          echo "libadwaita";;
        nautilus-extensions) echo "nautilus-extensions";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python3-pypdf python3-PyPDF2";;
        cairo)               echo "python3-cairo";;
        pangocairo)          echo "pango pango-devel";;
        pillow)              echo "python3-pillow";;
        mutagen)             echo "python3-mutagen";;
        libarchive-c)        echo "python3-libarchive-c";;
        p7zip)               echo "7zip p7zip";;
        poppler)             echo "poppler-utils";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    pacman)
      case "$1" in
        nautilus-python)     echo "nautilus-python python-nautilus";;
        gobject)             echo "python-gobject";;
        gtk4)                echo "gtk4";;
        libadwaita)          echo "libadwaita";;
        nautilus-extensions) echo "nautilus";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python-pypdf";;
        cairo)               echo "python-cairo";;
        pangocairo)          echo "pango";;
        pillow)              echo "python-pillow";;
        mutagen)             echo "python-mutagen";;
        libarchive-c)        echo "python-libarchive-c";;
        p7zip)               echo "7zip p7zip";;
        poppler)             echo "poppler";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    zypper)
      case "$1" in
        nautilus-python)     echo "python3-nautilus";;
        gobject)             echo "python3-gobject python3-gobject3";;
        gtk4)                echo "typelib-1_0-Gtk-4_0 gtk4";;
        libadwaita)          echo "typelib-1_0-Adw-1 libadwaita";;
        nautilus-extensions) echo "typelib-1_0-Nautilus-4_0 nautilus";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python3-pypdf python3-PyPDF2";;
        cairo)               echo "python3-cairo";;
        pangocairo)          echo "typelib-1_0-PangoCairo-1_0 pango";;
        pillow)              echo "python3-Pillow python3-pillow";;
        mutagen)             echo "python3-mutagen";;
        libarchive-c)        echo "python3-libarchive-c";;
        p7zip)               echo "7zip p7zip";;
        poppler)             echo "poppler-tools poppler-utils";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    apk)
      case "$1" in
        nautilus-python)     echo "nautilus-python";;
        gobject)             echo "py3-gobject3 pygobject3";;
        gtk4)                echo "gtk4";;
        libadwaita)          echo "libadwaita";;
        nautilus-extensions) echo "nautilus";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "py3-pypdf";;
        cairo)               echo "py3-cairo cairo";;
        pangocairo)          echo "pango";;
        pillow)              echo "py3-pillow";;
        mutagen)             echo "py3-mutagen";;
        libarchive-c)        echo "py3-libarchive-c";;
        p7zip)               echo "7zip p7zip";;
        poppler)             echo "poppler-utils poppler-tools";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    xbps)
      case "$1" in
        nautilus-python)     echo "nautilus-python";;
        gobject)             echo "python3-gobject";;
        gtk4)                echo "gtk4";;
        libadwaita)          echo "libadwaita";;
        nautilus-extensions) echo "nautilus";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python3-pypdf";;
        cairo)               echo "python3-cairo";;
        pangocairo)          echo "pango";;
        pillow)              echo "python3-pillow";;
        mutagen)             echo "python3-mutagen";;
        libarchive-c)        echo "python3-libarchive-c";;
        p7zip)               echo "p7zip 7zip";;
        poppler)             echo "poppler-utils";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
    eopkg)
      case "$1" in
        nautilus-python)     echo "nautilus-python";;
        gobject)             echo "python-gobject";;
        gtk4)                echo "gtk4";;
        libadwaita)          echo "libadwaita";;
        nautilus-extensions) echo "nautilus";;
        ghostscript)         echo "ghostscript";;
        ffmpeg)              echo "ffmpeg";;
        ffmpegthumbnailer)   echo "ffmpegthumbnailer";;
        pypdf)               echo "python-pypdf";;
        cairo)               echo "python-cairo";;
        pangocairo)          echo "pango";;
        pillow)              echo "python-pillow";;
        mutagen)             echo "python-mutagen";;
        libarchive-c)        echo "python-libarchive-c";;
        p7zip)               echo "p7zip 7zip";;
        poppler)             echo "poppler-utils";;
        rsync)               echo "rsync";;
        ripgrep)             echo "ripgrep";;
        git)                 echo "git";;
        unrar)               echo "unrar";;
      esac;;
  esac
}

# Install one candidate at a time so a single wrong/unavailable package name
# does not sink the whole dependency step. Returns 0 when any candidate worked.
try_key() {
  local key="$1" cand
  local cands
  cands="$(pkg_candidates "$key")"
  if [ -z "$cands" ]; then
    warn "no package mapping for '$key' on $PKG_MANAGER (skipping)"
    return 1
  fi
  for cand in $cands; do
    echo "    -> trying package '$cand'..."
    if pkg_install "$cand"; then
      return 0
    fi
    warn "package '$cand' failed for '$key'"
  done
  return 1
}

pkg_install() {
  [ "$#" -eq 0 ] && return 0
  case "$PKG_MANAGER" in
    apt)    sudo apt-get install -y "$@";;
    dnf)    sudo dnf install -y "$@";;
    pacman) sudo pacman -S --needed --noconfirm "$@";;
    zypper) sudo zypper --non-interactive install "$@";;
    apk)    sudo apk add "$@";;
    xbps)   sudo xbps-install -Sy "$@";;
    eopkg)  sudo eopkg install -y "$@";;
    *)      return 1;;
  esac
}

confirm() {
  local ans=""
  if [ -e /dev/tty ]; then
    printf "%s [y/N] " "$1" > /dev/tty
    read -r ans < /dev/tty || ans=""
  fi
  case "$ans" in
    [yY]*) return 0;;
    *)     return 1;;
  esac
}

# ---------------------------------------------------------------------------
# Coexistence with the (future) system-wide PPA install
# ---------------------------------------------------------------------------
if [ -d "$PPA_DIR" ]; then
  warn "A system-wide install already exists at $PPA_DIR (PPA layout)."
  warn "A per-user install may shadow or clash with it."
  if [ "$ASSUME_YES" -eq 1 ]; then
    warn "Continuing anyway because --yes was given."
  elif ! confirm "Continue with the per-user install anyway?"; then
    die "Aborted to avoid clashing with the system install."
  fi
fi

# ---------------------------------------------------------------------------
# Locate payload: use local checkout or clone the repo (curl | bash)
# ---------------------------------------------------------------------------
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/folder-color-revival.py" ]; then
  echo "==> No local checkout found, cloning $REPO_URL ..."
  if ! command -v git >/dev/null 2>&1; then
    echo "==> Installing git first..."
    try_key git || warn "git could not be installed automatically."
  fi
  SCRIPT_DIR="$(mktemp -d)/RedClaw-File-Tools"
  git clone --depth 1 "$REPO_URL" "$SCRIPT_DIR"
  trap 'rm -rf "$(dirname "$SCRIPT_DIR")"' EXIT
fi

# ---------------------------------------------------------------------------
# Resolve dependencies for the selected extensions
# ---------------------------------------------------------------------------
REQUIRED_KEYS=()
OPTIONAL_KEYS=()
declare -A KEY_SEEN=()

add_key() {
  local key="$1"
  if [ -n "${KEY_SEEN[$key]:-}" ]; then return 0; fi
  KEY_SEEN[$key]=1
  if [ "$key" = "unrar" ]; then
    OPTIONAL_KEYS+=("$key")
  else
    REQUIRED_KEYS+=("$key")
  fi
}

for key in "${BASE_KEYS[@]}"; do
  add_key "$key"
done
for slug in "${SELECTED[@]}"; do
  for key in $(slug_deps "$slug"); do
    add_key "$key"
  done
done

MISSING_KEYS=()
echo "==> Detected package manager: $PKG_MANAGER"
if [ "$PKG_MANAGER" = "unknown" ]; then
  warn "No known package manager found — skipping automatic dependency installation."
  warn "Extensions will still be copied; the verification step will report what is missing."
  MISSING_KEYS=("${REQUIRED_KEYS[@]}")
else
  echo "==> Installing dependencies for ${#SELECTED[@]} extension(s)..."
  for key in "${REQUIRED_KEYS[@]}"; do
    [ -z "$(pkg_candidates "$key")" ] && continue
    if ! try_key "$key"; then
      MISSING_KEYS+=("$key")
    fi
  done
fi

# unrar is optional (RPM Fusion nonfree on Fedora, not always available).
# 7z already covers regular RAR extraction.
if [ "${#OPTIONAL_KEYS[@]}" -gt 0 ] && [ "$NO_OPTIONAL" -eq 0 ]; then
  for key in "${OPTIONAL_KEYS[@]}"; do
    if ! command -v unrar >/dev/null 2>&1; then
      if [ "$PKG_MANAGER" = "unknown" ]; then
        warn "unrar not found — install it manually for password-protected RARs."
      else
        echo "==> Trying optional unrar ..."
        try_key "$key" || warn "unrar unavailable — password-protected RAR will use 7z."
      fi
    fi
  done
fi

# ---------------------------------------------------------------------------
# Verification: check what the extensions actually need — GI typelibs,
# Python modules and helper binaries — and report it, whatever the distro.
# Never aborts the install; the goal is an honest report, not a hard stop.
# ---------------------------------------------------------------------------
verify_environment() {
  echo "==> Verifying the environment (python3 + GObject/GTK + modules)..."
  python3 - <<'PYEOF'
import sys

try:
    import gi
    print("  [ ok ] python3 gobject-introspection (gi)")
except Exception:
    print("  [ MISSING ] gobject-introspection (install e.g. python3-gi / python3-gobject / py3-gobject3)")
    print("              Nautilus extensions cannot load without it. Fix that first, then re-run.")
    sys.exit(0)

def gi_check(lib, ver, mod):
    try:
        gi.require_version(lib, ver)
        getattr(__import__("gi.repository", fromlist=[mod]), mod)
        print("  [ ok ] %s %s typelib" % (lib, ver))
        return True
    except Exception:
        print("  [ MISSING ] %s %s typelib" % (lib, ver))
        return False

gi_check("Gtk", "4.0", "Gtk")
gi_check("Adw", "1", "Adw")
try:
    gi.require_version("Nautilus", "4.0")
    print("  [ ok ] Nautilus 4.0 typelib")
except Exception:
    try:
        gi.require_version("Nautilus", "4.1")
        print("  [ ok ] Nautilus 4.1 typelib")
    except Exception:
        print("  [ MISSING ] Nautilus 4.x typelib (install nautilus / gir1.2-nautilus-4.0 / nautilus-dev)")

gi_check("PangoCairo", "1.0", "PangoCairo")
gi_check("GdkPixbuf", "2.0", "GdkPixbuf")

for mod, hint in [("PIL.Image", "pillow / python-pillow / py3-pillow"),
                  ("cairo", "python3-cairo / python-cairo / py3-cairo"),
                  ("mutagen", "python3-mutagen / python-mutagen / py3-mutagen"),
                  ("pypdf", "pypdf / python3-pypdf / python-pypdf / py3-pypdf"),
                  ("libarchive", "libarchive-c / python3-libarchive-c / python-libarchive-c / py3-libarchive-c")]:
    try:
        __import__(mod)
        print("  [ ok ] python module %s" % mod)
    except Exception:
        print("  [ MISSING ] python module %s (%s)" % (mod, hint))
PYEOF
  command -v ffmpeg >/dev/null 2>&1       && echo "  [ ok ] ffmpeg"              || echo "  [ MISSING ] ffmpeg"
  { command -v 7z >/dev/null 2>&1 || command -v 7za >/dev/null 2>&1 || command -v 7zr >/dev/null 2>&1 || command -v 7zz >/dev/null 2>&1; } \
                                            && echo "  [ ok ] 7z (7-zip)"          || echo "  [ MISSING ] 7z (7zip / p7zip)"
  command -v gs >/dev/null 2>&1           && echo "  [ ok ] ghostscript (gs)"   || echo "  [ MISSING ] ghostscript (gs)"
  command -v rsync >/dev/null 2>&1        && echo "  [ ok ] rsync"              || echo "  [ MISSING ] rsync"
  command -v rg >/dev/null 2>&1           && echo "  [ ok ] ripgrep (rg)"       || echo "  [ MISSING ] ripgrep (rg)"
  command -v pdfinfo >/dev/null 2>&1      && echo "  [ ok ] poppler-utils"      || echo "  [ MISSING ] poppler-utils (pdfinfo)"
  command -v git >/dev/null 2>&1          && echo "  [ ok ] git"                || echo "  [ MISSING ] git"
}
verify_environment

# ---------------------------------------------------------------------------
# Install the selected extensions
# ---------------------------------------------------------------------------
echo "==> Installing extensions into $EXT_DIR ..."
mkdir -p "$EXT_DIR"

NEED_MEDIA_CORE=0
for slug in "${SELECTED[@]}"; do
  for f in $(slug_files "$slug"); do
    cp "$SCRIPT_DIR/$f" "$EXT_DIR"/
  done
  if needs_media_core "$slug"; then
    NEED_MEDIA_CORE=1
  fi
done

if [ -f "$SCRIPT_DIR/nautilus_i18n.py" ]; then
  cp "$SCRIPT_DIR/nautilus_i18n.py" "$EXT_DIR"/
fi

if printf '%s\n' "${SELECTED[@]}" | grep -qx folder-color-revival; then
  # Symbol assets and their license must travel with the editor, including
  # selective installations. Runtime lookup is relative to the helper module.
  mkdir -p "$EXT_DIR/assets"
  cp -R "$SCRIPT_DIR/assets/folder-icons" "$EXT_DIR/assets/"
fi

if [ "$NEED_MEDIA_CORE" -eq 1 ] && [ -d "$SCRIPT_DIR/$MEDIA_CORE_DIR" ]; then
  rm -rf "$EXT_DIR/$MEDIA_CORE_DIR"
  cp -r "$SCRIPT_DIR/$MEDIA_CORE_DIR" "$EXT_DIR"/
fi

# Drop any stale bytecode from a previous install (including media_core/).
rm -rf "$EXT_DIR/__pycache__"
if [ -d "$EXT_DIR/$MEDIA_CORE_DIR" ]; then
  find "$EXT_DIR/$MEDIA_CORE_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
fi

# Comic Tools also owns the default handler for comic archives, so that
# double-clicking a .cbz opens the pages instead of an archive browser.
if printf '%s\n' "${SELECTED[@]}" | grep -qx comic-tools; then
  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
  install -m 755 "$SCRIPT_DIR/comic-reader" "$HOME/.local/bin/comic-reader"
  install -m 644 "$SCRIPT_DIR/comic-reader.desktop" \
    "$HOME/.local/share/applications/comic-reader.desktop"
  if command -v xdg-mime >/dev/null 2>&1; then
    for mime in application/vnd.comicbook+zip application/vnd.comicbook-rar \
                application/x-cbz application/x-cbr application/x-cb7 \
                application/x-cbt application/x-ext-cbz application/x-ext-cbr \
                application/x-ext-cb7 application/x-ext-cbt; do
      xdg-mime default comic-reader.desktop "$mime" 2>/dev/null || true
    done
  fi
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
  fi
fi

# Terminal Tools also ships the synced terminal's command line client and the
# desktop entry that runs a script inside the terminal following Nautilus.
# Only the shell script types are claimed as the default handler: .py and the
# other types stay available through "Open With", so nothing the user already
# opens in an editor gets hijacked.
if printf '%s\n' "${SELECTED[@]}" | grep -qx terminal-tools; then
  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
  if [ -f "$SCRIPT_DIR/nautilus-follow-run" ]; then
    install -m 755 "$SCRIPT_DIR/nautilus-follow-run" "$HOME/.local/bin/nautilus-follow-run"
  fi
  if [ -f "$SCRIPT_DIR/nautilus-follow-run.desktop" ]; then
    install -m 644 "$SCRIPT_DIR/nautilus-follow-run.desktop" \
      "$HOME/.local/share/applications/nautilus-follow-run.desktop"
    if command -v xdg-mime >/dev/null 2>&1; then
      for mime in text/x-shellscript application/x-sh application/x-shellscript; do
        xdg-mime default nautilus-follow-run.desktop "$mime" 2>/dev/null || true
      done
    fi
  fi
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
  fi
fi

echo "==> Restarting Nautilus..."
nautilus -q || true

if [ "${#MISSING_KEYS[@]}" -gt 0 ]; then
  echo "Dependency groups that could not be installed: ${MISSING_KEYS[*]}"
  echo "(They may already be present — check the verification report above.)"
  echo "Packages missing there: install the matching names shown in the report, then re-run."
fi
echo "Done! Installed ${#SELECTED[@]} extension(s). Open Nautilus and right-click, or use F3 F4 F7 F8 F9."
