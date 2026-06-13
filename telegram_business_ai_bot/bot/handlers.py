import logging
from html import escape
import json
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.ai_service import FALLBACK_MESSAGE, HuggingFaceAIService
from bot.cart import cart_total, make_cart_item
from bot.catalog import (
    find_category_by_subcategory,
    get_categories,
    get_product_by_id,
    get_product_id,
    get_products,
)
from bot.customers import CustomerStorage, is_valid_phone
from bot.customers import PendingOrderStorage, is_valid_rostov_address
from bot.manager_notifications import ManagerNotifier
from bot.keyboards import (
    ABOUT_BUTTON,
    ASK_AI_BUTTON,
    CART_BUTTON,
    CATALOG_BUTTON,
    CONTACT_BUTTON,
    HOME_BUTTON,
    OLD_BACK_BUTTON,
    OLD_SHOP_BUTTON,
    PROFILE_BUTTON,
    SHOP_BUTTON,
    back_to_menu_keyboard,
    build_main_menu_keyboard,
    catalog_keyboard,
    cart_actions_keyboard,
    contact_request_keyboard,
    address_confirmation_keyboard,
    #order_cta_inline_keyboard,
    product_actions_keyboard,
    subcategory_keyboard,
)
from bot.order_messages import format_customer_order_confirmation
from bot.storage import SessionStorage


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WELCOME_TEXT = (
    "<b>Вас приветствует Мир Сухофруктов!</b>\n"
    "----------------------------------------\n\n"
    "Мы - сеть магазинов продукций высокого качества, такие как <b>сухофрукты</b>, <b>орехи</b>, <b>финики</b>, "
    "<b>сладости</b> и подарочные наборы для дома, офиса и подарков и еще многое другое."
)

WELCOME_ACTIONS_TEXT = (
    "<b>Что можно сделать в боте:</b>\n\n"
    "• <b>Заказать</b>\n"
    "Открыть витрину, собрать корзину и оформить заказ.\n\n"
    "• <b>Каталог</b>\n"
    "Посмотреть товары прямо в боте по категориям.\n\n"
    "• <b>Задать вопрос Искусственному Интеллекту</b>\n"
    "Уточнить состав, вкус, отличия и полезные свойства продуктов, или попросить рекомендовать Вам что-то из каталога.\n\n"
    "• <b>Корзина</b>\n"
    "Проверить выбранные позиции перед оформлением.\n\n"
    "• <b>Связаться с менеджером</b>\n"
    "Быстро задать вопрос по заказу и доставке.\n\n"
    "• <b>О магазине</b>\n"
    "Посмотреть адреса и контакты.\n\n"
    "👇 Чтобы оформить заказ, нажмите кнопку <b>Заказать</b> в нижнем меню."
)

ABOUT_TEXT = (
    "<b>О нас</b>\n\n"
    "Мир Сухофруктов — торговая сеть качественных сухофруктов, орехов, кураги, "
    "изюма, фиников, сладостей и подарочных наборов.\n\n"
    "<b>Адреса магазинов:</b>\n"
    "Ростов-на-Дону, ул. Пойменная, 1\n"
    "Проспект Стачки, 25\n"
    "Коммунистический проспект, 32\n"
    "Сельмаш, 2\n"
    "Таганрогская, 151\n\n"
    "<b>Менеджер:</b> +7-928-199-38-00\n\n"
    "AI-ассистент помогает быстро выбрать товары, ответить на вопросы и подготовить заказ."
)

CONTACT_TEXT = (
    "<b>Менеджер</b>\n\n"
    "Для оформления заказа или уточнения деталей свяжитесь с менеджером:\n\n"
    "+7-928-199-38-00\n\n"
    "<b>Адреса магазинов:</b>\n"
    "Ростов-на-Дону, ул. Пойменная, 1\n"
    "Проспект Стачки, 25\n"
    "Коммунистический проспект, 32\n"
    "Сельмаш, 2\n"
    "Таганрогская, 151"
)

