"""Native per-file-manager menu generators for portable subsets."""
from __future__ import annotations

import os
import shlex
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


ACTION_LABELS = {
    "sha256": {
        "en": "Create SHA-256 checksum",
        "pt": "Criar checksum SHA-256",
        "es": "Crear suma SHA-256",
        "fr": "Créer une somme SHA-256",
        "de": "SHA-256-Prüfsumme erstellen",
    },
    "copy-path": {
        "en": "Copy absolute path",
        "pt": "Copiar caminho absoluto",
        "es": "Copiar ruta absoluta",
        "fr": "Copier le chemin absolu",
        "de": "Absoluten Pfad kopieren",
    },
    "extract": {
        "en": "Extract ZIP/TAR here",
        "pt": "Extrair ZIP/TAR aqui",
        "es": "Extraer ZIP/TAR aquí",
        "fr": "Extraire ZIP/TAR ici",
        "de": "ZIP/TAR hier entpacken",
    },
    "to-png": {
        "en": "Convert image to PNG",
        "pt": "Converter imagem para PNG",
        "es": "Convertir imagen a PNG",
        "fr": "Convertir l’image en PNG",
        "de": "Bild in PNG umwandeln",
    },
    "identify": {"en": "Identify AI watermarks", "pt": "Identificar marcas de IA", "es": "Identificar marcas de agua de IA", "fr": "Identifier les filigranes IA", "de": "KI-Wasserzeichen erkennen"},
    "visible": {"en": "Remove visible AI watermark", "pt": "Remover marca d’água visível de IA", "es": "Eliminar marca de agua visible de IA", "fr": "Supprimer le filigrane IA visible", "de": "Sichtbares KI-Wasserzeichen entfernen"},
    "metadata": {"en": "Remove AI metadata", "pt": "Remover metadados de IA", "es": "Eliminar metadatos de IA", "fr": "Supprimer les métadonnées IA", "de": "KI-Metadaten entfernen"},
    "all": {"en": "Remove AI watermarks and metadata", "pt": "Remover marcas e metadados de IA", "es": "Eliminar marcas y metadatos de IA", "fr": "Supprimer filigranes et métadonnées IA", "de": "KI-Wasserzeichen und Metadaten entfernen"},
    "batch": {"en": "Batch remove visible AI watermarks", "pt": "Remover marcas visíveis em lote", "es": "Eliminar marcas visibles por lote", "fr": "Supprimer les filigranes visibles par lot", "de": "Sichtbare Wasserzeichen im Stapel entfernen"},

}


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def runner_path() -> Path:
    return data_home() / "redclaw-file-tools" / "runtime" / "redclaw.py"


def quote_exec(item: str) -> str:
    # Freedesktop desktop Entry quoting is not POSIX shell quoting.
    return '"' + item.replace("\\", "\\\\").replace('"', '\\"') + '"'


def exec_line(slug: str, action: str, placeholder: str = "%F") -> str:
    return f'python3 {quote_exec(str(runner_path()))} run {slug} {action} {placeholder}'


def _action_dest(fm: str, name: str) -> Path:
    data = data_home()
    base = {
        "dolphin": data / "kio/servicemenus",
        "nemo": data / "nemo/actions",
        "pcmanfm-qt": data / "file-manager/actions",
    }[fm]
    return base / name


def _translations(labels: dict[str, str]) -> str:
    return "\n".join([
        f"Name[{language}]={label}"
        for language, label in labels.items() if language != "en"
    ])


