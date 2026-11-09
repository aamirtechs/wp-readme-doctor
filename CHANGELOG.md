# Changelog

## 1.0.0 - 2026-11-04

Initial release.

* Parses readme.txt headers (Contributors, Tags, Requires at least,
  Tested up to, Requires PHP, Stable tag, License, License URI) and
  sections (Description, Installation, Frequently Asked Questions,
  Screenshots, Changelog, Upgrade Notice).
* Errors for missing required headers, a Stable tag with no matching
  Changelog entry, more than 12 tags, duplicate tags, bad version
  formats, Tested up to older than Requires at least, and missing or
  empty Description and Changelog sections.
* Warnings for missing recommended headers and sections, a Stable tag
  of trunk with no trunk Changelog entry, screenshot numbering and
  format problems, out of order Changelog entries, and lines over
  1000 characters.
* Optional screenshot file check with --screenshots-dir, matching
  numbered Screenshots entries against screenshot-N image files.
* Text and --json output, --check CI gate (exit 1 on any error),
  --strict to promote warnings to errors, file or stdin input.
* Zero dependencies, Python 3.10 or newer.
