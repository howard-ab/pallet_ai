from dataclasses import dataclass

from dotenv import load_dotenv
import os


DEFAULT_HUGGINGFACE_MODEL = "Qwen/Qwen2.5-Coder-3B-Instruct"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    huggingface_api_token: str
    huggingface_model: str = DEFAULT_HUGGINGFACE_MODEL


def load_settings() -> Settings:
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()
    huggingface_model = (
        os.getenv("HUGGINGFACE_MODEL", DEFAULT_HUGGINGFACE_MODEL).strip()
        or DEFAULT_HUGGINGFACE_MODEL
    )

    if not telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    if not huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is not set")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        huggingface_api_token=huggingface_api_token,
        huggingface_model=huggingface_model,
    )
