from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.manager_access import ManagerAccessStorage
from bot.keyboards import (
    MANAGER_DATE_BUTTON,
    MANAGER_DONE_BUTTON,
    MANAGER_FIND_BUTTON,
    MANAGER_IN_DELIVERY_BUTTON,
    MANAGER_NEW_BUTTON,
    MANAGER_PROFILE_BUTTON,
    MANAGER_READY_BUTTON,
    MANAGER_TODAY_BUTTON,
    MANAGER_YESTERDAY_BUTTON,
    manager_menu_keyboard,
)
from bot.manager_notifications import STATUS_LABELS, format_order_message, order_status_keyboard


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ManagerAccessFlow(StatesGroup):
    waiting_for_code = State()
    waiting_for_order_search = State()
    waiting_for_date = State()


def _summarize_orders(title: str, orders: list[dict[str, object]]) -> str:
    status_counts = {status: 0 for status in STATUS_LABELS}
    for order in orders:
        status = str(order.get("status", "new"))
        status_counts[status] = status_counts.get(status, 0) + 1
    active_count = (
        status_counts.get("new", 0)
        + status_counts.get("assembled", 0)
        + status_counts.get("in_delivery", 0)
    )

    lines = [
        f"<b>{title}</b>",
        "",
        f"Активные: <b>{active_count}</b>",
        f"Новые: <b>{status_counts.get('new', 0)}</b>",
        f"Готовы к доставке: <b>{status_counts.get('assembled', 0)}</b>",
        f"В доставке: <b>{status_counts.get('in_delivery', 0)}</b>",
        f"Доставленные: <b>{status_counts.get('delivered', 0)}</b>",
        "",
    ]

    for index, order in enumerate(orders[-10:], start=1):
        customer = order.get("customer", {}) or {}
        customer_name = customer.get("first_name") or customer.get("username") or "без имени"
        lines.extend(
            [
                f"<b>{index}. Заказ</b>",
                f"Номер: <code>{escape(str(order.get('order_number', '-')))}</code>",
                f"Статус: <b>{escape(STATUS_LABELS.get(str(order.get('status', 'new')), 'Новый'))}</b>",
                f"Клиент: {escape(str(customer_name))}",
                f"Сумма: <b>{escape(str(order.get('total', '0')))} руб.</b>",
                "",
            ]
        )
    return "\n".join(lines)


def _status_list_title(status: str) -> str:
    titles = {
        "new": "Новые заказы",
        "assembled": "Готовы к доставке",
        "in_delivery": "Заказы в доставке",
        "delivered": "Доставленные заказы",
    }
    return titles.get(status, "Заказы")


