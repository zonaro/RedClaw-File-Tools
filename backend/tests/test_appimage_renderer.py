"""AppImage rendering hardening tests.

Hardware-specific Wayland/NVIDIA failures cannot be reproduced in headless CI,
but the native Skia opt-out and AppDir library boundaries are testable.
"""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts/patch_flutter_linux_runner.py"
STRIP = ROOT / "scripts/strip_host_graphics_libs.sh"
LAUNCHER = ROOT / "scripts/AppRun"

spec = importlib.util.spec_from_file_location("patch_flutter_linux_runner", PATCH)
assert spec and spec.loader
patch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch_module)


class RendererPatchTests(unittest.TestCase):
    @staticmethod
    def template() -> str:
        return (
            '#include "my_application.h"\n'
            'static void my_application_activate(GApplication* application) {\n'
            '  gtk_window_set_title(window, "redclaw_file_tools");\n'
            '  g_autoptr(FlDartProject) project = fl_dart_project_new();\n'
            '  fl_dart_project_set_dart_entrypoint_arguments(project, nullptr);\n'
            '}\n'
        )

    def test_skia_default_impeller_opt_in_and_app_title(self):
        result = patch_module.patched_runner(self.template())
        self.assertEqual(result.count("fl_dart_project_set_enable_impeller"), 1)
        self.assertIn('g_getenv("REDCLAW_ENABLE_IMPELLER")', result)
        self.assertIn('fl_dart_project_set_enable_impeller(project, FALSE);', result)
        self.assertIn('gtk_window_set_title(window, "RedClaw File Tools");', result)
        self.assertNotIn('gtk_window_set_title(window, "redclaw_file_tools");', result)

    def test_patch_is_idempotent(self):
        once = patch_module.patched_runner(self.template())
        self.assertEqual(patch_module.patched_runner(once), once)

    def test_template_change_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "template changed"):
            patch_module.patched_runner("int main() { return 0; }")


class AppImageLibraryTests(unittest.TestCase):
    def test_excludes_host_graphics_not_flutter_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdir = Path(tmp)
            libs = appdir / "usr/lib"
            flutter_libs = appdir / "usr/bin/lib"
            libs.mkdir(parents=True)
            flutter_libs.mkdir(parents=True)
            prohibited = [
                "libEGL.so.1", "libGL.so.1", "libGLX.so.0",
                "libGLdispatch.so.0", "libOpenGL.so.0",
                "libgbm.so.1", "libdrm.so.2",
                "libwayland-client.so.0", "libwayland-egl.so.1",
                "libvulkan.so.1",
            ]
            for name in prohibited:
                (libs / name).write_bytes(b"host-specific")
            # Real files and symlinks both need removing.
            (libs / "libGLX.so").symlink_to("libGLX.so.0")
            (flutter_libs / "libEGL.so").write_bytes(b"bad")
            (flutter_libs / "libflutter_linux_gtk.so").write_bytes(b"keep")
            (libs / "libgtk-3.so.0").write_bytes(b"keep")

            subprocess.run(["bash", str(STRIP), str(appdir)], check=True,
                           capture_output=True, text=True)
            for name in prohibited:
                self.assertFalse((libs / name).exists(), name)
            self.assertFalse((libs / "libGLX.so").is_symlink())
            self.assertFalse((flutter_libs / "libEGL.so").exists())
            self.assertTrue((flutter_libs / "libflutter_linux_gtk.so").is_file())
            self.assertTrue((libs / "libgtk-3.so.0").is_file())

            # Idempotent; rerunning must not remove allowed runtime libraries.
            subprocess.run(["bash", str(STRIP), str(appdir)], check=True)
            self.assertTrue((flutter_libs / "libflutter_linux_gtk.so").is_file())

    def test_app_run_exposes_diagnostics_without_starting_flutter(self):
        result = subprocess.run(
            ["bash", str(LAUNCHER), "--redclaw-diagnostics"],
            check=True, capture_output=True, text=True,
        )
        self.assertIn("Skia", result.stdout)
        self.assertIn("Bundled host graphics libraries", result.stdout)

    def test_all_build_scripts_parse(self):
        for source in (
            LAUNCHER,
            STRIP,
            ROOT / "scripts/build-appimage.sh",
            ROOT / "scripts/smoke-appimage.sh",
        ):
            with self.subTest(source=source.name):
                subprocess.run(["bash", "-n", str(source)], check=True)


if __name__ == "__main__":
    unittest.main()
