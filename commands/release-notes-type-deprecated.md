##### Deprecated features

Deprecated features are supported but will be removed in a future version. Deprecating a feature is a signal to customers that they should not use the feature for new deployments.

**Deprecated feature engineering template**

```
Description - describe the discontinued feature
Consequence - describe the recommended replacement, if applicable
```

**Deprecated feature release note text template**

* **_<feature>_ is deprecated**\
The _<feature>_, which <purpose>, is deprecated and might be removed in a future major release. You can _<purpose>_ by using _<alternative>_ instead.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Describe the feature or component that is deprecated.
* Write the proposed alternative for the user. Do not use the term "Recommended". See the [recommend](#recommend-verb) glossary entry.
* Do not repeat the definition of "deprecated" from the section intro.
* Avoid predicting future feature statuses in release notes, such as "will be deprecated next release".
* If cloning a previous version of the release notes file for the latest version, ensure the table feature statuses are current for that version.

**Examples of deprecation release notes**

* **The `preserveBootstrapIgnition` parameter for AWS is deprecated**\
The `preserveBootstrapIgnition` parameter for AWS in the `install-config.yaml` file is deprecated. You can use the `bestEffortDeleteIgnition` parameter instead.

  [OCPBUGS-33661](https://issues.redhat.com/browse/OCPBUGS-33661)

* **`katello-agent` is deprecated**\
`katello-agent` is deprecated and might be removed in a future version. Migrate immediately to Remote Execution or Remote Execution pull mode. If you upgrade to Satellite 6.15 without migrating, you will not be able to perform critical host package actions, including patching and security updates. For more information about migrating to Remote Execution, see [Migrating From Katello Agent to Remote Execution](https://access.redhat.com/documentation/en-us/red_hat_satellite/6.14/html-single/managing_hosts/index#Migrating_From_Katello_Agent_to_Remote_Execution_managing-hosts) in _Managing Hosts_.

  SAT-18124

* **Bootstrap.py host registration script**\
The `bootstrap.py` script for registering a host to Satellite or Capsule is deprecated in 6.9. It has been replaced by the `curl` command created by using the global registration template.

  [SAT-21137](https://issues.redhat.com/browse/SAT-21137)

If your product presents deprecations and removals in a table, define the following columns:

* **Category**\
Shows what is impacted by the deprecation, for example, Installation. This can be a header for the table, or a column in your table.
* **Feature or component**\
Provides the specific feature or component.
* **Version**\
Shows when the feature is first deprecated. Keep that version in the table until the feature moves to your list or table of removed features.
* **Alternative action**\
Directs the user to another solution.
* **More information**\
If you do not describe alternative actions, link to documentation, and so on in a separate release note, this column guides the user to the alternative feature or component.

Follow these guidelines for the deprecation and removal tables:

* For scannability, reduce the number of columns and rows to only what is needed.
* Avoid overly long descriptions in tables. Aim for between 3 and 11 words. Link to documentation if more information is needed.
* Avoid blank cells in a table. Define a status, such as "Not available", to represent that a feature did not exist in a release.
* Make sure that markup is displayed correctly in table cells, for example, `arm64`.
* See the following example table that you can use for deprecations:

  **Example table of deprecations**

  | Category | Feature or component | Version | Alternative action | More information |
  | --- | --- | --- | --- | --- |
  | Installation | Hive settings in the `mch` API | 2.2 | Edit hive configuration directly with the `oc edit` command. | For more information, see  _<insert_link>_ . |