MAIN_MENU_TEXT = (
    "<b>Главное меню</b> ✨\n\n"
    "• <b>Заказать</b> — открыть витрину\n"
    "• <b>Каталог</b> — посмотреть товары в боте\n"
    "• <b>Задать вопрос ИИ</b> — уточнить состав и свойства\n"
    "• <b>Корзина</b> — проверить выбранные позиции\n"
    "• <b>Связаться с менеджером</b> — быстро написать по заказу\n\n"
    "👇 Нажмите кнопку <b>Заказать</b> в нижнем меню 🛍."
)


class UserFlow(StatesGroup):
    waiting_for_ai_question = State()
    waiting_for_manual_phone = State()
    waiting_for_address = State()


async def answer_and_log(
    message: Message,
    storage: SessionStorage,
    text: str,
    **kwargs: object,
) -> None:
    await message.answer(text, **kwargs)
    await storage.log_bot_text(message, text)


def product_caption(index: int, product: dict[str, str]) -> str:
    return "\n".join(
        [
            f"<b>{index}. {escape(product['name'])}</b>",
            "",
            escape(product["description"]),
            "",
            f"<b>{escape(product['price'])}</b>",
            f"Вес: {escape(product['weight'])}",
            f"Происхождение: {escape(product['origin'])}",
        ]
    )


def registration_text(message: Message) -> str:
    username = message.from_user.username if message.from_user else None
    username_text = f"@{username}" if username else "не указан в Telegram"
    return (
        "<b>Мир Сухофруктов</b> ✨\n\n"
        "<b>Перед покупками сохраним контакты</b>\n\n"
        f"Telegram username: <b>{escape(username_text)}</b>\n"
        "Телефон: будет получен после нажатия кнопки ниже.\n\n"
        "Контакты нужны менеджеру, чтобы подтвердить заказ. "
        "Если номер неактуален, его можно ввести вручную."
    )


def format_moscow_datetime(raw: object) -> str:
    value = str(raw or "")
    if not value:
        return "-"
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        return datetime.fromisoformat(value).astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M MSK")
    except ValueError:
        return value


def build_welcome_actions_text(shop_webapp_url: str) -> str:
    # text = WELCOME_ACTIONS_TEXT
    # if shop_webapp_url:
    #     text += (
    #         "\n\n"
    #         f"🔗 <a href=\"{escape(shop_webapp_url)}\">Открыть витрину в один тап</a>"
    #     )
    return WELCOME_ACTIONS_TEXT


