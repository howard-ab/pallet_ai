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
ORDERS_LOG_DIR = STAFF_ACCESS_DIR / "orders"
ORDERS_BY_DAY_DIR = STAFF_ACCESS_DIR / "orders_by_day"
ORDER_STATUS_DIR = STAFF_ACCESS_DIR / "order_status"
STAFF_DIR = STAFF_ACCESS_DIR / "staff"
ORDER_INDEX_FILE = STAFF_ACCESS_DIR / "orders_index.json"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

ORDER_STATUS_FLOW = ("new", "assembled", "in_delivery", "delivered", "cancelled")


def format_moscow_datetime(moment: datetime) -> str:
    return moment.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M MSK")


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
        ORDERS_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ORDERS_BY_DAY_DIR.mkdir(parents=True, exist_ok=True)
        ORDER_STATUS_DIR.mkdir(parents=True, exist_ok=True)
        STAFF_DIR.mkdir(parents=True, exist_ok=True)
        for status in ORDER_STATUS_FLOW:
            (ORDER_STATUS_DIR / status).mkdir(parents=True, exist_ok=True)

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
            "verified_at_text": format_moscow_datetime(now),
            "last_seen_at": now.isoformat(),
            "last_seen_at_text": format_moscow_datetime(now),
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
            existing["last_seen_at_text"] = format_moscow_datetime(now)
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
            "timestamp_text": format_moscow_datetime(now),
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
            "created_at": now.isoformat(),
            "created_at_text": format_moscow_datetime(now),
            "updated_at": now.isoformat(),
            "updated_at_text": format_moscow_datetime(now),
            "date": now.date().isoformat(),
            "order_number": order_number,
            "status": "new",
            "customer": {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "phone": (customer or {}).get("phone"),
            },
            "items": items,
            "total": total,
            "history": [
                {
                    "timestamp": now.isoformat(),
                    "timestamp_text": format_moscow_datetime(now),
                    "event": "created",
                    "status": "new",
                    "actor": {
                        "source": "customer_bot",
                        "user_id": user_id,
                        "username": username,
                        "first_name": first_name,
                    },
                }
            ],
            "last_action_by": None,
        }
        await asyncio.to_thread(self._store_order_record_sync, record)
        return record

    async def get_order(self, order_number: str) -> dict[str, Any] | None:
        index = await asyncio.to_thread(self._read_order_index_sync)
        entry = index.get(order_number)
        if not entry:
            return None
        path = Path(entry["path"])
        return await asyncio.to_thread(self._read_json_file_sync, path)

    async def get_orders_for_date(
        self,
        target_date: date,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_orders_for_date_sync, target_date, status)

    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search_orders_sync, query, limit)

    async def update_order_status(
        self,
        *,
        order_number: str,
        status: str,
        actor: User,
    ) -> dict[str, Any] | None:
        if status not in ORDER_STATUS_FLOW:
            return None
        return await asyncio.to_thread(
            self._update_order_status_sync,
            order_number,
            status,
            {
                "user_id": actor.id,
                "username": actor.username,
                "first_name": actor.first_name,
                "last_name": actor.last_name,
            },
        )

    async def get_staff_actions(self, user_id: int) -> list[dict[str, Any]]:
        path = STAFF_DIR / str(user_id) / "actions.jsonl"
        return await asyncio.to_thread(self._read_jsonl_sync, path)

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

    def _read_json_file_sync(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _write_json_file_sync(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_order_index_sync(self) -> dict[str, dict[str, Any]]:
        if not ORDER_INDEX_FILE.exists():
            return {}
        try:
            return json.loads(ORDER_INDEX_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_order_index_sync(self, payload: dict[str, dict[str, Any]]) -> None:
        ORDER_INDEX_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _order_file_path(self, order_date: str, order_number: str) -> Path:
        return ORDERS_BY_DAY_DIR / order_date / f"{order_number}.json"

    def _status_file_path(self, status: str, order_date: str, order_number: str) -> Path:
        return ORDER_STATUS_DIR / status / order_date / f"{order_number}.json"

    def _staff_actions_path(self, user_id: int) -> Path:
        return STAFF_DIR / str(user_id) / "actions.jsonl"

    def _store_order_record_sync(self, record: dict[str, Any]) -> None:
        order_number = str(record["order_number"])
        order_date = str(record["date"])
        order_file = self._order_file_path(order_date, order_number)
        self._write_json_file_sync(order_file, record)

        log_file = ORDERS_LOG_DIR / f"{order_date}.jsonl"
        self._append_jsonl_sync(log_file, record)

        status_file = self._status_file_path(str(record["status"]), order_date, order_number)
        self._write_json_file_sync(status_file, record)

        index = self._read_order_index_sync()
        index[order_number] = {
            "date": order_date,
            "status": str(record["status"]),
            "path": str(order_file),
            "updated_at": str(record["updated_at"]),
        }
        self._write_order_index_sync(index)

    def _get_orders_for_date_sync(self, target_date: date, status: str | None) -> list[dict[str, Any]]:
        base_dir = ORDERS_BY_DAY_DIR / target_date.isoformat()
        if not base_dir.exists():
            legacy_file = ORDERS_LOG_DIR / f"{target_date.isoformat()}.jsonl"
            rows = self._read_jsonl_sync(legacy_file)
            if status is None:
                return rows
            return [row for row in rows if row.get("status") == status]

        rows: list[dict[str, Any]] = []
        for path in sorted(base_dir.glob("*.json")):
            payload = self._read_json_file_sync(path)
            if not payload:
                continue
            if status is not None and payload.get("status") != status:
                continue
            rows.append(payload)
        rows.sort(key=lambda row: row.get("updated_at", row.get("timestamp", "")))
        return rows

    def _search_orders_sync(self, query: str, limit: int) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        if not needle:
            return []
        index = self._read_order_index_sync()
        matches: list[dict[str, Any]] = []
        for order_number, entry in sorted(
            index.items(),
            key=lambda item: item[1].get("updated_at", ""),
            reverse=True,
        ):
            haystack = order_number.lower()
            if needle not in haystack:
                continue
            payload = self._read_json_file_sync(Path(entry["path"]))
            if payload:
                matches.append(payload)
            if len(matches) >= limit:
                break
        return matches

    def _update_order_status_sync(
        self,
        order_number: str,
        status: str,
        actor: dict[str, Any],
    ) -> dict[str, Any] | None:
        index = self._read_order_index_sync()
        entry = index.get(order_number)
        if not entry:
            return None

        order_file = Path(entry["path"])
        record = self._read_json_file_sync(order_file)
        if not record:
            return None

        now = datetime.now(MOSCOW_TZ)
        previous_status = str(record.get("status", "new"))
        if previous_status == status:
            return record
        record["status"] = status
        record["updated_at"] = now.isoformat()
        record["updated_at_text"] = format_moscow_datetime(now)
        record["last_action_by"] = actor
        history = list(record.get("history", []))
        history.append(
            {
                "timestamp": now.isoformat(),
                "timestamp_text": format_moscow_datetime(now),
                "event": "status_changed",
                "from_status": previous_status,
                "status": status,
                "actor": actor,
            }
        )
        record["history"] = history

        self._write_json_file_sync(order_file, record)

        legacy_log_file = ORDERS_LOG_DIR / f"{record['date']}.jsonl"
        self._append_jsonl_sync(
            legacy_log_file,
            {
                "timestamp": now.isoformat(),
                "timestamp_text": format_moscow_datetime(now),
                "event": "status_changed",
                "order_number": order_number,
                "from_status": previous_status,
                "status": status,
                "actor": actor,
            },
        )

        old_status_file = self._status_file_path(previous_status, str(record["date"]), order_number)
        if old_status_file.exists():
            old_status_file.unlink()
        new_status_file = self._status_file_path(status, str(record["date"]), order_number)
        self._write_json_file_sync(new_status_file, record)

        index[order_number] = {
            "date": str(record["date"]),
            "status": status,
            "path": str(order_file),
            "updated_at": str(record["updated_at"]),
        }
        self._write_order_index_sync(index)

        if actor.get("user_id") is not None:
            self._append_jsonl_sync(
                self._staff_actions_path(int(actor["user_id"])),
                {
                    "timestamp": now.isoformat(),
                    "timestamp_text": format_moscow_datetime(now),
                    "event": "status_changed",
                    "order_number": order_number,
                    "status": status,
                    "from_status": previous_status,
                    "date": record["date"],
                    "actor": actor,
                },
            )

        return record
