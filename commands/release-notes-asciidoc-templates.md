# Release note AsciiDoc templates (description list format)

Templates and examples for each release note type in the description list format used by Renoa and the RHDH release notes.

## New feature or enhancement

```
<Heading that summarizes the enhancement or feature>::
+
--
<Feature, enhancement>. <Reason>. As a result, <result>.

For more information, see <link_to_product_docs>.
--
```

**Example:**

```
The Template Sync plugin supports using an HTTP proxy to connect to a repository::
+
--
You can use an HTTP proxy to synchronize templates between your Satellite server and a git repository. Configuring an HTTP proxy for template synchronization ensures that Satellite routes the Template Sync request to the repository through the specified proxy server.
For more information, see link:https://docs.redhat.com/en/documentation/red_hat_satellite/6.17/html-single/administering_red_hat_satellite/index#Synchronizing_Templates_Repositories_admin[Synchronizing template repositories] in _Administering Red Hat Satellite_.
--
```

## Technology Preview

```
<Feature> (Technology Preview)::
+
--
<Release note text>. This capability is a Technology Preview feature.
--
```

**Example:**

```
Azure File CSI supports snapshots (Technology Preview)::
+
--
OpenShift Container Platform 4.17 introduces volume snapshot support for the Microsoft Azure File Container Storage Interface (CSI) Driver Operator. This capability is a Technology Preview feature.

For more information, see link:https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html-single/storage/#csi-drivers-supported_persistent-storage-csi[CSI drivers supported by OpenShift Container Platform] and link:https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html-single/storage/#csi-volume-snapshots[CSI volume snapshots].
--
```

## Deprecated feature

```
<feature> is deprecated::
+
--
The <feature>, which <purpose>, is deprecated and might be removed in a future major release. You can <purpose> by using <alternative> instead.
--
```

**Example:**

```
The `preserveBootstrapIgnition` parameter for AWS is deprecated::
+
--
The `preserveBootstrapIgnition` parameter for AWS in the `install-config.yaml` file is deprecated. You can use the `bestEffortDeleteIgnition` parameter instead.
--
```

## Removed feature

```
<feature> is removed::
+
--
The <feature>, which <purpose>, is removed and is no longer supported. You can <purpose> by using <alternative> instead.
--
```

**Example:**

```
`scap-workbench` is removed::
+
--
The `scap-workbench` package is removed in RHEL 10. The `scap-workbench` graphical utility performed configuration and vulnerability scans on a single local or remote system. As an alternative, you can scan local systems for configuration compliance by using the `oscap` command and remote systems by using the `oscap-ssh` command. For more information, see link:https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/scanning-the-system-for-configuration-compliance[Configuration compliance scanning].
--
```

## Known issue

```
<Heading that summarizes the known issue>::
+
--
<Cause>. As a consequence, <consequence>.

To work around this problem, <workaround in imperative>. As a result, <result>.
--
```

**Example (with workaround):**

```
SELinux autorelabel in the Rescue Mode might cause reboot loop::
+
--
Accessing a file system in `rescue` mode triggers SELinux to autorelabel the file system on the next boot, which continues until SELinux runs in the `permissive` mode. Consequently, the system might go into an infinite loop of reboots after exiting the `rescue` mode because it cannot delete the `/.autorelabel` file.

To work around this problem, switch to the `permissive` mode by adding `enforcing=0` to the kernel command line on the next boot. The system displays a warning message. This message indicates that you might see this problem when accessing the file system in `rescue` mode.
--
```

**Example (no workaround):**

```
Inconsistent NVMe device names after reboot::
+
--
A new kernel feature that enables asynchronous NVMe namespace scans is introduced in RHEL 10 to accelerate NVMe disk detection. As a consequence of the asynchronous scans, the `/dev/nvmeXnY` device files might point to different namespaces after each reboot. This can lead to inconsistent device names.

No known workaround exists.
--
```

## Fixed issue (bug fix)

```
<Heading that summarizes the fixed issue>::
+
--
Before this update, <cause>. As a consequence, <consequence>. With this release, <fix>. As a result, <result>.
--
```

**Example:**

```
IPsec `ondemand` connections no longer fail to establish::
+
--
Before this update, when an IPsec connection with the `ondemand` option was configured by using the TCP protocol, the connection failed to establish. With this update, the new Libreswan package makes sure that the initial IKE negotiation completes over TCP. As a result, Libreswan successfully establishes the connection even in TCP mode of IKE negotiation.
--
```
