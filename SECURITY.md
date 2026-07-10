# Security Policy

## Supported versions

Security fixes are applied to the latest release on the default branch.

| Version | Supported |
|---|---|
| 1.x | Yes |
| Earlier versions | No |

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's **Report a vulnerability** option under the repository's Security tab.

Include the affected component, reproduction steps, expected impact, and a suggested mitigation if known. You should receive an acknowledgement within 72 hours. Confirmed issues will be triaged by severity and disclosed after a safe release is available.

## Deployment expectations

- Never commit credentials, API keys, production data, or `.env` files.
- Use a unique production JWT secret of at least 32 random characters.
- Deploy behind TLS and keep PostgreSQL and upload storage private.
- Enable branch protection, secret scanning with push protection, Dependabot alerts, and CodeQL.
- Treat uploads as untrusted. Production deployments should add antivirus or content-disarm scanning.

No control makes software invulnerable. Operators remain responsible for patching, monitoring, backups, incident response, and infrastructure security.
