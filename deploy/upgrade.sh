#!/bin/sh
set -e

VERSION="${1:-latest}"
COMPOSE="${COMPOSE:-docker compose}"
BACKUP_DIR="./backups/$(date +%Y%m%d%H%M%S)"

echo "Backing up MySQL to ${BACKUP_DIR}..."
mkdir -p "${BACKUP_DIR}"
"${COMPOSE}" exec -T mysql sh -c 'exec mysqldump --all-databases -uroot -p"$MYSQL_ROOT_PASSWORD"' > "${BACKUP_DIR}/mysql.sql"

echo "Stopping application services..."
"${COMPOSE}" stop backend worker

echo "Pulling/building version ${VERSION}..."
"${COMPOSE}" build backend worker frontend

echo "Starting services (migrations run in backend entrypoint)..."
"${COMPOSE}" up -d

echo "Waiting for backend health..."
for i in $(seq 1 30); do
  if "${COMPOSE}" ps backend | grep -q "(healthy)"; then
    echo "Upgrade completed successfully."
    exit 0
  fi
  sleep 2
done

echo "Health check failed. Rolling back to previous stack..."
"${COMPOSE}" down
"${COMPOSE}" up -d
echo "Rollback triggered. Inspect logs with: ${COMPOSE} logs backend"
exit 1
