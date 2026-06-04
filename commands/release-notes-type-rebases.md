##### Rebases
A rebase is an enhancement in which the version of a component increases. Versions are typically presented in the following format:

X.Y.Z-A.elN, where X.Y.Z is version, A is build, and elN stands for Enterprise Linux version

Example: 1.3.6-3.el8

Rebuilds (change in A) are not rebases. Some products include rebases in the New features and enhancements section; some products do not have rebases at all.

**Rebase engineering template**

```
Version
List of highlights - notable new features and bug fixes since the last available version within the same RHEL major version
```

**Rebase release note text template**

* **`_<package>_` rebased to <X.Y.Z>**\
The `_<package>_` package, which <purpose>, has been rebased to upstream version X.Y.Z. This version provides important fixes and enhancements, most notably the following:

  * _<Enhancement_or_fix>_.
  * _<Enhancement_or_fix>_.

  TICKET-REFERENCE

In addition to general style, follow these guidelines:

* Write the version of the component only in the X.Y.Z format. Do not include the +1-A.elN part. Do not use monospace or other markup for the version number.
* Include a grammatically parallel list of highlights, usually an unordered (bulleted) list.
* Avoid blank rebase descriptions (just a version and no details). If the component is important, include it even if the rebase description is blank.
* Avoid using ungrammatical language common in merge requests and changelogs, such as infinitive statements and incomplete sentences that do not use articles. For example, a phrase such as "remove deprecated support macros" needs to be rewritten into "Deprecated support macros are removed."
* Do not include CVEs in the list of highlights for a rebase if your product does not document CVEs in release notes.
* In the zeroth minor version (for example, 10.0), rebases are documented as "Package is provided in version X.Y.Z" instead of "Package is rebased to version X.Y.Z".

**Examples of rebase release notes**

* **OpenSSL rebased to 3.2.2**\
The OpenSSL packages are rebased to upstream version 3.2.2. This update includes the following enhancements and bug fixes:

  * The `openssl req` command with the `-extensions` option no longer mishandles extensions when creating certificate signing requests (CSR). Before this update, the command fetched, parsed, and checked the name of the configuration file section for consistency but the name was not used for adding extensions to the created CSR file. With this fix, the extension is added to the generated CSR. As a side effect of this change, if the section specifies an extension incompatible with its use in the CSR, the command might fail with an error similar to this: `error:11000080:X509 V3 routines:X509V3_EXT_nconf_int:error in extension:crypto/x509/v3_conf.c:48:section=server_cert, name=authorityKeyIdentifier, value=keyid, issuer:always`.
  * The default X.500 distinguished name (DN) formatting uses the UTF-8 formatter. This change also removes space characters around the equal sign (`=`) that separates DN element types from their values.
  * The certificate compression extension (RFC 8879) is supported.
  * You can use the QUIC protocol on the client side as a Technology Preview.
  * The Argon2d, Argon2i, and Argon2id key derivation functions (KDF) are supported.
  * Brainpool curves are added to the TLS 1.3 protocol (RFC 8734), but Brainpool curves remain disabled in all supported system-wide cryptographic policies.

  TICKET-REFERENCE

* **`nbdkit` rebased to version 1.38**\
The `nbdkit` package is rebased to upstream version 1.38, which includes the following notable bug fixes and enhancements:

  * Block size advertising is enhanced, and a new read-only filter is added.
  * The Python and OCaml bindings support more features of the server API.
  * Internal struct integrity checks are added to make the server more robust.

  TICKET-REFERENCE
