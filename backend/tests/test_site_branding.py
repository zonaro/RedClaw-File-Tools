"""Protect RedClaw brand assets and the Brazilian Portuguese landing translation."""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS = "{http://www.w3.org/2000/svg}"


class SiteBrandingTests(unittest.TestCase):
    def test_portuguese_section_never_contains_german_copy(self):
        translations = (ROOT / "docs/i18n.js").read_text(encoding="utf-8")
        start = translations.index('"pt-BR": {')
        end = translations.index("\nes: {", start)
        block = translations[start:end]
        for word in (
            "Erweiterungen", "Dateimanager", "Mehrsprachiger",
            "Werkzeugkasten", "Werkzeuge", "Wählen Sie",
            "Laden Sie", "herunterladen", "Nautilus-Erweiterungen",
        ):
            with self.subTest(word=word):
                self.assertNotIn(word, block)
        for phrase in ("Baixar o AppImage", "30 ferramentas", "gerenciadores"):
            self.assertIn(phrase, block)

    def test_landing_uses_company_accent_and_brand_logo(self):
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn("--accent:#e10600;", html)
        self.assertIn('src="redclaw_logo.svg"', html)
        self.assertIn('<link rel="icon" type="image/svg+xml" href="redclaw_logo.svg">', html)
        self.assertNotIn("--zorin", html)
        self.assertNotIn("rgba(139,92,246", html)

    def test_official_logo_is_exactly_preserved_and_embedded(self):
        logo_path = ROOT / "assets/redclaw_logo.svg"
        site_path = ROOT / "docs/redclaw_logo.svg"
        icon_path = ROOT / "assets/redclaw-file-tools.svg"
        self.assertEqual(logo_path.read_bytes(), site_path.read_bytes())
        original = ET.parse(logo_path).getroot()
        site = ET.parse(site_path).getroot()
        icon = ET.parse(icon_path).getroot()
        self.assertEqual(original.attrib["viewBox"], "0 0 1254 1254")
        official_group = original.find(f"{NS}g")
        self.assertIsNotNone(official_group)
        embedded_group = icon.find(f".//{NS}g[@fill='#e10600']")
        self.assertIsNotNone(embedded_group)
        official_paths = [p.attrib["d"] for p in official_group.findall(f"{NS}path")]
        embedded_paths = [p.attrib["d"] for p in embedded_group.findall(f"{NS}path")]
        self.assertEqual(len(official_paths), 57)
        self.assertEqual(official_paths, embedded_paths)
        self.assertEqual(site.find(f"{NS}g").attrib["fill"], "#e10600")


if __name__ == "__main__":
    unittest.main()
