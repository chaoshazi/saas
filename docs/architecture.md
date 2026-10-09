# Architecture

## Overview
Single-tenant project management SaaS delivered as a private-deployment package.

## Components
- `backend/` ? FastAPI + SQLAlchemy 2.0 (async) + Alembic + Celery + Redis.
- `frontend/` ? React 18 + Vite + TypeScript + Tailwind CSS + TanStack Query + Zustand.
- `docker-compose.yml` ? MySQL 8, Redis 7, backend, Celery worker, Nginx-served frontend.

## Backend layout
- `app/core` ? config, security (Argon2id + JWT + TOTP), exceptions, logging, rate limiting.
- `app/models` ? SQLAlchemy models for users/roles, projects/boards/tasks, documents, notifications, billing, license/audit.
- `app/api/v1` ? routers for auth, users, projects, tasks, documents, notifications, billing, license, admin, realtime WebSocket.
- `app/services` ? bootstrap seeding, notifications, audit, license, email, users.
- `app/integrations` ? Alipay RSA2 and WeChat Pay V3 gateway skeletons, WeCom OAuth/messaging.
- `app/storage` ? storage abstraction with local filesystem backend (S3/OSS/MinIO reserved).
- `app/realtime` ? WebSocket connection manager with Redis pub/sub fan-out.

## Security model
- Access token 15m, refresh token 30d, both carry `ver` for instant revocation via `token_version`.
- Argon2id password hashing; TOTP 2FA; RBAC with four seeded roles and granular permissions.
- Rate limiting (Redis with memory fallback), CORS allowlist, request IDs, structured JSON logs, audit trail.

## Data isolation
One instance = one organization. Models intentionally avoid `tenant_id` while keeping `organizations` as a config row.

## Upgrade flow
`deploy/upgrade.sh` performs a MySQL dump, stops the app, builds the target version, restarts, runs Alembic migrations in the backend entrypoint, and health-checks before reporting success.
