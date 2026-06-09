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
from bot.manager_notifications import ManagerNotifier
from bot.keyboards import (
    ABOUT_BUTTON,
    ASK_AI_BUTTON,
    CART_BUTTON,
    CATALOG_BUTTON,
    CONTACT_BUTTON,
    HOME_BUTTON,
    OLD_BACK_BUTTON,
    PROFILE_BUTTON,
    SHOP_BUTTON,
    back_to_menu_keyboard,
    build_main_menu_keyboard,
    catalog_keyboard,
    cart_actions_keyboard,
    contact_request_keyboard,
    product_actions_keyboard,
    subcategory_keyboard,
)
from bot.storage import SessionStorage


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WELCOME_TEXT = (
    "<b>Мир Сухофруктов</b> ✨\n\n"
    "Здесь можно выбрать <b>сухофрукты</b>, <b>орехи</b>, <b>финики</b>, "
    "<b>сладости</b> и подарочные наборы.\n\n"
    "Откройте витрину 🛍, задайте вопрос AI ౨ৎ или соберите заказ прямо в боте."
)

ABOUT_TEXT = (
    "<b>О нас</b>\n\n"
    "Мир Сухофруктов — торговая сеть качественных сухофруктов, орехов, кураги, "
    "изюма, фиников, сладостей и подарочных наборов.\n\n"
    "AI-ассистент помогает быстро выбрать товары, ответить на вопросы и подготовить заказ."
)

CONTACT_TEXT = (
    "<b>Менеджер</b>\n\n"
    "Для оформления заказа или уточнения деталей:\n"
    "@your_manager_username - Telegram\n"
    "+7-928-111-11-11 - WhatsApp\n"
    "+7-928-111-11-11 - телефон"
)

MAIN_MENU_TEXT = (
    "<b>Главное меню</b> ✨\n\n"
    "Витрина 🛍, AI-помощник ౨ৎ, корзина и контакты — все в одном месте."
)


class UserFlow(StatesGroup):
    waiting_for_ai_question = State()
    waiting_for_manual_phone = State()


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


def profile_text(customer: dict[str, object]) -> str:
    username = customer.get("username") or "не указан"
    phone = customer.get("phone") or "не указан"
    return (
        "<b>Ваши контакты</b>\n\n"
        f"Telegram: @{escape(str(username))}\n"
        f"Телефон: {escape(str(phone))}\n\n"
        "Если номер изменился, поделитесь контактом снова или введите новый номер вручную."
    )


async def show_cart(
    message: Message,
    state: FSMContext,
    storage: SessionStorage,
    menu_keyboard: object,
) -> None:
    data = await state.get_data()
    items = data.get("cart", [])
    if not items:
        await answer_and_log(
            message,
            storage,
            "<b>Корзина</b>\n\nПока пусто. Откройте витрину или каталог и добавьте товары.",
            reply_markup=menu_keyboard,
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
        reply_markup=cart_actions_keyboard(),
        parse_mode="HTML",
    )


def create_router(
    ai_service: HuggingFaceAIService,
    storage: SessionStorage,
    customer_storage: CustomerStorage,
    manager_notifier: ManagerNotifier,
    shop_webapp_url: str = "",
) -> Router:
    router = Router()
    menu_keyboard = build_main_menu_keyboard(shop_webapp_url)

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        if message.from_user and await customer_storage.get(message.from_user.id) is None:
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
            WELCOME_TEXT,
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
        await state.clear()
        await answer_and_log(
            message,
            storage,
            profile_text(customer) + "\n\n<b>Готово.</b> Теперь можно перейти к покупкам.",
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )

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
        await state.clear()
        await answer_and_log(
            message,
            storage,
            profile_text(customer) + "\n\n<b>Готово.</b> Контакты обновлены.",
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )

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

    @router.message(F.text == SHOP_BUTTON)
    async def shop(message: Message) -> None:
        if not shop_webapp_url:
            await answer_and_log(
                message,
                storage,
                "<b>Покупки</b>\n\nMini App готов в папке <code>webapp/</code>. "
                "Чтобы открыть его из Telegram, укажите HTTPS-ссылку в <code>SHOP_WEBAPP_URL</code>.",
                reply_markup=menu_keyboard,
                parse_mode="HTML",
            )
            return
        await answer_and_log(
            message,
            storage,
            "<b>Покупки</b>\n\nНажмите кнопку «Покупки» в меню, чтобы открыть витрину.",
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )

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
        await answer_and_log(message, storage, answer, reply_markup=menu_keyboard)

    @router.message(Command("cart"))
    @router.message(F.text == CART_BUTTON)
    async def cart(message: Message, state: FSMContext) -> None:
        await show_cart(message, state, storage, menu_keyboard)

    @router.message(F.web_app_data)
    async def webapp_order(message: Message) -> None:
        try:
            payload = json.loads(message.web_app_data.data)
        except json.JSONDecodeError:
            await answer_and_log(
                message,
                storage,
                "Не удалось прочитать заказ из Mini App.",
                reply_markup=menu_keyboard,
            )
            return

        if payload.get("type") != "order":
            return

        items = payload.get("items", [])
        total = payload.get("total", 0)
        lines = ["<b>Заказ из Mini App</b>", ""]
        customer = await customer_storage.get(message.from_user.id) if message.from_user else None
        if customer:
            username = customer.get("username") or "не указан"
            phone = customer.get("phone") or "не указан"
            lines.append(f"Клиент: @{escape(str(username))}")
            lines.append(f"Телефон: {escape(str(phone))}")
            lines.append("")
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {escape(str(item.get('name', 'Товар')))}")
            lines.append(
                f"   {escape(str(item.get('weight', '')))} · "
                f"<b>{escape(str(item.get('price', '')))}</b>"
            )
        lines.extend(["", f"<b>Итого: {escape(str(total))} руб.</b>", "", "Менеджер скоро свяжется с вами."])
        await manager_notifier.send_order_notification(
            message.bot,
            customer=customer,
            telegram_user=message.from_user,
            items=items,
            total=total,
        )
        await answer_and_log(
            message,
            storage,
            "\n".join(lines),
            reply_markup=menu_keyboard,
            parse_mode="HTML",
        )

    @router.message(Command("about"))
    @router.message(F.text.in_({ABOUT_BUTTON, "О нас"}))
    async def about_business(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            ABOUT_TEXT,
            reply_markup=menu_keyboard,
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
            reply_markup=menu_keyboard,
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
                reply_markup=menu_keyboard,
                parse_mode="HTML",
            )

    @router.message()
    async def unknown_message(message: Message) -> None:
        await answer_and_log(
            message,
            storage,
            "Выберите действие из меню или отправьте /menu.",
            reply_markup=menu_keyboard,
        )

    return router
