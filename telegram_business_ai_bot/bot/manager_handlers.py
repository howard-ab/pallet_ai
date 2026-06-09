from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.manager_access import ManagerAccessStorage
from bot.keyboards import (
    MANAGER_FIND_BUTTON,
    MANAGER_PROFILE_BUTTON,
    MANAGER_TODAY_BUTTON,
    manager_menu_keyboard,
)
from bot.manager_notifications import STATUS_LABELS, format_order_message, order_status_keyboard


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ManagerAccessFlow(StatesGroup):
    waiting_for_code = State()


def _summarize_orders(title: str, orders: list[dict[str, object]]) -> str:
    status_counts = {status: 0 for status in STATUS_LABELS}
    for order in orders:
        status = str(order.get("status", "new"))
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [f"<b>{title}</b>", ""]
    lines.append(
        " · ".join(
            [
                f"Новые: <b>{status_counts.get('new', 0)}</b>",
                f"Собранные: <b>{status_counts.get('assembled', 0)}</b>",
                f"В доставке: <b>{status_counts.get('in_delivery', 0)}</b>",
                f"Доставленные: <b>{status_counts.get('delivered', 0)}</b>",
            ]
        )
    )
    lines.append("")

    for order in orders[-10:]:
        customer = order.get("customer", {}) or {}
        customer_name = customer.get("first_name") or customer.get("username") or "без имени"
        lines.append(
            f"• <code>{escape(str(order.get('order_number', '-')))}</code> "
            f"· <b>{escape(STATUS_LABELS.get(str(order.get('status', 'new')), 'Новый'))}</b> "
            f"· {escape(str(order.get('total', '0')))} руб."
        )
        lines.append(f"  Клиент: {escape(str(customer_name))}")
    return "\n".join(lines)


def create_manager_router(
    *,
    access_storage: ManagerAccessStorage,
    manager_notifier: object,
    access_code: str,
) -> Router:
    router = Router()
    menu_keyboard = manager_menu_keyboard()

    async def require_verified_message(message: Message) -> bool:
        if not message.from_user:
            return False
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user, event="session_resume")
            return True
        await message.answer("Введите код доступа для входа в бот заказов.")
        await access_storage.log_access_event(message.from_user, "code_requested")
        return False

    async def require_verified_callback(callback: CallbackQuery) -> bool:
        if not callback.from_user:
            return False
        if await access_storage.is_verified(callback.from_user.id):
            await access_storage.touch_session(callback.from_user, event="callback")
            return True
        await callback.answer("Сначала войдите по коду доступа.", show_alert=True)
        await access_storage.log_access_event(callback.from_user, "code_requested")
        return False

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user)
            await state.clear()
            await message.answer(
                "<b>Доступ подтвержден</b>\n\n"
                "Заказы будут приходить в этот бот.\n"
                "Команды:\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/find MS-...</code> — поиск по номеру заказа\n"
                "<code>/whoami</code> — профиль сотрудника",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return

        await state.set_state(ManagerAccessFlow.waiting_for_code)
        await access_storage.log_access_event(message.from_user, "code_prompt_shown")
        await message.answer("Введите код доступа для входа в бот заказов.", reply_markup=menu_keyboard)

    @router.message(ManagerAccessFlow.waiting_for_code)
    async def check_code(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.text:
            return
        if message.text.strip() != access_code:
            await access_storage.log_access_event(message.from_user, "code_invalid")
            await message.answer("Код неверный. Попробуйте еще раз.", reply_markup=menu_keyboard)
            return

        record = await access_storage.verify_user(message.from_user)
        await state.clear()
        await message.answer(
            "<b>Доступ открыт</b>\n\n"
            f"Сотрудник: <b>{escape(str(record.get('first_name') or record.get('username') or 'без имени'))}</b>\n"
            f"Смена: <b>{escape(str(record.get('shift')))}</b>\n\n"
            "Теперь заказы будут приходить в этот бот.\n"
            "Команды:\n"
            "<code>/today</code> — заказы за сегодня\n"
            "<code>/find MS-...</code> — поиск по номеру заказа",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("today"))
    @router.message(F.text == MANAGER_TODAY_BUTTON)
    async def show_today(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        orders = await access_storage.get_orders_for_date(datetime.now(MOSCOW_TZ).date())
        if not orders:
            await message.answer("За сегодня заказов пока нет.", reply_markup=menu_keyboard)
            return
        await message.answer(
            _summarize_orders("Заказы за сегодня", orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("find"))
    @router.message(F.text == MANAGER_FIND_BUTTON)
    async def find_order(message: Message, command: CommandObject | None = None) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        query = ((command.args if command else None) or "").strip()
        if not query:
            await message.answer(
                "Укажите номер заказа после команды.\nПример: <code>/find MS-20260610-1200-5467423100</code>",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        orders = await access_storage.search_orders(query)
        if not orders:
            await message.answer("По этому номеру заказ не найден.", reply_markup=menu_keyboard)
            return
        for order in orders[:3]:
            await message.answer(
                format_order_message(order),
                parse_mode="HTML",
                reply_markup=order_status_keyboard(order),
            )

    @router.message(Command("whoami"))
    @router.message(F.text == MANAGER_PROFILE_BUTTON)
    async def whoami(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        record = await access_storage.get_verified_staff(message.from_user.id)
        if not record:
            await message.answer("Данные сотрудника не найдены.", reply_markup=menu_keyboard)
            return
        actions = await access_storage.get_staff_actions(message.from_user.id)
        await message.answer(
            "<b>Профиль сотрудника</b>\n\n"
            f"Telegram: @{escape(str(record.get('username') or 'не указан'))}\n"
            f"Смена: <b>{escape(str(record.get('shift') or '-'))}</b>\n"
            f"Последний вход: <code>{escape(str(record.get('last_seen_at') or '-'))}</code>\n"
            f"Действий по заказам: <b>{len(actions)}</b>",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.callback_query(F.data.startswith("order:status:"))
    async def set_order_status(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        if not await require_verified_callback(callback):
            return

        parts = (callback.data or "").split(":", 3)
        if len(parts) != 4:
            await callback.answer("Не удалось обработать заказ.", show_alert=True)
            return
        next_status = parts[2]
        order_number = parts[3]
        order = await access_storage.update_order_status(
            order_number=order_number,
            status=next_status,
            actor=callback.from_user,
        )
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        if callback.message:
            await callback.message.edit_text(
                format_order_message(order),
                parse_mode="HTML",
                reply_markup=order_status_keyboard(order),
            )
        await callback.answer(f"Статус обновлен: {STATUS_LABELS.get(next_status, next_status)}")

    @router.message(F.text)
    async def fallback(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user, event="message")
            await message.answer(
                "Команды:\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/find MS-...</code> — поиск по номеру заказа\n"
                "<code>/whoami</code> — профиль сотрудника",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        await state.set_state(ManagerAccessFlow.waiting_for_code)
        await access_storage.log_access_event(message.from_user, "code_prompt_shown")
        await message.answer("Введите код доступа для входа в бот заказов.", reply_markup=menu_keyboard)

    return router
