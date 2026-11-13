"""Independent install/uninstall state for each extension and file manager."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import adapters
import dependencies


def _home(env_key: str, fallback: str) -> Path:
    return Path(os.environ.get(env_key, str(Path.home() / fallback))).expanduser()


STATE = _home("XDG_STATE_HOME", ".local/state") / "redclaw-file-tools/installed.json"
RUNTIME = adapters.data_home() / "redclaw-file-tools/runtime"
SUPPORTED = ("nautilus", "dolphin", "nemo", "caja", "thunar", "pcmanfm-qt")


def payload_dir() -> Path:
    return Path(os.environ.get("REDCLAW_PAYLOAD", str(Path(__file__).resolve().parent.parent)))


def read_catalog() -> dict:
    return json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))


def _sha(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _load_state() -> dict:
    if not STATE.exists():
        return {"schema_version": 1, "installed": {}}
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("installed"), dict):
        raise RuntimeError("Unrecognized installed-state schema; refusing to modify it.")
    return data


def _atomic_write(path: Path, contents: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".rft-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(contents)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _save_state(state: dict) -> None:
    _atomic_write(STATE, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())


def _key(fm: str, slug: str) -> str:
    return fm + "/" + slug


def get_entry(catalog: dict, slug: str) -> dict:
    return next((entry for entry in catalog["extensions"] if entry["id"] == slug), None)


def detect_file_managers(catalog: dict, state: dict | None = None) -> list[dict]:
    state = state or _load_state()
    result = []
    for fm in catalog["file_managers"]:
        installed = shutil.which(fm["binary"]) is not None
        has_data = any(key.startswith(fm["id"] + "/") for key in state["installed"])
        if installed or has_data:
            result.append({**fm, "detected": installed, "has_managed_extensions": has_data})
    return result


def _external_nautilus(entry: dict) -> bool:
    items = entry["files"]
    if not items:
        return False
    source = items[0]
    filename = Path(source).name
    return (adapters.data_home() / "nautilus-python/extensions" / filename).exists()


def installed_status(entry: dict, fm: str, state: dict) -> str:
    record = state["installed"].get(_key(fm, entry["id"]))
    if record:
        disabled = record.get("enabled", True) is False
        disabled_files = record.get("disabled_files", {})
        if fm == "thunar":
            has_actions = adapters.thunar_has(entry)
            if has_actions == disabled:
                return "modified"
        for name, expected in record.get("files", {}).items():
            target = Path(disabled_files.get(name, name))
            if not target.is_file() or _sha(target.read_bytes()) != expected:
                return "modified"
            if name in disabled_files and Path(name).exists():
                return "modified"
        return "disabled" if disabled else "installed"
    if fm == "nautilus" and _external_nautilus(entry):
        return "external"
    return "not_installed"

def inventory() -> dict:
    catalog = read_catalog()
    state = _load_state()
    fms = detect_file_managers(catalog, state)
    entries = []
    for entry in catalog["extensions"]:
        compatibility = {}
        for fm in fms:
            fm_id = fm["id"]
            info = dict(entry["compatibility"][fm_id])
            if entry["id"] == "deb-installer" and fm_id == "nautilus":
                release = Path("/etc/os-release")
                data = release.read_text(errors="replace") if release.exists() else ""
                if not any(piece in data.lower() for piece in ("debian", "ubuntu", "linuxmint")):
                    info.update(recommendation="redundant", reason="DEB packages are not native on this distribution.")
            info["status"] = installed_status(entry, fm_id, state)
            compatibility[fm_id] = info
        entries.append({
            "id": entry["id"], "name": entry["name"], "category": entry["category"],
            "compatibility": compatibility, "dependencies": entry["dependencies"],
        })
    return {
        "product": catalog["product"], "schema_version": 1,
        "file_managers": fms, "extensions": entries,
        "managed_count": len(state["installed"]),
    }


def plan(fm: str, slug: str) -> dict:
    if fm not in SUPPORTED:
        raise ValueError("Unknown file manager: " + fm)
    entry = get_entry(read_catalog(), slug)
    if entry is None:
        raise ValueError("Unknown extension: " + slug)
    capability = entry["compatibility"][fm]
    if capability["support"] == "unsupported":
        raise ValueError("This extension is not supported on " + fm)
    if shutil.which(fm) is None and not (fm == "pcmanfm-qt" and shutil.which("pcmanfm")):
        raise ValueError(f"File manager not installed: {fm}")
    state = _load_state()
    dep = dependencies.dependency_plan(entry, fm)
    conflicts = [candidate for candidate in entry.get("conflicts", [])
                 if _key(fm, candidate) in state["installed"]]
    return {
        "file_manager": fm,
        "slug": slug,
        "support": capability["support"],
        "recommendation": capability["recommendation"],
        "status": installed_status(entry, fm, state),
        "conflicts": conflicts,
        "dependencies": dep,
        "requires_confirmation": True,
    }


def _runtime_sources() -> dict[Path, tuple[bytes, int]]:
    backend = Path(__file__).resolve().parent
    return {
        RUNTIME / name: ((backend / name).read_bytes(), 0o644)
        for name in ("redclaw.py", "engine.py", "adapters.py", "dependencies.py", "portable.py", "ai_watermarks.py", "catalog.json")
    }


def _other_owner(state: dict, path: str, current_key: str) -> bool:
    return any(path in record.get("files", {})
               for key, record in state["installed"].items() if key != current_key)


def install(fm: str, slug: str, *, install_deps: bool, confirmed: bool) -> dict:
    if not confirmed:
        raise ValueError("Installation requires explicit --yes confirmation.")
    planned = plan(fm, slug)
    if planned.get("conflicts"):
        raise RuntimeError("Remove conflicting extensions first: " + ", ".join(planned["conflicts"]))
    if planned["status"] == "external":
        raise RuntimeError("An unmanaged Nautilus installation already exists. Refusing to overwrite it.")
    if planned["status"] == "disabled":
        raise RuntimeError("Enable this extension before updating it.")
    if planned["status"] == "modified":
        raise RuntimeError("Managed files were modified or removed; refusing to overwrite without recovery.")
    entry = get_entry(read_catalog(), slug)
    state = _load_state()
    key = _key(fm, slug)
    mapping = adapters.render_files(fm, entry, payload_dir())
    previous = state["installed"].get(key, {"files": {}})
    # Refuse to overwrite files from unknown installers or local changes.
    for dest, (contents, _) in mapping.items():
        name = str(dest)
        if dest.is_file():
            old = _sha(dest.read_bytes())
            owned_digest = previous["files"].get(name)
            if owned_digest is None:
                for record in state["installed"].values():
                    if name in record.get("files", {}):
                        owned_digest = record["files"][name]
                        break
            if owned_digest is None or owned_digest != old:
                raise RuntimeError("Unmanaged or modified file at " + name)
    dep = planned["dependencies"]
    if dep["missing"]:
        if not install_deps:
            raise RuntimeError("Missing dependencies: " + ", ".join(dep["missing"]))
        dependencies.install_dependencies(dep)
    # Thunar's existing uca.xml is not a standalone managed file.
    if fm == "thunar":
        if adapters.thunar_has(entry) and key not in state["installed"]:
            raise RuntimeError("Unmanaged Thunar actions with our identifiers already exist.")
        old_uca = adapters.thunar_file().read_bytes() if adapters.thunar_file().exists() else None
    else:
        old_uca = None
    # Stage and atomically replace per-user files; restore previous files on error.
    changed: dict[Path, tuple[bytes | None, int]] = {}
    try:
        if fm != "nautilus" or slug == "ai-watermarks":
            for dest, (content, mode) in _runtime_sources().items():
                _atomic_write(dest, content, mode)
        for dest, (content, mode) in mapping.items():
            changed[dest] = (dest.read_bytes() if dest.is_file() else None,
                             dest.stat().st_mode & 0o777 if dest.is_file() else 0o644)
            _atomic_write(dest, content, mode)
        if fm == "thunar":
            adapters.thunar_change(entry, True)
        record = {"file_manager": fm, "slug": slug, "enabled": True,
                  "files": {str(dest): _sha(content) for dest, (content, _) in mapping.items()},
                  "modes": {str(dest): mode for dest, (_, mode) in mapping.items()}}
        state["installed"][key] = record
        # Shared helper changes are owned by each consumer; synchronize hashes.
        for other_key, other in state["installed"].items():
            if other_key == key:
                continue
            for name, digest in record["files"].items():
                if name in other.get("files", {}):
                    other["files"][name] = digest
        _save_state(state)
    except Exception:
        for dest, (old_bytes, old_mode) in changed.items():
            if old_bytes is None:
                dest.unlink(missing_ok=True)
            else:
                _atomic_write(dest, old_bytes, old_mode)
        if fm == "thunar":
            if old_uca is None:
                adapters.thunar_file().unlink(missing_ok=True)
            else:
                _atomic_write(adapters.thunar_file(), old_uca)
        raise
    return {"ok": True, "file_manager": fm, "slug": slug, "status": "installed",
            "files_installed": len(mapping), "dependencies": dep}


def uninstall(fm: str, slug: str, *, confirmed: bool) -> dict:
    if not confirmed:
        raise ValueError("Uninstallation requires explicit --yes confirmation.")
    state = _load_state()
    key = _key(fm, slug)
    if key not in state["installed"]:
        raise ValueError("No managed installation found for " + key)
    entry = get_entry(read_catalog(), slug)
    record = state["installed"][key]
    for name, expected_digest in record.get("files", {}).items():
        target = Path(name)
        if target.exists() and _sha(target.read_bytes()) != expected_digest:
            raise RuntimeError("File modified since installation: " + name)
    if fm == "thunar":
        adapters.thunar_change(entry, False)
    removed = []
    for name in record.get("files", {}):
        if not _other_owner(state, name, key):
            Path(name).unlink(missing_ok=True)
            removed.append(name)
    del state["installed"][key]
    _save_state(state)
    # Do not remove system packages, shared runtime, or user-generated outputs.
    return {"ok": True, "file_manager": fm, "slug": slug,
            "status": "not_installed", "files_removed": len(removed)}