def render_files(fm: str, entry: dict, payload: Path) -> dict[Path, tuple[bytes, int]]:
    """Returns only files managed by RedClaw. No writes performed here."""
    slug = entry["id"]
    result: dict[Path, tuple[bytes, int]] = {}
    if fm == "nautilus" and slug == "ai-watermarks":
        # Nautilus script menus, not nautilus-python providers.
        for action in entry.get("portable_actions", []):
            action_id = action["id"]
            label = ACTION_LABELS[action_id]["en"]
            command = (
                "#!/bin/sh\n"
                f"exec python3 {shlex.quote(str(runner_path()))} run "
                f"{shlex.quote(slug)} {shlex.quote(action_id)} \"$@\"\n"
            )
            dest = data_home() / "nautilus/scripts/RedClaw File Tools/AI Watermarks" / label
            result[dest] = (command.encode(), 0o755)
        return result
    if fm == "nautilus":
        dest = data_home() / "nautilus-python/extensions"
        items = list(dict.fromkeys([*entry["files"], "nautilus_i18n.py"]))
        for relative in items:
            source = payload / relative
            if not source.exists():
                raise FileNotFoundError(f"Missing extension payload: {relative}")
            sources = [source] if source.is_file() else source.rglob("*")
            for current in sources:
                if not current.is_file() or "__pycache__" in current.parts:
                    continue
                target = dest / current.relative_to(payload)
                result[target] = (current.read_bytes(), 0o644)
        return result

    for action in entry.get("portable_actions", []):
        action_id = action["id"]
        titles = ACTION_LABELS[action_id]
        safe_name = f"redclaw-file-tools-{slug}-{action_id}"
        command = exec_line(slug, action_id)
        if fm == "dolphin":
            mimetypes = (
                "image/*;inode/directory;" if slug == "ai-watermarks" and action_id == "batch"
                else "image/*;" if slug in ("image-tools", "ai-watermarks")
                else "application/zip;application/x-tar;application/x-compressed-tar;" if slug == "extract-here"
                else "all/allfiles;inode/directory;"
            )
            text = (
                "[Desktop Entry]\n"
                "Type=Service\n"
                "X-KDE-ServiceTypes=KonqPopupMenu/Plugin\n"
                f"MimeType={mimetypes}\n"
                "Actions=redclaw;\n"
                "X-KDE-Priority=TopLevel\n\n"
                "[Desktop Action redclaw]\n"
                f"Name={titles['en']}\n{_translations(titles)}\n"
                f"Exec={command}\n"
                "Icon=applications-utilities\n"
            )
            result[_action_dest(fm, safe_name + ".desktop")] = (text.encode(), 0o644)
        elif fm == "nemo":
            text = (
                "[Nemo Action]\n"
                "Active=true\n"
                f"Name={titles['en']}\n{_translations(titles)}\n"
                f"Exec={command}\n"
                "Selection=notnone\n"
                "Extensions=any;\n"
                "Quote=double\n"
                "Icon-Name=applications-utilities\n"
            )
            result[_action_dest(fm, safe_name + ".nemo_action")] = (text.encode(), 0o644)
        elif fm == "caja":
            script = (
                "#!/bin/sh\n"
                f"exec python3 {shlex.quote(str(runner_path()))} run "
                f"{shlex.quote(slug)} {shlex.quote(action_id)} \"$@\"\n"
            )
            dest = data_home() / "caja/scripts/RedClaw File Tools" / titles["en"]
            result[dest] = (script.encode(), 0o755)
        elif fm == "pcmanfm-qt":
            text = (
                "[Desktop Entry]\n"
                "Type=Action\n"
                f"Name={titles['en']}\n{_translations(titles)}\n"
                "Profiles=redclaw;\n\n"
                "[X-Action-Profile redclaw]\n"
                f"Exec={command}\n"
                "MimeTypes=all/allfiles;inode/directory;\n"
            )
            result[_action_dest(fm, safe_name + ".desktop")] = (text.encode(), 0o644)
        elif fm != "thunar":
            raise ValueError(f"Unsupported file manager: {fm}")
    return result


def thunar_file() -> Path:
    return config_home() / "Thunar" / "uca.xml"


def _thunar_tree() -> ET.ElementTree:
    path = thunar_file()
    return ET.parse(path) if path.is_file() else ET.ElementTree(ET.Element("actions"))


def thunar_ids(entry: dict) -> set[str]:
    return {f"redclaw-file-tools-{entry['id']}-{a['id']}" for a in entry.get("portable_actions", [])}


def thunar_has(entry: dict) -> bool:
    try:
        root = _thunar_tree().getroot()
    except ET.ParseError:
        return False
    existing = {element.findtext("unique-id") for element in root.findall("action")}
    return bool(thunar_ids(entry) & existing)


def _write_xml(tree: ET.ElementTree) -> None:
    dest = thunar_file()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".uca-redclaw-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            tree.write(stream, encoding="utf-8", xml_declaration=True)
        os.replace(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def thunar_change(entry: dict, install: bool) -> None:
    """Add/remove only our unique IDs, preserving user-defined Thunar actions."""
    tree = _thunar_tree()
    root = tree.getroot()
    if root.tag != "actions":
        raise ValueError("Unexpected Thunar uca.xml root; refusing to edit.")
    ids = thunar_ids(entry)
    for child in list(root.findall("action")):
        if child.findtext("unique-id") in ids:
            root.remove(child)
    if install:
        for action in entry.get("portable_actions", []):
            node = ET.SubElement(root, "action")
            tag_id = f"redclaw-file-tools-{entry['id']}-{action['id']}"
            for tag, value in {
                "icon": "applications-utilities",
                "name": ACTION_LABELS[action["id"]]["en"],
                "unique-id": tag_id,
                "command": exec_line(entry["id"], action["id"]),
                "description": "Managed by RedClaw File Tools",
                "range": "*",
                "patterns": "*",
            }.items():
                ET.SubElement(node, tag).text = value
            for kind in ["directories", "audio-files", "image-files", "other-files", "text-files", "video-files"]:
                ET.SubElement(node, kind)
    _write_xml(tree)
