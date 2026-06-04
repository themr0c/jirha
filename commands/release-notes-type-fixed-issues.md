##### Fixed issues
Fixed issues, also called "bug fixes", list problems that are resolved in the current release.

**Fixed issues engineering template**

```
Cause – the user action or circumstance that triggered the bug, in the past tense.
Consequence – what the user experience was when the bug occurred, in the past tense.
Fix – what has changed to fix the bug; do not include overly technical details, in the present perfect or present simple tense.
Result – what happens after the patch is applied, in the present tense.
```

**Fixed issues release note text template**

* **Heading that summarizes the fixed issue**\
Before this update, _<cause>_. As a consequence, _<consequence>_. With this release, _<fix>_. As a result, _<result>_.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Follow the Cause-Consequence-Fix-Result (CCFR) tense logic: "Before this update, a problem occurred. The current update has fixed the problem. As a result, the problem no longer occurs."
  * **Cause**\
  The user action or circumstance that triggered the bug, in the past tense.
  * **Consequence**\
  What the user experience was when the bug occurred, in the past tense.
  * **Fix**\
  What has changed to fix the bug; do not include overly technical details; do not use the present perfect or present simple tense.
  * **Result**\
  What happens after the patch is applied, in the present tense.
* Use "before this update" instead of "previously" to refer to the past situation. See the [previously](#previously-adverb) glossary entry.
* Partially fixed issues might require a separate Known issue for the unfixed scenario.

**Example fixed issue release notes**

* **IPsec `ondemand` connections no longer fail to establish**\
Before this update, when an IPsec connection with the `ondemand` option was configured by using the TCP protocol, the connection failed to establish. With this update, the new Libreswan package makes sure that the initial IKE negotiation completes over TCP. As a result, Libreswan successfully establishes the connection even in TCP mode of IKE negotiation.

  RHEL-51880
* **Multipath no longer crashes because of errors encountered by the ontap prioritizer**\
Before this update, `multipathd` failed when it was configured to use the ontap prioritizer on an unsupported path, because the prioritizer only works with NetApp storage arrays. This failure occurred because of a bug in the prioritizer's error logging code, which caused it to overflow the error message buffer. With this update, the error logging code is fixed, and `multipathd` no longer crashes because of errors encountered by the ontap prioritizer.

  RHEL-49747
* **Infoblox plugin no longer suggests IP addresses already in use**\
Before this update, when you used the Infoblox plugin as the DHCP provider, it suggested free IP addresses that were already in use. With this fix, you can configure the plugin to check the availability of IP addresses. The availability checks are enabled by default.

  TICKET-REFERENCE
