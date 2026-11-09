# wp-readme-doctor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/aamirtechs/wp-readme-doctor/blob/main/LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/aamirtechs/wp-readme-doctor/issues)

A zero-dependency Python CLI that validates a WordPress plugin
readme.txt against wordpress.org rules, offline, before you submit
it. It parses the header fields and the sections, then reports
errors and warnings with a rule id for each finding.

A readme rejected by wordpress.org usually fails on something small:
a Stable tag with no matching Changelog entry, 13 tags, or a
Tested up to version older than Requires at least. This tool catches
those before submission, and it doubles as a CI gate with `--check`.

## Install

Requires Python 3.10 or newer. No dependencies beyond the standard library.

```bash
pip install wp-readme-doctor
```

Or run it straight from the source checkout:

```bash
python3 wp_readme_doctor.py examples/good-readme.txt
```

It also runs as a module:

```bash
python3 -m wp_readme_doctor examples/good-readme.txt
```

## Usage

Validate a file:

```bash
python3 wp_readme_doctor.py readme.txt
```

Validate from stdin (omit the argument, or pass `-`):

```bash
cat readme.txt | python3 wp_readme_doctor.py -
```

Gate a CI job on it (exit 1 on any error, exit 0 if only warnings
or clean):

```bash
python3 wp_readme_doctor.py readme.txt --check
```

Treat warnings as errors as well:

```bash
python3 wp_readme_doctor.py readme.txt --check --strict
```

Check screenshot files against the Screenshots section:

```bash
python3 wp_readme_doctor.py readme.txt --screenshots-dir assets/screenshots
```

Emit JSON instead of text:

```bash
python3 wp_readme_doctor.py readme.txt --json
```

## Captured output: a valid readme

```bash
python3 wp_readme_doctor.py examples/good-readme.txt
```

Captured output:

```
OK: readme passes all checks
```

With the bundled screenshot files, the same readme passes the
screenshot check and the CI gate:

```bash
python3 wp_readme_doctor.py examples/good-readme.txt --screenshots-dir examples/screenshots --check
```

Captured output (exit code 0):

```
OK: readme passes all checks
```

## Captured output: a broken readme

```bash
python3 wp_readme_doctor.py examples/bad-readme.txt
```

Captured output:

```
ERROR [missing-header]: required header 'Stable tag' is missing or empty
WARNING [missing-header]: header 'License URI' is missing
ERROR [tested-before-requires]: 'Tested up to' (6.0) is older than 'Requires at least' (6.7)
ERROR [version-format]: 'Requires PHP' is not a dotted version: 'seven'
ERROR [tags-count]: 'Tags' has 13 tags, wordpress.org allows at most 12
ERROR [tags-duplicate]: 'Tags' repeats 'forms'
ERROR [missing-section]: section 'Description' is missing or empty
WARNING [missing-section]: section 'Frequently Asked Questions' is missing or empty
WARNING [missing-section]: section 'Screenshots' is missing or empty
FAIL: 6 error(s), 3 warning(s)
```

Without `--check`, that run still exits 0, so a report never breaks
a script that did not ask for gating. With `--check` it exits 1.

```bash
python3 wp_readme_doctor.py examples/bad-readme.txt --json
```

Captured output:

```
{
  "file": "examples/bad-readme.txt",
  "status": "FAIL",
  "errors": 6,
  "warnings": 3,
  "findings": [
    {
      "rule": "missing-header",
      "severity": "error",
      "message": "required header 'Stable tag' is missing or empty"
    },
    {
      "rule": "missing-header",
      "severity": "warning",
      "message": "header 'License URI' is missing"
    },
    {
      "rule": "tested-before-requires",
      "severity": "error",
      "message": "'Tested up to' (6.0) is older than 'Requires at least' (6.7)"
    },
    {
      "rule": "version-format",
      "severity": "error",
      "message": "'Requires PHP' is not a dotted version: 'seven'"
    },
    {
      "rule": "tags-count",
      "severity": "error",
      "message": "'Tags' has 13 tags, wordpress.org allows at most 12"
    },
    {
      "rule": "tags-duplicate",
      "severity": "error",
      "message": "'Tags' repeats 'forms'"
    },
    {
      "rule": "missing-section",
      "severity": "error",
      "message": "section 'Description' is missing or empty"
    },
    {
      "rule": "missing-section",
      "severity": "warning",
      "message": "section 'Frequently Asked Questions' is missing or empty"
    },
    {
      "rule": "missing-section",
      "severity": "warning",
      "message": "section 'Screenshots' is missing or empty"
    }
  ],
  "plugin_name": "Broken Plugin",
  "headers": {
    "Contributors": "aamirtechs",
    "Tags": "forms, contact, spam, security, forms, seo, analytics, backup, cache, shop, gallery, maps, video",
    "Requires at least": "6.7",
    "Tested up to": "6.0",
    "Requires PHP": "seven",
    "License": "GPLv2 or later"
  },
  "sections": [
    "Installation",
    "Changelog"
  ],
  "changelog_versions": [
    "1.0.0"
  ]
}
```

## Captured output: warnings only, and --strict

