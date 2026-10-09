# Deployment

## Local development
Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
$env:APP_ENV="development"
$env:DATABASE_URL="sqlite+aiosqlite:///./dev.db"
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Docker Compose (single package)
```bash
copy .env.example .env           # edit secrets
docker compose up -d --build
docker compose ps
```
The stack exposes the UI on port `80` by default (`HTTP_PORT` override).

## Online upgrade
```bash
bash deploy/upgrade.sh <version-tag>
```
This backs up MySQL, rebuilds services, runs migrations, health-checks, and triggers rollback on failure.

## Configuration
All runtime configuration comes from environment variables; see `.env.example`. Critical values:
- `SECRET_KEY` ? long random string for JWT signing.
- `DATABASE_URL` ? `mysql+asyncmy://...` in production.
- `LICENSE_PUBLIC_KEY` ? PEM public key for verifying signed license keys.
- `SMTP_*` and `WECOM_*` ? enable email and WeCom notification channels.
- `ALIPAY_*` / `WECHAT_*` ? payment gateway credentials.

## Verification
```bash
cd backend && pytest
cd frontend && npm run build
```


## Initial account & database access
- There is **no preset account**. Register from the UI, or create an admin from the backend directory:
  ```bash
  python -m app.cli create-superuser admin@example.com 'StrongPass123!' --name Admin
  ```
- Local development uses SQLite by default at `backend/saas.db` (relative to the backend working directory).
- Docker Compose uses MySQL 8: database `saas`, user `saas`, password from `MYSQL_PASSWORD` (default `saas`), root password from `MYSQL_ROOT_PASSWORD` (default `root`).
- To inspect MySQL from the host, publish the port and connect:
  ```bash
  docker compose exec mysql mysql -usaas -psaas saas
  ```
  Or add `ports: ["3306:3306"]` to the `mysql` service, then:
  ```bash
  mysql -h127.0.0.1 -P3306 -usaas -psaas saas
  ```