=== Example Plugin ===
Contributors: aamirtechs
Donate link: https://example.com/donate
Tags: forms, contact, spam, security
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 1.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

A small contact form plugin with spam protection.

== Description ==

Example Plugin adds a simple contact form to any page. It blocks
common spam patterns without a captcha, and it stores nothing
outside your own site.

== Installation ==

1. Upload the plugin folder to /wp-content/plugins/.
2. Activate the plugin through the Plugins screen.
3. Add the form with the [example-form] shortcode.

== Frequently Asked Questions ==

= Does it need a captcha? =

No. It filters spam by pattern matching, so visitors never solve
a puzzle.

= Does it store submissions? =

No. Messages are emailed and then discarded.

== Screenshots ==

1. The settings page.
2. A form on a page.

== Changelog ==

= 1.2.0 =

* Fixed a notice on PHP 8.2.
* Added a honeypot field.

= 1.1.0 =

* First public release.

== Upgrade Notice ==

= 1.2.0 =

Upgrade for the PHP 8.2 fix. No settings change is needed.
