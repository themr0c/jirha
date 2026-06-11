##### Technology Preview features
Technology Preview features offer early access to new product innovations. This enables customers to test them and provide feedback. These features are not fully supported, might be incomplete, and are not for production use.
For more information, see [Technology Preview Features Support Scope](https://access.redhat.com/support/offerings/techpreview/).

**Technology Preview engineering template**

```
Package - list the package that includes the Technology Preview feature
Description - describe what the feature does
```

**Technology Preview release note text template**

* **_<Feature>_ (Technology Preview)**\
_<Release note text>_.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Always capitalize both words in "Technology Preview". Never shorten to "Tech" in customer-facing documents. Do not use the term "Technical Preview".
* Never use "supported as a Technology Preview". Avoid _support_ in Technology Preview descriptions. Instead, use neutral words, for example: _available_, _provide_, _capability_, _functionality_, _implement_, and _enable_. For hardware devices, _recognize_ is usually the correct term. For example, components can recognize devices, but Red Hat does not support the devices themselves.
* Write headings for Technology Preview features similar to headings for new features. End the heading with "(Technology Preview)".
* After you briefly describe the feature, mention again that it is a Technology Preview.
* Do not use the Technology Preview admonition in the release notes because it would be repetitive.
* Repeat a Technology Preview release note in all subsequent releases until the feature moves to full support or is removed. If necessary, you can adjust the RN text for a minor release.
* Mention deprecated Technology Previews in both Technology Preview features and Deprecated features sections, and repeat until the last minor release within the major release.
* When required by stakeholders, you can include the following information in the description:
  * Request for feedback
  * Link to upstream docs
  * Link to a verified Knowledgebase article

**Examples of Technology Preview release notes**

* **Azure File CSI supports snapshots (Technology Preview)**\
OpenShift Container Platform 4.17 introduces volume snapshot support for the Microsoft Azure File Container Storage Interface (CSI) Driver Operator. This capability is a Technology Preview feature.

  For more information, see [CSI drivers supported by OpenShift Container Platform](https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html-single/storage/#csi-drivers-supported_persistent-storage-csi) and [CSI volume snapshots](https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html-single/storage/#csi-volume-snapshots).

  TICKET-REFERENCE

* **System-wide post-quantum cryptography is available through `crypto-policies-pq-preview` (Technology Preview)**\
The `TEST-PQ` subpolicy contained in the new `crypto-policies-pq-preview` package provides system-wide post-quantum cryptography (PQC) as a Technology Preview. You can enable PQC by switching to the TEST-PQ subpolicy and restarting the system, for example:

  ```
  # update-crypto-policies --set DEFAULT:TEST-PQ
  # reboot
  ```

  Note that all PQC algorithms in RHEL 10 are provided as a Technology Preview feature. The package and system-wide cryptographic policy name are subject to change when post-quantum cryptography exits Technology Preview.

  [RHEL-58241](https://issues.redhat.com/browse/RHEL-58241)
