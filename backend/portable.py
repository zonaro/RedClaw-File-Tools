"""Portable file operations. Never depends on Nautilus or a desktop session."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


class ActionError(RuntimeError):
    pass


def _notify(title: str, message: str) -> None:
    notifier = shutil.which("notify-send")
    if notifier:
        subprocess.run([notifier, title, message], check=False, timeout=10)


def _unique_output(candidate: Path) -> Path:
    if not candidate.exists():
        return candidate
    for n in range(2, 10000):
        alternative = candidate.with_name(f"{candidate.stem}-{n}{candidate.suffix}")
        if not alternative.exists():
            return alternative
    raise ActionError(f"No available output name for {candidate}")


def _selected(paths: list[str]) -> list[Path]:
    if not paths:
        raise ActionError("No files selected.")
    result = [Path(item).expanduser().absolute() for item in paths]
    if any(not item.exists() for item in result):
        raise ActionError("Some selected paths do not exist.")
    return result


def checksum(paths: list[str]) -> list[str]:
    output = []
    for item in _selected(paths):
        if not item.is_file():
            continue
        digest = hashlib.sha256()
        with item.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        report = _unique_output(item.with_name(item.name + ".sha256"))
        report.write_text(f"{digest.hexdigest()}  {item.name}\n", encoding="utf-8")
        output.append(str(report))
    if not output:
        raise ActionError("Select one or more regular files.")
    _notify("RedClaw File Tools", f"Created {len(output)} SHA-256 report(s).")
    return output


def copy_paths(paths: list[str]) -> list[str]:
    normalized = [str(path) for path in _selected(paths)]
    content = "\n".join(normalized)
    clipboard = None
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
        clipboard = ["wl-copy"]
    elif shutil.which("xclip"):
        clipboard = ["xclip", "-selection", "clipboard"]
    elif shutil.which("xsel"):
        clipboard = ["xsel", "--clipboard", "--input"]
    if not clipboard:
        raise ActionError("Clipboard helper missing (wl-clipboard, xclip or xsel).")
    subprocess.run(clipboard, input=content.encode("utf-8"), check=True, timeout=15)
    _notify("RedClaw File Tools", f"Copied {len(normalized)} path(s).")
    return normalized


def _safe_target(root: Path, name: str) -> Path:
    if not name or name.startswith("/") or "\\x00" in name:
        raise ActionError("Unsafe archive entry.")
    destination = (root / name).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ActionError("Archive entry escapes destination directory.")
    return destination


def extract_archives(paths: list[str]) -> list[str]:
    outputs = []
    for item in _selected(paths):
        if not item.is_file():
            continue
        lower = item.name.lower()
        if lower.endswith(".tar.gz"):
            stem = item.name[:-7]
        elif lower.endswith(".tar.bz2"):
            stem = item.name[:-8]
        elif lower.endswith(".tar.xz"):
            stem = item.name[:-7]
        elif lower.endswith(".tgz"):
            stem = item.name[:-4]
        else:
            stem = item.stem
        root = item.parent / stem
        root = _unique_output(root)
        if zipfile.is_zipfile(item):
            with zipfile.ZipFile(item) as archive:
                entries = archive.infolist()
                for entry in entries:
                    _safe_target(root, entry.filename)
                    # Ignore Unix symlink entries, which could point outside root.
                    if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ActionError("Archive symlinks are not supported.")
                root.mkdir(parents=True)
                for entry in entries:
                    archive.extract(entry, root)
        elif tarfile.is_tarfile(item):
            with tarfile.open(item) as archive:
                entries = archive.getmembers()
                for entry in entries:
                    _safe_target(root, entry.name)
                    if not (entry.isfile() or entry.isdir()):
                        raise ActionError("Archive contains special or linked entries.")
                root.mkdir(parents=True)
                for entry in entries:
                    target = _safe_target(root, entry.name)
                    if entry.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = archive.extractfile(entry)
                        if source is None:
                            raise ActionError("Unreadable archive entry.")
                        with source, target.open("xb") as dest:
                            shutil.copyfileobj(source, dest)
        else:
            raise ActionError(f"Unsupported archive format: {item.name} (ZIP/TAR only)")
        outputs.append(str(root))
    if not outputs:
        raise ActionError("Select one or more ZIP/TAR archives.")
    _notify("RedClaw File Tools", f"Extracted {len(outputs)} archive(s).")
    return outputs


def convert_png(paths: list[str]) -> list[str]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ActionError("Pillow is required for PNG conversion.") from exc
    outputs = []
    for item in _selected(paths):
        if not item.is_file():
            continue
        output = _unique_output(item.with_name(item.stem + "_rft.png"))
        with Image.open(item) as image:
            image.convert("RGBA").save(output, format="PNG")
        outputs.append(str(output))
    if not outputs:
        raise ActionError("Select one or more image files.")
    _notify("RedClaw File Tools", f"Converted {len(outputs)} image(s).")
    return outputs


ACTIONS = {
    ("file-tools", "sha256"): checksum,
    ("file-tools", "copy-path"): copy_paths,
    ("extract-here", "extract"): extract_archives,
    ("image-tools", "to-png"): convert_png,
}


def run(slug: str, action: str, paths: list[str]) -> list[str]:
    if slug == "ai-watermarks":
        # Lazy import: the optional third-party engine is never a base dependency.
        from ai_watermarks import run as run_ai_watermarks
        return run_ai_watermarks(action, paths)
    handler = ACTIONS.get((slug, action))
    if handler is None:
        raise ActionError(f"Unsupported action: {slug}/{action}")
    return handler(paths)
