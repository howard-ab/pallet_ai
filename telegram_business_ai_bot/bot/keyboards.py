from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.catalog import get_categories, get_subcategories


CATALOG_BUTTON = "Каталог"
ASK_AI_BUTTON = "Спросить AI"
ABOUT_BUTTON = "О магазине"
CONTACT_BUTTON = "Связаться с менеджером"
CART_BUTTON = "Корзина"
HOME_BUTTON = "В главное меню"
OLD_BACK_BUTTON = "Назад в меню"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CATALOG_BUTTON), KeyboardButton(text=ASK_AI_BUTTON)],
            [KeyboardButton(text=CART_BUTTON), KeyboardButton(text=CONTACT_BUTTON)],
            [KeyboardButton(text=ABOUT_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def catalog_keyboard() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=category)] for category in get_categories()]
    rows.append([KeyboardButton(text=HOME_BUTTON)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите категорию",
    )


def subcategory_keyboard(category: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=subcategory)] for subcategory in get_subcategories(category)]
    rows.append([KeyboardButton(text=CATALOG_BUTTON), KeyboardButton(text=HOME_BUTTON)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите подкатегорию",
    )


def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CART_BUTTON), KeyboardButton(text=CATALOG_BUTTON)],
            [KeyboardButton(text=HOME_BUTTON)],
        ],
        resize_keyboard=True,
    )


def product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="В корзину",
                    callback_data=f"cart:add:{product_id}",
                )
            ]
        ]
    )


def cart_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Очистить корзину", callback_data="cart:clear"),
            ]
        ]
    )
