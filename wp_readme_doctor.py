#!/usr/bin/env python3
"""wp-readme-doctor: offline validator for a WordPress plugin readme.txt.

Checks a readme.txt against wordpress.org rules before submission:
required headers, Stable tag against the Changelog, tag count and
duplicates, Requires/Tested version sanity, required sections, and
screenshot entries against screenshot files when a directory is given.

Findings have two severities. Errors fail a CI gate, warnings do not,
unless --strict promotes them. Run it on a file, or pipe a readme on
stdin with "-" or no input argument:

    python3 wp_readme_doctor.py examples/good-readme.txt
    cat readme.txt | python3 wp_readme_doctor.py -
    python3 wp_readme_doctor.py readme.txt --check --json

Zero dependencies, Python 3.10 or newer, standard library only.
"""

import argparse
import json
import os
import re
import sys

VERSION_RE = re.compile(r"^\d+(\.\d+)*$")
PLUGIN_NAME_RE = re.compile(r"^===\s*(.+?)\s*===\s*$")
SECTION_RE = re.compile(r"^==\s*(.+?)\s*==\s*$")
SUBSECTION_RE = re.compile(r"^=\s*(.+?)\s*=\s*$")
SCREENSHOT_RE = re.compile(r"^(\d+)\.\s+\S")
SCREENSHOT_FILE_RE = re.compile(r"^screenshot-(\d+)\.(png|jpg|jpeg|gif|webp)$", re.I)

# Canonical header names, keyed by the lowercased name as written.
HEADER_ALIASES = {
    "contributors": "Contributors",
    "tags": "Tags",
    "requires at least": "Requires at least",
    "tested up to": "Tested up to",
    "requires php": "Requires PHP",
    "stable tag": "Stable tag",
    "license": "License",
    "license uri": "License URI",
    "donate link": "Donate link",
}

REQUIRED_HEADERS = ("Contributors", "Requires at least", "Tested up to",
                    "Stable tag", "License")
MAX_TAGS = 12
MAX_LINE_LENGTH = 1000


class Finding:
    """One check result: a rule id, a severity, and a message."""

    def __init__(self, rule, severity, message):
        self.rule = rule
        self.severity = severity
        self.message = message

    def as_dict(self):
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message}

    def __repr__(self):
        return "%s [%s]: %s" % (self.severity.upper(), self.rule, self.message)


def error(rule, message):
    return Finding(rule, "error", message)


def warning(rule, message):
    return Finding(rule, "warning", message)


def parse_version(text):
    """Parse a dotted version into a tuple of ints, or None if invalid."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not VERSION_RE.match(text):
        return None
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return None


def version_key(version):
    """Pad a version tuple so 6.0 and 6.0.0 compare equal."""
    return tuple(version) + (0,) * (3 - len(version)) if len(version) < 3 else tuple(version)


def normalize_version(text):
    """Strip a leading v and surrounding space for comparison."""
    return text.strip().lstrip("vV") if isinstance(text, str) else text


class Readme:
    """Parsed readme.txt: plugin name, headers, and sections."""

    def __init__(self, text):
        self.text = text
        self.lines = text.splitlines()
        self.plugin_name = None
        self.headers = {}
        self.sections = {}
        self.section_order = []
        self._parse()

    def _parse(self):
        in_header = False
        current = None
        for line in self.lines:
            stripped = line.strip()
            name_match = PLUGIN_NAME_RE.match(stripped)
            if name_match and self.plugin_name is None and current is None:
                self.plugin_name = name_match.group(1).strip()
                in_header = True
                continue
            section_match = SECTION_RE.match(stripped)
            if section_match:
                in_header = False
                current = section_match.group(1).strip()
                if current not in self.sections:
                    self.sections[current] = []
                    self.section_order.append(current)
                continue
            if in_header and ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                if key:
                    self.headers[key] = value.strip()
                continue
            if current is not None:
                self.sections[current].append(line)

    def header(self, canonical):
        """Return a header value by canonical name, case-insensitive."""
        for key, value in self.headers.items():
            if key.lower() == canonical.lower():
                return value
        return None

    def section_text(self, name):
        """Return a section's text, matching the name case-insensitively."""
        for key, lines in self.sections.items():
            if key.lower() == name.lower():
                return "\n".join(lines)
        return None

    def section_is_empty(self, name):
        text = self.section_text(name)
        if text is None:
            return True
        return not text.strip()

    def changelog_versions(self):
        """Version strings from = x.y.z = entries in the Changelog section."""
        text = self.section_text("Changelog")
        if text is None:
            return []
        versions = []
        for line in text.splitlines():
            match = SUBSECTION_RE.match(line.strip())
            if match:
                versions.append(match.group(1).strip())
        return versions

    def screenshot_numbers(self):
        """Numbers from 'N. caption' lines in the Screenshots section."""
        text = self.section_text("Screenshots")
        if text is None:
            return []
        numbers = []
        for line in text.splitlines():
            match = SCREENSHOT_RE.match(line.strip())
            if match:
                numbers.append(int(match.group(1)))
        return numbers