`examples/warnings-readme.txt` uses Stable tag `trunk` with no trunk
Changelog entry and omits License URI, so it produces warnings only:

```bash
python3 wp_readme_doctor.py examples/warnings-readme.txt
```

Captured output:

```
WARNING [missing-header]: header 'License URI' is missing
WARNING [stable-tag-trunk]: 'Stable tag' is 'trunk' but Changelog has no trunk entry
WARN: 0 error(s), 2 warning(s)
```

With `--check` alone that file still exits 0. With `--strict`, the
warnings become errors and the gate fails:

```bash
python3 wp_readme_doctor.py examples/warnings-readme.txt --check --strict
```

Captured output (exit code 1):

```
ERROR [missing-header]: header 'License URI' is missing
ERROR [stable-tag-trunk]: 'Stable tag' is 'trunk' but Changelog has no trunk entry
FAIL: 2 error(s), 0 warning(s)
```

## Options

| Flag | Meaning |
| --- | --- |
| `input` | readme.txt path, or `-` / omitted for stdin |
| `--json` | Emit JSON instead of text |
| `--check` | Exit 1 on any error, 0 if only warnings or clean |
| `--strict` | Treat warnings as errors |
| `--screenshots-dir` | Directory of screenshot-N image files to check |

A missing input file or a missing screenshots directory exits 2
with an error message on stderr.

## Rule list

Headers parsed: Contributors, Tags, Requires at least, Tested up to,
Requires PHP, Stable tag, License, License URI. Sections parsed:
Description, Installation, Frequently Asked Questions, Screenshots,
Changelog, Upgrade Notice. Header and section names match
case-insensitively. An empty section counts as missing.

### Errors

| Rule | Check |
| --- | --- |
| `plugin-name` | Readme does not start with an `=== Plugin Name ===` line |
| `missing-header` | A required header is missing or empty: Contributors, Requires at least, Tested up to, Stable tag, License |
| `version-format` | Requires at least, Tested up to, or Requires PHP is not a dotted version like 6.0 or 7.4 |
| `tested-before-requires` | Tested up to is older than Requires at least |
| `tags-count` | More than 12 tags (wordpress.org guidance) |
| `tags-empty` | Tags contains an empty entry, for example from a trailing comma |
| `tags-duplicate` | A tag repeats, compared case-insensitively |
| `stable-tag-not-in-changelog` | Stable tag has no matching `= version =` entry in Changelog |
| `missing-section` | Description or Changelog is missing or empty |
| `screenshot-file-missing` | A numbered Screenshots entry has no matching screenshot-N image file in `--screenshots-dir` |

### Warnings

| Rule | Check |
| --- | --- |
| `missing-header` | A recommended header is missing: Requires PHP, License URI (when License is present), or Tags |
| `license-uri` | License URI does not look like a URL |
| `stable-tag-prefix` | Stable tag starts with `v`, use the bare version |
| `stable-tag-trunk` | Stable tag is `trunk` but Changelog has no trunk entry |
| `missing-section` | Installation, Frequently Asked Questions, or Screenshots is missing or empty; Upgrade Notice is present but empty |
| `faq-format` | Frequently Asked Questions has no `= Question =` entries |
| `screenshots-format` | Screenshots has no numbered `N. caption` entries |
| `screenshots-numbering` | Screenshots entries are not numbered 1, 2, 3 in order, or repeat a number |
| `changelog-order` | Changelog entries are not in newest-first order |
| `line-length` | A line is over 1000 characters |
| `screenshot-file-unlisted` | A screenshot-N image file in `--screenshots-dir` has no matching Screenshots entry |

With `--strict`, every warning above is reported as an error instead.

## Edge cases

* Trunk: Stable tag `trunk` is valid, but only if Changelog has a
  trunk entry. Without one it is a warning, not an error, because a
  trunk release is a deliberate choice that deserves a note, not a
  rejection.
* Version comparison pads short versions, so 6.0 and 6.0.0 compare
  equal, and 6.10 correctly beats 6.9.
* A Stable tag of `v1.2.0` still matches Changelog entry `1.2.0`,
  but it draws a warning to drop the `v`.
* Tags are split on commas, trimmed, and compared case-insensitively,
  so `Forms` and `forms` count as a duplicate.
* Changelog order is only a warning: some plugins list versions
  oldest-first on purpose, and that should not fail a gate.
* Screenshot files match `screenshot-N.png`, `.jpg`, `.jpeg`, `.gif`,
  or `.webp`, case-insensitively on the extension. The screenshot
  check only runs when `--screenshots-dir` is given, so a readme
  without local screenshots still validates.
* Upgrade Notice is optional. It is only flagged when present but
  empty. Absence is not a finding.
* A readme read from stdin reports its file as `stdin` in JSON output.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

18 tests, all passing: a valid readme passes, missing Stable tag,
Stable tag not in Changelog, trunk handling, Tested before Requires,
bad version format, missing Description, tag count and duplicates,
screenshot file matching and unlisted files, `--check` exit codes
for good, bad, and strict modes, JSON output shape, stdin input,
and the exit code 2 for a missing file.

## License

MIT. See [LICENSE](LICENSE).
