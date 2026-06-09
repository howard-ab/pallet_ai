from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from aiogram.types import User


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAFF_ACCESS_DIR = PROJECT_ROOT / "staff_access"
VERIFIED_STAFF_FILE = STAFF_ACCESS_DIR / "verified_staff.json"
ACCESS_EVENTS_FILE = STAFF_ACCESS_DIR / "access_events.jsonl"
ORDERS_DIR = STAFF_ACCESS_DIR / "orders"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def current_shift(moment: datetime | None = None) -> str:
    now = moment or datetime.now(MOSCOW_TZ)
    hour = now.hour
    if 6 <= hour < 14:
        return "morning"
    if 14 <= hour < 22:
        return "evening"
    return "night"


class ManagerAccessStorage:
    def __init__(self) -> None:
        STAFF_ACCESS_DIR.mkdir(parents=True, exist_ok=True)
        ORDERS_DIR.mkdir(parents=True, exist_ok=True)

    async def is_verified(self, user_id: int) -> bool:
        staff = await self._read_verified_staff()
        return str(user_id) in staff

    async def get_verified_staff(self, user_id: int) -> dict[str, Any] | None:
        staff = await self._read_verified_staff()
        return staff.get(str(user_id))

    async def get_all_verified_staff(self) -> list[dict[str, Any]]:
        staff = await self._read_verified_staff()
        return list(staff.values())

    async def verify_user(self, user: User) -> dict[str, Any]:
        now = datetime.now(MOSCOW_TZ)
        staff = await self._read_verified_staff()
        record = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "verified_at": now.isoformat(),
            "last_seen_at": now.isoformat(),
            "shift": current_shift(now),
        }
        staff[str(user.id)] = record
        await asyncio.to_thread(self._write_verified_staff_sync, staff)
        await self.log_access_event(user, "verified", {"shift": record["shift"]})
        return record

    async def touch_session(self, user: User, event: str = "start") -> None:
        now = datetime.now(MOSCOW_TZ)
        staff = await self._read_verified_staff()
        existing = staff.get(str(user.id))
        if existing is not None:
            existing["last_seen_at"] = now.isoformat()
            existing["shift"] = current_shift(now)
            staff[str(user.id)] = existing
            await asyncio.to_thread(self._write_verified_staff_sync, staff)
        await self.log_access_event(user, event, {"shift": current_shift(now)})

    async def log_access_event(
        self,
        user: User,
        event: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(MOSCOW_TZ)
        record = {
            "timestamp": now.isoformat(),
            "event": event,
            "shift": current_shift(now),
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "metadata": metadata or {},
        }
        await asyncio.to_thread(self._append_jsonl_sync, ACCESS_EVENTS_FILE, record)

    async def store_order_record(
        self,
        *,
        order_number: str,
        customer: dict[str, object] | None,
        telegram_user: object | None,
        items: list[dict[str, object]],
        total: object,
    ) -> dict[str, Any]:
        now = datetime.now(MOSCOW_TZ)
        user_id = getattr(telegram_user, "id", None) if telegram_user is not None else None
        username = getattr(telegram_user, "username", None) if telegram_user is not None else None
        first_name = getattr(telegram_user, "first_name", None) if telegram_user is not None else None

        if customer:
            username = customer.get("username") or username
            first_name = customer.get("first_name") or first_name

        record = {
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
            "order_number": order_number,
            "customer": {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "phone": (customer or {}).get("phone"),
            },
            "items": items,
            "total": total,
        }
        order_file = ORDERS_DIR / f"{now.date().isoformat()}.jsonl"
        await asyncio.to_thread(self._append_jsonl_sync, order_file, record)
        return record

    async def get_orders_for_date(self, target_date: date) -> list[dict[str, Any]]:
        order_file = ORDERS_DIR / f"{target_date.isoformat()}.jsonl"
        return await asyncio.to_thread(self._read_jsonl_sync, order_file)

    async def _read_verified_staff(self) -> dict[str, dict[str, Any]]:
        return await asyncio.to_thread(self._read_verified_staff_sync)

    def _read_verified_staff_sync(self) -> dict[str, dict[str, Any]]:
        if not VERIFIED_STAFF_FILE.exists():
            return {}
        try:
            return json.loads(VERIFIED_STAFF_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_verified_staff_sync(self, payload: dict[str, dict[str, Any]]) -> None:
        VERIFIED_STAFF_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_jsonl_sync(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read_jsonl_sync(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows
