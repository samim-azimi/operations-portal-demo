# Deployment

Mission Operations Portal can run as a local-first field-office system on a LAN server.

## Local Demo

1. Copy `.env.example` to `.env`.
2. Fill only local demo values.
3. Start PostgreSQL, the FastAPI backend, and the React frontend.
4. Seed the demo data.

## LAN Deployment

- Host the backend and frontend on an internal server reachable by office devices.
- Keep the database and upload storage private to the server or trusted network.
- Use HTTPS where possible, even on internal networks.
- Back up the database and document storage together.
- Restrict admin access to trusted staff.

## Optional Integrations

SMTP can send notifications. OpenAI can assist ticket triage. Future deployments may add a Microsoft 365/OneDrive sync folder option and a UniFi/Network Access module.
