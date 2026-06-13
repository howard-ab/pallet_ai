from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.catalog import get_categories, get_subcategories


CATALOG_BUTTON = "Каталог"
ASK_AI_BUTTON = "Задать вопрос ИИ"
ABOUT_BUTTON = "О магазине"
CONTACT_BUTTON = "Связаться с менеджером"
CART_BUTTON = "Корзина"
OLD_SHOP_BUTTON = "Покупки"
SHOP_BUTTON = "Каталог"
PROFILE_BUTTON = "Мои контакты"
HOME_BUTTON = "В главное меню"
OLD_BACK_BUTTON = "Назад в меню"
MANAGER_TODAY_BUTTON = "Заказы сегодня"
MANAGER_YESTERDAY_BUTTON = "Заказы вчера"
MANAGER_DATE_BUTTON = "Выбрать дату"
MANAGER_FIND_BUTTON = "Найти заказ"
MANAGER_PROFILE_BUTTON = "Мой профиль"
MANAGER_NEW_BUTTON = "Новые заказы"
MANAGER_READY_BUTTON = "Готовы к доставке"
MANAGER_IN_DELIVERY_BUTTON = "В доставке"
MANAGER_DONE_BUTTON = "Доставленные"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return build_main_menu_keyboard()


def build_webapp_launch_url(shop_webapp_url: str = "", checkout_api_url: str = "") -> str:
    if not shop_webapp_url:
        return ""
    if not checkout_api_url:
        return shop_webapp_url

    parts = urlsplit(shop_webapp_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["api"] = checkout_api_url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def build_main_menu_keyboard(shop_webapp_url: str = "", checkout_api_url: str = "") -> ReplyKeyboardMarkup:
    launch_url = build_webapp_launch_url(shop_webapp_url, checkout_api_url)
    shop_button = KeyboardButton(
        text=SHOP_BUTTON,
        web_app=WebAppInfo(url=launch_url),
    ) if launch_url else KeyboardButton(text=SHOP_BUTTON)

    return ReplyKeyboardMarkup(
        keyboard=[
            [shop_button, KeyboardButton(text=ASK_AI_BUTTON)],
            [KeyboardButton(text=PROFILE_BUTTON), KeyboardButton(text=CONTACT_BUTTON)],
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
            [KeyboardButton(text=CART_BUTTON), KeyboardButton(text=SHOP_BUTTON)],
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


# def order_cta_inline_keyboard(shop_webapp_url: str = "", checkout_api_url: str = "") -> InlineKeyboardMarkup | None:
#     launch_url = build_webapp_launch_url(shop_webapp_url, checkout_api_url)
#     if not launch_url:
#         return None
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     text="Заказать сейчас",
#                     web_app=WebAppInfo(url=launch_url),
#                 )
#             ]
#         ]
#     )


def cart_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Очистить корзину", callback_data="cart:clear"),
            ]
        ]
    )


def address_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, адрес верный", callback_data="order:address_confirm"),
                InlineKeyboardButton(text="Изменить адрес", callback_data="order:address_change"),
            ]
        ]
    )


def contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="Ввести номер вручную")],
            [KeyboardButton(text=HOME_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Поделитесь номером телефона",
    )


def manager_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MANAGER_NEW_BUTTON), KeyboardButton(text=MANAGER_READY_BUTTON)],
            [KeyboardButton(text=MANAGER_FIND_BUTTON), KeyboardButton(text=MANAGER_DONE_BUTTON)],
            [KeyboardButton(text=MANAGER_TODAY_BUTTON), KeyboardButton(text=MANAGER_IN_DELIVERY_BUTTON)],
            [KeyboardButton(text=MANAGER_YESTERDAY_BUTTON), KeyboardButton(text=MANAGER_DATE_BUTTON)],
            [KeyboardButton(text=MANAGER_PROFILE_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def order_list_keyboard(orders: list[dict[str, object]]) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for index, order in enumerate(orders[:10], start=1):
        order_number = str(order.get("order_number", "")).strip()
        if not order_number:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Заказ {index}: {order_number}",
                    callback_data=f"order:view:{order_number}",
                )
            ]
        )
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)
