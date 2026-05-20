import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware
from aiogram.types import Message


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = PROJECT_ROOT / "sessions"
LOGS_DIR = PROJECT_ROOT / "logs"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class SessionStorage:
    def __init__(self, sessions_dir: Path = SESSIONS_DIR) -> None:
        self._sessions_dir = sessions_dir
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    async def log_message(
        self,
        message: Message,
        direction: str,
        text: str | None = None,
        event: str = "message",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(MOSCOW_TZ).isoformat(),
            "event": event,
            "direction": direction,
            "chat_id": message.chat.id,
            "message_id": message.message_id,
            "user": self._user_payload(message),
            "text": text if text is not None else message.text,
            "metadata": metadata or {},
        }

        await self._append_record(self._chat_session_name(message), record)
        await self._append_session_index(message)

    async def log_bot_text(
        self,
        source_message: Message,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.log_message(
            message=source_message,
            direction="out",
            text=text,
            event="bot_response",
            metadata=metadata,
        )

    async def log_ai_interaction(
        self,
        source_message: Message,
        model: str,
        question: str,
        answer: str,
        success: bool,
    ) -> None:
        record = {
            "timestamp": datetime.now(MOSCOW_TZ).isoformat(),
            "event": "ai_interaction",
            "chat_id": source_message.chat.id,
            "message_id": source_message.message_id,
            "user": self._user_payload(source_message),
            "model": model,
            "question": question,
            "answer": answer,
            "success": success,
        }

        await self._append_record(self._chat_session_name(source_message), record)
        await self._append_record("ai_interactions", record)
        await self._append_session_index(source_message)

    async def _append_record(self, session_name: int | str, record: dict[str, Any]) -> None:
        if isinstance(session_name, int):
            file_name = f"chat_{session_name}.jsonl"
        else:
            file_name = f"{session_name}.jsonl"

        file_path = self._sessions_dir / file_name
        line = json.dumps(record, ensure_ascii=False)
        await asyncio.to_thread(self._write_line, file_path, line)

    @staticmethod
    def _write_line(file_path: Path, line: str) -> None:
        with file_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")

    async def _append_session_index(self, message: Message) -> None:
        user = self._user_payload(message)
        record = {
            "timestamp": datetime.now(MOSCOW_TZ).isoformat(),
            "chat_id": message.chat.id,
            "user": user,
            "session_file": f"{self._chat_session_name(message)}.jsonl",
        }

        await self._append_record("session_index", record)

    def _chat_session_name(self, message: Message) -> str:
        user = self._user_payload(message)
        username = user.get("username")
        first_name = user.get("first_name")
        user_id = user.get("id")

        if username:
            readable_name = str(username)
        elif first_name:
            readable_name = str(first_name)
        else:
            readable_name = "unknown_user"

        safe_name = self._safe_filename_part(readable_name)
        return f"{safe_name}_user_{user_id or 'unknown'}_chat_{message.chat.id}"

    @staticmethod
    def _safe_filename_part(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"[^a-zа-яё0-9_.-]+", "_", value, flags=re.IGNORECASE)
        value = value.strip("._-")
        return value or "unknown_user"

    @staticmethod
    def _user_payload(message: Message) -> dict[str, Any]:
        if not message.from_user:
            return {}

        return {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language_code": message.from_user.language_code,
            "is_bot": message.from_user.is_bot,
        }


class MessageLoggingMiddleware(BaseMiddleware):
    def __init__(self, storage: SessionStorage) -> None:
        self._storage = storage

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            await self._storage.log_message(event, direction="in")

        return await handler(event, data)


def setup_file_logging(logs_dir: Path = LOGS_DIR) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(logs_dir / "bot.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
