"""Regression tests for the opt-in, multi-file-manager AI watermark add-on."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adapters
import ai_watermarks
import dependencies
import engine
import portable


class AIWatermarksTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        patcher = patch.dict(os.environ, {
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "state"),
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        state_patch = patch.object(engine, "STATE", self.root / "state/installations.json")
        runtime_patch = patch.object(engine, "RUNTIME", self.root / "data/redclaw-file-tools/runtime")
        state_patch.start()
        runtime_patch.start()
        self.addCleanup(state_patch.stop)
        self.addCleanup(runtime_patch.stop)

    def entry(self):
        catalog = engine.read_catalog()
        return engine.get_entry(catalog, "ai-watermarks")

    def test_catalog_marks_addon_as_opt_in(self):
        entry = self.entry()
        self.assertTrue(entry["optional_addon"])
        self.assertEqual(len(entry["portable_actions"]), 5)
        self.assertNotEqual(entry["compatibility"]["dolphin"]["recommendation"], "recommended")
        self.assertIn("uv", entry["dependencies"])

    def test_batch_only_immediate_images_without_previous_outputs(self):
        folder = self.root / "images"
        folder.mkdir()
        (folder / "portrait.jpg").write_bytes(b"original")
        (folder / "portrait_ai_cleaned.jpg").write_bytes(b"previous")
        (folder / "notes.txt").write_text("ignore", encoding="utf8")
        subdir = folder / "subfolder"
        subdir.mkdir()
        (subdir / "nested.jpg").write_bytes(b"ignore")
        images = ai_watermarks.image_files("batch", [str(folder)])
        self.assertEqual([item.name for item in images], ["portrait.jpg"])

    def test_non_batch_folders_are_rejected(self):
        with self.assertRaisesRegex(portable.ActionError, "Batch"):
            ai_watermarks.image_files("visible", [str(self.root)])

    def test_identify_writes_a_separate_report(self):
        image = self.root / "sample image.jpg"
        image.write_bytes(b"unchanged")
        process = subprocess.CompletedProcess(["mock"], 0, "AI watermark: none", "")
        with patch.object(ai_watermarks, "executable", return_value="/bin/raiw"), \
             patch.object(ai_watermarks, "_run_cli", return_value=process) as cli, \
             patch.object(ai_watermarks, "_notify"):
            outputs = portable.run("ai-watermarks", "identify", [str(image)])
        self.assertEqual(len(outputs), 1)
        self.assertIn("AI watermark: none", Path(outputs[0]).read_text(encoding="utf8"))
        self.assertEqual(image.read_bytes(), b"unchanged")
        cli.assert_called_once_with(["/bin/raiw", "identify", str(image)])

    def test_visible_never_overwrites_outputs_or_original(self):
        image = self.root / "picture.png"
        image.write_bytes(b"original")
        operations = []
        def fake_cli(args):
            operations.append(args)
            Path(args[args.index("-o") + 1]).write_bytes(b"cleaned")
            return subprocess.CompletedProcess(args, 0, "", "")
        with patch.object(ai_watermarks, "executable", return_value="/bin/raiw"), \
             patch.object(ai_watermarks, "_run_cli", side_effect=fake_cli), \
             patch.object(ai_watermarks, "_notify"):
            first = ai_watermarks.run("visible", [str(image)])
            second = ai_watermarks.run("visible", [str(image)])
        self.assertEqual(image.read_bytes(), b"original")
        self.assertNotEqual(first, second)
        self.assertEqual(len(operations), 2)

    def test_missing_engine_never_downloads_silently(self):
        image = self.root / "test.jpg"
        image.write_bytes(b"unchanged")
        with patch.object(ai_watermarks, "executable", return_value=None):
            with self.assertRaisesRegex(portable.ActionError, "missing"):
                ai_watermarks.run("visible", [str(image)])
        self.assertEqual(image.read_bytes(), b"unchanged")

    def test_dependency_plan_includes_third_party_install_notice(self):
        with patch.object(dependencies, "available",
                          side_effect=lambda key: key in ("python3", "uv")):
            p = dependencies.dependency_plan(self.entry(), "dolphin")
        self.assertEqual(p["packages"], [])
        self.assertEqual(p["missing"], ["remove-ai-watermarks"])
        self.assertTrue(p["network_download"])
        self.assertEqual(p["uv_python"], "3.12")
        self.assertIn("remove-ai-watermarks[all]", p["uv_tool"])

    def test_uninstall_nautilus_keeps_dolphin_and_cli(self):
        def fake_plan(fm, slug):
            return {
                "file_manager": fm, "slug": slug, "status": "not_installed",
                "dependencies": {"missing": [], "packages": [], "unresolved": []},
            }
        with patch.object(engine, "plan", side_effect=fake_plan):
            engine.install("nautilus", "ai-watermarks",
                           install_deps=False, confirmed=True)
            engine.install("dolphin", "ai-watermarks",
                           install_deps=False, confirmed=True)
        desktop = self.root / "data/kio/servicemenus/redclaw-file-tools-ai-watermarks-visible.desktop"
        nautilus = self.root / "data/nautilus/scripts/RedClaw File Tools/AI Watermarks/Remove visible AI watermark"
        helper = self.root / "data/redclaw-file-tools/runtime/ai_watermarks.py"
        self.assertTrue(desktop.exists())
        self.assertTrue(nautilus.exists())
        self.assertTrue(helper.exists())
        engine.uninstall("nautilus", "ai-watermarks", confirmed=True)
        self.assertFalse(nautilus.exists())
        self.assertTrue(desktop.exists())
        self.assertTrue(helper.exists())
        self.assertIn("dolphin/ai-watermarks", engine._load_state()["installed"])

    def test_localized_desktop_actions(self):
        desktop_map = adapters.render_files("dolphin", self.entry(), self.root)
        self.assertEqual(len(desktop_map), 5)
        text = next(content.decode("utf-8")
                    for path, (content, _) in desktop_map.items()
                    if path.name.endswith("identify.desktop"))
        self.assertIn("Name[pt]=", text)
        self.assertIn("Name[fr]=", text)
        self.assertIn("MimeType=image/*;", text)


if __name__ == "__main__":
    unittest.main()
