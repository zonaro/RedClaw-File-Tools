# Linux AppImage rendering and black-window troubleshooting

## Symptom

The native window title bar is visible, but the Flutter interface appears
partially at the bottom-left while the rest of the window is black. This is
**not** a Flutter widget overflow. It happens below Dart's layout layer, in
the Linux GTK/graphics renderer and/or the packaged graphics libraries.

The first reported screenshots were captured on CachyOS + GNOME.
A responsive sliver layout alone did not fix the black window.

## What changed

1. **Skia is now the default Linux renderer.** Flutter 3.47+ enables Impeller
   by default on Linux, and Impeller has documented compatibility problems on
   certain Wayland/NVIDIA/Mesa combinations. The build patches the generated
   `manager/linux/runner/my_application.cc` via
   `scripts/patch_flutter_linux_runner.py` immediately after `flutter create`,
   using the official `fl_dart_project_set_enable_impeller(project, FALSE)` API.
   The patch is deterministic, idempotent and fails when the Flutter template
   changes.
2. **Driver/display-server libraries are excluded from AppImage.**
   `scripts/strip_host_graphics_libs.sh` removes bundled Ubuntu
   GL/GLX/EGL/GLES/GBM/DRM/Wayland/Vulkan shared objects after linuxdeploy and
   before appimagetool. These libraries must match the user's running graphics
   driver. The Flutter engine and other runtime libraries remain bundled.
3. **No forced X11 by default.** The launcher respects the host's native
   Wayland/X11 session. X11 and software rendering are available as
   opt-in troubleshooting modes.
4. **Host Python is isolated.** The Flutter manager no longer passes the
   AppImage's `LD_LIBRARY_PATH` or `LD_PRELOAD` to the host Python process,
   preventing conflict with the distribution's own GTK/GLib and package tools.
5. **Release smoke tests** open the built AppImage under Xvfb, capture the
   actual GTK window, and fail if most of the viewport is black. Hardware
   differences mean the reporter still needs to verify the result.

## How to test the current AppImage

The following options are available in **new builds only**:

```bash
chmod +x RedClaw_File_Tools-*.AppImage

# Default: Skia + native display backend (recommended).
./RedClaw_File_Tools-*.AppImage

# Diagnostics (does not launch the UI).
./RedClaw_File_Tools-*.AppImage --redclaw-diagnostics

# Alternative 1: XWayland/X11 with Skia, if a native Wayland issue persists.
./RedClaw_File_Tools-*.AppImage --redclaw-x11

# Alternative 2: experimental software rendering.
./RedClaw_File_Tools-*.AppImage --redclaw-software

# Development comparison only: opt back into Impeller.
./RedClaw_File_Tools-*.AppImage --redclaw-impeller

# Show all launcher options.
./RedClaw_File_Tools-*.AppImage --redclaw-help
```

Only one AppImage should match the `*.AppImage` wildcard in these commands;
otherwise, substitute the exact filename.

To capture graphics errors, run in a terminal with:

```bash
./RedClaw_File_Tools-*.AppImage 2>&1 | tee /tmp/redclaw-renderer.log
```

Share the messages that mention `EGL`, `GLX`, `Impeller`, `Skia` or
`Gdk` together with the output of `--redclaw-diagnostics`. Do not include
private file paths or other sensitive log contents.

## Why no unconditional X11 or software renderer?

X11 may be unavailable on some environments, and Flutter software rendering
can be slower or unsupported on some engine versions. The preferred fix is to
use a stable Linux Flutter renderer and let the machine load its own graphics
drivers. The extra options are manual fallbacks, not silent changes to the
user's desktop session.

## Links to upstream technical findings

- [Flutter official Impeller documentation](https://docs.flutter.dev/perf/impeller)
- [Flutter Linux: Wayland + NVIDIA black screen](https://github.com/flutter/flutter/issues/188966)
- [Flutter Linux: resize / EGL issues](https://github.com/flutter/flutter/issues/191775)
- [CachyOS: bundled Wayland/EGL graphics libraries break AppImage](https://github.com/espressif/idf-im-ui/issues/755)
- [AppImage community graphics-library exclusions](https://github.com/AppImageCommunity/pkg2appimage/blob/master/excludelist)

## Release requirements

Release names use `YY.DDD.HHMM` based on build time in
`America/Sao_Paulo`. All GitHub Releases must have English descriptions;
the Flutter UI and extensions retain pt-BR, English, Spanish, French and German.

This issue is tracked at [#79](https://github.com/zonaro/RedClaw-File-Tools/issues/79),
with related user-interface findings at [#76](https://github.com/zonaro/RedClaw-File-Tools/issues/76).
