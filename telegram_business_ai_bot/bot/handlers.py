from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.ai_service import HuggingFaceAIService
from bot.ai_service import FALLBACK_MESSAGE
from bot.catalog import get_categories, get_products
from bot.keyboards import back_to_menu_keyboard, catalog_keyboard, main_menu_keyboard
from bot.storage import SessionStorage


WELCOME_TEXT = (
    "Добро пожаловать! Я AI-ассистент для малого бизнеса. Я помогу посмотреть "
    "каталог, отвечу на вопросы о продуктах и помогу с заказом."
)

ABOUT_TEXT = (
    "Мы небольшой бизнес, который продает качественные сухофрукты, орехи, "
    "курагу, изюм, финики и подарочные наборы. Этот бот показывает, как AI "
    "может автоматизировать общение с клиентами, рекомендации товаров и "
    "поддержку заказов."
)

CONTACT_TEXT = (
    "Чтобы оформить заказ или задать подробные вопросы, напишите менеджеру: "
    "@your_manager_username"
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
        )

    @router.message(F.text == "Назад в меню")
    async def back_to_menu(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(F.text == "Каталог")
    async def show_catalog(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            "Выберите категорию:",
            reply_markup=catalog_keyboard(),
        )

    @router.message(F.text.in_(get_categories()))
    async def show_category_products(message: Message) -> None:
        category = message.text or ""
        products = get_products(category)
        if not products:
            await answer_and_log(
                message,
                storage,
                "В этой категории пока нет товаров.",
                reply_markup=catalog_keyboard(),
            )
            return

        product_lines = [f"{category}:\n"]
        for index, product in enumerate(products, start=1):
            product_lines.append(
                "\n".join(
                    [
                        f"{index}. {product['name']}",
                        f"{product['description']}",
                        f"Цена: {product['price']}",
                        f"Вес: {product['weight']}",
                        f"Происхождение: {product['origin']}",
                    ]
                )
            )

        await answer_and_log(
            message,
            storage,
            "\n\n".join(product_lines),
            reply_markup=back_to_menu_keyboard(),
        )

    @router.message(F.text == "Спросить AI")
    async def ask_ai(message: Message, state: FSMContext) -> None:
        await state.set_state(UserFlow.waiting_for_ai_question)
        await answer_and_log(
            message,
            storage,
            "Напишите вопрос о товарах. Я передам его AI-ассистенту.",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.message(UserFlow.waiting_for_ai_question)
    async def answer_ai_question(message: Message, state: FSMContext) -> None:
        if not message.text:
            await answer_and_log(
                message,
                storage,
                "Пожалуйста, отправьте вопрос текстом.",
            )
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
        await answer_and_log(
            message,
            storage,
            answer,
            reply_markup=main_menu_keyboard(),
        )

    @router.message(F.text == "О бизнесе")
    async def about_business(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            ABOUT_TEXT,
            reply_markup=main_menu_keyboard(),
        )

    @router.message(F.text == "Связаться с менеджером")
    async def contact_manager(message: Message, state: FSMContext) -> None:
        await state.clear()
        await answer_and_log(
            message,
            storage,
            CONTACT_TEXT,
            reply_markup=main_menu_keyboard(),
        )

    @router.message()
    async def unknown_message(message: Message) -> None:
        await answer_and_log(
            message,
            storage,
            "Пожалуйста, выберите действие из меню.",
            reply_markup=main_menu_keyboard(),
        )

    return router
