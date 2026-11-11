"""Checks the interface catalogs (static/lang) and the language selection logic."""

import json
import re
import shutil
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from endfield_checkin.config import UI_LANGUAGES  # noqa: E402
from endfield_checkin.notify import discord_text  # noqa: E402

STATIC = ROOT / "app" / "endfield_checkin" / "static"
LANG = STATIC / "lang"
LANGUAGES = json.loads((LANG / "languages.json").read_text(encoding="utf-8"))
MASTER = json.loads((LANG / "en_US.json").read_text(encoding="utf-8"))
PLACEHOLDER = re.compile(r"\{[a-z]+\}")
UNRAID_LOCALES = {"ar_AR", "bn_BN", "ca_CA", "cs_CZ", "da_DA", "de_DE", "el_GR", "en_US", "es_ES", "fr_FR",
                  "hr_HR", "hu_HU", "it_IT", "ja_JA", "ko_KO", "lv_LV", "nl_NL", "no_NO", "pl_PL", "pt_BR",
                  "pt_PT", "ro_RO", "ru_RU", "sv_SE", "uk_UA", "zh_CN", "zh_TW"}


def leaves(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from leaves(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from leaves(value, f"{path}[{index}]")
    else:
        yield path, node


class CatalogTest(unittest.TestCase):
    def test_languages_match_unraid(self):
        self.assertEqual(set(LANGUAGES), UNRAID_LOCALES)
        self.assertEqual(set(UI_LANGUAGES), UNRAID_LOCALES)
        for code, info in LANGUAGES.items():
            self.assertTrue(info["name"], code)
            self.assertIn(info["dir"], ("ltr", "rtl"))
            self.assertRegex(info["bcp47"], r"^[a-z]{2}(-[A-Z]{2})?$")
        self.assertEqual(LANGUAGES["ar_AR"]["dir"], "rtl")
        files = {p.stem for p in LANG.glob("*.json")} - {"languages"}
        self.assertEqual(files, UNRAID_LOCALES, "one catalog per Unraid locale")

    def test_every_catalog_is_complete_and_safe(self):
        master = dict(leaves(MASTER))
        for code in sorted(UNRAID_LOCALES):
            with self.subTest(code=code):
                catalog = json.loads((LANG / f"{code}.json").read_text(encoding="utf-8"))
                strings = dict(leaves(catalog))
                self.assertEqual(set(strings), set(master), "same keys and list sizes as en_US")
                for path, text in strings.items():
                    self.assertIsInstance(text, str, path)
                    self.assertTrue(text.strip(), path)
                    self.assertNotRegex(text, r"[<>]", f"{path}: no HTML")
                    self.assertEqual(sorted(PLACEHOLDER.findall(text)), sorted(PLACEHOLDER.findall(master[path])),
                                     f"{path}: placeholders")
                if code != "en_US":
                    translated = sum(1 for path, text in strings.items() if text != master[path])
                    self.assertGreater(translated / len(master), 0.6, "catalog looks untranslated")

    def test_template_offers_every_language(self):
        root = ET.parse(ROOT / "templates" / "endfield-checkin.xml").getroot()
        config = next(c for c in root.findall("Config") if c.get("Target") == "UI_LANGUAGE")
        self.assertEqual(config.get("Default").split("|"), ["auto"] + list(LANGUAGES))
        self.assertEqual(config.text, "auto")

    def test_discord_text_falls_back_to_english(self):
        self.assertEqual(discord_text("fr_FR")["claimed"], "Récompense quotidienne récupérée")
        self.assertEqual(discord_text("xx_XX"), MASTER["discord"])
        self.assertEqual(discord_text("../en_US"), MASTER["discord"])


NODE_TEST = r"""
const i18n = require(process.argv[1]);
const supported = Object.keys(require(process.argv[2]));
const cases = [
  [["fr-FR"], "fr_FR"], [["fr-CA", "en"], "fr_FR"], [["de-AT"], "de_DE"], [["ja-JP"], "ja_JA"],
  [["ko-KR"], "ko_KO"], [["da-DK"], "da_DA"], [["nb-NO"], "no_NO"], [["zh-CN"], "zh_CN"],
  [["zh-Hant-HK"], "zh_TW"], [["zh-TW"], "zh_TW"], [["zh"], "zh_CN"], [["pt-BR"], "pt_BR"],
  [["pt"], "pt_PT"], [["ar-EG"], "ar_AR"], [["es-MX"], "es_ES"], [["en-GB"], "en_US"],
  [["xx", "it-CH"], "it_IT"], [["xx"], "en_US"], [[], "en_US"], [["uk"], "uk_UA"], [["sv-FI"], "sv_SE"],
];
const failures = cases.filter(([prefs, want]) => i18n.resolveLanguage(prefs, supported) !== want)
  .map(([prefs, want]) => `${prefs} -> ${i18n.resolveLanguage(prefs, supported)} (want ${want})`);
const master = { a: "A", list: ["1", "2"], deep: { b: "B {n}", c: "C" } };
const merged = i18n.mergeCatalog(master, { a: "x", list: ["only one"], deep: { b: "", c: "y" }, extra: "z" });
if (JSON.stringify(merged) !== JSON.stringify({ a: "x", list: ["1", "2"], deep: { b: "B {n}", c: "y" } })) {
  failures.push("mergeCatalog: " + JSON.stringify(merged));
}
const iso = i18n.isolateLatin({ a: "احفظ /config {n} 3_UID_SERVER", b: ["{done} / {total}"] });
if (iso.a !== "احفظ \u2068/config\u2069 {n} \u20683_UID_SERVER\u2069" || iso.b[0] !== "{done} / {total}") {
  failures.push("isolateLatin: " + JSON.stringify(iso));
}
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
"""


@unittest.skipUnless(shutil.which("node"), "node not installed")
class LanguageSelectionTest(unittest.TestCase):
    def test_browser_language_resolution_and_fallback(self):
        result = subprocess.run(["node", "-e", NODE_TEST, str(STATIC / "i18n.js"), str(LANG / "languages.json")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_scripts_parse(self):
        for name in ("i18n.js", "app.js"):
            result = subprocess.run(["node", "--check", str(STATIC / name)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
