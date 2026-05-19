import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.ai_service import HuggingFaceAIService
from bot.config import load_settings
from bot.handlers import create_router
from bot.storage import MessageLoggingMiddleware, SessionStorage, setup_file_logging


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Открыть главное меню"),
            BotCommand(command="catalog", description="Посмотреть каталог"),
            BotCommand(command="ai", description="Задать вопрос AI"),
            BotCommand(command="about", description="О магазине"),
            BotCommand(command="contact", description="Связаться с менеджером"),
        ]
    )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    setup_file_logging()

    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    ai_service = HuggingFaceAIService(settings)
    storage = SessionStorage()

    dispatcher.message.middleware(MessageLoggingMiddleware(storage))
    dispatcher.include_router(create_router(ai_service, storage))

    await setup_bot_commands(bot)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
