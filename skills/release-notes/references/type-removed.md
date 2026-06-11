##### Removed features
Removed features were deprecated in earlier releases and are no longer supported in the current release.

**Removed feature engineering template**

```
Description - describe the removed feature
Consequence - describe the recommended replacement, if applicable
```

**Removed feature release note text template**

* **<feature> is removed**\
The _<feature>_, which _<purpose>_, is removed and is no longer supported. You can _<purpose>_ by using _<alternative>_ instead.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* If a functionality is removed in a release (for example, in RHEL 9), it must be documented as deprecated in a preceding release (RHEL 8).
* Describe the feature or component that is removed.
* Write the proposed alternative for the user. Do not use the term "Recommended". See the [recommend](#recommend-verb) glossary entry.
* If a small part of a feature is removed, treat that as a feature change, not a removed feature. Focus on why the change was made and what replaces the removed item.

**Examples of removed feature release notes**

* **`scap-workbench` is removed**\
The `scap-workbench` package is removed in RHEL 10. The `scap-workbench` graphical utility performed configuration and vulnerability scans on a single local or remote system. As an alternative, you can scan local systems for configuration compliance by using the `oscap` command and remote systems by using the `oscap-ssh` command. For more information, see [Configuration compliance scanning](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/scanning-the-system-for-configuration-compliance#configuration-compliance-scanning).

  RHELDOCS-19009

* **Service Binding Operator documentation removed**\
With this release, the documentation for the Service Binding Operator (SBO) has been removed because this Operator is no longer supported.

  TICKET-REFERENCE

If your product presents deprecations and removals in a table, follow the guidance for deprecation tables.

* Remove the entry from the table when the version for that removal is no longer fully supported. Removals are included in removal tables for a product-specific number of releases after the removal; typically for two or three releases.

**Example table of removed features**

| Category | Feature or component | Version | Alternative action | More information |
| --- | --- | --- | --- | --- |
| Application management | Subscriptions | 2.5 | Use GitOps for application management | See _<insert_link_to_GitOps>_ for more details. |
