"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AICRM SaaS"
    app_env: str = "development"
    debug: bool = False
    seed_demo: bool = False
    secret_key: str = "change-me-to-a-long-random-string"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    database_url: str = "sqlite+aiosqlite:///./saas.db"
    redis_url: str = "redis://127.0.0.1:6379/0"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    totp_issuer: str = "AICRM SaaS"

    storage_backend: str = "local"
    storage_local_root: str = "./uploads"
    storage_max_bytes: int = 25 * 1024 * 1024

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True

    wecom_corp_id: str = ""
    wecom_agent_id: str = ""
    wecom_secret: str = ""
    wecom_callback_token: str = ""
    wecom_callback_aes_key: str = ""

    alipay_app_id: str = ""
    alipay_private_key: str = ""
    alipay_public_key: str = ""
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"

    wechat_mch_id: str = ""
    wechat_app_id: str = ""
    wechat_api_v3_key: str = ""
    wechat_private_key: str = ""
    wechat_serial_no: str = ""
    wechat_platform_cert: str = ""

    license_public_key: str = ""
    license_issuer: str = "saas-licensing"
    license_grace_days: int = 7

    celery_broker_url: str = "redis://127.0.0.1:6379/1"
    celery_result_backend: str = "redis://127.0.0.1:6379/2"

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
