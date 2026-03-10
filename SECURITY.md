# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Execution Market, please report it responsibly through one of the following channels:

- **Email**: [security@ultravioletadao.xyz](mailto:security@ultravioletadao.xyz)
- **GitHub**: Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on this repository.

Please **do not** open public issues for security vulnerabilities.

## Scope

The following components are in scope for security reports:

- **Smart contracts** (Solidity) — task escrow, payment release, and related on-chain logic
- **MCP API server** (Python) — agent-facing endpoints, authentication, and authorization
- **React dashboard** — client-side security, XSS, injection, and session handling
- **Payment flows** — x402 protocol integration, EIP-3009 authorized transfers, USDC handling
- **Evidence verification** — proof submission, validation logic, and storage integrity

## Out of Scope

The following are **not** in scope:

- Social engineering attacks against team members or users
- Denial of service (DoS/DDoS) attacks
- Vulnerabilities in third-party services we depend on (Supabase, Dynamic.xyz, etc.)
- Issues that require physical access to a user's device
- Automated scanner output without a demonstrated proof of concept

## Responsible Disclosure Timeline

We follow a **90-day** responsible disclosure policy:

1. **Day 0** — You report the vulnerability through a private channel listed above.
2. **Day 1-3** — We acknowledge receipt and begin triage.
3. **Day 1-30** — We investigate, develop, and test a fix.
4. **Day 30-90** — We deploy the fix and coordinate public disclosure with you.
5. **Day 90** — If unresolved, you may disclose publicly at your discretion.

We will make every effort to resolve critical issues well before the 90-day window.

## Severity Classification

When reporting, please assess severity using the following guidance:

| Severity | Description | Examples |
|----------|-------------|----------|
| **Critical** | Direct loss of funds or complete system compromise | Escrow bypass, unauthorized USDC transfers, private key exposure |
| **High** | Significant impact on security or functionality | Authentication bypass, privilege escalation, evidence forgery |
| **Medium** | Limited impact requiring specific conditions | Information disclosure, improper input validation, access control gaps |
| **Low** | Minimal impact or theoretical risk | Missing security headers, verbose error messages, minor configuration issues |

## Existing Audits

The following security audits have been completed:

- [`docs/reports/SECURITY_AUDIT_2026-02-18.md`](docs/reports/SECURITY_AUDIT_2026-02-18.md)
- [`docs/reports/PRE_PUBLIC_SECURITY_AUDIT_2026-02-15.md`](docs/reports/PRE_PUBLIC_SECURITY_AUDIT_2026-02-15.md)

## Bug Bounty

We do not currently operate a formal bug bounty program with monetary rewards. However, we appreciate responsible disclosure and will acknowledge reporters publicly (with permission) in our release notes and security advisories.

## Contact

For security-related questions that are not vulnerability reports, reach out to [security@ultravioletadao.xyz](mailto:security@ultravioletadao.xyz).
