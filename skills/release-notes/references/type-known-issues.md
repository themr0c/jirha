##### Known issues
Known issues describe existing problems that customers should be aware of, so that they can mitigate them and avoid unnecessary reporting.

**Known issue engineering template**

```
Cause - the user action or circumstances that trigger the bug
Consequence - what the user experience is when the bug occurs
Workaround - if available
Result – mandatory if the workaround does not solve the problem completely
```

**Known issue release note text template**

* **Heading that summarizes the known issue**\
_<Cause>_. As a consequence, _<consequence>_.

  To work around this problem, _<workaround in imperative>_. As a result, _<result>_.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Always provide information about a workaround in a separate paragraph:
  * If a workaround exists, describe it in the following format:

    To work around this problem, <workaround in imperative>.
  * If no workaround is mentioned, investigate and try to describe how to avoid or partially mitigate the problem. If there is no workaround or mitigation, explicitly say: "No known workaround exists."
* Use the present tense.
* If the known issue applies only to specific batch updates (z-streams), clarify that. For example, the known issue might exist from 4.14.0 to 4.14.4 but not 4.14.5 onwards.
* Never promise future fixes. Avoid making claims that are related to a future release; do not announce a new component will replace a deprecated one until it is released.
* For customer reference, include a Jira ticket link to each Known issue on the line directly after the entry. Do not place that link inside parenthesis or brackets. Notify the user if the references are not public in one of the following ways:
  * If you link to tickets that are not public, tell the user that some Jira tickets might require login credentials, for example: "Some linked Jira tickets are accessible only with Red Hat credentials."
  * If you refer to non-public tickets without a link, inform the user, for example: "Some referenced tickets are not linked. This means that the ticket is accessible only with Red Hat credentials."
* Before a release, always check the status of all known issues. If a previously identified known issue is fixed, the customer must be informed in a product-consistent way, for example:
  * A _Fixed issues_ release note contains a reference to the previous known issue.
  * A _New features_ and enhancements release note announces fixes that cover multiple known issues and contains references to those issues.
  * An erratum that contains a fix refers to the previous known issue.
* A partially resolved issue becomes a fixed issue for the fixed scenario but remains a known issue for the unfixed part.

**Examples of known issue release notes**

* **Inconsistent NVMe device names after reboot**\
A new kernel feature that enables asynchronous NVMe namespace scans is introduced in RHEL 10 to accelerate NVMe disk detection. As a consequence of the asynchronous scans, the `/dev/nvmeXnY` device files might point to different namespaces after each reboot. This can lead to inconsistent device names.

  No known workaround exists.

  TICKET-REFERENCE

* **SELinux autorelabel in the Rescue Mode might cause reboot loop**\
Accessing a file system in `rescue` mode triggers SELinux to autorelabel the file system on the next boot, which continues until SELinux runs in the `permissive` mode. Consequently, the system might go into an infinite loop of reboots after exiting the `rescue` mode because it cannot delete the `/.autorelabel` file.

  To work around this problem, switch to the `permissive` mode by adding `enforcing=0` to the kernel command line on the next boot. The system displays a warning message. This message indicates that you might see this problem when accessing the file system in `rescue` mode.

  [RHEL-14005](https://issues.redhat.com/browse/RHEL-14005)
