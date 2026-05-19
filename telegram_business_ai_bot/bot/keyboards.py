from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.catalog import get_categories


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Каталог"), KeyboardButton(text="Спросить AI")],
            [KeyboardButton(text="О бизнесе"), KeyboardButton(text="Связаться с менеджером")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def catalog_keyboard() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=category)] for category in get_categories()]
    rows.append([KeyboardButton(text="Назад в меню")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите категорию",
    )


def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Назад в меню")]],
        resize_keyboard=True,
    )
