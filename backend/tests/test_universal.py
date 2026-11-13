"""Headless integration tests for the initial universal backend."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adapters
import engine
import portable


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env_patch = patch.dict(os.environ, {
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.state_patch = patch.object(engine, "STATE", self.root / "state/installations.json")
        self.runtime_patch = patch.object(engine, "RUNTIME", self.root / "data/redclaw-file-tools/runtime")
        self.state_patch.start()
        self.runtime_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.addCleanup(self.runtime_patch.stop)

    def plan_result(self, fm, slug):
        return {
            "file_manager": fm,
            "slug": slug,
            "status": "not_installed",
            "dependencies": {"missing": [], "packages": [], "unresolved": []},
        }

    def test_catalog_all_extensions(self):
        catalog = engine.read_catalog()
        self.assertEqual(len(catalog["extensions"]), 30)
        self.assertNotIn("extensions-manager", [e["id"] for e in catalog["extensions"]])
        self.assertIn("dolphin", [fm["id"] for fm in catalog["file_managers"]])
        for entry in catalog["extensions"]:
            self.assertEqual(len(entry["compatibility"]), 6)

    def test_independent_dolphin_and_nemo_installs(self):
        with patch.object(engine, "plan", side_effect=self.plan_result):
            one = engine.install("dolphin", "file-tools", install_deps=False, confirmed=True)
            two = engine.install("nemo", "file-tools", install_deps=False, confirmed=True)
        self.assertTrue(one["ok"])
        self.assertTrue(two["ok"])
        data = engine._load_state()["installed"]
        self.assertIn("dolphin/file-tools", data)
        self.assertIn("nemo/file-tools", data)
        file_a = self.root / "data/kio/servicemenus/redclaw-file-tools-file-tools-sha256.desktop"
        file_b = self.root / "data/nemo/actions/redclaw-file-tools-file-tools-sha256.nemo_action"
        self.assertTrue(file_a.exists())
        self.assertTrue(file_b.exists())
        engine.uninstall("dolphin", "file-tools", confirmed=True)
        self.assertFalse(file_a.exists())
        self.assertTrue(file_b.exists())
        self.assertIn("nemo/file-tools", engine._load_state()["installed"])

    def test_dolphin_toggle_does_not_affect_nemo(self):
        with patch.object(engine, "plan", side_effect=self.plan_result):
            engine.install("dolphin", "file-tools", install_deps=False, confirmed=True)
            engine.install("nemo", "file-tools", install_deps=False, confirmed=True)
        entry = engine.get_entry(engine.read_catalog(), "file-tools")
        self.assertEqual(engine.installed_status(entry, "dolphin", engine._load_state()), "installed")
        result = engine.set_enabled("dolphin", "file-tools", enabled=False, confirmed=True)
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(engine.installed_status(entry, "dolphin", engine._load_state()), "disabled")
        self.assertEqual(engine.installed_status(entry, "nemo", engine._load_state()), "installed")
        desktop = self.root / "data/kio/servicemenus/redclaw-file-tools-file-tools-sha256.desktop"
        self.assertFalse(desktop.exists())
        self.assertTrue((self.root / "data/nemo/actions/redclaw-file-tools-file-tools-sha256.nemo_action").exists())
        result = engine.set_enabled("dolphin", "file-tools", enabled=True, confirmed=True)
        self.assertEqual(result["status"], "installed")
        self.assertTrue(desktop.exists())
        self.assertEqual(engine.installed_status(entry, "dolphin", engine._load_state()), "installed")

    def test_uninstall_disabled_keeps_other_managers(self):
        with patch.object(engine, "plan", side_effect=self.plan_result):
            engine.install("dolphin", "file-tools", install_deps=False, confirmed=True)
            engine.install("nemo", "file-tools", install_deps=False, confirmed=True)
        engine.set_enabled("dolphin", "file-tools", enabled=False, confirmed=True)
        engine.uninstall("dolphin", "file-tools", confirmed=True)
        state = engine._load_state()
        self.assertNotIn("dolphin/file-tools", state["installed"])
        self.assertIn("nemo/file-tools", state["installed"])
        self.assertFalse(list((self.root / "state").rglob("disabled/dolphin/file-tools/*")))

    def test_nautilus_disable_only_entrypoint_and_preserve_helpers(self):
        with patch.object(engine, "plan", side_effect=self.plan_result):
            engine.install("nautilus", "file-tools", install_deps=False, confirmed=True)
        ext_dir = self.root / "data/nautilus-python/extensions"
        plugin = ext_dir / "file-tools.py"
        helper = ext_dir / "nautilus_i18n.py"
        self.assertTrue(plugin.exists())
        self.assertTrue(helper.exists())
        engine.set_enabled("nautilus", "file-tools", enabled=False, confirmed=True)
        self.assertFalse(plugin.exists())
        self.assertTrue(helper.exists())
        engine.set_enabled("nautilus", "file-tools", enabled=True, confirmed=True)
        self.assertTrue(plugin.exists())

    def test_thunar_enable_disable_keeps_user_custom_actions(self):
        entry = engine.get_entry(engine.read_catalog(), "file-tools")
        thunar = adapters.thunar_file()
        thunar.parent.mkdir(parents=True, exist_ok=True)
        thunar.write_text(
            '<actions><action><unique-id>keep-me</unique-id><name>Personal</name>'
            '</action></actions>', encoding="utf-8")
        with patch.object(engine, "plan", side_effect=self.plan_result):
            engine.install("thunar", "file-tools", install_deps=False, confirmed=True)
        self.assertTrue(adapters.thunar_has(entry))
        engine.set_enabled("thunar", "file-tools", enabled=False, confirmed=True)
        self.assertFalse(adapters.thunar_has(entry))
        state = engine._load_state()
        self.assertEqual(engine.installed_status(entry, "thunar", state), "disabled")
        engine.set_enabled("thunar", "file-tools", enabled=True, confirmed=True)
        self.assertTrue(adapters.thunar_has(entry))
        ids = [el.findtext("unique-id") for el in ET.parse(thunar).getroot().findall("action")]
        self.assertIn("keep-me", ids)

    def test_reject_toggle_when_unmanaged_or_modified(self):
        with self.assertRaises(ValueError):
            engine.set_enabled("dolphin", "file-tools", enabled=False, confirmed=True)
        with patch.object(engine, "plan", side_effect=self.plan_result):
            engine.install("dolphin", "file-tools", install_deps=False, confirmed=True)
        target = self.root / "data/kio/servicemenus/redclaw-file-tools-file-tools-sha256.desktop"
        target.write_text("user edited", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "modified"):
            engine.set_enabled("dolphin", "file-tools", enabled=False, confirmed=True)
        self.assertEqual(target.read_text(), "user edited")

    def test_thunar_preserves_user_actions(self):
        thunar = adapters.thunar_file()
        thunar.parent.mkdir(parents=True, exist_ok=True)
        thunar.write_text(
            '<?xml version="1.0"?><actions><action><unique-id>my-own-action</unique-id>'
            '<name>My action</name></action></actions>', encoding="utf-8")
        entry = engine.get_entry(engine.read_catalog(), "file-tools")
        adapters.thunar_change(entry, True)
        self.assertTrue(adapters.thunar_has(entry))
        adapters.thunar_change(entry, False)
        root = ET.parse(thunar).getroot()
        ids = [element.findtext("unique-id") for element in root.findall("action")]
        self.assertEqual(ids, ["my-own-action"])

    def test_never_adopt_unmanaged_dolphin_file(self):
        path = self.root / "data/kio/servicemenus/redclaw-file-tools-file-tools-sha256.desktop"
        path.parent.mkdir(parents=True)
        path.write_text("User-owned customization", encoding="utf-8")
        with patch.object(engine, "plan", side_effect=self.plan_result):
            with self.assertRaisesRegex(RuntimeError, "Unmanaged"):
                engine.install("dolphin", "file-tools", install_deps=False, confirmed=True)
        self.assertEqual(path.read_text(), "User-owned customization")

    def test_unsafe_zip_member_is_rejected(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("../outside.txt", "no")
        with self.assertRaises(portable.ActionError):
            portable.extract_archives([str(archive)])
        self.assertFalse((self.root / "outside.txt").exists())

    def test_declaration_of_multiple_file_managers(self):
        with patch.object(engine.shutil, "which", side_effect=lambda key:
                          f"/usr/bin/{key}" if key in ("nautilus", "dolphin") else None):
            found = engine.detect_file_managers(engine.read_catalog())
        self.assertEqual([item["id"] for item in found], ["nautilus", "dolphin"])


if __name__ == "__main__":
    unittest.main()
