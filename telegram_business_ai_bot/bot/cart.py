import re
from typing import Any

from bot.catalog import Product


CartItem = dict[str, Any]


def parse_price(price: str) -> int:
    match = re.search(r"\d+", price.replace(" ", ""))
    return int(match.group(0)) if match else 0


def make_cart_item(
    product: Product,
    category: str,
    subcategory: str,
    index: int,
) -> CartItem:
    return {
        "category": category,
        "subcategory": subcategory,
        "index": index,
        "name": product["name"],
        "price": product["price"],
        "price_value": parse_price(product["price"]),
        "weight": product["weight"],
    }


def cart_total(items: list[CartItem]) -> int:
    return sum(int(item.get("price_value", 0)) for item in items)
