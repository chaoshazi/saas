"""WeCom (WeChat Work) integration helpers."""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings

WECOM_API = "https://qyapi.weixin.qq.com"


def build_oauth_url(state: str, redirect_uri: str) -> str:
    params = {
        "appid": settings.wecom_corp_id,
        "agentid": settings.wecom_agent_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": "snsapi_base",
    }
    return f"{WECOM_API}/connect/oauth2/authorize?{urlencode(params)}#wechat_redirect"


async def get_access_token() -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{WECOM_API}/cgi-bin/gettoken",
            params={"corpid": settings.wecom_corp_id, "corpsecret": settings.wecom_secret},
        )
        data = response.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"wecom token error: {data}")
    return data["access_token"]


async def exchange_code(code: str) -> dict:
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{WECOM_API}/cgi-bin/auth/getuserinfo",
            params={"access_token": token, "code": code},
        )
        data = response.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"wecom auth error: {data}")
    return data


async def send_text(user_id: str, content: str) -> dict:
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WECOM_API}/cgi-bin/message/send",
            params={"access_token": token},
            json={
                "touser": user_id,
                "msgtype": "text",
                "agentid": settings.wecom_agent_id,
                "text": {"content": content},
            },
        )
        return response.json()
