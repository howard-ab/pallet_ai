from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


CUSTOMER_NOTIFICATION_STATUSES = {"in_delivery", "delivered", "Cancelled"}


def _customer_chat_id(order: dict[str, object]) -> int | None:
    customer = order.get("customer") or {}
    if not isinstance(customer, dict):
        return None
    try:
        return int(customer["user_id"])
    except (KeyError, TypeError, ValueError):
        return None


def _channel_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("@"):
        return f"https://t.me/{value[1:]}"
    if value.startswith("t.me/"):
        return f"https://{value}"
    if value.startswith(("https://", "http://")):
        return value
    return ""


def format_customer_status_message(
    order: dict[str, object],
    status: str,
    *,
    channel_url: str = "",
) -> str:
    order_number = escape(str(order.get("order_number") or "-"))

    if status == "in_delivery":
        return (
            "<b>🚚 Ваш заказ в доставке</b>\n\n"
            f"Номер заказа: <code>{order_number}</code>\n\n"
            "Курьер уже в пути. Постараемся доставить заказ в ближайшее время. "
            "Пожалуйста, оставайтесь на связи, чтобы курьер мог связаться с вами."
        )
    
    if status == "Cancelled":
        return (
            "<b>Ваш заказ отменён</b>\n\n"
            f"Номер заказа: <code>{order_number}</code>\n\n"
            "Свяжитесь с менеджером для уточнения деталей, если заказ был отменён не Вами. "
        )

    if status == "delivered":
        text = (
            "<b>✅ Ваш заказ доставлен</b>\n\n"
            f"Номер заказа: <code>{order_number}</code>\n\n"
            "Спасибо, что выбрали «Мир Сухофруктов»! "
            "Будем рады видеть вас снова."
        )
        normalized_channel_url = _channel_url(channel_url)
        if normalized_channel_url:
            safe_url = escape(normalized_channel_url, quote=True)
            text += (
                "\n\nПодписывайтесь на наш канал, чтобы следить за акциями, "
                f"новинками и специальными предложениями: <a href=\"{safe_url}\">перейти в канал</a>."
            )
        return text

    raise ValueError(f"Unsupported customer notification status: {status}")


def channel_keyboard(channel_url: str) -> InlineKeyboardMarkup | None:
    normalized_channel_url = _channel_url(channel_url)
    if not normalized_channel_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=normalized_channel_url)]
        ]
    )


async def notify_customer_about_status(
    bot: Bot,
    *,
    order: dict[str, object],
    status: str,
    channel_url: str = "",
) -> bool:
    if status not in CUSTOMER_NOTIFICATION_STATUSES:
        return False

    chat_id = _customer_chat_id(order)
    if chat_id is None:
        logging.warning(
            "Cannot notify customer about order status: missing user_id order_number=%s status=%s",
            order.get("order_number"),
            status,
        )
        return False

    for attempt in range(1, 4):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=format_customer_status_message(order, status, channel_url=channel_url),
                parse_mode="HTML",
                reply_markup=channel_keyboard(channel_url) if status == "delivered" else None,
            )
            break
        except TelegramNetworkError:
            logging.warning(
                "Customer status notification network error attempt=%s/3 chat_id=%s order_number=%s status=%s",
                attempt,
                chat_id,
                order.get("order_number"),
                status,
            )
            if attempt == 3:
                return False
            await asyncio.sleep(attempt)
        except TelegramAPIError:
            logging.exception(
                "Telegram rejected customer status notification chat_id=%s order_number=%s status=%s",
                chat_id,
                order.get("order_number"),
                status,
            )
            return False

    logging.info(
        "Customer status notification sent chat_id=%s order_number=%s status=%s",
        chat_id,
        order.get("order_number"),
        status,
    )
    return True
