# Security

This public repository must contain demo data only. Do not commit real organization records, credentials, uploads, signed documents, logs, or database backups.

## Controls

- Role-based access controls protect module actions and records.
- Audit logs record important operational events.
- JWT secrets must be unique and strong in production.
- Uploaded documents should be stored outside the source tree in production.
- Digital signature files and verification data should be protected as sensitive records.
- SMTP, OpenAI, Microsoft 365, OneDrive, UniFi, and database credentials belong only in local environment files or secret managers.

## Public Demo Expectations

Use `.env.example` only as a placeholder template. Use fake users, fake assets, fake stock, fake suppliers, fake locations, and fake dashboard URLs.

Before publishing, create a fresh Git history so old committed secrets or private files are not exposed.
