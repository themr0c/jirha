##### New features and enhancements

New features are new functions, and enhancements are improvements to existing functions. The release notes for both types are similar, and you can group them together in a single section, or they can be separate.

**New feature and enhancement engineering template**

```
Feature, enhancement – describe the feature or enhancement from the user's point of view
Reason – why has the feature or enhancement been implemented
Result – what is the current user experience
```

**New feature and enhancement release note text template**

* **_<Heading that summarizes the enhancement or feature>_**\
_<Feature, enhancement>_. _<Reason>_. As a result, _<result>_.

  For more information, see _<link_to_product_docs>_.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Describe why the feature or enhancement benefits the customer or why it is required.
* Add a link to the product documentation for the feature, if it exists.
* When a previous Technology Preview changes to full support, make this information clear. Use text similar to these examples:
  * _<Feature>_, available as a Technology Preview before this update, is fully supported from RHEL X.Y.
  * _<Feature>_, introduced in RHEL X.Y as a Technology Preview, is fully supported with this release.

**Examples of new features and enhancements release notes**

* **Cluster API replaces Terraform for VMware vSphere installations**\
In OpenShift Container Platform 4.16, the installation program uses Cluster API instead of Terraform to provision cluster infrastructure during installations on VMware vSphere.

  TICKET-REFERENCE

* **New packages: keylime**\
RHEL 9.1 introduces Keylime, a tool for attestation of remote systems, which uses the trusted platform module (TPM) technology. With Keylime, you can verify and continuously monitor the integrity of remote systems. You can also specify encrypted payloads that Keylime delivers to the monitored machines, and define automated actions that trigger whenever a system fails the integrity test.
For more information, see [Ensuring system integrity with Keylime](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/security_hardening/index#assembly_ensuring-system-integrity-with-keylime_security-hardening) in the RHEL 9 _Security hardening_ document.

  RHELPLAN-92522

* **The Template Sync plugin supports using an HTTP proxy to connect to a repository**\
You can use an HTTP proxy to synchronize templates between your Satellite server and a git repository. Configuring an HTTP proxy for template synchronization ensures that Satellite routes the Template Sync request to the repository through the specified proxy server.
For more information, see [Synchronizing template repositories](https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html-single/administering_red_hat_satellite/index#Synchronizing_Templates_Repositories_admin) in _Administering Red Hat Satellite_.

  [SAT-27349](https://issues.redhat.com/browse/SAT-27349)
