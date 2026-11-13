# Optional AI Watermarks add-on

The **Remove AI Watermarks** add-on is based on the user-facing actions from [zonaro/remove-ai-watermarks-contextmenu](https://github.com/zonaro/remove-ai-watermarks-contextmenu). It is an optional part of RedClaw File Tools, **not** part of the 30 base extensions.

## Features

- **Identify** possible AI marks and save an analysis report alongside the selected image.
- **Visible** process a visible AI watermark.
- **Metadata** process embedded AI metadata.
- **All** apply both processing modes.
- **Batch** process multiple selected images or *immediate* images in one directory; output files ending in `_ai_cleaned` are skipped.

The original files are never deliberately overwritten; generated files use `_ai_cleaned` or `_ai_analysis.txt` names, with numeric suffixes if those already exist.

Supported input filename extensions: JPG, JPEG, PNG, WEBP, BMP, TIFF, TIF.

## File-manager independence

The manager installs menu entries independently for Nautilus, Dolphin, Nemo, Caja, Thunar and experimental PCManFM-Qt. You may enable the same add-on in Nautilus and Dolphin separately, and uninstall it from one without removing it from the other.

Menu adapters:

| File manager | Integration |
| --- | --- |
| Nautilus | User-local scripts under `~/.local/share/nautilus/scripts/RedClaw File Tools/AI Watermarks/` |
| Dolphin | KDE ServiceMenu `.desktop` entries |
| Nemo | Nemo `.nemo_action` entries |
| Caja | User-local Caja scripts |
| Thunar | Custom actions added by unique ID to `uca.xml`, preserving unrelated entries |
| PCManFM-Qt | Experimental DES-EMA entries; desktop QA still needed |

Menu labels are localized to pt-BR, en, es, fr and de. Exact behaviour of native menu filters must be verified in desktop sessions.

## Dependencies and safety

Processing is performed by the **third-party** `remove-ai-watermarks` Python command-line application. It is not bundled in the AppImage or installed merely because the manager was opened.

The dependency plan inspects `python3`, `uv` and the existing CLI. If the CLI is missing, the Flutter app explains that installing it may fetch Python 3.12, Python dependencies and AI models; a **separate approval checkbox** is required. The backend invokes `uv tool install --python 3.12 'remove-ai-watermarks[all]'` without shell script piping, uses the distribution's native package manager for missing `uv` where available, and does not use `--force` to overwrite existing tools.

Network downloads may be large and processing may require substantial CPU/GPU and disk space. Check the upstream project's hardware requirements and license before opting in. No API calls are made by the base manager solely to identify an installed file manager.

Uninstalling the menu integration **does not automatically uninstall** `uv`, Python runtimes, packages, downloaded models or the external CLI; they may be used by other managers or user workflows. Remove them manually only after checking ownership.

## CLI examples

```bash
python3 backend/redclaw.py --json plan --fm dolphin --slug ai-watermarks

# After reviewing the plan and approving the third-party downloads:
python3 backend/redclaw.py --json install --fm dolphin --slug ai-watermarks --install-deps --yes
python3 backend/redclaw.py --json install --fm nautilus --slug ai-watermarks --yes

# Only the Dolphin menu integration is removed; Nautilus and shared CLI remain.
python3 backend/redclaw.py --json uninstall --fm dolphin --slug ai-watermarks --yes
```

The `--yes` CLI option is an **explicit opt-in intended for automation**; unlike the Flutter UI, the CLI cannot show a graphical confirmation dialog.

## Outstanding work

- Cross-distribution end-to-end QA for optional tool installation and large model downloads.
- Verify current upstream CLI arguments and exit-code semantics on real images.
- Assisted migration and conflict detection for users of the standalone context-menu integration.
- Cancellation, progress streaming and friendly error messages for long model operations.
- Validate actual native menu behaviour and localization on six file managers.

Tracked in [#72](https://github.com/zonaro/RedClaw-File-Tools/issues/72)–[#75](https://github.com/zonaro/RedClaw-File-Tools/issues/75).
