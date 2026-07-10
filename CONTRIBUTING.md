# Contributing

Thank you for helping improve Mission Operations Portal.

## Development workflow

1. Create a focused branch from the default branch.
2. Keep secrets and real support data out of commits and tests.
3. Add or update tests for behavior changes.
4. Run `pytest` in `backend/`.
5. Run `pnpm run build` in `frontend/`.
6. Open a pull request describing user impact, security impact, and verification.

## Review requirements

- Do not weaken authentication, role checks, upload validation, audit logging, or human approval.
- Document new environment variables.
- Pin new dependencies and explain why they are needed.
- Resolve critical code-scanning and dependency alerts before merge.
- Keep AI output advisory for account, security, and closure actions.

Be respectful, specific, and constructive. Harassment, disclosure of private data, and unsafe security testing are not accepted.

