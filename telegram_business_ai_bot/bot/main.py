import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.ai_service import HuggingFaceAIService
from bot.config import load_settings
from bot.customers import CustomerStorage
from bot.handlers import create_router
from bot.manager_notifications import ManagerNotifier
from bot.storage import MessageLoggingMiddleware, SessionStorage, setup_file_logging


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Открыть главное меню"),
            BotCommand(command="catalog", description="Посмотреть каталог"),
            BotCommand(command="ai", description="Задать вопрос AI"),
            BotCommand(command="cart", description="Открыть корзину"),
            BotCommand(command="about", description="О магазине"),
            BotCommand(command="contact", description="Связаться с менеджером"),
        ]
    )


async def main() -> None:
    # Make log timestamps match Europe/Moscow (UTC+3) on systems where TZ is honored.
    os.environ.setdefault("TZ", "Europe/Moscow")
    if hasattr(time, "tzset"):
        time.tzset()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    setup_file_logging()

    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    manager_bot = Bot(token=settings.manager_bot_token) if settings.manager_bot_token else None
    dispatcher = Dispatcher()
    ai_service = HuggingFaceAIService(settings)
    storage = SessionStorage()
    customer_storage = CustomerStorage()
    manager_notifier = ManagerNotifier(
        settings.manager_chat_ids,
        manager_bot=manager_bot,
        main_bot_token=settings.telegram_bot_token,
    )

    dispatcher.message.middleware(MessageLoggingMiddleware(storage))
    dispatcher.include_router(
        create_router(
            ai_service=ai_service,
            storage=storage,
            customer_storage=customer_storage,
            manager_notifier=manager_notifier,
            shop_webapp_url=settings.shop_webapp_url,
        )
    )

    await setup_bot_commands(bot)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        if manager_bot is not None:
            await manager_bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
