#!/usr/bin/env python3
"""Patch Flutter's generated GTK3 Linux runner to avoid Impeller graphics bugs.

Flutter 3.47+ enables Impeller by default on Linux. Some Wayland/NVIDIA/Mesa
combinations produce black or incorrectly positioned Flutter surfaces. The
official Linux embedder API supports opting out in my_application.cc.

Run this *after* 'flutter create --platforms=linux' and before 'flutter build'.
The patch is idempotent and intentionally fails if the generated template
changes, to avoid silently releasing a broken AppImage.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MARKER = "// RedClaw: use the stable Skia renderer by default on Linux."
PROJECT_INIT = re.compile(
    r"^(?P<indent>[ \t]*)g_autoptr\(FlDartProject\)\s+"
    r"project\s*=\s*fl_dart_project_new\(\);[ \t]*$",
    re.MULTILINE,
)


def patched_runner(original: str) -> str:
    if MARKER in original:
        if original.count(MARKER) != 1:
            raise ValueError("Duplicate renderer compatibility patches found.")
        return original
    matches = list(PROJECT_INIT.finditer(original))
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one FlDartProject construction in the generated "
            "Linux runner. Flutter's template changed; review it before "
            "building another release."
        )
    match = matches[0]
    indent = match.group("indent")
    addition = "\n".join([
        indent + MARKER,
        indent + "// Set REDCLAW_ENABLE_IMPELLER=1 to opt in when testing new drivers.",
        indent + 'if (g_strcmp0(g_getenv("REDCLAW_ENABLE_IMPELLER"), "1") != 0) {',
        indent + "  fl_dart_project_set_enable_impeller(project, FALSE);",
        indent + "}",
    ])
    result = original[: match.end()] + "\n" + addition + original[match.end():]
    # GTK-generated runner uses this label as the native title bar caption.
    result = result.replace('"redclaw_file_tools"', '"RedClaw File Tools"')
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "runner", type=Path,
        help="Generated manager/linux/runner/my_application.cc file",
    )
    args = parser.parse_args()
    if not args.runner.is_file():
        parser.error(f"Runner does not exist: {args.runner}")
    old = args.runner.read_text(encoding="utf-8")
    new = patched_runner(old)
    if new != old:
        args.runner.write_text(new, encoding="utf-8")
        print(f"Patched Flutter Linux runner: {args.runner}")
    else:
        print(f"Flutter Linux runner already patched: {args.runner}")


if __name__ == "__main__":
    main()
