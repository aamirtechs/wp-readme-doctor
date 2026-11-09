"""Tests for wp_readme_doctor. Standard library only."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wp_readme_doctor as doctor

BASE = """=== Test Plugin ===
Contributors: aamirtechs
Tags: forms, contact
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 1.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

== Description ==

A test plugin.

== Installation ==

1. Activate it.

== Frequently Asked Questions ==

= Does it work? =

Yes.

== Screenshots ==

1. The settings page.

== Changelog ==

= 1.2.0 =

* Fixed a bug.

= 1.1.0 =

* First release.
"""


def validate(text, **kwargs):
    _, findings, status = doctor.validate(text, **kwargs)
    return findings, status


def rules(findings, severity=None):
    return [f.rule for f in findings
            if severity is None or f.severity == severity]


def run_cli(args, stdin_text=None):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(here, "wp_readme_doctor.py")
    return subprocess.run([sys.executable, script] + args,
                          input=stdin_text, capture_output=True, text=True,
                          cwd=here)


def write_temp(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


class TestValidReadme(unittest.TestCase):
    def test_valid_readme_passes(self):
        findings, status = validate(BASE)
        self.assertEqual(status, "PASS")
        self.assertEqual(findings, [])

    def test_stdin_input(self):
        result = run_cli(["-"], stdin_text=BASE)
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK: readme passes all checks", result.stdout)


class TestHeadersAndVersions(unittest.TestCase):
    def test_missing_stable_tag_error(self):
        text = BASE.replace("Stable tag: 1.2.0\n", "")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("missing-header", rules(findings, "error"))
        self.assertTrue(any("Stable tag" in f.message for f in findings))

    def test_stable_tag_not_in_changelog_error(self):
        text = BASE.replace("Stable tag: 1.2.0", "Stable tag: 9.9.9")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("stable-tag-not-in-changelog", rules(findings, "error"))

    def test_stable_tag_trunk_without_entry_is_warning(self):
        text = BASE.replace("Stable tag: 1.2.0", "Stable tag: trunk")
        findings, status = validate(text)
        self.assertEqual(status, "WARN")
        self.assertIn("stable-tag-trunk", rules(findings, "warning"))

    def test_tested_before_requires_error(self):
        text = BASE.replace("Tested up to: 6.7", "Tested up to: 5.0")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("tested-before-requires", rules(findings, "error"))

    def test_bad_version_format_error(self):
        text = BASE.replace("Requires PHP: 7.4", "Requires PHP: seven")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("version-format", rules(findings, "error"))

    def test_missing_description_is_error(self):
        text = BASE.replace("== Description ==\n\nA test plugin.\n", "")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any(f.rule == "missing-section" and "Description" in f.message
                            for f in findings if f.severity == "error"))


class TestTags(unittest.TestCase):
    def test_too_many_tags_error(self):
        tags = ", ".join("tag%d" % n for n in range(13))
        text = BASE.replace("Tags: forms, contact", "Tags: " + tags)
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("tags-count", rules(findings, "error"))

    def test_twelve_tags_ok(self):
        tags = ", ".join("tag%d" % n for n in range(12))
        text = BASE.replace("Tags: forms, contact", "Tags: " + tags)
        _, status = validate(text)
        self.assertEqual(status, "PASS")

    def test_duplicate_tags_error(self):
        text = BASE.replace("Tags: forms, contact", "Tags: forms, Forms")
        findings, status = validate(text)
        self.assertEqual(status, "FAIL")
        self.assertIn("tags-duplicate", rules(findings, "error"))


class TestScreenshots(unittest.TestCase):
    def test_missing_screenshot_file_error(self):
        with tempfile.TemporaryDirectory() as directory:
            findings, status = validate(BASE, screenshots_dir=directory)
            self.assertEqual(status, "FAIL")
            self.assertIn("screenshot-file-missing", rules(findings, "error"))

    def test_present_screenshot_file_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            open(os.path.join(directory, "screenshot-1.png"), "w").close()
            _, status = validate(BASE, screenshots_dir=directory)
            self.assertEqual(status, "PASS")

    def test_unlisted_screenshot_file_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            open(os.path.join(directory, "screenshot-1.png"), "w").close()
            open(os.path.join(directory, "screenshot-2.png"), "w").close()
            findings, status = validate(BASE, screenshots_dir=directory)
            self.assertEqual(status, "WARN")
            self.assertIn("screenshot-file-unlisted", rules(findings, "warning"))


class TestCli(unittest.TestCase):
    def test_check_exit_codes_good_and_bad(self):
        good = write_temp(BASE)
        bad = write_temp(BASE.replace("Stable tag: 1.2.0", "Stable tag: 9.9.9"))
        try:
            self.assertEqual(run_cli([good, "--check"]).returncode, 0)
            self.assertEqual(run_cli([bad, "--check"]).returncode, 1)
            self.assertEqual(run_cli([bad]).returncode, 0)
        finally:
            os.unlink(good)
            os.unlink(bad)

    def test_check_strict_promotes_warnings(self):
        text = BASE.replace("Stable tag: 1.2.0", "Stable tag: trunk")
        path = write_temp(text)
        try:
            self.assertEqual(run_cli([path, "--check"]).returncode, 0)
            self.assertEqual(run_cli([path, "--check", "--strict"]).returncode, 1)
            strict = run_cli([path, "--strict"])
            self.assertIn("stable-tag-trunk", strict.stdout)
            self.assertIn("ERROR [stable-tag-trunk]", strict.stdout)
        finally:
            os.unlink(path)

    def test_json_output_shape(self):
        path = write_temp(BASE.replace("Stable tag: 1.2.0", "Stable tag: 9.9.9"))
        try:
            result = run_cli([path, "--json"])
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "FAIL")
            self.assertEqual(data["errors"], 1)
            self.assertEqual(data["warnings"], 0)
            self.assertEqual(data["plugin_name"], "Test Plugin")
            self.assertEqual(data["changelog_versions"], ["1.2.0", "1.1.0"])
            self.assertIsInstance(data["findings"], list)
            finding = data["findings"][0]
            self.assertEqual(set(finding), {"rule", "severity", "message"})
            self.assertEqual(finding["rule"], "stable-tag-not-in-changelog")
            self.assertEqual(finding["severity"], "error")
        finally:
            os.unlink(path)

    def test_missing_file_exit_code(self):
        result = run_cli(["/nonexistent/readme.txt"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
