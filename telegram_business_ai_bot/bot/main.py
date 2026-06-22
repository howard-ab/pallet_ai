import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BotCommand

from bot.ai_service import HuggingFaceAIService
from bot.checkout_api import MiniAppCheckoutServer
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
            BotCommand(command="new", description="Показать новые заказы"),
            BotCommand(command="ready", description="Показать готовые к доставке"),
            BotCommand(command="delivery", description="Показать заказы в доставке"),
            BotCommand(command="done", description="Показать доставленные заказы"),
            BotCommand(command="today", description="Показать заказы за сегодня"),
            BotCommand(command="yesterday", description="Показать заказы за вчера"),
            BotCommand(command="date", description="Показать заказы по дате"),
            BotCommand(command="find", description="Найти заказ по номеру"),
            BotCommand(command="whoami", description="Показать профиль сотрудника"),
        ]
    )


async def setup_bot_commands_with_retry(
    bot: Bot,
    *,
    label: str,
    setup_func,
    retries: int = 3,
) -> None:
    for attempt in range(1, retries + 1):
        try:
            await setup_func(bot)
            if attempt > 1:
                logging.info("%s commands configured on retry %s", label, attempt)
            return
        except TelegramNetworkError as exc:
            logging.warning(
                "Failed to configure %s commands on attempt %s/%s: %s",
                label,
                attempt,
                retries,
                exc,
            )
            if attempt == retries:
                logging.warning(
                    "Skipping %s command setup for now. The bot can still continue if Telegram API becomes reachable.",
                    label,
                )
                return
            await asyncio.sleep(min(2 * attempt, 5))


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
    checkout_server = MiniAppCheckoutServer(
        bot=bot,
        telegram_bot_token=settings.telegram_bot_token,
        manager_notifier=manager_notifier,
        customer_storage=customer_storage,
        host=settings.checkout_api_bind_host,
        port=settings.checkout_api_port,
    )

    dispatcher.message.middleware(MessageLoggingMiddleware(storage))
    dispatcher.include_router(
        create_router(
            ai_service=ai_service,
            storage=storage,
            customer_storage=customer_storage,
            manager_notifier=manager_notifier,
            shop_webapp_url=settings.shop_webapp_url,
            shop_channel_url=settings.shop_channel_url,
            checkout_api_url=settings.checkout_api_url,
        )
    )
    if manager_bot is not None:
        manager_dispatcher.include_router(
            create_manager_router(
                access_storage=manager_access_storage,
                manager_notifier=manager_notifier,
                customer_bot=bot,
                shop_channel_url=settings.shop_channel_url,
                access_code=settings.manager_access_code,
            )
        )

    await setup_bot_commands_with_retry(
        bot,
        label="customer bot",
        setup_func=setup_bot_commands,
    )
    if manager_bot is not None:
        await setup_bot_commands_with_retry(
            manager_bot,
            label="manager bot",
            setup_func=setup_manager_bot_commands,
        )
    await checkout_server.start()

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
        await checkout_server.stop()
        await bot.session.close()
        if manager_bot is not None:
            await manager_bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
