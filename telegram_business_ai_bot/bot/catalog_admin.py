from __future__ import annotations

import asyncio
import json
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_DIR = PROJECT_ROOT / "webapp"
CATALOG_FILE = WEBAPP_DIR / "catalog.json"
ADMIN_PRODUCTS_DIR = WEBAPP_DIR / "assets" / "products" / "admin"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


EDITABLE_FIELDS = {
    "name": "название",
    "price": "цена",
    "description": "описание",
    "photo": "фото",
    "origin": "страна/производитель",
    "weight": "вес",
}


def normalize_catalog(catalog: dict, layout: dict) -> dict:
    """Use the storefront layout, preserving products from unlisted sections."""
    result = {category: {sub: [] for sub in subs} for category, subs in layout.items()}
    sources = {
        tuple(source): (category, sub)
        for category, subs in layout.items()
        for sub, paths in subs.items()
        for source in paths
    }
    for category, subs in catalog.items():
        for sub, products in subs.items():
            target = (category, sub) if sub in layout.get(category, {}) else sources.get((category, sub), (category, sub))
            for product in products:
                destination = target
                # Legacy catalog placed chocolate among nuts and sweets.
                if category not in layout or sub == "Орехи в глазури":
                    name = str(product.get("name", "")).lower()
                    if "шоколад" in name or "глазур" in name:
                        destination = ("Орехи и фрукты в шоколаде", "Шоколад и глазурь")
                result.setdefault(destination[0], {}).setdefault(destination[1], []).append(product)
    return result


