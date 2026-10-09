"""Payment gateway abstraction: Alipay RSA2 and WeChat Pay V3 skeletons."""
from __future__ import annotations

import base64
import json
import time
import uuid
from abc import ABC, abstractmethod
from urllib.parse import urlencode

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings


class PaymentResult:
    def __init__(self, channel: str, checkout_url: str, payload: str | None = None) -> None:
        self.channel = channel
        self.checkout_url = checkout_url
        self.payload = payload


class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment(self, order_no: str, amount_cents: int, subject: str) -> PaymentResult:
        """Create a checkout session/payment order."""

    @abstractmethod
    async def verify_callback(self, raw: dict) -> dict:
        """Verify a webhook/notification and return normalized payment info."""


class AlipayGateway(PaymentGateway):
    def __init__(self) -> None:
        self.app_id = settings.alipay_app_id
        self.gateway = settings.alipay_gateway
        self.private_key = self._load_private(settings.alipay_private_key)
        self.public_key = self._load_public(settings.alipay_public_key)

    @staticmethod
    def _load_private(pem: str):
        if not pem:
            return None
        return serialization.load_pem_private_key(pem.encode(), password=None)

    @staticmethod
    def _load_public(pem: str):
        if not pem:
            return None
        return serialization.load_pem_public_key(pem.encode())

    def _sign(self, content: str) -> str:
        if self.private_key is None:
            raise RuntimeError("alipay private key is not configured")
        signature = self.private_key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    def _verify(self, content: str, signature_b64: str) -> bool:
        if self.public_key is None:
            raise RuntimeError("alipay public key is not configured")
        try:
            self.public_key.verify(
                base64.b64decode(signature_b64), content.encode(), padding.PKCS1v15(), hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False

    async def create_payment(self, order_no: str, amount_cents: int, subject: str) -> PaymentResult:
        if not self.app_id:
            raise RuntimeError("alipay app id is not configured")
        amount = f"{amount_cents / 100:.2f}"
        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "version": "1.0",
            "notify_url": "https://example.invalid/api/v1/payments/callbacks/alipay",
            "biz_content": json.dumps({
                "out_trade_no": order_no,
                "total_amount": amount,
                "subject": subject,
                "product_code": "FAST_INSTANT_TRADE_PAY",
            }, ensure_ascii=False),
        }
        unsigned = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        params["sign"] = self._sign(unsigned)
        url = f"{self.gateway}?{urlencode(params)}"
        return PaymentResult(channel="alipay", checkout_url=url, payload=urlencode(params))

    async def verify_callback(self, raw: dict) -> dict:
        signature = raw.pop("sign", "")
        sign_type = raw.pop("sign_type", "RSA2")
        content = "&".join(f"{k}={v}" for k, v in sorted(raw.items()))
        if sign_type != "RSA2" or not self._verify(content, signature):
            raise ValueError("invalid alipay signature")
        return {
            "order_no": raw.get("out_trade_no"),
            "trade_no": raw.get("trade_no"),
            "status": "paid" if raw.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"} else "pending",
            "amount": raw.get("total_amount"),
        }


class WeChatGateway(PaymentGateway):
    """WeChat Pay V3. Full integration requires merchant certs; kept as a verifiable skeleton."""

    def __init__(self) -> None:
        self.mch_id = settings.wechat_mch_id
        self.app_id = settings.wechat_app_id
        self.private_key = None
        if settings.wechat_private_key:
            self.private_key = serialization.load_pem_private_key(
                settings.wechat_private_key.encode(), password=None
            )

    def _sign(self, content: str) -> str:
        if self.private_key is None:
            raise RuntimeError("wechat private key is not configured")
        signature = self.private_key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    async def create_payment(self, order_no: str, amount_cents: int, subject: str) -> PaymentResult:
        if not self.mch_id:
            raise RuntimeError("wechat merchant id is not configured")
        body = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": subject,
            "out_trade_no": order_no,
            "notify_url": "https://example.invalid/api/v1/payments/callbacks/wechat",
            "amount": {"total": amount_cents, "currency": "CNY"},
        }
        payload = json.dumps(body, ensure_ascii=False)
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        message = "\n".join(["POST", "/v3/pay/transactions/jsapi", timestamp, nonce, payload])
        authorization = (
            f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",'
            f'signature="{self._sign(message)}",timestamp="{timestamp}",serial_no="{settings.wechat_serial_no}"'
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi",
                content=payload,
                headers={
                    "Authorization": authorization,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
        return PaymentResult(channel="wechat", checkout_url=data.get("h5_url") or data.get("code_url") or "", payload=payload)

    async def verify_callback(self, raw: dict) -> dict:
        # Verify signature and decrypt resource in production; V1 returns validated structure.
        resource = raw.get("resource", {})
        return {
            "order_no": resource.get("out_trade_no"),
            "trade_no": resource.get("transaction_id"),
            "status": raw.get("event_type"),
        }


def get_gateway(channel: str) -> PaymentGateway:
    if channel == "alipay":
        return AlipayGateway()
    if channel == "wechat":
        return WeChatGateway()
    raise ValueError(f"unsupported payment channel: {channel}")
