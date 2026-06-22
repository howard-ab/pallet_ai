from dataclasses import dataclass

from dotenv import load_dotenv
import os


DEFAULT_HUGGINGFACE_MODEL = "Qwen/Qwen2.5-Coder-3B-Instruct"
DEFAULT_MANAGER_ACCESS_CODE = "ЯХЁЕВ47"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    huggingface_api_token: str
    huggingface_model: str = DEFAULT_HUGGINGFACE_MODEL
    shop_webapp_url: str = ""
    shop_channel_url: str = ""
    checkout_api_url: str = ""
    checkout_api_bind_host: str = "127.0.0.1"
    checkout_api_port: int = 8081
    manager_chat_ids: tuple[int, ...] = ()
    manager_bot_token: str = ""
    manager_access_code: str = DEFAULT_MANAGER_ACCESS_CODE


def load_settings() -> Settings:
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()
    huggingface_model = (
        os.getenv("HUGGINGFACE_MODEL", DEFAULT_HUGGINGFACE_MODEL).strip()
        or DEFAULT_HUGGINGFACE_MODEL
    )
    shop_webapp_url = os.getenv("SHOP_WEBAPP_URL", "").strip()
    shop_channel_url = os.getenv("SHOP_CHANNEL_URL", "").strip()
    checkout_api_url = os.getenv("CHECKOUT_API_URL", "").strip()
    checkout_api_bind_host = os.getenv("CHECKOUT_API_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    checkout_api_port = int((os.getenv("CHECKOUT_API_PORT", "8081").strip() or "8081"))
    raw_manager_chat_ids = os.getenv("MANAGER_CHAT_IDS", "").strip()
    manager_chat_ids = tuple(
        int(item.strip())
        for item in raw_manager_chat_ids.split(',')
        if item.strip()
    )
    manager_bot_token = os.getenv("MANAGER_BOT_TOKEN", "").strip()
    manager_access_code = (
        os.getenv("MANAGER_ACCESS_CODE", DEFAULT_MANAGER_ACCESS_CODE).strip()
        or DEFAULT_MANAGER_ACCESS_CODE
    )

    if not telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    if not huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is not set")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        huggingface_api_token=huggingface_api_token,
        huggingface_model=huggingface_model,
        shop_webapp_url=shop_webapp_url,
        shop_channel_url=shop_channel_url,
        checkout_api_url=checkout_api_url,
        checkout_api_bind_host=checkout_api_bind_host,
        checkout_api_port=checkout_api_port,
        manager_chat_ids=manager_chat_ids,
        manager_bot_token=manager_bot_token,
        manager_access_code=manager_access_code,
    )
