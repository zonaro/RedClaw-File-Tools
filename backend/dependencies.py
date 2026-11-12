"""Host dependency discovery and explicit, auditable package installation."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


BASE_NAUTILUS = ("nautilus-python", "gobject", "gtk4", "libadwaita", "nautilus-extensions")
BINARIES = {
    "git": ("git",), "ffmpeg": ("ffmpeg",), "ffmpegthumbnailer": ("ffmpegthumbnailer",),
    "ghostscript": ("gs",), "rsync": ("rsync",), "ripgrep": ("rg",),
    "p7zip": ("7z", "7zz", "7za"), "unrar": ("unrar",), "poppler": ("pdfinfo",),
}
MODULES = {
    "pillow": "PIL", "pypdf": "pypdf", "mutagen": "mutagen",
    "cairo": "cairo", "libarchive-c": "libarchive", "gobject": "gi",
}
GI_MODULES = {
    "nautilus-python": ("Nautilus", "4.0"),
    "gtk4": ("Gtk", "4.0"),
    "libadwaita": ("Adw", "1"),
    "nautilus-extensions": ("Nautilus", "4.0"),
    "pangocairo": ("PangoCairo", "1.0"),
}
PACKAGES = {
    "apt": {
        "python3": "python3", "nautilus-python": "python3-nautilus", "gobject": "python3-gi",
        "gtk4": "gir1.2-gtk-4.0", "libadwaita": "gir1.2-adw-1", "nautilus-extensions": "gir1.2-nautilus-4.0",
        "pillow": "python3-pil", "pypdf": "python3-pypdf", "mutagen": "python3-mutagen",
        "cairo": "python3-cairo", "libarchive-c": "python3-libarchive-c",
        "pangocairo": "gir1.2-pangocairo-1.0", "p7zip": "7zip", "poppler": "poppler-utils", "clipboard": "xclip",
    },
    "pacman": {
        "python3": "python", "nautilus-python": "python-nautilus", "gobject": "python-gobject",
        "gtk4": "gtk4", "libadwaita": "libadwaita", "nautilus-extensions": "nautilus",
        "pillow": "python-pillow", "pypdf": "python-pypdf", "mutagen": "python-mutagen",
        "cairo": "python-cairo", "libarchive-c": "python-libarchive-c",
        "pangocairo": "pango", "p7zip": "7zip", "poppler": "poppler", "clipboard": "xclip",
    },
    "dnf": {
        "python3": "python3", "nautilus-python": "nautilus-python", "gobject": "python3-gobject",
        "gtk4": "gtk4", "libadwaita": "libadwaita", "nautilus-extensions": "nautilus-extensions",
        "pillow": "python3-pillow", "pypdf": "python3-pypdf", "mutagen": "python3-mutagen",
        "cairo": "python3-cairo", "libarchive-c": "python3-libarchive-c",
        "pangocairo": "pango", "p7zip": "7zip", "poppler": "poppler-utils", "clipboard": "xclip",
    },
    "zypper": {
        "python3": "python3", "nautilus-python": "python3-nautilus", "gobject": "python3-gobject",
        "gtk4": "typelib-1_0-Gtk-4_0", "libadwaita": "typelib-1_0-Adw-1",
        "nautilus-extensions": "typelib-1_0-Nautilus-4_0",
        "pillow": "python3-Pillow", "pypdf": "python3-pypdf", "mutagen": "python3-mutagen",
        "cairo": "python3-cairo", "libarchive-c": "python3-libarchive-c",
        "pangocairo": "typelib-1_0-PangoCairo-1_0", "p7zip": "7zip",
        "poppler": "poppler-tools", "clipboard": "xclip",
    },
}
for row in PACKAGES.values():
    for name in ("git", "ffmpeg", "ffmpegthumbnailer", "ghostscript", "rsync", "ripgrep", "unrar"):
        row.setdefault(name, name)


def package_manager() -> str | None:
    for name, binary in (("apt", "apt-get"), ("dnf", "dnf"), ("pacman", "pacman"), ("zypper", "zypper")):
        if shutil.which(binary):
            return name
    return None


def _python_check(code: str) -> bool:
    binary = shutil.which("python3")
    if binary is None:
        return False
    return subprocess.run([binary, "-c", code], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False, timeout=12).returncode == 0


def available(key: str) -> bool:
    if key == "python3":
        return shutil.which("python3") is not None
    if key == "clipboard":
        return any(shutil.which(name) for name in ("wl-copy", "xclip", "xsel"))
    if key in BINARIES:
        return any(shutil.which(binary) for binary in BINARIES[key])
    if key in GI_MODULES:
        namespace, version = GI_MODULES[key]
        return _python_check(
            f"import gi; gi.require_version('{namespace}', '{version}');"
            f"from gi.repository import {namespace}"
        )
    if key in MODULES:
        return _python_check(f"import {MODULES[key]}")
    return False


def requirements(entry: dict, fm: str) -> list[str]:
    if fm == "nautilus":
        return list(dict.fromkeys(("python3", *BASE_NAUTILUS, *entry["dependencies"])))
    keys = ["python3"]
    if entry["id"] == "image-tools":
        keys.append("pillow")
    if entry["id"] == "file-tools":
        keys.append("clipboard")
    return keys


def dependency_plan(entry: dict, fm: str) -> dict:
    keys = requirements(entry, fm)
    missing = [key for key in keys if not available(key) and key != "unrar"]
    optional = [key for key in keys if key == "unrar" and not available(key)]
    manager = package_manager()
    mapping = PACKAGES.get(manager, {})
    packages = list(dict.fromkeys(mapping[key] for key in missing if key in mapping))
    unresolved = [key for key in missing if key not in mapping]
    return {
        "required": keys,
        "missing": missing,
        "optional_missing": optional,
        "manager": manager,
        "packages": packages,
        "unresolved": unresolved,
        "requires_admin": bool(packages) and os.geteuid() != 0,
    }


def install_dependencies(plan: dict) -> None:
    packages = plan["packages"]
    if not packages:
        if plan["unresolved"]:
            raise RuntimeError("No automatic package mapping for: " + ", ".join(plan["unresolved"]))
        return
    manager = plan["manager"]
    commands = {
        "apt": ["apt-get", "install", "-y"],
        "dnf": ["dnf", "install", "-y"],
        "pacman": ["pacman", "-S", "--needed", "--noconfirm"],
        "zypper": ["zypper", "--non-interactive", "install"],
    }
    if manager not in commands:
        raise RuntimeError("Unsupported distribution package manager.")
    command = commands[manager] + packages
    if os.geteuid() != 0:
        pkexec = shutil.which("pkexec")
        if not pkexec:
            raise RuntimeError("Polkit (pkexec) is required to install system dependencies.")
        command = [pkexec, *command]
    subprocess.run(command, check=True)
    remaining = [key for key in plan["missing"] if not available(key)]
    if remaining:
        raise RuntimeError("Dependencies still missing after installation: " + ", ".join(remaining))
