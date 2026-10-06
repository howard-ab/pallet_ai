from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
import re
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from bot.catalog_admin import (
    CatalogAdminStorage,
    catalog_admin_edit_keyboard,
    catalog_admin_product_keyboard,
    catalog_admin_root_keyboard,
    catalog_admin_subcategory_keyboard,
    format_edit_prompt,
    format_product_admin_card,
    normalize_price,
    product_revision,
)
from bot.manager_access import ManagerAccessStorage
from bot.customer_notifications import (
    CUSTOMER_NOTIFICATION_STATUSES,
    notify_customer_about_status,
)
from bot.keyboards import (
    MANAGER_CATALOG_ADMIN_BUTTON,
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
    order_list_keyboard,
)
from bot.manager_notifications import (
    STATUS_LABELS,
    format_order_message,
    order_cancel_confirmation_keyboard,
    order_status_keyboard,
)


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ManagerAccessFlow(StatesGroup):
    waiting_for_code = State()
    waiting_for_order_search = State()
    waiting_for_date = State()
    waiting_for_catalog_value = State()
    waiting_for_new_product = State()
    waiting_for_section_name = State()


def _format_datetime(raw: object) -> str:
    value = str(raw or "")
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M MSK")
    except ValueError:
        return value


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
        f"В доставку: <b>{status_counts.get('assembled', 0)}</b>",
        f"В доставке: <b>{status_counts.get('in_delivery', 0)}</b>",
        f"Доставленные: <b>{status_counts.get('delivered', 0)}</b>",
        "",
    ]

    for index, order in enumerate(orders[-10:], start=1):
        customer = order.get("customer", {}) or {}
        customer_name = customer.get("first_name") or customer.get("username") or "без имени"
        created_text = _format_datetime(order.get("created_at") or order.get("timestamp"))
        lines.extend(
            [
                f"<b>{index}. Заказ</b>",
                f"Номер: <code>{escape(str(order.get('order_number', '-')))}</code>",
                f"Статус: <b>{escape(STATUS_LABELS.get(str(order.get('status', 'new')), 'Новый'))}</b>",
                f"Оформлен: <b>{escape(created_text)}</b>",
                f"Клиент: {escape(str(customer_name))}",
                f"Сумма: <b>{escape(str(order.get('total', '0')))} руб.</b>",
                "",
            ]
        )
    return "\n".join(lines)


