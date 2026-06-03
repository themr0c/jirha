# Red Hat SSG — Release Notes Style Guide

Bundled reference from the [Red Hat Supplementary Style Guide](https://redhat-documentation.github.io/supplementary-style-guide/#release-notes). Use this when drafting or reviewing release note text.

## Core principles

- Focus on the impact on the user; omit overly technical details.
- Write easily readable text. Avoid infinitive statements common in changelogs.
- Define unfamiliar terms on first mention. Omit definitions in later occurrences.
- Do not start a sentence with a lowercase word.
- Keep admonitions to a minimum. Do not begin a release note with an admonition.

## Tenses

Write from the perspective of just after the release (present tense for current state, past tense for previous behavior).

- Use **simple present tense** as much as possible.
- Use **simple past tense** for the previous situation before the update.
- Do **not** use future tenses, "should", "might", or "now".
- Follow the **CCFR** (Cause-Consequence-Fix-Result) tense logic for bug fixes.

## Headings

- Summarize the release note in an informative, specific heading.
- Sentence-style capitalization, not title case. No period at the end.
- Keep under 120 characters.
- Do not start with a gerund. Do not expand abbreviations in headings.
- Mention the component whenever it might not be obvious.

## Release note types and templates

### 1. New features and enhancements

Template: `<Heading>::` `<Feature/enhancement>. <Reason>. As a result, <result>.`

- Describe why the feature benefits the customer.
- Add a link to product documentation if it exists.
- When a Technology Preview moves to full support, state this clearly.

### 2. Technology Preview features

Template: `<Feature> (Technology Preview)::` `<Release note text>.`

- Always capitalize "Technology Preview" (never "Tech" or "Technical Preview").
- Never use "supported as a Technology Preview". Use: available, provide, capability, functionality.
- End headings with "(Technology Preview)".
- Repeat the TP release note in all subsequent releases until it moves to full support or is removed.

### 3. Deprecated features

Template: `<feature> is deprecated::` `The <feature>, which <purpose>, is deprecated and might be removed in a future major release. You can <purpose> by using <alternative> instead.`

- Describe the feature and write the proposed alternative.
- Do not use "Recommended". Do not predict future statuses.

### 4. Removed features

Template: `<feature> is removed::` `The <feature>, which <purpose>, is removed and is no longer supported. You can <purpose> by using <alternative> instead.`

- Must have been documented as deprecated in a preceding release.
- If a small part of a feature is removed, treat it as a feature change.

### 5. Known issues

Template: `<Heading>::` `<Cause>. As a consequence, <consequence>.` + `To work around this problem, <workaround>. As a result, <result>.`

- Always provide workaround information (or state "No known workaround exists.").
- Use present tense. Never promise future fixes.
- Include Jira ticket link for customer reference.

### 6. Fixed issues (Bug fixes)

Template: `<Heading>::` `Before this update, <cause>. As a consequence, <consequence>. With this release, <fix>. As a result, <result>.`

- Follow CCFR tense logic:
  - **Cause:** past tense (what triggered the bug)
  - **Consequence:** past tense (user experience)
  - **Fix:** present perfect or present simple (what changed)
  - **Result:** present tense (what happens now)
- Use "before this update" instead of "previously".

## Jira references

- Include Jira ticket links on all Known Issues and Fixed Issues.
- Place the reference on the line directly after the entry.
- Note: "Some linked Jira tickets are accessible only with Red Hat credentials."

## AsciiDoc formatting

```
Release note heading::
Release note text.
+
Additional paragraph if necessary.
+
link:https://issues.redhat.com/browse/TICKET[TICKET]
```
