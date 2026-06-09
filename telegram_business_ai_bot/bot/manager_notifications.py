from __future__ import annotations

import logging
from html import escape
from typing import Iterable

from aiogram import Bot

DEFAULT_MANAGER_CHAT_IDS = [5467423100]


class ManagerNotifier:
    def __init__(self, manager_chat_ids: Iterable[int] | None = None) -> None:
        self._manager_chat_ids = [int(chat_id) for chat_id in (manager_chat_ids or DEFAULT_MANAGER_CHAT_IDS)]

    @property
    def manager_chat_ids(self) -> list[int]:
        return list(self._manager_chat_ids)

    async def send_order_notification(
        self,
        bot: Bot,
        *,
        customer: dict[str, object] | None,
        telegram_user: object | None,
        items: list[dict[str, object]],
        total: object,
    ) -> None:
        if not self._manager_chat_ids:
            return

        lines = ["<b>Новый заказ из Mini App</b>", ""]

        username = None
        first_name = None
        user_id = None
        if telegram_user is not None:
            username = getattr(telegram_user, 'username', None)
            first_name = getattr(telegram_user, 'first_name', None)
            user_id = getattr(telegram_user, 'id', None)

        if customer:
            username = customer.get('username') or username
            first_name = customer.get('first_name') or first_name

        display_name = first_name or username or 'без имени'
        lines.append(f"Клиент: <b>{escape(str(display_name))}</b>")
        lines.append(f"Telegram: @{escape(str(username or 'не указан'))}")
        if user_id is not None:
            lines.append(f"User ID: <code>{escape(str(user_id))}</code>")
        lines.append(f"Телефон: <b>{escape(str((customer or {}).get('phone') or 'не указан'))}</b>")
        lines.append("")
        lines.append("<b>Состав заказа</b>")

        for index, item in enumerate(items, start=1):
            name = escape(str(item.get('name', 'Товар')))
            weight = escape(str(item.get('weight', '')))
            price = escape(str(item.get('price', '')))
            lines.append(f"{index}. {name}")
            lines.append(f"   {weight} · <b>{price}</b>")

        lines.extend(["", f"<b>Итого: {escape(str(total))} руб.</b>"])
        text = "\n".join(lines)

        for chat_id in self._manager_chat_ids:
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            except Exception:  # noqa: BLE001
                logging.exception('Failed to send manager notification to chat_id=%s', chat_id)
