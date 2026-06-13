from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot

from bot.customers import CustomerStorage, PendingOrderStorage
from bot.keyboards import address_confirmation_keyboard, contact_request_keyboard

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class MiniAppUser:
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any]:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise ValueError("Missing Telegram initData hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid Telegram initData signature")

    result: dict[str, Any] = dict(pairs)
    if "user" in result:
        result["user"] = json.loads(result["user"])
    return result


def profile_completion_text() -> str:
    return (
        "<b>Перед оформлением заказа сохраните контакты</b>\n\n"
        "Поделитесь номером телефона в чате бота, затем укажите адрес доставки в Ростове-на-Дону. "
        "После этого заказ отправится менеджеру автоматически."
    )


def address_request_text() -> str:
    return (
        "<b>Укажите адрес доставки</b>\n\n"
        "Введите адрес в пределах Ростова-на-Дону: улица, дом, квартира или подъезд, если нужно.\n\n"
        "Например: Ростов-на-Дону, ул. Пойменная, 21, кв. 14."
    )


def address_confirmation_text(address: str) -> str:
    return (
        "<b>Подтвердите адрес доставки</b>\n\n"
        f"{escape(address)}\n\n"
        "Если адрес актуален, подтвердите его. Если нет, введите новый адрес в пределах Ростова-на-Дону."
    )


class MiniAppCheckoutServer:
    def __init__(
        self,
        *,
        bot: Bot,
        telegram_bot_token: str,
        manager_notifier,
        customer_storage: CustomerStorage,
        host: str,
        port: int,
    ) -> None:
        self._bot = bot
        self._telegram_bot_token = telegram_bot_token
        self._manager_notifier = manager_notifier
        self._customer_storage = customer_storage
        self._pending_orders = PendingOrderStorage()
        self._host = host
        self._port = port
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_route("OPTIONS", "/api/orders", self._handle_options)
        app.router.add_post("/api/orders", self._handle_order)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host=self._host, port=self._port)
        await site.start()
        logging.info("Mini App checkout API started on %s:%s", self._host, self._port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_options(self, request: web.Request) -> web.Response:
        return self._json_response({"ok": True})

    async def _handle_order(self, request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return self._json_response({"ok": False, "error": "invalid_json"}, status=400)

        init_data = str(payload.get("init_data", "")).strip()
        if not init_data:
            return self._json_response({"ok": False, "error": "missing_init_data"}, status=400)

        try:
            init_payload = validate_telegram_init_data(init_data, self._telegram_bot_token)
        except ValueError as exc:
            logging.warning("Mini App initData validation failed: %s", exc)
            return self._json_response({"ok": False, "error": "invalid_init_data"}, status=403)

        user_payload = init_payload.get("user") or {}
        try:
            telegram_user = MiniAppUser(
                id=int(user_payload["id"]),
                username=user_payload.get("username"),
                first_name=user_payload.get("first_name"),
                last_name=user_payload.get("last_name"),
            )
        except (KeyError, TypeError, ValueError):
            return self._json_response({"ok": False, "error": "missing_user"}, status=400)

        items = payload.get("items", [])
        total = payload.get("total", 0)
        if not items:
            return self._json_response({"ok": False, "error": "empty_cart"}, status=400)

        customer = await self._customer_storage.get(telegram_user.id)
        await self._pending_orders.set(
            telegram_user.id,
            {
                "items": items,
                "total": total,
                "requested_at": datetime.now(MOSCOW_TZ).isoformat(),
                "source": "checkout_api",
            },
        )

        if customer is None or not customer.get("phone"):
            await self._bot.send_message(
                chat_id=telegram_user.id,
                text=profile_completion_text(),
                parse_mode="HTML",
                reply_markup=contact_request_keyboard(),
            )
            return self._json_response(
                {
                    "ok": True,
                    "awaiting_profile": True,
                    "message": "Откройте чат бота и сохраните номер телефона, затем укажите адрес доставки.",
                }
            )

        address = customer.get("address")
        if address:
            await self._bot.send_message(
                chat_id=telegram_user.id,
                text=address_confirmation_text(str(address)),
                parse_mode="HTML",
                reply_markup=address_confirmation_keyboard(),
            )
            return self._json_response(
                {
                    "ok": True,
                    "awaiting_address_confirmation": True,
                    "message": "Подтвердите адрес доставки в чате бота, и заказ сразу уйдет менеджеру.",
                }
            )

        await self._bot.send_message(
            chat_id=telegram_user.id,
            text=address_request_text(),
            parse_mode="HTML",
        )
        logging.info(
            "Checkout API queued Mini App order for address confirmation user_id=%s items=%s total=%s",
            telegram_user.id,
            len(items),
            total,
        )
        return self._json_response(
            {
                "ok": True,
                "awaiting_address_confirmation": True,
                "message": "Откройте чат бота и укажите адрес доставки, после этого заказ отправится менеджеру.",
            }
        )

    def _json_response(self, payload: dict[str, Any], *, status: int = 200) -> web.Response:
        response = web.json_response(payload, status=status)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
