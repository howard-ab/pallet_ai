from pathlib import Path

from html import escape
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.ai_service import FALLBACK_MESSAGE
from bot.ai_service import HuggingFaceAIService
from bot.cart import cart_total, make_cart_item
from bot.catalog import (
    find_category_by_subcategory,
    get_categories,
    get_product_by_id,
    get_product_id,
    get_products,
)
from bot.keyboards import (
    ABOUT_BUTTON,
    ASK_AI_BUTTON,
    CART_BUTTON,
    CATALOG_BUTTON,
    CONTACT_BUTTON,
    HOME_BUTTON,
    OLD_BACK_BUTTON,
    back_to_menu_keyboard,
    catalog_keyboard,
    cart_actions_keyboard,
    main_menu_keyboard,
    product_actions_keyboard,
    subcategory_keyboard,
)
from bot.storage import SessionStorage


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WELCOME_TEXT = (
    "<b>Мир Сухофруктов Вас приветствует! 🌸 </b>\n\n"
    "----------------------------------------"
    "Здесь Вы можете заказать все позиции нашей торговой сети, рехи, финики и сладости для дома, офиса и подарков и не только.\n\n"
    "Выберите раздел ниже. Я помогу подобрать товар и собрать корзину."
)

ABOUT_TEXT = (
    "<b>О нас</b>\n\n"
    "Мир Сухофруктов — торговая сеть качественных сухофруктов, орехов, кураги, изюма, "
    "фиников, сладостей и подарочных наборов и не только.\n\n"
    "AI-ассистент помогает быстро выбрать товары, ответить на вопросы и подготовить заказ."
)

CONTACT_TEXT = (
    "<b>Менеджер</b>\n\n"
    "Для оформления заказа или уточнения деталей:\n"
    "@your_manager_username - Телеграм\n"
    "+7-928-111-11-11 - WhatsApp\n"
    "+7-928-111-11-11 - Связаться с нами по телефону\n"
)

MAIN_MENU_TEXT = (
    "<b>Главное меню</b>\n\n"
    "Каталог, AI-помощник, корзина и контакты — все под рукой."
)


class UserFlow(StatesGroup):
    waiting_for_ai_question = State()


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


async def show_cart(message: Message, state: FSMContext, storage: SessionStorage) -> None:
    data = await state.get_data()
    items = data.get("cart", [])
    if not items:
        await answer_and_log(
            message,
            storage,
            "<b>Корзина</b>\n\nПока пусто. Откройте каталог и добавьте товары.",
            reply_markup=main_menu_keyboard(),
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


def create_router(ai_service: HuggingFaceAIService, storage: SessionStorage) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            WELCOME_TEXT,
            reply_markup=main_menu_keyboard(),
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
            reply_markup=main_menu_keyboard(),
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
            await answer_and_log(
                message,
                storage,
                "Подкатегория не найдена.",
                reply_markup=catalog_keyboard(),
            )
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
                await storage.log_bot_text(
                    message,
                    caption,
                    metadata={"photo": product["photo"]},
                )
            elif product.get("photo_url"):
                await message.answer_photo(
                    photo=product["photo_url"],
                    caption=caption,
                    reply_markup=actions,
                    parse_mode="HTML",
                )
                await storage.log_bot_text(
                    message,
                    caption,
                    metadata={"photo_url": product["photo_url"]},
                )
            else:
                await answer_and_log(
                    message,
                    storage,
                    caption,
                    reply_markup=actions,
                    parse_mode="HTML",
                )

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
        await answer_and_log(message, storage, answer, reply_markup=main_menu_keyboard())

    @router.message(Command("cart"))
    @router.message(F.text == CART_BUTTON)
    async def cart(message: Message, state: FSMContext) -> None:
        await show_cart(message, state, storage)

    @router.message(Command("about"))
    @router.message(F.text.in_({ABOUT_BUTTON, "О нас"}))
    async def about_business(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            ABOUT_TEXT,
            reply_markup=main_menu_keyboard(),
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
            reply_markup=main_menu_keyboard(),
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
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML",
            )

    @router.message()
    async def unknown_message(message: Message) -> None:
        await answer_and_log(
            message,
            storage,
            "Выберите действие из меню или отправьте /menu.",
            reply_markup=main_menu_keyboard(),
        )

    return router
