# Mission Operations Portal

A local-first humanitarian operations platform for field offices.

Mission Operations Portal brings common field-office workflows into one internal web portal: support tickets, inventory, stock, signing, messaging, reports, dashboards, and administration. It is designed for LAN-first use where connectivity can be limited and core operations should keep working on a local office server.

This public repository uses demo data only and must not include real organization data or secrets.

## Features

- Help Desk with ticket intake, categories, notes, attachments, knowledge suggestions, and audit history
- IMS for inventory assets, assigned-user assets, exports, and asset forms
- Stock for stock items, requests, approvals, stock cards, movements, and reports
- Digital Signature for internal PDF signing workflows and verification records
- LAN Messenger for local direct, group, and channel communication
- Reports and Dashboards for operational visibility
- Role-based access controls, module permissions, and audit logs
- Future Procurement module
- Future Network Access module, including possible UniFi-oriented workflows

## Humanitarian Field-Office Use Case

The portal is intended for small and mid-sized field offices that need practical internal systems without depending on constant internet access. A local server can host the application on the LAN so teams can manage support, assets, stock, internal documents, signatures, and reports from office devices.

## LAN-First Design

Core workflows are designed to run inside the office network. Optional services such as SMTP, OpenAI, Microsoft 365/OneDrive sync folders, or future UniFi integrations should be treated as add-ons. The app should not require public internet access for basic daily operations.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, React Router, Lucide |
| API | FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy 2 |
| Authentication | JWT, role-based access control |
| PDFs | ReportLab, pypdf |
| Spreadsheets | OpenPyXL |
| AI Assistance | OpenAI API with fallback behavior |
| Deployment | Docker Compose, Nginx |
| Tests | pytest |

## Screenshots

Screenshots for the public demo can be added here.

## Installation

### Docker

```bash
cp .env.example .env
docker compose up
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
corepack enable
pnpm install
pnpm run dev
```

Open http://127.0.0.1:5173.

## Environment Setup

Copy `.env.example` to `.env` and replace placeholder values for your local demo environment.

Do not commit `.env`, production credentials, database backups, logs, uploads, signed PDFs, or real organization documents.

## Demo Credentials

These accounts are fake demo users for local testing only.

| User | Email | Password |
|---|---|---|
| Demo Admin | `admin@example.com` | `admin123` |
| Demo Manager | `manager@example.com` | `manager123` |
| Demo Inventory Officer | `inventory@example.com` | `inventory123` |
| Demo Stock Officer | `stock@example.com` | `stock123` |
| Demo User | `user@example.com` | `user123` |

Replace all demo credentials before any real deployment.

## Security Notes

- This repository must contain demo data only.
- Use a strong production JWT secret of at least 32 random characters.
- Store credentials in local environment files or a secret manager, never in source control.
- Keep upload storage, signed documents, and databases outside the public repository.
- Treat uploaded files as untrusted and add malware scanning for production.
- Create a fresh Git history before publishing if this folder was copied from a private project.

## Documentation

- [Architecture](docs/architecture.md)
- [Modules](docs/modules.md)
- [Security](docs/security.md)
- [Deployment](docs/deployment.md)
- [Roadmap](docs/roadmap.md)

## Roadmap

- Formal database migrations
- Procurement workflows
- Network Access and future UniFi integration
- Microsoft 365/OneDrive sync folder option
- SSO and MFA options
- Background jobs for notifications and reports
- Stronger document retention controls
- Public demo screenshots and expanded tests

## Disclaimer

This public repository uses demo data only and must not include real organization data or secrets. Review all files, history, uploads, logs, databases, and generated artifacts before publishing.

## License

MIT
