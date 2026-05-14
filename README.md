# ShubhACS Server

ShubhACS is a premium, SaaS-ready ACS (Auto Configuration Server) Management application designed specifically to onboard, monitor, and diagnose Indian ISP Router Models. 

It provides end-to-end orchestration via TR-069 (CWMP) and TR-369 (USP) protocols, paired with a beautiful, responsive React Admin Dashboard.

## Architecture

- **Frontend**: React 18, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, PyMongo
- **Reverse Proxy**: Caddy (Automatic SSL)
- **Database**: MongoDB 7.0

## Installation & Deployment

For detailed containerized instructions, see the comprehensive [DOCKER.md](DOCKER.md) guide.

### Quick Start

1.  Create an `.env` file from template:
    ```env
    ACS_PUBLIC_URL=http://localhost
    ACS_DOMAIN=
    JWT_SECRET=your_generated_jwt_secret
    ADMIN_PASSWORD=YourSecretPassword
    ```
2.  Run docker-compose:
    ```bash
    docker compose up -d --build
    ```
3.  Access backend documentation at `http://localhost/api/docs` and the UI dashboard at `http://localhost`.

## Development Lifecycle

For architectural insights, PRDs, Changelogs, and developer handoff documentation, explore the [memory/](memory/) folder.