def check_plugin_name(readme):
    if readme.plugin_name is None:
        return [error("plugin-name",
                      "readme does not start with an '=== Plugin Name ===' line")]
    return []


def check_headers(readme):
    findings = []
    for name in REQUIRED_HEADERS:
        value = readme.header(name)
        if value is None or not value:
            findings.append(error("missing-header",
                                  "required header '%s' is missing or empty" % name))
    if readme.header("Requires PHP") is None:
        findings.append(warning("missing-header",
                                "recommended header 'Requires PHP' is missing"))
    if readme.header("License URI") is None and readme.header("License"):
        findings.append(warning("missing-header",
                                "header 'License URI' is missing"))
    license_uri = readme.header("License URI")
    if license_uri and not license_uri.lower().startswith(("http://", "https://")):
        findings.append(warning("license-uri",
                                "'License URI' does not look like a URL: %r" % license_uri))
    return findings


def check_versions(readme):
    findings = []
    requires = readme.header("Requires at least")
    tested = readme.header("Tested up to")
    requires_v = parse_version(requires) if requires else None
    tested_v = parse_version(tested) if tested else None
    if requires and requires_v is None:
        findings.append(error("version-format",
                              "'Requires at least' is not a dotted version: %r" % requires))
    if tested and tested_v is None:
        findings.append(error("version-format",
                              "'Tested up to' is not a dotted version: %r" % tested))
    if requires_v is not None and tested_v is not None:
        if version_key(tested_v) < version_key(requires_v):
            findings.append(error("tested-before-requires",
                                  "'Tested up to' (%s) is older than 'Requires at least' (%s)"
                                  % (tested, requires)))
    php = readme.header("Requires PHP")
    if php and parse_version(php) is None:
        findings.append(error("version-format",
                              "'Requires PHP' is not a dotted version: %r" % php))
    return findings


def check_tags(readme):
    findings = []
    tags_value = readme.header("Tags")
    if tags_value is None:
        findings.append(warning("missing-header",
                                "header 'Tags' is missing (up to 12 tags recommended)"))
        return findings
    tags = [tag.strip() for tag in tags_value.split(",")]
    if any(not tag for tag in tags):
        findings.append(error("tags-empty",
                              "'Tags' contains an empty entry (check for a trailing comma)"))
    tags = [tag for tag in tags if tag]
    if len(tags) > MAX_TAGS:
        findings.append(error("tags-count",
                              "'Tags' has %d tags, wordpress.org allows at most %d"
                              % (len(tags), MAX_TAGS)))
    seen = {}
    for tag in tags:
        lowered = tag.lower()
        if lowered in seen:
            findings.append(error("tags-duplicate",
                                  "'Tags' repeats %r" % tag))
        seen[lowered] = True
    return findings


def check_stable_tag(readme):
    findings = []
    stable = readme.header("Stable tag")
    if not stable:
        return findings
    if stable.startswith(("v", "V")):
        findings.append(warning("stable-tag-prefix",
                                "'Stable tag' starts with 'v' (%r); use the bare version"
                                % stable))
    versions = readme.changelog_versions()
    if readme.section_is_empty("Changelog"):
        return findings
    normalized = normalize_version(stable)
    if normalized.lower() == "trunk":
        if not any(v.strip().lower() == "trunk" for v in versions):
            findings.append(warning("stable-tag-trunk",
                                    "'Stable tag' is 'trunk' but Changelog has no trunk entry"))
        return findings
    normalized_versions = [normalize_version(v) for v in versions]
    if normalized not in normalized_versions:
        findings.append(error("stable-tag-not-in-changelog",
                              "'Stable tag' %r has no matching entry in Changelog (found: %s)"
                              % (stable, ", ".join(versions) if versions else "none")))
    return findings


