"""Checks the Community Applications requirements that can be verified offline."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from endfield_checkin import __version__  # noqa: E402

RAW = "https://raw.githubusercontent.com/MrPatates/endfield-checkin/main/"
TEMPLATE = ROOT / "templates" / "endfield-checkin.xml"


class TemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(TEMPLATE).getroot()

    def text(self, tag):
        node = self.root.find(tag)
        return (node.text or "").strip() if node is not None else ""

    def test_minimum_and_recommended_fields(self):
        self.assertEqual(self.root.tag, "Container")
        self.assertEqual(self.root.get("version"), "2")
        for tag in ("Name", "Repository", "Category", "Icon", "Overview", "Project", "Support", "TemplateURL", "WebUI"):
            self.assertTrue(self.text(tag), f"<{tag}> is empty")
        self.assertRegex(self.text("Repository"), r"^ghcr\.io/[a-z0-9-]+/[a-z0-9-]+:latest$")
        self.assertGreater(len(self.text("Overview")), 200, "CA requires a reasonable description")
        self.assertEqual(self.text("Privileged"), "false")
        self.assertEqual(self.text("ExtraParams"), "")

    def test_urls_point_to_files_of_this_repository(self):
        self.assertEqual(self.text("TemplateURL"), RAW + "templates/endfield-checkin.xml")
        for tag in ("Icon", "Screenshot"):
            url = self.text(tag)
            self.assertTrue(url.startswith(RAW), url)
            self.assertTrue((ROOT / url[len(RAW):]).is_file(), f"{url} does not exist in the repository")

    def test_config_matches_application(self):
        targets = {c.get("Target") for c in self.root.findall("Config")}
        self.assertTrue({"8080", "/config"} <= targets)
        config_py = (ROOT / "app" / "endfield_checkin" / "config.py").read_text()
        env_vars = set(re.findall(r'"([A-Z_]{3,})"', config_py)) - {"DEBUG", "INFO", "WARNING", "ERROR"}
        documented_elsewhere = {"DATA_DIR", "WEBUI_PORT", "STARTUP_DELAY", "SKPORT_AS_BASE", "SKPORT_ZONAI_BASE"}
        self.assertEqual(env_vars - documented_elsewhere, targets - {"8080", "/config"})
        for config in self.root.findall("Config"):
            self.assertTrue(config.get("Description"), config.get("Name"))
            if config.get("Target") in ("DISCORD_WEBHOOK", "WEBUI_PASSWORD", "ACCOUNT_TOKEN"):
                self.assertEqual(config.get("Mask"), "true", "secrets must be masked")

    def test_changes_and_versions(self):
        self.assertEqual((ROOT / "VERSION").read_text().strip(), __version__)
        self.assertIn(__version__, self.text("Changes"))
        self.assertIn(f"## {__version__}", (ROOT / "CHANGELOG.md").read_text())


class RepositoryTest(unittest.TestCase):
    def test_ca_profile(self):
        root = ET.parse(ROOT / "ca_profile.xml").getroot()
        self.assertEqual(root.tag, "CommunityApplications")
        self.assertGreater(len((root.findtext("Profile") or "").strip()), 50)
        icon = root.findtext("Icon").strip()
        self.assertTrue((ROOT / icon[len(RAW):]).is_file())

    def test_license_and_readme(self):
        self.assertIn("GNU GENERAL PUBLIC LICENSE", (ROOT / "LICENSE").read_text()[:200])
        self.assertTrue((ROOT / "README.md").is_file())

    def test_single_template_with_unique_name(self):
        names = [ET.parse(p).getroot().findtext("Name") for p in ROOT.glob("templates/*.xml")]
        self.assertEqual(len(names), len(set(names)))

    def test_no_secret_file_tracked(self):
        ignored = (ROOT / ".gitignore").read_text()
        self.assertIn("unraid.txt", ignored)


if __name__ == "__main__":
    unittest.main()
