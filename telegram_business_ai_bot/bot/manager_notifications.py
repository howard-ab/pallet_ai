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
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.manager_access import ManagerAccessStorage

DEFAULT_MANAGER_CHAT_IDS = [5467423100]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECIPIENTS_FILE = PROJECT_ROOT / "data" / "manager_recipients.json"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
STATUS_LABELS = {
    "new": "Новый",
    "assembled": "Готов к доставке",
    "in_delivery": "В доставке",
    "delivered": "Доставлен",
}
STATUS_ICONS = {
    "new": "🆕",
    "assembled": "✅",
    "in_delivery": "🚚",
    "delivered": "✅",
}
STATUS_ACTION_LABELS = {
    "assembled": "Готов к доставке",
    "in_delivery": "Передать в доставку",
    "delivered": "Отметить доставленным",
}
STATUS_TRANSITIONS = {
    "new": ("assembled",),
    "assembled": ("in_delivery",),
    "in_delivery": ("delivered",),
    "delivered": (),
}


@dataclass(frozen=True)
class ManagerRecipient:
    chat_id: int
    name: str = ""
    username: str = ""
    enabled: bool = True
    role: str = ""


def order_status_keyboard(order: dict[str, object]) -> InlineKeyboardMarkup | None:
    order_number = str(order.get("order_number", "")).strip()
    status = str(order.get("status", "new"))
    transitions = STATUS_TRANSITIONS.get(status, ())
    if not order_number or not transitions:
        return None

    inline_keyboard: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for next_status in transitions:
        current_row.append(
            InlineKeyboardButton(
                text=STATUS_ACTION_LABELS.get(next_status, STATUS_LABELS[next_status]),
                callback_data=f"order:status:{next_status}:{order_number}",
            )
        )
        if len(current_row) == 2:
            inline_keyboard.append(current_row)
            current_row = []
    if current_row:
        inline_keyboard.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def format_order_message(order: dict[str, object]) -> str:
    customer = order.get("customer", {}) or {}
    customer_name = customer.get("first_name") or customer.get("username") or "без имени"
    username = customer.get("username") or "не указан"
    phone = customer.get("phone") or "не указан"
    updated_at = str(order.get("updated_at") or order.get("timestamp") or "")
    updated_text = updated_at
    if updated_at:
        try:
            updated_text = datetime.fromisoformat(updated_at).strftime("%d.%m.%Y %H:%M MSK")
        except ValueError:
            updated_text = updated_at
    last_action_by = order.get("last_action_by") or {}
    actor_name = last_action_by.get("first_name") or last_action_by.get("username")

    lines = [
        f"<b>{escape(STATUS_ICONS.get(str(order.get('status', 'new')), '📦'))} Заказ</b>",
        "",
        f"Номер: <code>{escape(str(order.get('order_number', '-')))}</code>",
        f"Статус: <b>{escape(STATUS_LABELS.get(str(order.get('status', 'new')), 'Новый'))}</b>",
        f"Обновлен: <b>{escape(updated_text)}</b>",
    ]
    if actor_name:
        lines.append(f"Последнее действие: <b>{escape(str(actor_name))}</b>")

    lines.extend(
        [
            "",
            f"Клиент: <b>{escape(str(customer_name))}</b>",
            f"Telegram: @{escape(str(username))}",
            f"Телефон: <b>{escape(str(phone))}</b>",
        ]
    )
    user_id = customer.get("user_id")
    if user_id is not None:
        lines.append(f"User ID: <code>{escape(str(user_id))}</code>")

    lines.extend(["", "<b>Что собрать</b>"])

    for index, item in enumerate(order.get("items", []), start=1):
        name = escape(str(item.get("name", "Товар")))
        weight = escape(str(item.get("weight", "")))
        price = escape(str(item.get("price", "")))
        quantity = int(item.get("quantity", 1) or 1)
        quantity_text = f" × {quantity}" if quantity > 1 else ""
        lines.append(f"{index}. {name}{quantity_text}")
        lines.append(f"   {weight} · <b>{price}</b>")

    lines.extend(["", f"<b>Итого: {escape(str(order.get('total', '0')))} руб.</b>"])
    return "\n".join(lines)


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

    async def _delivery_targets(self) -> list[ManagerRecipient]:
        targets: dict[int, ManagerRecipient] = {
            recipient.chat_id: recipient
            for recipient in self._recipients
            if recipient.enabled
        }
        verified_staff = await self._access_storage.get_all_verified_staff()
        for staff in verified_staff:
            try:
                chat_id = int(staff["user_id"])
            except (KeyError, TypeError, ValueError):
                continue
            targets.setdefault(
                chat_id,
                ManagerRecipient(
                    chat_id=chat_id,
                    name=str(staff.get("first_name") or ""),
                    username=str(staff.get("username") or ""),
                    enabled=True,
                    role="verified_staff",
                ),
            )
        return list(targets.values())

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
    ) -> dict[str, object]:
        recipients = await self._delivery_targets()

        delivery_bot = self._manager_bot or bot
        user_id = getattr(telegram_user, "id", None) if telegram_user is not None else None
        now = datetime.now(MOSCOW_TZ)
        order_number = f"MS-{now.strftime('%Y%m%d-%H%M')}-{user_id or 'guest'}"
        order = await self._access_storage.store_order_record(
            order_number=order_number,
            customer=customer,
            telegram_user=telegram_user,
            items=items,
            total=total,
        )
        text = format_order_message(order)
        reply_markup = order_status_keyboard(order)

        if not recipients:
            return order

        for recipient in recipients:
            if recipient.role != "verified_staff" and not await self._access_storage.is_verified(recipient.chat_id):
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
                await delivery_bot.send_message(
                    chat_id=recipient.chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
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
        return order