def check_sections(readme):
    findings = []
    for name, severity in (("Description", "error"), ("Changelog", "error"),
                           ("Installation", "warning"),
                           ("Frequently Asked Questions", "warning"),
                           ("Screenshots", "warning")):
        if readme.section_is_empty(name):
            make = error if severity == "error" else warning
            findings.append(make("missing-section",
                                 "section '%s' is missing or empty" % name))
    faq = readme.section_text("Frequently Asked Questions")
    if faq and faq.strip():
        has_question = any(SUBSECTION_RE.match(line.strip())
                           for line in faq.splitlines())
        if not has_question:
            findings.append(warning("faq-format",
                                    "'Frequently Asked Questions' has no '= Question =' entries"))
    screenshots = readme.section_text("Screenshots")
    if screenshots and screenshots.strip():
        numbers = readme.screenshot_numbers()
        if not numbers:
            findings.append(warning("screenshots-format",
                                    "'Screenshots' has no numbered 'N. caption' entries"))
        elif numbers != list(range(1, len(numbers) + 1)):
            findings.append(warning("screenshots-numbering",
                                    "'Screenshots' entries are not numbered 1, 2, 3 in order: %s"
                                    % ", ".join(str(n) for n in numbers)))
        elif len(numbers) != len(set(numbers)):
            findings.append(warning("screenshots-numbering",
                                    "'Screenshots' repeats a screenshot number"))
    upgrade = readme.section_text("Upgrade Notice")
    if upgrade is not None and not upgrade.strip():
        findings.append(warning("missing-section",
                                "section 'Upgrade Notice' is present but empty"))
    versions = readme.changelog_versions()
    parsed = [(v, parse_version(normalize_version(v)))
              for v in versions if normalize_version(v).lower() != "trunk"]
    parsed = [(v, p) for v, p in parsed if p is not None]
    keys = [version_key(p) for _, p in parsed]
    if keys != sorted(keys, reverse=True):
        findings.append(warning("changelog-order",
                                "Changelog entries are not in newest-first order"))
    return findings


def check_lines(readme):
    findings = []
    for number, line in enumerate(readme.lines, start=1):
        if len(line) > MAX_LINE_LENGTH:
            findings.append(warning("line-length",
                                    "line %d is %d characters (over %d)"
                                    % (number, len(line), MAX_LINE_LENGTH)))
    return findings


def check_screenshots(readme, screenshots_dir):
    findings = []
    if screenshots_dir is None:
        return findings
    if not os.path.isdir(screenshots_dir):
        raise ValueError("screenshots directory does not exist: %s" % screenshots_dir)
    present = {}
    for name in os.listdir(screenshots_dir):
        match = SCREENSHOT_FILE_RE.match(name)
        if match:
            present[int(match.group(1))] = name
    for number in readme.screenshot_numbers():
        if number not in present:
            findings.append(error("screenshot-file-missing",
                                  "Screenshots entry %d has no screenshot-%d.png (or jpg/gif) "
                                  "file in %s" % (number, number, screenshots_dir)))
    for number in sorted(present):
        if number not in readme.screenshot_numbers():
            findings.append(warning("screenshot-file-unlisted",
                                    "file %s has no matching entry in the Screenshots section"
                                    % present[number]))
    return findings


def validate(text, screenshots_dir=None, strict=False):
    """Validate readme text. Returns (readme, findings, status)."""
    readme = Readme(text)
    findings = []
    findings += check_plugin_name(readme)
    findings += check_headers(readme)
    findings += check_versions(readme)
    findings += check_tags(readme)
    findings += check_stable_tag(readme)
    findings += check_sections(readme)
    findings += check_lines(readme)
    findings += check_screenshots(readme, screenshots_dir)
    if strict:
        for finding in findings:
            if finding.severity == "warning":
                finding.severity = "error"
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"
    return readme, findings, status


def report_dict(readme, findings, status, source):
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    return {
        "file": source,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "findings": [f.as_dict() for f in findings],
        "plugin_name": readme.plugin_name,
        "headers": dict(readme.headers),
        "sections": list(readme.section_order),
        "changelog_versions": readme.changelog_versions(),
    }


def render_text(readme, findings, status):
    lines = []
    for finding in findings:
        lines.append("%s [%s]: %s" % (finding.severity.upper(), finding.rule,
                                      finding.message))
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    if not findings:
        lines.append("OK: readme passes all checks")
    else:
        lines.append("%s: %d error(s), %d warning(s)" % (status, errors, warnings))
    return "\n".join(lines) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wp-readme-doctor",
        description="Validate a WordPress plugin readme.txt against wordpress.org rules.")
    parser.add_argument("input", nargs="?", default="-",
                        help="readme.txt file path, or '-' / omitted for stdin")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of text")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 on any error, 0 if only warnings or clean")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as errors")
    parser.add_argument("--screenshots-dir", default=None,
                        help="directory of screenshot-N.png files to check against "
                             "the Screenshots section")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.input == "-":
            text = sys.stdin.read()
            source = "stdin"
        else:
            with open(args.input, "r", encoding="utf-8") as handle:
                text = handle.read()
            source = args.input
        readme, findings, status = validate(text, args.screenshots_dir, args.strict)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        output = json.dumps(report_dict(readme, findings, status, source), indent=2) + "\n"
    else:
        output = render_text(readme, findings, status)
    sys.stdout.write(output)
    if args.check and status == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
