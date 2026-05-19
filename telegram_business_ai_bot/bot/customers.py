import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiogram.types import User


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.json"


class CustomerStorage:
    def __init__(self, file_path: Path = CUSTOMERS_FILE) -> None:
        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    async def get(self, user_id: int) -> dict[str, Any] | None:
        customers = await self._read_all()
        return customers.get(str(user_id))

    async def upsert(self, user: User, phone: str) -> dict[str, Any]:
        customers = await self._read_all()
        record = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": normalize_phone(phone),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        customers[str(user.id)] = record
        await asyncio.to_thread(self._write_all_sync, customers)
        return record

    async def _read_all(self) -> dict[str, dict[str, Any]]:
        return await asyncio.to_thread(self._read_all_sync)

    def _read_all_sync(self) -> dict[str, dict[str, Any]]:
        if not self._file_path.exists():
            return {}
        try:
            return json.loads(self._file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_all_sync(self, customers: dict[str, dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(customers, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith("+"):
        return "+" + re.sub(r"\D", "", phone)
    return re.sub(r"\D", "", phone)


def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15
