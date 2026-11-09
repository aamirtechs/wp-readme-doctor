# Good first issues

Seeded issues for new contributors. File each one on GitHub with the
`good first issue` and `help wanted` labels.

## 1. Check the short description length

Title: Warn when the short description is over 150 characters

Description: wordpress.org shows the first paragraph after the
header block as the short description, and long ones get cut off in
listings. Add a warning when that paragraph is longer than 150
characters. The paragraph is the non-empty text between the header
block and the first `== Section ==` heading.

Difficulty: easy

Acceptance criteria:

* A readme with a short description over 150 characters gets a
  `short-description-length` warning naming the character count.
* A readme with a short description of 150 characters or fewer gets
  no such warning.
* A readme with no short description paragraph gets no such warning.
* A test covers the over-limit case and the at-limit case.
* The rule is documented in the README rule list.

## 2. Validate the Donate link

Title: Warn when Donate link is present but not a URL

Description: The Donate link header is optional, but when a plugin
author includes it, it should be a real URL, just like License URI
already is. Mirror the existing `license-uri` check for the Donate
link header.

Difficulty: easy

Acceptance criteria:

* A Donate link that does not start with http:// or https:// gets a
  warning.
* A valid http or https Donate link gets no warning.
* A readme with no Donate link gets no warning.
* A test covers all three cases.
* The rule is documented in the README rule list.

## 3. Add a --fix flag for the Stable tag prefix

Title: Add --fix to strip a leading v from Stable tag

Description: The `stable-tag-prefix` warning already flags a Stable
tag like `v1.2.0`. Add an opt-in `--fix` mode that rewrites the
input file in place, stripping the leading `v` from Stable tag, and
prints what changed. It must refuse to run on stdin input, and it
must leave every other line byte for byte unchanged.

Difficulty: medium

Acceptance criteria:

* Running with `--fix` on a file with Stable tag `v1.2.0` rewrites
  that line to `Stable tag: 1.2.0` and reports the change.
* A second run on the fixed file reports no `stable-tag-prefix`
  warning.
* Running with `--fix` on stdin input exits 2 with an error message.
* A file with no fixable finding is left unchanged.
* Tests cover the rewrite, the stdin refusal, and the no-change case.

## 4. Support readme.md as well as readme.txt

Title: Accept Markdown readme files with the same header format

Description: Some plugins ship a readme.md that still uses the
wordpress.org header block and `== Section ==` headings. Accept a
`.md` input file with the same parser, and detect the format from
the file extension rather than requiring a new flag. Nothing about
the existing `.txt` behavior may change.

Difficulty: medium

Acceptance criteria:

* A readme.md with valid headers and sections passes with status PASS.
* A readme.md with a Stable tag missing from Changelog fails with
  `stable-tag-not-in-changelog`, exactly as a .txt file does.
* Existing .txt behavior is unchanged, verified by the current test
  suite still passing.
* Tests cover a valid .md file and a broken .md file.
* The README documents that .md input is accepted.
