# Provisional compatibility matrix — RedClaw File Tools

> **Initial implementation only.** Based on the existing Nautilus installer catalog and the first portable action adapters, not a complete manual desktop QA campaign. See issue #58. Full = original Nautilus plugin; Partial = only a selected portable subset; — = not ported. A technically compatible extension can still be redundant on a particular desktop.

| Extension | Nautilus | Dolphin | Nemo | Caja | Thunar | PCManFM-Qt |
|---|---|---|---|---|---|---|
| `archive-browser` | Full | — | — | — | — | — |
| `audio-tools` | Full | — | — | — | — | — |
| `clone-repository` | Full | — | — | — | — | — |
| `column-browser` | Full | — | — | — | — | — |
| `comic-tools` | Full | — | — | — | — | — |
| `compress-pdf` | Full | — | — | — | — | — |
| `cut-dim` | Full | — | — | — | — | — |
| `deb-installer` | Full | — | — | — | — | — |
| `dev-tools-minify` | Full | — | — | — | — | — |
| `dual-panel` | Full | — | — | — | — | — |
| `duration-column` | Full | — | — | — | — | — |
| `edit-with` | Full | — | — | — | — | — |
| `extensions-manager` | Full (redundant) | — | — | — | — | — |
| `extract-here` | Full | Partial (redundant) | Partial | Partial | Partial | Partial |
| `file-tools` | Full | Partial | Partial | Partial | Partial | Partial |
| `folder-color-revival` | Full | — | — | — | — | — |
| `hidden-dim-all` | Full | — | — | — | — | — |
| `hidden-dim-icon` | Full | — | — | — | — | — |
| `move-and-symlink` | Full | — | — | — | — | — |
| `image-tools` | Full | Partial | Partial | Partial | Partial | Partial |
| `media-converter` | Full | — | — | — | — | — |
| `merge-pdf` | Full | — | — | — | — | — |
| `paste-into-file` | Full | — | — | — | — | — |
| `preview-panel` | Full | — | — | — | — | — |
| `progress-mirror` | Full | — | — | — | — | — |
| `search-content` | Full | — | — | — | — | — |
| `terminal-tools` | Full | — | — | — | — | — |
| `video-to-audio` | Full | — | — | — | — | — |
| `video-tools` | Full | — | — | — | — | — |
| `watermark-pdf` | Full | — | — | — | — | — |

## Supported portable action subsets

- `file-tools`: SHA-256 report creation and copy absolute path (requires clipboard helper).
- `extract-here`: built-in Python ZIP/TAR extraction (not the legacy multi-format archive browser).
- `image-tools`: image-to-PNG conversion only (Pillow).

All other modules require porting or native file-manager integration. Nautilus plugin abilities such as `ColumnProvider`, `InfoProvider`, windows, overlays, shortcuts and dynamic visual decorations cannot be considered portable simply because a Service Menu can run a CLI command.

## Selection and recommendation

The manager detects every compatible file-manager executable it can find, not merely the current default. A user may install the same extension in Nautilus and Dolphin independently. For each pair, the catalog records `support`, `recommendation` and `reason`. The UI distinguishes missing/installed/modified/external states per target.

The initial rules avoid recommending features that are not available or likely redundant (for example, Dolphin's archive capabilities). Further extension-level audits and native capability probes remain required before declaring more adapters fully supported.
