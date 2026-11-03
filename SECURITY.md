# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | Yes                |
| < 0.2   | No                 |

Townlight Core is in pre-1.0; only the latest minor (`0.2.x`) receives security
fixes. Once we cut `0.3.0`, support for `0.2.x` ends.

## Reporting a vulnerability

**Please do not file a public GitHub issue for security reports.**

Two preferred channels, in order:

1. **GitHub Security Advisory** — open a private security advisory at
   https://github.com/townlight/core/security/advisories/new. This
   is the fastest path; it is private to maintainers until disclosure.
2. **Email** — if you cannot use the advisory flow, email the maintainer
   listed at https://github.com/townlight/core (the `Maintained by`
   link in the README) with subject prefix `[townlight_core-security]`.

### What to include

- A description of the vulnerability and where it lives in the codebase.
- A reproducer (minimal code or steps).
- The townlight_core version affected.
- Your assessment of impact (data exposure, privilege escalation, denial
  of service, etc.).
- Whether you believe downstream consumers (records-ai, future modules)
  are likely affected.

### What to expect

- Acknowledgement within **5 business days**.
- An initial triage response within **10 business days** with a tentative
  severity assessment and a target patch window.
- Coordinated disclosure: we'll work with you on a disclosure timeline,
  typically 30 to 90 days depending on severity and downstream blast
  radius. We will credit you in the advisory unless you ask us not to.

### Scope

In scope:

- Code in `townlight_core/`.
- Build / packaging configuration that ships in the release artifact.
- The migration runner and any SQL it generates.
- LLM provider abstraction (sanitization, prompt-injection defense, secret
  handling).

Out of scope:

- Vulnerabilities in third-party LLM provider SDKs (`openai`, `anthropic`,
  `httpx`) — please report those upstream.
- Vulnerabilities in downstream consumers (records-ai etc.) — please
  report those at the consuming repo.
- Issues that require an attacker to already control the operator's
  database, environment, or filesystem.
