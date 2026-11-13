"""Optional Remove AI Watermarks actions, independent from desktop-specific scripts.

Based on the action semantics of zonaro/remove-ai-watermarks-contextmenu.
The third-party engine is NOT bundled or installed by default.
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from portable import ActionError, _unique_output, _notify, _selected

MODES = frozenset({"identify", "visible", "metadata", "all", "batch"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"})


def executable() -> str | None:
    return shutil.which("remove-ai-watermarks") or (
        str(Path.home() / ".local/bin/remove-ai-watermarks")
        if (Path.home() / ".local/bin/remove-ai-watermarks").is_file() else None
    )


def image_files(mode: str, targets: list[str]) -> list[Path]:
    """Use immediate children only for batch folders; never recurse."""
    selected = _selected(targets)
    found: list[Path] = []
    for selected_path in selected:
        if selected_path.is_dir():
            if mode != "batch":
                raise ActionError("Select individual images, or use Batch for a directory.")
            files = sorted(
                (p for p in selected_path.iterdir() if p.is_file()),
                key=lambda path: path.name.lower(),
            )
        else:
            files = [selected_path]
        for path in files:
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                if not selected_path.is_dir():
                    raise ActionError(f"Not a supported image: {path.name}")
                continue
            if "_ai_cleaned" in path.stem.lower() and mode == "batch":
                continue
            if path not in found:
                found.append(path)
    if not found:
        raise ActionError("No supported images selected.")
    return found


def _run_cli(command: list[str], timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, errors="replace",
            check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ActionError("Remove AI Watermarks timed out.") from exc


def run(mode: str, paths: list[str]) -> list[str]:
    if mode not in MODES:
        raise ActionError(f"Unsupported Remove AI Watermarks mode: {mode}")
    binary = executable()
    if not binary:
        raise ActionError(
            "The optional remove-ai-watermarks CLI is missing. "
            "Install this add-on's dependencies in RedClaw File Tools first."
        )
    files = image_files(mode, paths)
    produced: list[str] = []
    errors: list[str] = []
    report_lines: list[str] = []
    if mode == "identify":
        report_lines = [
            "======= Remove AI Watermarks — AI Analysis =======",
            f"Date: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
        ]
    for path in files:
        if mode == "identify":
            command = [binary, "identify", str(path)]
        else:
            operation = "visible" if mode == "batch" else mode
            destination = _unique_output(
                path.with_name(f"{path.stem}_ai_cleaned{path.suffix}")
            )
            command = [binary, operation, str(path), "-o", str(destination)]
        completed = _run_cli(command)
        if completed.returncode == 2 and mode != "identify":
            # The upstream CLI uses code 2 for 'no watermark detected'.
            continue
        if completed.returncode != 0:
            errors.append(f"{path.name}: exit code {completed.returncode}")
            continue
        if mode == "identify":
            report_lines.extend([
                f"File: {path}", completed.stdout.strip(), "",
            ])
        elif destination.exists():
            produced.append(str(destination))
        else:
            errors.append(f"{path.name}: CLI reported success but did not create output")
    if mode == "identify" and len(report_lines) > 3:
        report = _unique_output(
            files[0].with_name(files[0].stem + "_ai_analysis.txt")
        )
        report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        produced.append(str(report))
    if errors:
        raise ActionError(
            "Some images could not be processed (others may have succeeded): "
            + "; ".join(errors[:10])
        )
    _notify("RedClaw File Tools", f"Remove AI Watermarks: {len(produced)} output(s).")
    return produced
