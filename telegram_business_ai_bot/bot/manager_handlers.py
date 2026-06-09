from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.manager_access import ManagerAccessStorage
from bot.manager_notifications import ManagerNotifier


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ManagerAccessFlow(StatesGroup):
    waiting_for_code = State()


def create_manager_router(
    *,
    access_storage: ManagerAccessStorage,
    manager_notifier: ManagerNotifier,
    access_code: str,
) -> Router:
    router = Router()

    async def require_verified(message: Message) -> bool:
        if not message.from_user:
            return False
        if not manager_notifier.is_allowed_chat(message.from_user.id):
            await message.answer(
                "Этот аккаунт не входит в список сотрудников для бота заказов."
            )
            return False
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user, event="session_resume")
            return True
        await message.answer("Введите код доступа для входа в бот заказов.")
        await access_storage.log_access_event(message.from_user, "code_requested")
        return False

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if not manager_notifier.is_allowed_chat(message.from_user.id):
            await access_storage.log_access_event(message.from_user, "blocked_not_in_allowlist")
            await message.answer(
                "Этот аккаунт не входит в список сотрудников для бота заказов."
            )
            return
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user)
            await state.clear()
            await message.answer(
                "<b>Доступ подтвержден</b>\n\n"
                "Заказы будут приходить в этот бот.\n"
                "Команда <code>/today</code> покажет заказы за сегодня.",
                parse_mode="HTML",
            )
            return

        await state.set_state(ManagerAccessFlow.waiting_for_code)
        await access_storage.log_access_event(message.from_user, "code_prompt_shown")
        await message.answer("Введите код доступа для входа в бот заказов.")

    @router.message(ManagerAccessFlow.waiting_for_code)
    async def check_code(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.text:
            return
        if not manager_notifier.is_allowed_chat(message.from_user.id):
            await access_storage.log_access_event(message.from_user, "blocked_not_in_allowlist")
            await state.clear()
            await message.answer(
                "Этот аккаунт не входит в список сотрудников для бота заказов."
            )
            return

        if message.text.strip() != access_code:
            await access_storage.log_access_event(message.from_user, "code_invalid")
            await message.answer("Код неверный. Попробуйте еще раз.")
            return

        record = await access_storage.verify_user(message.from_user)
        await state.clear()
        await message.answer(
            "<b>Доступ открыт</b>\n\n"
            f"Сотрудник: <b>{escape(str(record.get('first_name') or record.get('username') or 'без имени'))}</b>\n"
            f"Смена: <b>{escape(str(record.get('shift')))}</b>\n\n"
            "Теперь заказы будут приходить в этот бот. "
            "Для просмотра заказов за сегодня используйте <code>/today</code>.",
            parse_mode="HTML",
        )

    @router.message(Command("today"))
    async def show_today(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified(message):
            return
        orders = await access_storage.get_orders_for_date(datetime.now(MOSCOW_TZ).date())
        if not orders:
            await message.answer("За сегодня заказов пока нет.")
            return

        lines = ["<b>Заказы за сегодня</b>", ""]
        for index, order in enumerate(orders[-10:], start=max(len(orders) - 9, 1)):
            customer = order.get("customer", {})
            customer_name = (
                customer.get("first_name")
                or customer.get("username")
                or "без имени"
            )
            lines.append(
                f"{index}. <b>{escape(str(order.get('order_number', '-')))}</b> · "
                f"{escape(str(order.get('total', '0')))} руб."
            )
            lines.append(f"   Клиент: {escape(str(customer_name))}")
        await message.answer("\n".join(lines), parse_mode="HTML")

    @router.message(Command("whoami"))
    async def whoami(message: Message) -> None:
        if not message.from_user:
            return
        if not await require_verified(message):
            return
        record = await access_storage.get_verified_staff(message.from_user.id)
        if not record:
            await message.answer("Данные сотрудника не найдены.")
            return
        await message.answer(
            "<b>Профиль сотрудника</b>\n\n"
            f"Telegram: @{escape(str(record.get('username') or 'не указан'))}\n"
            f"Смена: <b>{escape(str(record.get('shift') or '-'))}</b>\n"
            f"Последний вход: <code>{escape(str(record.get('last_seen_at') or '-'))}</code>",
            parse_mode="HTML",
        )

    @router.message(F.text)
    async def fallback(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user, event="message")
            await message.answer(
                "Используйте <code>/today</code>, чтобы посмотреть заказы за сегодня.",
                parse_mode="HTML",
            )
            return
        await state.set_state(ManagerAccessFlow.waiting_for_code)
        await access_storage.log_access_event(message.from_user, "code_prompt_shown")
        await message.answer("Введите код доступа для входа в бот заказов.")

    return router
