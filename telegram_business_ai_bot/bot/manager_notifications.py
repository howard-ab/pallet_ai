from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.manager_access import ManagerAccessStorage

DEFAULT_MANAGER_CHAT_IDS = [5467423100]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECIPIENTS_FILE = PROJECT_ROOT / "data" / "manager_recipients.json"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class ManagerRecipient:
    chat_id: int
    name: str = ""
    username: str = ""
    enabled: bool = True
    role: str = ""


class ManagerNotifier:
    def __init__(
        self,
        manager_chat_ids: Iterable[int] | None = None,
        *,
        manager_bot: Bot | None = None,
        access_storage: ManagerAccessStorage | None = None,
    ) -> None:
        self._manager_bot = manager_bot
        self._access_storage = access_storage or ManagerAccessStorage()
        recipients = self._load_recipients_file()
        if not recipients:
            recipients = [
                ManagerRecipient(chat_id=int(chat_id))
                for chat_id in (manager_chat_ids or DEFAULT_MANAGER_CHAT_IDS)
            ]
        self._recipients = recipients

    @property
    def manager_chat_ids(self) -> list[int]:
        return [recipient.chat_id for recipient in self._recipients if recipient.enabled]

    def is_allowed_chat(self, chat_id: int) -> bool:
        return any(recipient.enabled and recipient.chat_id == chat_id for recipient in self._recipients)

    def _load_recipients_file(self) -> list[ManagerRecipient]:
        if not RECIPIENTS_FILE.exists():
            return []
        try:
            payload = json.loads(RECIPIENTS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logging.exception("Failed to decode manager recipients file")
            return []

        recipients = []
        for raw in payload.get("recipients", []):
            try:
                recipients.append(
                    ManagerRecipient(
                        chat_id=int(raw["chat_id"]),
                        name=str(raw.get("name", "")),
                        username=str(raw.get("username", "")),
                        enabled=bool(raw.get("enabled", True)),
                        role=str(raw.get("role", "")),
                    )
                )
            except (KeyError, TypeError, ValueError):
                logging.exception("Invalid manager recipient entry: %s", raw)
        return recipients

    async def send_order_notification(
        self,
        bot: Bot,
        *,
        customer: dict[str, object] | None,
        telegram_user: object | None,
        items: list[dict[str, object]],
        total: object,
    ) -> None:
        recipients = [recipient for recipient in self._recipients if recipient.enabled]
        if not recipients:
            return

        delivery_bot = self._manager_bot or bot

        username = None
        first_name = None
        user_id = None
        if telegram_user is not None:
            username = getattr(telegram_user, "username", None)
            first_name = getattr(telegram_user, "first_name", None)
            user_id = getattr(telegram_user, "id", None)

        if customer:
            username = customer.get("username") or username
            first_name = customer.get("first_name") or first_name

        now = datetime.now(MOSCOW_TZ)
        order_number = f"MS-{now.strftime('%Y%m%d-%H%M')}-{user_id or 'guest'}"
        await self._access_storage.store_order_record(
            order_number=order_number,
            customer=customer,
            telegram_user=telegram_user,
            items=items,
            total=total,
        )
        display_name = first_name or username or "без имени"
        phone = (customer or {}).get("phone") or "не указан"

        lines = [
            "<b>Новый заказ</b> 📦",
            "",
            f"Номер: <code>{escape(order_number)}</code>",
            f"Время: <b>{escape(now.strftime('%d.%m.%Y %H:%M MSK'))}</b>",
            "",
            f"Клиент: <b>{escape(str(display_name))}</b>",
            f"Telegram: @{escape(str(username or 'не указан'))}",
            f"Телефон: <b>{escape(str(phone))}</b>",
        ]

        if user_id is not None:
            lines.append(f"User ID: <code>{escape(str(user_id))}</code>")

        lines.extend(["", "<b>Что собрать</b>"])

        for index, item in enumerate(items, start=1):
            name = escape(str(item.get("name", "Товар")))
            weight = escape(str(item.get("weight", "")))
            price = escape(str(item.get("price", "")))
            lines.append(f"{index}. {name}")
            lines.append(f"   {weight} · <b>{price}</b>")

        lines.extend(["", f"<b>Итого: {escape(str(total))} руб.</b>"])
        text = "\n".join(lines)

        for recipient in recipients:
            if not await self._access_storage.is_verified(recipient.chat_id):
                logging.info(
                    "Skipping manager notification to unverified staff chat_id=%s username=%s",
                    recipient.chat_id,
                    recipient.username,
                )
                continue
            if self._manager_bot is None and user_id is not None and recipient.chat_id == user_id:
                logging.info(
                    "Skipping manager notification to the same main-bot dialog chat_id=%s. Configure MANAGER_BOT_TOKEN or a separate group chat.",
                    recipient.chat_id,
                )
                continue
            try:
                await delivery_bot.send_message(chat_id=recipient.chat_id, text=text, parse_mode="HTML")
            except TelegramBadRequest:
                logging.exception(
                    "Telegram rejected manager notification to chat_id=%s username=%s",
                    recipient.chat_id,
                    recipient.username,
                )
            except Exception:  # noqa: BLE001
                logging.exception(
                    "Failed to send manager notification to chat_id=%s username=%s",
                    recipient.chat_id,
                    recipient.username,
                )