def _parse_date_input(raw: str) -> datetime | None:
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


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
                "<b>✅ Доступ подтвержден</b>\n\n"
                "Заказы будут приходить в этот бот.\n"
                "Команды:\n"
                "<code>/new</code> — новые заказы\n"
                "<code>/ready</code> — готовы к доставке\n"
                "<code>/delivery</code> — в доставке\n"
                "<code>/done</code> — доставленные\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/yesterday</code> — заказы за вчера\n"
                "<code>/date 10.06.2026</code> — заказы по дате\n"
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
            "<b>✅ Доступ открыт</b>\n\n"
            f"Сотрудник: <b>{escape(str(record.get('first_name') or record.get('username') or 'без имени'))}</b>\n"
            f"Смена: <b>{escape(str(record.get('shift')))}</b>\n\n"
            "Теперь заказы будут приходить в этот бот.\n"
            "Команды:\n"
            "<code>/new</code> — новые заказы\n"
            "<code>/ready</code> — готовы к доставке\n"
            "<code>/delivery</code> — в доставке\n"
            "<code>/done</code> — доставленные\n"
            "<code>/today</code> — заказы за сегодня\n"
            "<code>/yesterday</code> — заказы за вчера\n"
            "<code>/date 10.06.2026</code> — заказы по дате\n"
            "<code>/find MS-...</code> — поиск по номеру заказа",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    async def show_status_orders(message: Message, status: str) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        orders = await access_storage.get_orders_for_date(datetime.now(MOSCOW_TZ).date(), status=status)
        if not orders:
            await message.answer(
                f"✅ {_status_list_title(status)}: на сегодня пусто.",
                reply_markup=menu_keyboard,
            )
            return
        await message.answer(
            _summarize_orders(_status_list_title(status), orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("new"))
    @router.message(F.text == MANAGER_NEW_BUTTON)
    async def show_new_orders(message: Message) -> None:
        await show_status_orders(message, "new")

    @router.message(Command("ready"))
    @router.message(F.text == MANAGER_READY_BUTTON)
    async def show_ready_orders(message: Message) -> None:
        await show_status_orders(message, "assembled")

    @router.message(Command("delivery"))
    @router.message(F.text == MANAGER_IN_DELIVERY_BUTTON)
    async def show_delivery_orders(message: Message) -> None:
        await show_status_orders(message, "in_delivery")

    @router.message(Command("done"))
    @router.message(F.text == MANAGER_DONE_BUTTON)
    async def show_delivered_orders(message: Message) -> None:
        await show_status_orders(message, "delivered")

    @router.message(Command("today"))
    @router.message(F.text == MANAGER_TODAY_BUTTON)
    async def show_today(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        orders = await access_storage.get_orders_for_date(datetime.now(MOSCOW_TZ).date())
        if not orders:
            await message.answer("✅ За сегодня заказов пока нет.", reply_markup=menu_keyboard)
            return
        await message.answer(
            _summarize_orders("Заказы за сегодня", orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("yesterday"))
    @router.message(F.text == MANAGER_YESTERDAY_BUTTON)
    async def show_yesterday(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        target_date = (datetime.now(MOSCOW_TZ) - timedelta(days=1)).date()
        orders = await access_storage.get_orders_for_date(target_date)
        if not orders:
            await message.answer("✅ За вчера заказов нет.", reply_markup=menu_keyboard)
            return
        await message.answer(
            _summarize_orders(f"Заказы за {target_date.strftime('%d.%m.%Y')}", orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("date"))
    async def show_date_command(message: Message, command: CommandObject) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        raw_date = (command.args or "").strip()
        if not raw_date:
            await message.answer(
                "Укажите дату после команды.\nПример: <code>/date 10.06.2026</code>",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        parsed = _parse_date_input(raw_date)
        if parsed is None:
            await message.answer(
                "Не удалось распознать дату. Используйте формат <code>10.06.2026</code> или <code>2026-06-10</code>.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        orders = await access_storage.get_orders_for_date(parsed.date())
        if not orders:
            await message.answer(
                f"✅ За {parsed.strftime('%d.%m.%Y')} заказов нет.",
                reply_markup=menu_keyboard,
            )
            return
        await message.answer(
            _summarize_orders(f"Заказы за {parsed.strftime('%d.%m.%Y')}", orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(F.text == MANAGER_DATE_BUTTON)
    async def request_date(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        await state.set_state(ManagerAccessFlow.waiting_for_date)
        await message.answer(
            "Введите дату, например <code>10.06.2026</code> или <code>2026-06-10</code>.",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("find"))
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
            await message.answer("✅ По этому номеру заказ не найден.", reply_markup=menu_keyboard)
            return
        for order in orders[:3]:
            await message.answer(
                format_order_message(order),
                parse_mode="HTML",
                reply_markup=order_status_keyboard(order),
            )

    @router.message(F.text == MANAGER_FIND_BUTTON)
    async def request_find_order(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if not await require_verified_message(message):
            return
        await state.set_state(ManagerAccessFlow.waiting_for_order_search)
        await message.answer(
            "Введите номер заказа целиком или его часть.\nПример: <code>MS-20260610</code>",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(ManagerAccessFlow.waiting_for_order_search)
    async def find_order_from_state(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.text:
            return
        if not await require_verified_message(message):
            return
        orders = await access_storage.search_orders(message.text.strip())
        await state.clear()
        if not orders:
            await message.answer("✅ По этому номеру заказ не найден.", reply_markup=menu_keyboard)
            return
        for order in orders[:5]:
            await message.answer(
                format_order_message(order),
                parse_mode="HTML",
                reply_markup=order_status_keyboard(order),
            )

    @router.message(ManagerAccessFlow.waiting_for_date)
    async def show_date_from_state(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.text:
            return
        if not await require_verified_message(message):
            return
        parsed = _parse_date_input(message.text)
        if parsed is None:
            await message.answer(
                "Не удалось распознать дату. Используйте формат <code>10.06.2026</code> или <code>2026-06-10</code>.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        await state.clear()
        orders = await access_storage.get_orders_for_date(parsed.date())
        if not orders:
            await message.answer(
                f"✅ За {parsed.strftime('%d.%m.%Y')} заказов нет.",
                reply_markup=menu_keyboard,
            )
            return
        await message.answer(
            _summarize_orders(f"Заказы за {parsed.strftime('%d.%m.%Y')}", orders),
            parse_mode="HTML",
            reply_markup=menu_keyboard,
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
            await message.answer("✅ Данные сотрудника не найдены.", reply_markup=menu_keyboard)
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
            await callback.message.answer(
                f"✅ Заказ <code>{escape(str(order_number))}</code> переведен в статус "
                f"<b>{escape(STATUS_LABELS.get(next_status, next_status))}</b>.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
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
                "<code>/new</code> — новые заказы\n"
                "<code>/ready</code> — готовы к доставке\n"
                "<code>/delivery</code> — в доставке\n"
                "<code>/done</code> — доставленные\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/yesterday</code> — заказы за вчера\n"
                "<code>/date 10.06.2026</code> — заказы по дате\n"
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
