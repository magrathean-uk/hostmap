# Security Policy

## Reporting a Vulnerability

Use [GitHub private vulnerability reporting](https://github.com/magrathean-uk/hostmap/security/advisories/new) as the primary reporting route. You can also use the published email route, `contact@magrathean.uk`, with subject `SECURITY: hostmap`.

Do not publish credentials, private keys, database dumps, signing certificates, or exploit details.

Include affected version/commit, platform, topology, reproduction steps, impact, and redacted evidence.

## System and Scope

Hostmap is a Python command-line tool that maps a Linux host and writes a bundle or offline comparison report to a user-selected local path. The collector reads host command output, directory names, selected small configuration files, and local repository metadata. It can inspect existing local Docker or Podman Unix sockets. It does not query remote container contexts or Kubernetes clusters.

The `diff` command reads two existing bundles and writes a comparison report. Hostmap is an architecture-mapping tool, not a vulnerability scanner.

## Trust Boundaries and Security Invariants

The target host, its command output, local container sockets, input bundles, and generated artifacts are security-relevant boundaries. The following properties must hold:

- Collection must not change the inspected host. It may write only its selected output bundle or diff report.
- Collection must not make network API calls or use remote container contexts.
- When copying configuration, `copy_redacted` must reject symbolic links. `read_small_text` must resolve candidate paths and exclude secret-like paths, binary files, and text files over 512 KiB. Included text must be redacted before it is written to the bundle.
- Directory walks and configuration discovery must remain bounded and must not follow symbolic links.
- Diff input paths and manifest entries must not cause Hostmap to read outside a selected bundle or write inside an input bundle.
- Generated bundles must remain review artifacts. Their contents can still expose topology and operational metadata.

## Reportable Findings

Report a vulnerability when Hostmap can realistically:

- disclose secrets or sensitive host content through collection, redaction, review material, or an archive;
- modify host state, use a remote endpoint, or access a remote container context;
- execute an attacker-controlled command or process untrusted bundle data unsafely;
- read or write outside the intended bundle and output boundaries; or
- bypass a stated bound in a way that creates a material availability or confidentiality impact.

Reachability matters. Include the required permissions, selected mode, and whether the behaviour needs a malicious local user, hostile host data, or a crafted bundle.

## Scope & Safe Harbour

Magrathean UK Ltd. will not pursue a good-faith researcher for security disclosures that:
- Target non-production test systems or researcher-owned environments;
- Avoid persistence, destructive changes, denial of service, and access to personal or customer data;
- Report promptly and permit reasonable time for remediation;
- Do not condition non-disclosure on financial compensation.

## Excluded Conduct

No safe harbour covers phishing, credential stuffing, accessing private production infrastructure, large-scale scanning, denial of service, or unlawful conduct.

## Detection Limits

Redaction reduces accidental exposure but cannot make an infrastructure inventory safe for public distribution. Review each generated bundle before sharing it beyond the system owner's trust boundary. Restricted permissions, skipped paths, and unavailable local sockets can leave gaps in the inventory.
