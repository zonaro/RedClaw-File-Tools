# Third Party Notices

This project incorporates code and concepts from third-party sources, in accordance with their licenses.

## Transmutia

- Source: https://github.com/NormalChelik/Transmutia
- License: MIT License
- Copyright (c) Transmutia Contributors

Portions of the following files were adapted from Transmutia:

- `media_core/models.py` - MediaCategory, ConvertStatus, MediaItem (concepts and structure)
- `media_core/detection.py` - detect_category logic
- `media_core/formats.py` - Format constants and extension mappings
- `media_core/ffmpeg_utils.py` - FFmpeg/ffprobe discovery utilities
- `media_core/ffmpeg_format_args.py` - FFmpeg preset argument definitions
- `media_core/backends/ffmpeg.py` - FFmpeg conversion logic, progress parsing

The original MIT license terms apply to those derived portions.

---

## Original Nautilus-Extensions

The remainder of this codebase is licensed under GPL-3.0 as specified in LICENSE.

---

## Lucide Icons (offline symbol catalogue)

The folder icon editor ships a vendored offline collection of monochrome
symbols from Lucide Icons, used as recolourable symbol layers. The artwork is
vendored by `scripts/generate_folder_icons.py` from the official
`lucide-static` npm tarball and lives under `assets/folder-icons/` (catalogue
metadata plus the ISC licence text). No network access or runtime dependency is
used.

- Project: https://github.com/lucide-icons/lucide
- Package: lucide-static 1.69.0 (npm), pinned by sha512/sha256/sha1
- Upstream commit: 91a1359b5ea235f620ba3a9682015ab8d6ada3af
- License: ISC License (see `assets/folder-icons/LICENSE`)
- Symbol count: 2023 canonical icons (+294 alias names sharing artwork)
- Files: `assets/folder-icons/catalog.json`, `manifest.json`, `LICENSE`