def _status_list_title(status: str) -> str:
    titles = {
        "new": "Новые заказы",
        "assembled": "В доставку",
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


async def _send_order_list(
    message: Message,
    *,
    title: str,
    orders: list[dict[str, object]],
    menu_keyboard,
) -> None:
    await message.answer(
        _summarize_orders(title, orders),
        parse_mode="HTML",
        reply_markup=menu_keyboard,
    )
    keyboard = order_list_keyboard(orders)
    if keyboard is not None:
        await message.answer(
            "Откройте нужный заказ по номеру:",
            reply_markup=keyboard,
        )


def create_manager_router(
    *,
    access_storage: ManagerAccessStorage,
    manager_notifier: object,
    customer_bot: Bot,
    shop_channel_url: str,
    access_code: str,
    catalog_admin_user_ids: tuple[int, ...] = (),
) -> Router:
    router = Router()
    menu_keyboard = manager_menu_keyboard()
    catalog_storage = CatalogAdminStorage()

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

    async def require_catalog_admin_message(message: Message) -> bool:
        if not message.from_user:
            return False
        if not await require_verified_message(message):
            return False
        if catalog_admin_user_ids and message.from_user.id not in catalog_admin_user_ids:
            await message.answer("⛔ У вас нет доступа к управлению каталогом.", reply_markup=menu_keyboard)
            await access_storage.log_access_event(message.from_user, "catalog_admin_denied")
            return False
        return True

    async def require_catalog_admin_callback(callback: CallbackQuery) -> bool:
        if not callback.from_user:
            return False
        if not await require_verified_callback(callback):
            return False
        if catalog_admin_user_ids and callback.from_user.id not in catalog_admin_user_ids:
            await callback.answer("Нет доступа к управлению каталогом.", show_alert=True)
            await access_storage.log_access_event(callback.from_user, "catalog_admin_denied")
            return False
        return True

    async def show_catalog_admin_home(message: Message) -> None:
        catalog = await catalog_storage.read_catalog()
        keyboard = catalog_admin_root_keyboard(catalog)
        await message.answer(
            "<b>🛠 Управление каталогом</b>\n\n"
            "Выберите категорию. Здесь можно создавать, переименовывать и удалять категории и подкатегории, добавлять и удалять товары, менять название, цену, описание, вес, страну, фото и скидку.\n\n"
            "Изменения сохраняются в каталог проекта. Публичный сайт GitHub Pages обновляется после публикации.",
            parse_mode="HTML",
            reply_markup=keyboard or menu_keyboard,
        )

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
                "Левый столбец кнопок — для сборки, правый — для доставки.\n\n"
                "Команды:\n"
                "<code>/new</code> — новые заказы\n"
                "<code>/ready</code> — передать в доставку\n"
                "<code>/delivery</code> — заказы в доставке\n"
                "<code>/done</code> — доставленные\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/yesterday</code> — заказы за вчера\n"
                "<code>/date 10.06.2026</code> — заказы по дате\n"
                "<code>/find MS-...</code> — поиск по номеру заказа\n"
                "<code>/whoami</code> — профиль сотрудника\n"
                "<code>/catalog_admin</code> — управление каталогом",
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
            "Левый столбец кнопок — для сборки, правый — для доставки.\n\n"
            "Команды:\n"
            "<code>/new</code> — новые заказы\n"
            "<code>/ready</code> — передать в доставку\n"
            "<code>/delivery</code> — заказы в доставке\n"
            "<code>/done</code> — доставленные\n"
            "<code>/today</code> — заказы за сегодня\n"
            "<code>/yesterday</code> — заказы за вчера\n"
            "<code>/date 10.06.2026</code> — заказы по дате\n"
            "<code>/find MS-...</code> — поиск по номеру заказа\n"
            "<code>/catalog_admin</code> — управление каталогом",
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
        await _send_order_list(
            message,
            title=_status_list_title(status),
            orders=orders,
            menu_keyboard=menu_keyboard,
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
        await _send_order_list(
            message,
            title="Заказы за сегодня",
            orders=orders,
            menu_keyboard=menu_keyboard,
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
        await _send_order_list(
            message,
            title=f"Заказы за {target_date.strftime('%d.%m.%Y')}",
            orders=orders,
            menu_keyboard=menu_keyboard,
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
        await _send_order_list(
            message,
            title=f"Заказы за {parsed.strftime('%d.%m.%Y')}",
            orders=orders,
            menu_keyboard=menu_keyboard,
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
                "Укажите номер заказа или его префикс.\nПример: <code>/find MS-20260613-1819</code>",
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
            "Введите номер заказа или его начало.\nПример: <code>MS-20260613-1819</code>",
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
        await _send_order_list(
            message,
            title=f"Заказы за {parsed.strftime('%d.%m.%Y')}",
            orders=orders,
            menu_keyboard=menu_keyboard,
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
            f"ID: <code>{escape(str(record.get('user_id') or message.from_user.id))}</code>\n"
            f"Telegram: @{escape(str(record.get('username') or 'не указан'))}\n"
            f"Смена: <b>{escape(str(record.get('shift') or '-'))}</b>\n"
            f"Последний вход: <code>{escape(str(record.get('last_seen_at_text') or record.get('last_seen_at') or '-'))}</code>\n"
            f"Действий по заказам: <b>{len(actions)}</b>",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    @router.message(Command("catalog_admin"))
    @router.message(F.text == MANAGER_CATALOG_ADMIN_BUTTON)
    async def catalog_admin_home(message: Message, state: FSMContext) -> None:
        if not await require_catalog_admin_message(message):
            return
        await state.clear()
        await show_catalog_admin_home(message)

    @router.callback_query(F.data == "catalog_admin:home")
    async def catalog_admin_home_callback(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        await state.clear()
        catalog = await catalog_storage.read_catalog()
        if callback.message:
            await callback.message.answer(
                "<b>🛠 Управление каталогом</b>\n\nВыберите категорию.",
                parse_mode="HTML",
                reply_markup=catalog_admin_root_keyboard(catalog),
            )
        await callback.answer("Категории")

    @router.callback_query(F.data.startswith("catalog_admin:cat:"))
    async def catalog_admin_category(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        await state.clear()
        parts = (callback.data or "").split(":")
        if len(parts) != 3:
            await callback.answer("Не удалось открыть категорию.", show_alert=True)
            return
        category_index = int(parts[2])
        catalog = await catalog_storage.read_catalog()
        categories = list(catalog.keys())
        if category_index < 0 or category_index >= len(categories):
            await callback.answer("Категория не найдена.", show_alert=True)
            return
        if callback.message:
            await callback.message.answer(
                f"<b>{escape(categories[category_index])}</b>\n\nВыберите подкатегорию.",
                parse_mode="HTML",
                reply_markup=catalog_admin_subcategory_keyboard(catalog, category_index),
            )
        await callback.answer("Категория открыта")

    @router.callback_query(F.data.startswith("catalog_admin:sub:"))
    async def catalog_admin_subcategory(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        await state.clear()
        parts = (callback.data or "").split(":")
        if len(parts) != 4:
            await callback.answer("Не удалось открыть подкатегорию.", show_alert=True)
            return
        category_index = int(parts[2])
        subcategory_index = int(parts[3])
        catalog = await catalog_storage.read_catalog()
        categories = list(catalog.keys())
        if category_index < 0 or category_index >= len(categories):
            await callback.answer("Категория не найдена.", show_alert=True)
            return
        subcategories = list((catalog.get(categories[category_index]) or {}).keys())
        if subcategory_index < 0 or subcategory_index >= len(subcategories):
            await callback.answer("Подкатегория не найдена.", show_alert=True)
            return
        if callback.message:
            await callback.message.answer(
                f"<b>{escape(categories[category_index])} / {escape(subcategories[subcategory_index])}</b>\n\n"
                "Выберите товар.",
                parse_mode="HTML",
                reply_markup=catalog_admin_product_keyboard(catalog, category_index, subcategory_index),
            )
        await callback.answer("Товары открыты")

    @router.callback_query(F.data.startswith("catalog_admin:prod:"))
    async def catalog_admin_product(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        await state.clear()
        parts = (callback.data or "").split(":")
        if len(parts) != 6:
            await callback.answer("Не удалось открыть товар.", show_alert=True)
            return
        found = await catalog_storage.get_product(int(parts[2]), int(parts[3]), int(parts[4]))
        if found is None or product_revision(found[1]) != parts[5]:
            await callback.answer("Товар не найден.", show_alert=True)
            return
        location, product = found
        if callback.message:
            await callback.message.answer(
                format_product_admin_card(location, product),
                parse_mode="HTML",
                reply_markup=catalog_admin_edit_keyboard(location, product),
            )
        await callback.answer("Товар открыт")

    @router.callback_query(F.data.startswith("catalog_admin:section:"))
    async def catalog_admin_section(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 6 or parts[2] not in {"add", "rename", "delete"}:
            await callback.answer("Откройте каталог заново.", show_alert=True)
            return
        try:
            category_index, subcategory_index = int(parts[3]), int(parts[4])
        except ValueError:
            await callback.answer("Некорректный раздел.", show_alert=True)
            return
        catalog = await catalog_storage.read_catalog()
        if product_revision(catalog) != parts[5]:
            await callback.answer("Каталог изменился. Откройте его заново.", show_alert=True)
            return
        await state.clear()
        action = parts[2]
        if action == "delete":
            categories = list(catalog)
            if not 0 <= category_index < len(categories):
                await callback.answer("Категория не найдена.", show_alert=True)
                return
            category = categories[category_index]
            if subcategory_index == -1:
                name = category
                count = sum(len(products) for products in catalog[category].values())
                scope = "категорию"
            else:
                subs = list(catalog[category])
                if not 0 <= subcategory_index < len(subs):
                    await callback.answer("Подкатегория не найдена.", show_alert=True)
                    return
                name = subs[subcategory_index]
                count = len(catalog[category][name])
                scope = "подкатегорию"
            if callback.message:
                await callback.message.answer(
                    f"Удалить {scope} <b>{escape(name)}</b>?\n\nТакже будут удалены товары: <b>{count}</b>. Отменить удаление нельзя.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Да, удалить раздел и товары", callback_data=f"catalog_admin:confirm:{category_index}:{subcategory_index}:{parts[5]}")],
                        [InlineKeyboardButton(text="Отмена", callback_data="catalog_admin:home")],
                    ]),
                )
        else:
            await state.set_state(ManagerAccessFlow.waiting_for_section_name)
            await state.update_data(section_action=action, section_category_index=category_index, section_subcategory_index=subcategory_index, section_revision=parts[5])
            scope = "подкатегории" if (action == "add" and category_index >= 0) or subcategory_index >= 0 else "категории"
            if callback.message:
                await callback.message.answer(f"Введите название {scope} (до 80 символов). Для отмены отправьте /cancel.")
        await callback.answer()

    @router.message(ManagerAccessFlow.waiting_for_section_name)
    async def catalog_admin_section_name(message: Message, state: FSMContext) -> None:
        if not await require_catalog_admin_message(message):
            return
        if message.text == "/cancel":
            await state.clear()
            await show_catalog_admin_home(message)
            return
        data = await state.get_data()
        try:
            await catalog_storage.change_section(data["section_action"], data["section_category_index"], data["section_subcategory_index"], data["section_revision"], (message.text or "").strip())
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("✅ Раздел сохранён.")
        await show_catalog_admin_home(message)

    @router.callback_query(F.data.startswith("catalog_admin:confirm:"))
    async def catalog_admin_section_delete(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 5:
            await callback.answer("Откройте каталог заново.", show_alert=True)
            return
        try:
            catalog = await catalog_storage.change_section("delete", int(parts[2]), int(parts[3]), parts[4])
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await state.clear()
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("✅ Раздел и его товары удалены.", reply_markup=catalog_admin_root_keyboard(catalog))
        await callback.answer()

    @router.callback_query(F.data.startswith("catalog_admin:add:"))
    async def catalog_admin_add(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 4 or not all(part.isdigit() for part in parts[2:]):
            await callback.answer("Откройте каталог заново.", show_alert=True)
            return
        category_index, subcategory_index = map(int, parts[2:])
        catalog = await catalog_storage.read_catalog()
        categories = list(catalog)
        if not 0 <= category_index < len(categories) or not 0 <= subcategory_index < len(catalog[categories[category_index]]):
            await callback.answer("Раздел не найден.", show_alert=True)
            return
        await state.clear()
        await state.set_state(ManagerAccessFlow.waiting_for_new_product)
        await state.update_data(catalog_category_index=category_index, catalog_subcategory_index=subcategory_index, new_product_step="name", new_product={}, new_product_catalog_revision=product_revision(catalog))
        if callback.message:
            await callback.message.answer("Введите название нового товара. Для отмены отправьте /cancel.")
        await callback.answer()

    @router.message(ManagerAccessFlow.waiting_for_new_product)
    async def catalog_admin_create_product(message: Message, state: FSMContext) -> None:
        if not await require_catalog_admin_message(message):
            return
        if message.text == "/cancel":
            await state.clear()
            await show_catalog_admin_home(message)
            return
        value = (message.text or "").strip()
        if not value:
            await message.answer("Пришлите текст или /cancel.")
            return
        data = await state.get_data()
        product = data.get("new_product", {})
        step = data.get("new_product_step", "name")
        if step == "name":
            if len(value) > 200:
                await message.answer("Название должно быть не длиннее 200 символов.")
                return
            product["name"] = value
            await state.update_data(new_product=product, new_product_step="price")
            await message.answer("Введите цену за указанный вес, например 690 или 690 руб.")
            return
        if step == "price":
            if not re.fullmatch(r"\d+(?:[.,]\d{1,2})?(?:\s*руб\.?)?", value) or float(re.search(r"\d+(?:[.,]\d+)?", value)[0].replace(",", ".")) <= 0:
                await message.answer("Введите положительную цену, например 690 руб.")
                return
            product["price"] = normalize_price(value)
            await state.update_data(new_product=product, new_product_step="weight")
            await message.answer("Введите вес, например 1 кг или 500 г.")
            return
        if not re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:кг|г)", value) or float(re.search(r"\d+(?:[.,]\d+)?", value)[0].replace(",", ".")) <= 0:
            await message.answer("Введите положительный вес с единицей: 1 кг или 500 г.")
            return
        product.update(weight=value, description="", origin="уточняется", photo="", photo_url="", promo=False, discount_percent=0)
        saved = await catalog_storage.add_product(int(data["catalog_category_index"]), int(data["catalog_subcategory_index"]), product, expected_catalog_revision=data.get("new_product_catalog_revision"))
        await state.clear()
        if saved is None:
            await message.answer("Раздел изменился. Откройте каталог заново.")
            return
        location, product = saved
        await message.answer("✅ Товар добавлен. Теперь добавьте фото и описание.\n\n" + format_product_admin_card(location, product), parse_mode="HTML", reply_markup=catalog_admin_edit_keyboard(location, product))

    @router.callback_query(F.data.startswith("catalog_admin:delete:"))
    async def catalog_admin_delete_prompt(callback: CallbackQuery) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 6 or not all(part.isdigit() for part in parts[2:5]):
            await callback.answer("Откройте каталог заново.", show_alert=True)
            return
        found = await catalog_storage.get_product(*map(int, parts[2:5]))
        if found is None or product_revision(found[1]) != parts[5]:
            await callback.answer("Товар не найден.", show_alert=True)
            return
        location, product = found
        if callback.message:
            await callback.message.answer(
                f"Удалить товар <b>{escape(str(product.get('name', '')))}</b>?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Да, удалить", callback_data=f"catalog_admin:remove:{location.category_index}:{location.subcategory_index}:{location.product_index}:{product_revision(product)}")],
                    [InlineKeyboardButton(text="Отмена", callback_data=f"catalog_admin:sub:{location.category_index}:{location.subcategory_index}")],
                ]),
            )
        await callback.answer()

    @router.callback_query(F.data.startswith("catalog_admin:remove:"))
    async def catalog_admin_delete(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 6 or not all(part.isdigit() for part in parts[2:5]):
            await callback.answer("Откройте каталог заново.", show_alert=True)
            return
        category_index, subcategory_index, product_index = map(int, parts[2:5])
        deleted = await catalog_storage.delete_product(category_index, subcategory_index, product_index, parts[5])
        if not deleted:
            await callback.answer("Товар изменился или уже удалён. Откройте каталог заново.", show_alert=True)
            return
        await state.clear()
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("✅ Товар удалён.", reply_markup=catalog_admin_product_keyboard(await catalog_storage.read_catalog(), category_index, subcategory_index))
        await callback.answer()

    @router.callback_query(F.data.startswith("catalog_admin:edit:"))
    async def catalog_admin_edit(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_catalog_admin_callback(callback):
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 7:
            await callback.answer("Не удалось открыть редактирование.", show_alert=True)
            return
        category_index = int(parts[2])
        subcategory_index = int(parts[3])
        product_index = int(parts[4])
        revision = parts[5]
        field = parts[6]
        if field not in {"name", "price", "description", "photo", "origin", "weight", "promo", "discount_percent"}:
            await callback.answer("Неизвестное поле.", show_alert=True)
            return
        if field == "promo":
            found = await catalog_storage.get_product(category_index, subcategory_index, product_index)
            if found is None or product_revision(found[1]) != revision:
                await callback.answer("Товар не найден.", show_alert=True)
                return
            _location, product = found
            promo_enabled = bool(product.get("promo")) or int(product.get("discount_percent") or 0) > 0
            updated = await catalog_storage.update_product_field(
                category_index=category_index,
                subcategory_index=subcategory_index,
                product_index=product_index,
                field="promo",
                value=not promo_enabled,
                expected_revision=revision,
            )
            if updated is None:
                await callback.answer("Не удалось обновить акцию.", show_alert=True)
                return
            location, updated_product = updated
            if callback.message:
                await callback.message.answer(
                    format_product_admin_card(location, updated_product),
                    parse_mode="HTML",
                    reply_markup=catalog_admin_edit_keyboard(location, updated_product),
                )
            await callback.answer("Акция обновлена")
            return

        await state.set_state(ManagerAccessFlow.waiting_for_catalog_value)
        await state.update_data(
            catalog_category_index=category_index,
            catalog_subcategory_index=subcategory_index,
            catalog_product_index=product_index,
            catalog_field=field,
            catalog_product_revision=revision,
        )
        if callback.message:
            await callback.message.answer(
                format_edit_prompt(field),
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
        await callback.answer("Введите новое значение")

    @router.message(ManagerAccessFlow.waiting_for_catalog_value)
    async def catalog_admin_save_value(message: Message, state: FSMContext) -> None:
        if not await require_catalog_admin_message(message):
            return
        if message.text == "/cancel":
            await state.clear()
            await show_catalog_admin_home(message)
            return
        data = await state.get_data()
        category_index = int(data.get("catalog_category_index", -1))
        subcategory_index = int(data.get("catalog_subcategory_index", -1))
        product_index = int(data.get("catalog_product_index", -1))
        field = str(data.get("catalog_field") or "")

        if field == "photo" and message.photo:
            saved = await catalog_storage.save_uploaded_photo(
                bot=message.bot,
                file_id=message.photo[-1].file_id,
                category_index=category_index,
                subcategory_index=subcategory_index,
                product_index=product_index,
                expected_revision=data.get("catalog_product_revision"),
            )
        else:
            if not message.text:
                await message.answer("Пришлите текстовое значение или фото.", reply_markup=menu_keyboard)
                return
            value = message.text.strip()
            if not value:
                await message.answer("Значение не должно быть пустым.")
                return
            if field == "discount_percent":
                if not value.isdigit() or not 0 <= int(value) <= 99:
                    await message.answer("Введите целое число от 0 до 99.")
                    return
            if field == "price":
                value = normalize_price(value)
            saved = await catalog_storage.update_product_field(
                category_index=category_index,
                subcategory_index=subcategory_index,
                product_index=product_index,
                field=field,
                value=value,
                expected_revision=data.get("catalog_product_revision"),
            )

        await state.clear()
        if saved is None:
            await message.answer("Не удалось сохранить товар. Попробуйте открыть каталог заново.", reply_markup=menu_keyboard)
            return

        location, product = saved
        await message.answer(
            "✅ Сохранено.\n\n" + format_product_admin_card(location, product),
            parse_mode="HTML",
            reply_markup=catalog_admin_edit_keyboard(location, product),
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
        current_order = await access_storage.get_order(order_number)
        previous_status = str((current_order or {}).get("status", ""))
        order = await access_storage.update_order_status(
            order_number=order_number,
            status=next_status,
            actor=callback.from_user,
        )
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        customer_notified: bool | None = None
        if previous_status != next_status and next_status in CUSTOMER_NOTIFICATION_STATUSES:
            customer_notified = await notify_customer_about_status(
                customer_bot,
                order=order,
                status=next_status,
                channel_url=shop_channel_url,
            )

        try:
            answer_text = f"Статус обновлен: {STATUS_LABELS.get(next_status, next_status)}"
            if customer_notified is True:
                answer_text += ". Клиент уведомлен"
            elif customer_notified is False:
                answer_text += ". Не удалось уведомить клиента"
            await callback.answer(answer_text)
        except TelegramNetworkError:
            pass

        if callback.message:
            try:
                await callback.message.edit_text(
                    format_order_message(order),
                    parse_mode="HTML",
                    reply_markup=order_status_keyboard(order),
                )
            except TelegramBadRequest:
                # The message may be outdated or already changed; the status is still saved.
                pass
            except TelegramNetworkError:
                pass

    @router.callback_query(F.data.startswith("order:view:"))
    async def view_order(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        if not await require_verified_callback(callback):
            return

        parts = (callback.data or "").split(":", 2)
        if len(parts) != 3:
            await callback.answer("Не удалось открыть заказ.", show_alert=True)
            return
        order_number = parts[2]
        order = await access_storage.get_order(order_number)
        if not order:
            await callback.answer("Заказ не найден.", show_alert=True)
            return

        if callback.message:
            await callback.message.answer(
                format_order_message(order),
                parse_mode="HTML",
                reply_markup=order_status_keyboard(order),
            )
        try:
            await callback.answer("Заказ открыт")
        except TelegramNetworkError:
            pass

    @router.callback_query(F.data.startswith("order:cancel_confirm:"))
    async def confirm_cancel_order(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        if not await require_verified_callback(callback):
            return

        parts = (callback.data or "").split(":", 2)
        if len(parts) != 3:
            await callback.answer("Не удалось открыть подтверждение.", show_alert=True)
            return
        order_number = parts[2]
        if callback.message:
            try:
                await callback.message.answer(
                    f"Подтверждаете отмену заказа <code>{escape(order_number)}</code>?",
                    parse_mode="HTML",
                    reply_markup=order_cancel_confirmation_keyboard(order_number),
                )
            except TelegramNetworkError:
                pass
        try:
            await callback.answer("Нужно подтверждение отмены")
        except TelegramNetworkError:
            pass

    @router.callback_query(F.data.startswith("order:cancel_abort:"))
    async def abort_cancel_order(callback: CallbackQuery) -> None:
        try:
            await callback.answer("Отмена заказа не выполнена")
        except TelegramNetworkError:
            pass

            try:
                await callback.message.answer(
                    f"✅ Заказ <code>{escape(str(order_number))}</code> переведен в статус "
                    f"<b>{escape(STATUS_LABELS.get(next_status, next_status))}</b>.\n"
                    f"Время: <code>{escape(_format_datetime(order.get('updated_at')))}</code>",
                    parse_mode="HTML",
                    reply_markup=menu_keyboard,
                )
            except TelegramNetworkError:
                pass

    @router.message(F.text)
    async def fallback(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if await access_storage.is_verified(message.from_user.id):
            await access_storage.touch_session(message.from_user, event="message")
            await message.answer(
                "Команды:\n"
                "<code>/new</code> — новые заказы\n"
                "<code>/ready</code> — передать в доставку\n"
                "<code>/delivery</code> — заказы в доставке\n"
                "<code>/done</code> — доставленные\n"
                "<code>/today</code> — заказы за сегодня\n"
                "<code>/yesterday</code> — заказы за вчера\n"
                "<code>/date 10.06.2026</code> — заказы по дате\n"
                "<code>/find MS-...</code> — поиск по номеру заказа\n"
                "<code>/whoami</code> — профиль сотрудника\n"
                "<code>/catalog_admin</code> — управление каталогом",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return
        await state.set_state(ManagerAccessFlow.waiting_for_code)
        await access_storage.log_access_event(message.from_user, "code_prompt_shown")
        await message.answer("Введите код доступа для входа в бот заказов.", reply_markup=menu_keyboard)

    return router
