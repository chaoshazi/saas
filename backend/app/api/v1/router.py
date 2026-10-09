"""Aggregate all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import admin, auth, billing, dashboard, documents, labels, license, notifications, projects, search, system, tasks, teams, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(documents.router)
api_router.include_router(labels.router)
api_router.include_router(teams.router)
api_router.include_router(notifications.router)
api_router.include_router(billing.router)
api_router.include_router(license.router)
api_router.include_router(dashboard.router)
api_router.include_router(search.router)
api_router.include_router(system.router)
api_router.include_router(admin.router)
