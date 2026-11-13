# RedClaw File Tools — universal architecture (initial implementation)

## Scope and status

The existing Nautilus Python plugins are preserved and remain the full-featured implementation. The new **Flutter Linux manager** and **Python 3 standard-library backend** provide an initial, incremental universal layer. **Cross-file-manager parity is not complete**; the user interface explicitly identifies partially supported or incompatible extensions.

Core issues: #58–#70. Rebranding: #71. Optional AI watermark add-ons: #72–#75.

## Directory layout

- `backend/catalog.json`: single declaration of 30 extension IDs, payloads, dependencies, capabilities and contextual recommendations.
- `backend/redclaw.py`: machine-readable JSON CLI.
- `backend/engine.py`: independent install state per `(file_manager, extension)`; conservative file ownership.
- `backend/adapters.py`: initial desktop integrations for Nautilus, Dolphin, Nemo, Caja, Thunar, PCManFM-Qt (experimental).
- `backend/portable.py`: independent portable operations: SHA-256, absolute-path clipboard, safe ZIP/TAR extraction and image-to-PNG.
- `backend/dependencies.py`: dependency planning, native apt/dnf/pacman/zypper packages and PolicyKit authorization.
- `manager/`: Flutter desktop UI, localized in pt-BR, en, es, fr, de.
- `scripts/build-appimage.sh`: builds Flutter Linux and a bundled AppImage; backend/runtime files are included.

## Separation by file manager

Installed state is keyed `<file-manager>/<extension>` under `${XDG_STATE_HOME:-~/.local/state}/redclaw-file-tools/installed.json`. The user can have Nautilus and Dolphin installed at the same time. A module may be installed in either, both or neither. Uninstalling one target **never** deletes files exclusively owned by the other target. Shared Nautilus helpers use file ownership references. Unknown local modifications block overwrite rather than silently destroying data.

For portable service menus, the manager installs a standalone host-runtime Python copy in `${XDG_DATA_HOME:-~/.local/share}/redclaw-file-tools/runtime/`. Therefore menus remain available **without keeping the AppImage running** or installed in a fixed location. Python 3 and other host dependencies still need to be available on the system; the AppImage is a controller, not a replacement for system GI/GTK libraries.

For Nautilus, the manager currently installs existing plugin payloads under `~/.local/share/nautilus-python/extensions/`. For Dolphin and Nemo, per-action menu files are generated. For Caja, scripts are generated. For Thunar, unique managed actions are added to `~/.config/Thunar/uca.xml` without removing unrelated user actions. PCManFM-Qt uses an experimental DES-EMA approach and requires testing on the target host.

## Compatibility policy

All legacy modules are fully supported **in Nautilus only**. Initial portable action subsets are available for:
- `file-tools`: SHA-256 reports, copy absolute path (requires a clipboard helper).
- `extract-here`: ZIP/TAR extraction only; no 7zip/RAR parity yet.
- `image-tools`: convert to PNG (Pillow) only.

All other modules remain incompatible with non-Nautilus managers until dedicated porting and tests are complete. A module may be compatible but redundant (e.g. built-in archive features in Dolphin). User recommendations are advisory; no extension is installed merely because it is recommended.

## Installed extensions and activation state

The Flutter manager now supports `install`, `uninstall`, `enable` and `disable` for each individual `(file manager, extension)` combination. Disabling **moves only owned entrypoint/menu files** out of the file manager's discovery path into private XDG state; it does not delete content, settings, shared Python helpers or host packages. Re-enabling restores the same file bytes and modes. The old Nautilus-only `extensions-manager.py` has been retired and removed from the installer, catalogue and Debian package manifest.

**Legacy Nautilus migration:** the manager detects both regular plugins and previously disabled plugins from `~/.local/share/nautilus-python/extensions/disabled/`. With explicit confirmation, it can adopt just the main plugin file, never untracked shared helpers. Installed package symlinks and modified files cannot be adopted automatically. Existing `extensions-manager.py` can be removed from the context menu with an on-disk backup. New versions do not silently remove old installs.

The Flutter language selector also writes the existing `~/.config/nautilus-extensions/language` preference, preserving localization compatibility with old Nautilus plugins. Non-Nautilus service menus use native localized names.

```bash
python3 backend/redclaw.py --json enable --fm dolphin --slug file-tools --yes
python3 backend/redclaw.py --json disable --fm nautilus --slug file-tools --yes
python3 backend/redclaw.py --json adopt --fm nautilus --slug file-tools --yes
python3 backend/redclaw.py --json retire-legacy-manager --yes
python3 backend/redclaw.py --json language --set pt-BR
```

**Limitations:** Imported legacy modules are not updated until their shared dependencies have been reviewed. The user should restart the affected file manager after enabling/disabling its Python providers. The GTK folder icon editor is still a Nautilus feature, but its interface now offers a resizable three-pane workspace: tools and colours | editable canvas | layers.

## CLI examples

```bash
python3 backend/redclaw.py --json inventory
python3 backend/redclaw.py --json plan --fm dolphin --slug file-tools
python3 backend/redclaw.py --json install --fm dolphin --slug file-tools --yes --install-deps
python3 backend/redclaw.py --json install --fm nautilus --slug file-tools --yes --install-deps
python3 backend/redclaw.py --json uninstall --fm dolphin --slug file-tools --yes
python3 backend/redclaw.py --json run file-tools sha256 /path/to/example.txt
```

The GUI shows a dependency plan and asks for confirmation. Installing missing packages uses the distro package manager via PolicyKit (pkexec) when privileges are required. No system dependencies are removed automatically during uninstall. Existing unmanaged extensions are reported rather than overwritten; **assisted migration is still pending**.

## Versioning, build and release

The build version is **`YY.DDD.HHMM`**, with padded day-of-year 001–366 and 24-hour time in **America/Sao_Paulo**, captured at compilation start. Example: `26.316.2043`. Distinct builds in the same minute intentionally share the same version; GitHub Releases are not overwritten if the version already exists.

Workflow: `.github/workflows/appimage-release.yml` builds on the main branch and via manual dispatch, runs unit tests and Flutter analysis/tests, constructs `RedClaw_File_Tools-<version>-x86_64.AppImage`, generates its SHA-256 checksum, and publishes a GitHub Release **in English**. The manager user interface offers pt-BR, English, Spanish, French and German.

## Safety and limitations

- Initial native extensions for non-Nautilus managers offer subsets, not menu/UI parity.
- Legacy Nautilus installations and packages may require an assisted migration; the backend refuses to overwrite unknown files.
- System dependencies are installed after explicit confirmation. They are **never** uninstalled automatically.
- Portable operations may create output files; original user files remain intact.
- External `remove-ai-watermarks` is **not bundled or installed by default**. Optional add-on integration is tracked under #72–#75.
- Platform integration needs real desktop-session testing. CI covers headless regression, not full graphical QA.
