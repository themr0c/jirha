### Release notes

A release note explains specific product behavior, capability, or problem relevant to a product version. Release notes for a particular product version are collected in a document that is published when the new version is released.

#### Style advice for release note texts

The normal stylistic guidelines for documentation from the _IBM Style_ guide and the _Red Hat supplementary style guide for product documentation_ apply also to release note texts, particularly the following:

Be clear and concise:

* Focus on the impact on the user, and omit any overly technical details.
* Avoid complicated syntax, such as passive voice and modal verbs, and ambiguous language. For example, replace "Should XY happen" with "If XY happens".
* Write easily readable text. Avoid using infinitive statements that are common in merge requests and changelogs, for example, "Remove deprecated support macros".

Define unfamiliar terms:

* When you first mention a utility, package, command, or similar item outside of a heading, define it. Do not assume that the customer is familiar with it.
* Omit the definition in later occurrences. If the context is ambiguous, for example, when the release note text mentions both an `example` package and an `example` service, you can repeat the definition to add clarity.
* Avoid definitions in headings, but you can use them to disambiguate different meanings of the same name.
* Expand abbreviations in descriptions. Do not expand abbreviations in headings. For more information, see "Abbreviations" in the _IBM Style_ guide.

Use correct capitalization:

* Do not start a sentence with a word in lowercase. You can repeat a definition to avoid starting a sentence with a lowercase name. For more information, see "Capitalization" in the _IBM Style_ guide.

Keep admonitions to a minimum:

* Avoid placing multiple admonitions in a single note.
* Do not begin a release note with an admonition.
* For more information, see [Admonitions](#admonitions).

#### Tenses in release notes

Write the release notes from the perspective of just after the release, which is when most of the customers read release notes. The state before the update is in the past and the state after the update is in the present.

* Use the _simple present tense_ as much as possible.
* Do not use _future tenses_ (or "should" or "might") to describe the state after the update.
* Use the _simple past tense_ to describe the previous situation before the current update.
* Follow the CCFR (Cause-Consequence-Fix-Result) tense logic in bug fixes.
* Do not use "now" to refer to the state after the update. For more information, see the [now](#now-adverb) glossary entry.

#### Headings for release notes

Introduce each release note with a heading that summarizes the release note. This practice helps customers to quickly determine if the release note is relevant to them.

* The heading can, but does not need to be, a full sentence. Do not use a period at the end of the heading.
* Use _sentence-style capitalization_, not _title case_. If necessary, headings can start with a lowercase letter in the case of a lowercase component name. For example: "```nvme-cli``` and `cryptsetup` are available for Opal automation on NVMe SEDs".
* Write headings that are informative and specific without being overly long or too short. Adhere to the following guidelines:
  * Keep the heading under 120 characters.
  * Follow the specifics for the release notes type.
  * Mention the component in a heading whenever it might not be obvious.
  * Be specific; do not over-generalize headings. For example, "Program no longer crashes" is too generic.
* Do not expand abbreviations in headings. If you use an abbreviation in a heading, expand it on the first mention in the text below.
* Avoid definitions in headings unless necessary for clarity. For example, use definitions to disambiguate different meanings of the same name: "The `journald` system role can tune the performance of the `journald` service".
* Do not start the heading with a gerund. Use gerunds only for procedural content.

#### References to Jira in release notes

For customer information, include references to Jira tickets on all _Known issues_  and _Fixed issues_. Some products provide ticket references for all release note types. Place the reference on the line directly after the entry, not inside parenthesis or brackets. See examples later in this guidance.

Inform the user that some Jira tickets might require login credentials. For example, write the following in the introduction of your _Known issues_ or _Fixed issues_:

"Some linked Jira tickets are accessible only with Red Hat credentials."

If you refer to those tickets without including a link, inform the user. See the following example:

"Some referenced tickets are not linked. This means that the ticket is not accessible without Red Hat credentials."

#### Release note formatting in AsciiDoc
To avoid nesting headings excessively, treat each release note as a description list item. This format is also compatible with the AEM DITA migration.

**Release note AsciiDoc basic formatting template**

```
Release note heading::
This is the main release note text.
+
Add another paragraph if necessary.
+
link:https://issues.redhat.com/browse/TICKET-REFERENCE[TICKET-REFERENCE]
```

For the DITA conversion to work correctly, the list must remain uninterrupted. Follow these guidelines:

* If the release note needs another paragraph or additional elements, you must attach all lines after the first line to the description with a plus sign on a separate line.
* If you need to have a list inside a release note text, attach it with a plus sign on a separate line, and add an empty line followed by a plus sign after the list to attach the next paragraph, such as the ticket reference.
* If you use an open block (`--`) to separate elements within the description, attach it with plus signs before and after.

**Release note AsciiDoc complex formatting template**

```
Release note heading::
This is the main release note text.
+
Add another list:

* List item 1
* List item 2

+
link:https://issues.redhat.com/browse/TICKET-REFERENCE[TICKET-REFERENCE]
```

#### Release note types and sections

Each release note is defined by a specific type based on the information it provides to customers. In Jira tickets, the type is defined in the **Release Note Type** field.

In a release note document, each release note type is presented in a specific section. Do not use other section names for these release note types.

**Release note types and sections**

| Release note type | Release note section |
| --- | --- |
| Feature, Enhancement, Rebase | New features and enhancements |
| Technology Preview | Technology Preview features |
| Deprecated functionality | Deprecated features |
| Removed functionality | Removed features |
| Known issue | Known issues |
| Bug fix | Fixed issues |

Every release note type has a template, which is pre-filled in many Jira projects, and that engineers fill in to provide the required information. The writer then rewrites that information into a customer-readable **release note text** (RN text). You can use standard connecting phrases, for example, "As a result," for results. Sometimes, the information is better presented by changing the order of the pieces of information, for example, a consequence before the cause, or combining them into a single sentence.
