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
from bot.manager_access import ManagerAccessStorage
from bot.manager_handlers import create_manager_router
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


async def setup_manager_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Войти в бот заказов"),
            BotCommand(command="today", description="Показать заказы за сегодня"),
            BotCommand(command="whoami", description="Показать профиль сотрудника"),
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
    manager_dispatcher = Dispatcher()
    ai_service = HuggingFaceAIService(settings)
    storage = SessionStorage()
    customer_storage = CustomerStorage()
    manager_access_storage = ManagerAccessStorage()
    manager_notifier = ManagerNotifier(
        settings.manager_chat_ids,
        manager_bot=manager_bot,
        access_storage=manager_access_storage,
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
    if manager_bot is not None:
        manager_dispatcher.include_router(
            create_manager_router(
                access_storage=manager_access_storage,
                manager_notifier=manager_notifier,
                access_code=settings.manager_access_code,
            )
        )

    await setup_bot_commands(bot)
    if manager_bot is not None:
        await setup_manager_bot_commands(manager_bot)

    polling_tasks: list[asyncio.Task[None]] = []
    try:
        polling_tasks.append(
            asyncio.create_task(
                dispatcher.start_polling(bot, handle_signals=False),
                name="customer-bot-polling",
            )
        )
        if manager_bot is not None:
            polling_tasks.append(
                asyncio.create_task(
                    manager_dispatcher.start_polling(manager_bot, handle_signals=False),
                    name="manager-bot-polling",
                )
            )
        await asyncio.gather(*polling_tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Shutdown requested, stopping bot polling tasks")
        raise
    finally:
        for task in polling_tasks:
            if not task.done():
                task.cancel()
        if polling_tasks:
            await asyncio.gather(*polling_tasks, return_exceptions=True)
        await bot.session.close()
        if manager_bot is not None:
            await manager_bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