def product_revision(product: dict) -> str:
    return hashlib.sha256(json.dumps(product, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class ProductLocation:
    category_index: int
    subcategory_index: int
    product_index: int
    category: str
    subcategory: str


class CatalogAdminStorage:
    def __init__(self, catalog_file: Path = CATALOG_FILE) -> None:
        self._catalog_file = catalog_file
        self._lock = asyncio.Lock()

    async def read_catalog(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        return await asyncio.to_thread(self._read_catalog_sync)

    async def get_product(
        self,
        category_index: int,
        subcategory_index: int,
        product_index: int,
    ) -> tuple[ProductLocation, dict[str, Any]] | None:
        catalog = await self.read_catalog()
        return self._get_product_from_catalog(catalog, category_index, subcategory_index, product_index)

    async def add_product(self, category_index: int, subcategory_index: int, product: dict) -> tuple[ProductLocation, dict] | None:
        async with self._lock:
            catalog = await asyncio.to_thread(self._read_catalog_sync)
            categories = list(catalog)
            if not 0 <= category_index < len(categories):
                return None
            category = categories[category_index]
            subs = list(catalog[category])
            if not 0 <= subcategory_index < len(subs):
                return None
            sub = subs[subcategory_index]
            products = catalog[category][sub]
            products.append(dict(product))
            await asyncio.to_thread(self._write_catalog_sync, catalog)
            return ProductLocation(category_index, subcategory_index, len(products) - 1, category, sub), dict(product)

    async def delete_product(self, category_index: int, subcategory_index: int, product_index: int, revision: str) -> bool:
        async with self._lock:
            catalog = await asyncio.to_thread(self._read_catalog_sync)
            found = self._get_product_from_catalog(catalog, category_index, subcategory_index, product_index)
            if found is None or product_revision(found[1]) != revision:
                return False
            location, _ = found
            del catalog[location.category][location.subcategory][product_index]
            await asyncio.to_thread(self._write_catalog_sync, catalog)
            return True

    async def update_product_field(
        self,
        *,
        category_index: int,
        subcategory_index: int,
        product_index: int,
        field: str,
        value: Any,
        expected_revision: str | None = None,
    ) -> tuple[ProductLocation, dict[str, Any]] | None:
        if field not in EDITABLE_FIELDS and field not in {"promo", "discount_percent"}:
            return None

        async with self._lock:
            catalog = await asyncio.to_thread(self._read_catalog_sync)
            found = self._get_product_from_catalog(catalog, category_index, subcategory_index, product_index)
            if found is None:
                return None
            location, product = found
            if expected_revision is not None and product_revision(product) != expected_revision:
                return None

            if field == "promo":
                enabled = bool(value)
                product["promo"] = enabled
                product["discount_percent"] = 10 if enabled else 0
            elif field == "discount_percent":
                product["discount_percent"] = int(value)
                product["promo"] = int(value) > 0
            elif field == "photo":
                text = str(value).strip()
                if _looks_like_url(text):
                    product["photo"] = ""
                    product["photo_url"] = text
                else:
                    product["photo"] = text
                    product["photo_url"] = ""
            else:
                product[field] = str(value).strip()

            await asyncio.to_thread(self._write_catalog_sync, catalog)
            return location, dict(product)

    async def save_uploaded_photo(
        self,
        *,
        bot,
        file_id: str,
        category_index: int,
        subcategory_index: int,
        product_index: int,
        expected_revision: str | None = None,
    ) -> tuple[ProductLocation, dict[str, Any]] | None:
        async with self._lock:
            catalog = await asyncio.to_thread(self._read_catalog_sync)
            found = self._get_product_from_catalog(catalog, category_index, subcategory_index, product_index)
            if found is None:
                return None
            location, product = found
            if expected_revision is not None and product_revision(product) != expected_revision:
                return None

            ADMIN_PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = _slugify(str(product.get("name") or "product"))
            timestamp = datetime.now(MOSCOW_TZ).strftime("%Y%m%d_%H%M%S")
            destination = ADMIN_PRODUCTS_DIR / f"{safe_name}_{timestamp}.jpg"
            await bot.download(file_id, destination=destination)

            product["photo"] = str(destination.relative_to(WEBAPP_DIR))
            product["photo_url"] = ""
            await asyncio.to_thread(self._write_catalog_sync, catalog)
            return location, dict(product)

    def _read_catalog_sync(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        if self._catalog_file.exists():
            payload = json.loads(self._catalog_file.read_text(encoding="utf-8"))
        else:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("Catalog must be a JSON object")
        layout = json.loads((WEBAPP_DIR / "catalog-layout.json").read_text(encoding="utf-8"))
        return normalize_catalog(payload, layout)

    def _write_catalog_sync(self, catalog: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
        self._catalog_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._catalog_file.with_suffix(".json.tmp")
        tmp_file.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_file.replace(self._catalog_file)

    def _get_product_from_catalog(
        self,
        catalog: dict[str, dict[str, list[dict[str, Any]]]],
        category_index: int,
        subcategory_index: int,
        product_index: int,
    ) -> tuple[ProductLocation, dict[str, Any]] | None:
        categories = list(catalog.keys())
        if category_index < 0 or category_index >= len(categories):
            return None
        category = categories[category_index]
        subcategories_payload = catalog.get(category) or {}
        subcategories = list(subcategories_payload.keys())
        if subcategory_index < 0 or subcategory_index >= len(subcategories):
            return None
        subcategory = subcategories[subcategory_index]
        products = subcategories_payload.get(subcategory) or []
        if product_index < 0 or product_index >= len(products):
            return None
        product = products[product_index]
        if not isinstance(product, dict):
            return None
        return (
            ProductLocation(
                category_index=category_index,
                subcategory_index=subcategory_index,
                product_index=product_index,
                category=category,
                subcategory=subcategory,
            ),
            product,
        )


def catalog_admin_root_keyboard(catalog: dict[str, dict[str, list[dict[str, Any]]]]) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for index, category in enumerate(catalog.keys()):
        rows.append(
            [
                InlineKeyboardButton(
                    text=category,
                    callback_data=f"catalog_admin:cat:{index}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def catalog_admin_subcategory_keyboard(
    catalog: dict[str, dict[str, list[dict[str, Any]]]],
    category_index: int,
) -> InlineKeyboardMarkup | None:
    categories = list(catalog.keys())
    if category_index < 0 or category_index >= len(categories):
        return None
    category = categories[category_index]
    rows: list[list[InlineKeyboardButton]] = []
    for index, subcategory in enumerate((catalog.get(category) or {}).keys()):
        rows.append(
            [
                InlineKeyboardButton(
                    text=subcategory,
                    callback_data=f"catalog_admin:sub:{category_index}:{index}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="catalog_admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_admin_product_keyboard(
    catalog: dict[str, dict[str, list[dict[str, Any]]]],
    category_index: int,
    subcategory_index: int,
) -> InlineKeyboardMarkup | None:
    categories = list(catalog.keys())
    if category_index < 0 or category_index >= len(categories):
        return None
    category = categories[category_index]
    subcategories = list((catalog.get(category) or {}).keys())
    if subcategory_index < 0 or subcategory_index >= len(subcategories):
        return None
    subcategory = subcategories[subcategory_index]
    products = (catalog.get(category) or {}).get(subcategory) or []

    rows: list[list[InlineKeyboardButton]] = []
    for index, product in enumerate(products):
        name = str(product.get("name") or f"Товар {index + 1}")
        price = str(product.get("price") or "").strip()
        label = f"{index + 1}. {name[:42]}"
        if price:
            label += f" · {price}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"catalog_admin:prod:{category_index}:{subcategory_index}:{index}:{product_revision(product)}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"catalog_admin:add:{category_index}:{subcategory_index}")])
    rows.append([InlineKeyboardButton(text="⬅️ Подкатегории", callback_data=f"catalog_admin:cat:{category_index}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_admin_edit_keyboard(location: ProductLocation, product: dict[str, Any]) -> InlineKeyboardMarkup:
    prefix = (
        f"catalog_admin:edit:{location.category_index}:"
        f"{location.subcategory_index}:{location.product_index}:{product_revision(product)}"
    )
    promo_enabled = bool(product.get("promo")) or int(product.get("discount_percent") or 0) > 0
    promo_text = "🟢 Убрать акцию" if promo_enabled else "🔥 Сделать акцией -10%"
    rows = [
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"{prefix}:name")],
        [
            InlineKeyboardButton(text="💰 Цена", callback_data=f"{prefix}:price"),
            InlineKeyboardButton(text="🖼 Фото", callback_data=f"{prefix}:photo"),
        ],
        [
            InlineKeyboardButton(text="📝 Описание", callback_data=f"{prefix}:description"),
        ],
        [
            InlineKeyboardButton(text="⚖️ Вес", callback_data=f"{prefix}:weight"),
            InlineKeyboardButton(text="🌍 Страна", callback_data=f"{prefix}:origin"),
        ],
        [
            InlineKeyboardButton(text=promo_text, callback_data=f"{prefix}:promo"),
            InlineKeyboardButton(text="Скидка %", callback_data=f"{prefix}:discount_percent"),
        ],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"catalog_admin:delete:{location.category_index}:{location.subcategory_index}:{location.product_index}:{product_revision(product)}")],
        [
            InlineKeyboardButton(
                text="⬅️ К товарам",
                callback_data=f"catalog_admin:sub:{location.category_index}:{location.subcategory_index}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_product_admin_card(location: ProductLocation, product: dict[str, Any]) -> str:
    discount = int(product.get("discount_percent") or 0)
    promo = "да" if bool(product.get("promo")) or discount > 0 else "нет"
    photo = str(product.get("photo") or product.get("photo_url") or "-")
    lines = [
        "<b>Редактирование товара</b>",
        "",
        f"Раздел: <b>{escape(location.category)}</b>",
        f"Подраздел: <b>{escape(location.subcategory)}</b>",
        "",
        f"Название: <b>{escape(str(product.get('name') or '-'))}</b>",
        f"Цена: <b>{escape(str(product.get('price') or '-'))}</b>",
        f"Вес: <b>{escape(str(product.get('weight') or '-'))}</b>",
        f"Страна: <b>{escape(str(product.get('origin') or '-'))}</b>",
        f"Акция: <b>{promo}</b>",
        f"Скидка: <b>{discount}%</b>",
        f"Фото: <code>{escape(photo)}</code>",
        "",
        f"Описание: {escape(str(product.get('description') or '-'))}",
    ]
    return "\n".join(lines)


def format_edit_prompt(field: str) -> str:
    if field == "name":
        return "Введите новое название товара."
    if field == "discount_percent":
        return "Введите скидку целым числом от 0 до 99. Ноль отключает акцию."
    if field == "price":
        return "Введите новую цену, например: <code>690 руб.</code>"
    if field == "description":
        return "Введите новое описание товара."
    if field == "photo":
        return (
            "Отправьте новое фото файлом/картинкой или пришлите ссылку на изображение.\n\n"
            "Если прислать ссылку, она будет записана как внешняя картинка."
        )
    if field == "origin":
        return "Введите страну или производителя, например: <code>Таджикистан</code>"
    if field == "weight":
        return "Введите вес, например: <code>1 кг</code> или <code>500 г</code>"
    return "Введите новое значение."


def normalize_price(raw: str) -> str:
    text = raw.strip()
    if not text:
        return text
    if re.search(r"\d", text) and "руб" not in text.lower():
        return f"{text} руб."
    return text


def _looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _slugify(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", "_", value, flags=re.IGNORECASE).strip("_")
    return value[:80] or "product"
