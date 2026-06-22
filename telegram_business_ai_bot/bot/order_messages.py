from __future__ import annotations

from html import escape


MANAGER_LABEL = "Менеджер"
MANAGER_PHONE = "+7-928-199-38-00"


def format_customer_order_confirmation(
    order: dict[str, object],
    *,
    channel_promo: str = "",
) -> str:
    text = (
        "<b>✅ Заказ принят</b> ✨\n\n"
        f"Номер заказа: <code>{escape(str(order.get('order_number', '-')))}</code>\n"
        f"Оформлен: <b>{escape(str(order.get('created_at_text') or order.get('timestamp') or '-'))}</b>\n\n"
        "Мы передали его в отдел заказов.\n"
        "Доставка осуществляется в течение суток.\n"
        "Если у вас срочный заказ, пожалуйста, свяжитесь с менеджером.\n"
        f"{MANAGER_LABEL}: <b>{escape(MANAGER_PHONE)}</b>\n\n"
        "Если понадобится, вы можете сразу связаться с менеджером по этому номеру."
    )
    if channel_promo:
        text += f"\n\n{channel_promo}"
    return text
