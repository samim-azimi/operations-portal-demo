# Architecture

Mission Operations Portal is a local-first web application for field-office operations.

## High-Level Design

- React and Vite provide the browser interface.
- FastAPI exposes authenticated API endpoints.
- SQLAlchemy stores operational records in PostgreSQL for deployment, with SQLite usable for local demo development.
- Uploaded documents are stored on the server filesystem or a mounted volume.
- ReportLab and OpenPyXL support PDF and spreadsheet output.

## LAN Deployment

The app is designed to run on a local office server and remain useful on the LAN when internet connectivity is limited. Optional integrations such as OpenAI, SMTP, Microsoft 365/OneDrive sync, and future UniFi network access should be add-ons rather than hard requirements for the core portal.

## Security Boundaries

Authentication, role-based access, and audit logs are enforced by backend APIs. The frontend hides unavailable modules for convenience, but authorization must remain server-side.
