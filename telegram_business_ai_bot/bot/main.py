import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.ai_service import HuggingFaceAIService
from bot.config import load_settings
from bot.handlers import create_router
from bot.storage import MessageLoggingMiddleware, SessionStorage, setup_file_logging


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

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