def profile_text(customer: dict[str, object]) -> str:
    username = customer.get("username") or "не указан"
    phone = customer.get("phone") or "не указан"
    address = customer.get("address") or "не указан"
    return (
        "<b>Ваши контакты</b>\n\n"
        f"Telegram: @{escape(str(username))}\n"
        f"Телефон: {escape(str(phone))}\n"
        f"Адрес: {escape(str(address))}\n\n"
        "Если данные изменились, поделитесь контактом снова или отправьте новый адрес."
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

async def show_cart(
    message: Message,
    state: FSMContext,
    storage: SessionStorage,
) -> None:
    data = await state.get_data()
    items = data.get("cart", [])
    if not items:
        await answer_and_log(
            message,
            storage,
            "<b>Корзина</b>\n\nПока пусто. Откройте витрину или каталог и добавьте товары.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    lines = ["<b>Корзина</b>", ""]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {escape(item['name'])}")
        lines.append(f"   {escape(item['weight'])} · <b>{escape(item['price'])}</b>")
    lines.extend(["", f"<b>Итого: {cart_total(items)} руб.</b>"])
    await answer_and_log(
        message,
        storage,
        "\n".join(lines),
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


def create_router(
    ai_service: HuggingFaceAIService,
    storage: SessionStorage,
    customer_storage: CustomerStorage,
    manager_notifier: ManagerNotifier,
    shop_webapp_url: str = "",
    checkout_api_url: str = "",
) -> Router:
    router = Router()
    menu_keyboard = build_main_menu_keyboard(shop_webapp_url, checkout_api_url)
    pending_orders = PendingOrderStorage()

    async def request_address_for_pending_order(
        message: Message,
        state: FSMContext | None = None,
    ) -> None:
        if state is not None:
            await state.set_state(UserFlow.waiting_for_address)
        await answer_and_log(
            message,
            storage,
            address_request_text(),
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

    async def finalize_pending_order(
        message: Message,
        pending_order: dict[str, object],
        state: FSMContext | None = None,
    ) -> None:
        if not message.from_user:
            return
        customer = await customer_storage.get(message.from_user.id)
        if customer is None or not customer.get("phone"):
            if state is not None:
                await state.clear()
            await answer_and_log(
                message,
                storage,
                "<b>Нужен номер телефона</b>\n\nПоделитесь контактом, затем укажите адрес доставки. После этого мы автоматически завершим заказ.",
                reply_markup=contact_request_keyboard(),
                parse_mode="HTML",
            )
            return
        order = await manager_notifier.send_order_notification(
            message.bot,
            customer=customer,
            telegram_user=message.from_user,
            items=list(pending_order.get("items", [])),
            total=pending_order.get("total", 0),
        )
        await pending_orders.clear(message.from_user.id)
        if state is not None:
            await state.clear()
        await answer_and_log(
            message,
            storage,
            format_customer_order_confirmation(order),
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

    async def begin_order_address_confirmation(
        message: Message,
        *,
        items: list[dict[str, object]],
        total: object,
        state: FSMContext | None = None,
    ) -> None:
        if not message.from_user:
            return
        await pending_orders.set(
            message.from_user.id,
            {
                "items": items,
                "total": total,
                "requested_at": format_moscow_datetime(message.date.isoformat() if getattr(message, "date", None) else ""),
            },
        )
        customer = await customer_storage.get(message.from_user.id)
        if customer is None or not customer.get("phone"):
            if state is not None:
                await state.clear()
            await answer_and_log(
                message,
                storage,
                "<b>Перед оформлением заказа сохраните контакты</b>\n\nПоделитесь номером телефона, затем укажите адрес доставки в Ростове-на-Дону. После этого заказ отправится менеджеру автоматически.",
                reply_markup=contact_request_keyboard(),
                parse_mode="HTML",
            )
            return
        address = (customer or {}).get("address")
        if address:
            if state is not None:
                await state.set_state(UserFlow.waiting_for_address)
            await answer_and_log(
                message,
                storage,
                address_confirmation_text(str(address)),
                reply_markup=address_confirmation_keyboard(),
                parse_mode="HTML",
            )
            return
        await request_address_for_pending_order(message, state)

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        customer = await customer_storage.get(message.from_user.id) if message.from_user else None
        if message.from_user and customer is None:
            await answer_and_log(
                message,
                storage,
                registration_text(message),
                reply_markup=contact_request_keyboard(),
                parse_mode="HTML",
            )
            return
        if customer is not None and not customer.get("address"):
            await state.set_state(UserFlow.waiting_for_address)
            await answer_and_log(
                message,
                storage,
                address_request_text(),
                reply_markup=back_to_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        await answer_and_log(
            message,
            storage,
            WELCOME_TEXT,
            parse_mode="HTML",
        )
        await answer_and_log(
            message,
            storage,
            build_welcome_actions_text(shop_webapp_url),
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )

    @router.message(F.contact)
    async def save_shared_contact(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.contact:
            return
        customer = await customer_storage.upsert(
            user=message.from_user,
            phone=message.contact.phone_number,
        )
        await answer_and_log(
            message,
            storage,
            profile_text(customer) + "\n\nТеперь укажите адрес доставки.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await request_address_for_pending_order(message, state)

    @router.message(F.text == "Ввести номер вручную")
    async def request_manual_phone(message: Message, state: FSMContext) -> None:
        await state.set_state(UserFlow.waiting_for_manual_phone)
        await answer_and_log(
            message,
            storage,
            "Введите номер телефона в формате +79990000000.",
            reply_markup=contact_request_keyboard(),
        )

    @router.message(UserFlow.waiting_for_manual_phone)
    async def save_manual_phone(message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.text:
            return
        if not is_valid_phone(message.text):
            await answer_and_log(
                message,
                storage,
                "Номер выглядит некорректно. Введите номер еще раз, например +79990000000.",
                reply_markup=contact_request_keyboard(),
            )
            return
        customer = await customer_storage.upsert(user=message.from_user, phone=message.text)
        await answer_and_log(
            message,
            storage,
            profile_text(customer) + "\n\nТеперь укажите адрес доставки.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await request_address_for_pending_order(message, state)



    @router.message(Command("menu"))
    @router.message(F.text.in_({HOME_BUTTON, OLD_BACK_BUTTON}))
    async def back_to_menu(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            MAIN_MENU_TEXT,
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )
        # cta_keyboard = order_cta_inline_keyboard(shop_webapp_url, checkout_api_url)
        # if cta_keyboard is not None:
        #     await answer_and_log(
        #         message,
        #         storage,
        #         "<b>🛍 Быстрый заказ</b>\n\nЕсли хотите сразу перейти к покупке, нажмите кнопку ниже.",
        #         reply_markup=cta_keyboard,
        #         parse_mode="HTML",
        #     )

    @router.message(F.text == PROFILE_BUTTON)
    async def profile(message: Message) -> None:
        customer = await customer_storage.get(message.from_user.id) if message.from_user else None
        if customer is None:
            await answer_and_log(
                message,
                storage,
                registration_text(message),
                reply_markup=contact_request_keyboard(),
                parse_mode="HTML",
            )
            return
        await answer_and_log(
            message,
            storage,
            profile_text(customer),
            reply_markup=contact_request_keyboard(),
            parse_mode="HTML",
        )

    @router.message(F.text.in_({SHOP_BUTTON, OLD_SHOP_BUTTON}))
    async def shop(message: Message) -> None:
        if not shop_webapp_url:
            await answer_and_log(
                message,
                storage,
                "<b>Покупки</b>\n\nMini App готов в папке <code>webapp/</code>. "
                "Чтобы открыть его из Telegram, укажите HTTPS-ссылку в <code>SHOP_WEBAPP_URL</code>.",
                reply_markup=back_to_menu_keyboard(),
                parse_mode="HTML",
            )
            return
        # await answer_and_log(
        #     message,
        #     storage,
        #     "<b>Покупки</b>\n\n"
        #     "Откройте витрину любым удобным способом:\n"
        #     f"• кнопкой <b>{SHOP_BUTTON}</b> в нижнем меню\n"
        #     "• синей кнопкой ниже\n"
        #     f"• ссылкой: <a href=\"{escape(shop_webapp_url)}\">открыть витрину</a>",
        #     reply_markup=order_cta_inline_keyboard(shop_webapp_url, checkout_api_url),
        #     parse_mode="HTML",
        # )

    @router.message(Command("catalog"))
    @router.message(F.text == CATALOG_BUTTON)
    async def show_catalog(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            "<b>Каталог</b>\n\nВыберите категорию.",
            reply_markup=catalog_keyboard(),
            parse_mode="HTML",
        )

    @router.message(F.text.in_(get_categories()))
    async def show_subcategories(message: Message) -> None:
        category = message.text or ""
        await answer_and_log(
            message,
            storage,
            f"<b>{escape(category)}</b>\n\nВыберите подкатегорию.",
            reply_markup=subcategory_keyboard(category),
            parse_mode="HTML",
        )

    @router.message(lambda message: bool(message.text and find_category_by_subcategory(message.text)))
    async def show_subcategory_products(message: Message) -> None:
        subcategory = message.text or ""
        category = find_category_by_subcategory(subcategory)
        if category is None:
            await answer_and_log(message, storage, "Подкатегория не найдена.", reply_markup=catalog_keyboard())
            return

        products = get_products(category, subcategory)
        if not products:
            await answer_and_log(
                message,
                storage,
                "В этой подкатегории пока нет товаров.",
                reply_markup=subcategory_keyboard(category),
            )
            return

        await answer_and_log(
            message,
            storage,
            f"<b>{escape(category)} / {escape(subcategory)}</b>\n\n"
            "Подборка товаров. Нажмите «В корзину» под нужной карточкой.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

        for index, product in enumerate(products, start=1):
            caption = product_caption(index, product)
            product_id = get_product_id(category, subcategory, index - 1)
            actions = product_actions_keyboard(product_id or 0)
            photo_path = PROJECT_ROOT / product["photo"]
            if product.get("photo") and photo_path.exists():
                await message.answer_photo(
                    photo=FSInputFile(photo_path),
                    caption=caption,
                    reply_markup=actions,
                    parse_mode="HTML",
                )
                await storage.log_bot_text(message, caption, metadata={"photo": product["photo"]})
            elif product.get("photo_url"):
                await message.answer_photo(
                    photo=product["photo_url"],
                    caption=caption,
                    reply_markup=actions,
                    parse_mode="HTML",
                )
                await storage.log_bot_text(message, caption, metadata={"photo_url": product["photo_url"]})
            else:
                await answer_and_log(message, storage, caption, reply_markup=actions, parse_mode="HTML")

    @router.message(Command("ai"))
    @router.message(F.text == ASK_AI_BUTTON)
    async def ask_ai(message: Message, state: FSMContext) -> None:
        await state.set_state(UserFlow.waiting_for_ai_question)
        await answer_and_log(
            message,
            storage,
            "<b>AI-помощник</b>\n\n"
            "Напишите вопрос о вкусе, составе, подарке или подборе товара.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

    @router.message(UserFlow.waiting_for_ai_question)
    async def answer_ai_question(message: Message, state: FSMContext) -> None:
        if not message.text:
            await answer_and_log(message, storage, "Пожалуйста, отправьте вопрос текстом.")
            return

        await answer_and_log(message, storage, "Думаю...")
        answer = await ai_service.ask(message.text)
        await storage.log_ai_interaction(
            source_message=message,
            model=ai_service.model,
            question=message.text,
            answer=answer,
            success=answer != FALLBACK_MESSAGE,
        )
        await state.clear()
        await answer_and_log(message, storage, answer, reply_markup=back_to_menu_keyboard())

    @router.message(Command("cart"))
    @router.message(F.text == CART_BUTTON)
    async def cart(message: Message, state: FSMContext) -> None:
        await show_cart(message, state, storage)

    @router.message(F.web_app_data)
    async def webapp_order(message: Message, state: FSMContext) -> None:
        logging.info("Received web_app_data from chat_id=%s", message.chat.id if message.chat else None)
        try:
            payload = json.loads(message.web_app_data.data)
        except json.JSONDecodeError:
            logging.exception("Failed to decode web_app_data payload")
            await answer_and_log(
                message,
                storage,
                "Не удалось прочитать заказ из Mini App.",
                reply_markup=menu_keyboard,
            )
            return

        if payload.get("type") != "order":
            logging.info("Ignoring web_app_data with unsupported type=%s", payload.get("type"))
            return

        items = payload.get("items", [])
        total = payload.get("total", 0)
        logging.info(
            "Processing order from Mini App: items=%s total=%s chat_id=%s",
            len(items),
            total,
            message.chat.id if message.chat else None,
        )
        await begin_order_address_confirmation(
            message,
            items=items,
            total=total,
            state=state,
        )

    @router.message(Command("about"))
    @router.message(F.text.in_({ABOUT_BUTTON, "О нас"}))
    async def about_business(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            ABOUT_TEXT,
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

    @router.message(Command("contact"))
    @router.message(F.text == CONTACT_BUTTON)
    async def contact_manager(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            CONTACT_TEXT,
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )

    @router.callback_query(F.data.startswith("cart:add:"))
    async def add_to_cart(callback: CallbackQuery, state: FSMContext) -> None:
        parts = (callback.data or "").split(":")
        if len(parts) != 3:
            await callback.answer("Не удалось добавить товар.")
            return

        product_data = get_product_by_id(int(parts[2]))
        if product_data is None:
            await callback.answer("Товар не найден.")
            return

        product, category, subcategory, index = product_data
        data = await state.get_data()
        items = list(data.get("cart", []))
        items.append(make_cart_item(product, category, subcategory, index))
        await state.update_data(cart=items)
        await callback.answer("Добавлено в корзину")

    @router.callback_query(F.data == "cart:clear")
    async def clear_cart(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(cart=[])
        await callback.answer("Корзина очищена")
        if callback.message:
            await callback.message.answer(
                "<b>Корзина очищена</b>\n\nМожно выбрать товары заново.",
                reply_markup=back_to_menu_keyboard(),
                parse_mode="HTML",
            )

    @router.callback_query(F.data == "order:address_confirm")
    async def confirm_saved_address(callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user or not callback.message:
            return
        pending_order = await pending_orders.get(callback.from_user.id)
        if not pending_order:
            await callback.answer("Активный заказ не найден.", show_alert=True)
            return
        await callback.answer("Адрес подтвержден")
        await finalize_pending_order(callback.message, pending_order, state)

    @router.callback_query(F.data == "order:address_change")
    async def request_new_address(callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.message:
            return
        await callback.answer("Введите новый адрес")
        await request_address_for_pending_order(callback.message, state)

    @router.message()
    async def unknown_message(message: Message, state: FSMContext) -> None:
        if message.from_user and message.text:
            customer = await customer_storage.get(message.from_user.id)
            pending_order = await pending_orders.get(message.from_user.id)
            if pending_order is not None and (customer is None or not customer.get("phone")):
                await answer_and_log(
                    message,
                    storage,
                    "<b>Сначала нужен номер телефона</b>\n\nПоделитесь контактом, затем укажите адрес доставки, и мы завершим оформление заказа.",
                    reply_markup=contact_request_keyboard(),
                    parse_mode="HTML",
                )
                return

            expects_address = pending_order is not None or (
                customer is not None
                and customer.get("phone")
                and not customer.get("address")
            )
            if expects_address:
                if not is_valid_rostov_address(message.text):
                    await answer_and_log(
                        message,
                        storage,
                        "Адрес выглядит неполным. Укажите адрес в пределах Ростова-на-Дону: улица, дом, квартира или подъезд. Например: Ростов-на-Дону, ул. Пойменная, 21, кв. 14.",
                        reply_markup=back_to_menu_keyboard(),
                    )
                    return
                saved_customer = await customer_storage.update_address(message.from_user, message.text)
                if pending_order is not None:
                    await answer_and_log(
                        message,
                        storage,
                        f"<b>Адрес сохранен</b>\n\n{escape(str(saved_customer.get('address') or '-'))}\n\nПодтверждение получено, передаю заказ менеджеру.",
                        reply_markup=back_to_menu_keyboard(),
                        parse_mode="HTML",
                    )
                    await finalize_pending_order(message, pending_order, state)
                    return
                await state.clear()
                await answer_and_log(
                    message,
                    storage,
                    profile_text(saved_customer) + "\n\n<b>Готово.</b> Адрес сохранен.",
                    reply_markup=menu_keyboard,
                    parse_mode="HTML",
                )
                return

        await answer_and_log(
            message,
            storage,
            "Выберите действие из меню или отправьте /menu.",
            reply_markup=menu_keyboard,
        )

    return router
