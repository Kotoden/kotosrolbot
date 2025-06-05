# handlers/user_handlers.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import get_db
from database import crud, models

router = Router()


@router.message(Command(commands=["start", "help"]))
async def cmd_start(message: Message) -> None:
    tg_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    with next(get_db()) as db:
        user = crud.get_or_create_user(db, tg_id, username, full_name)

    await message.reply(
        "👋 Здравствуйте, <b>{}</b>!\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/categories — выбрать категорию товаров\n"
        "/orders — посмотреть ваши заказы\n"
        "/order <i>order_id</i> — детали заказа\n"
        "/help — эта подсказка\n".format(user.full_name or user.username or tg_id),
        parse_mode="HTML"
    )


@router.message(Command(commands=["categories"]))
async def cmd_categories(message: Message) -> None:
    with next(get_db()) as db:
        cats = crud.get_all_categories(db)

    if not cats:
        return await message.reply("Пока нет категорий.", parse_mode="HTML")

    # Собираем клавиатуру (2 кнопки в ряд)
    inline_keyboard = []
    row = []
    for cat in cats:
        btn = InlineKeyboardButton(text=cat.name, callback_data=f"show_cat_{cat.id}")
        row.append(btn)
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await message.reply("<b>Выберите категорию:</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("show_cat_"))
async def process_category_callback(callback: CallbackQuery) -> None:
    try:
        cat_id = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        return await callback.answer("Неверный формат категории.", show_alert=True)

    with next(get_db()) as db:
        products = crud.get_products(db, category_id=cat_id)

    if not products:
        return await callback.answer("В этой категории нет товаров.", show_alert=True)

    text = f"<b>Товары в категории #{cat_id}:</b>\n"
    inline_keyboard = []
    for p in products:
        text += f"{p.id}. {p.name} — {p.price:.2f}₽ (в наличии: {p.quantity})\n"
        btn = InlineKeyboardButton(text=f"Купить {p.name}", callback_data=f"buy_{p.id}_1")
        inline_keyboard.append([btn])

    kb = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def process_buy_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split("_")
    if len(parts) != 3:
        return await callback.answer("Неверные данные для покупки.", show_alert=True)
    try:
        prod_id = int(parts[1])
        qty = int(parts[2])
    except ValueError:
        return await callback.answer("Неверный ID товара или количество.", show_alert=True)

    tg_id = callback.from_user.id
    username = callback.from_user.username
    full_name = f"{callback.from_user.first_name} {callback.from_user.last_name or ''}".strip()

    with next(get_db()) as db:
        user = crud.get_or_create_user(db, tg_id, username, full_name)
        order = crud.create_order(db, user.id)
        try:
            item = crud.add_item_to_order(db, order.id, prod_id, qty)
        except Exception as e:
            return await callback.answer(f"❗️ Ошибка: {e}", show_alert=True)

        order_db, total_price = crud.get_order_details(db, order.id)

    text = (
        f"✅ <b>Заказ #{order_db.id} оформлен!</b>\n\n"
        f"Товар: <b>{item.product.name}</b>\n"
        f"Количество: <b>{item.quantity}</b>\n"
        f"Цена за шт.: <b>{item.unit_price:.2f}₽</b>\n\n"
        f"<b>Итого: {total_price:.2f}₽</b>\n"
        "Спасибо за покупку!"
    )
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML")


@router.message(Command(commands=["orders"]))
async def cmd_orders(message: Message) -> None:
    tg_id = message.from_user.id
    with next(get_db()) as db:
        user = db.query(models.User).filter(models.User.telegram_id == tg_id).one_or_none()
        if not user:
            return await message.reply("Вы не зарегистрированы. Напишите /start.", parse_mode="HTML")
        orders = crud.get_orders_by_user(db, user.id)

    if not orders:
        return await message.reply("У вас нет заказов.", parse_mode="HTML")

    text = "<b>Ваши заказы:</b>\n"
    for o in orders:
        ts = o.created_at.strftime("%Y-%m-%d %H:%M")
        text += f"#{o.id}: <i>{o.status}</i>, {ts}\n"
    text += "\nЧтобы посмотреть детали, введите /order <i>order_id</i>"
    await message.reply(text, parse_mode="HTML")


@router.message(Command(commands=["order"]))
async def cmd_order_details(message: Message) -> None:
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("❗️ Использование: /order <i>order_id</i>", parse_mode="HTML")

    order_id = int(parts[1])
    tg_id = message.from_user.id

    with next(get_db()) as db:
        user = db.query(models.User).filter(models.User.telegram_id == tg_id).one_or_none()
        if not user:
            return await message.reply("Вы не зарегистрированы. Напишите /start.", parse_mode="HTML")

        try:
            order, total_price = crud.get_order_details(db, order_id)
        except Exception:
            return await message.reply("❗️ Заказ не найден.", parse_mode="HTML")

        if order.user_id != user.id:
            return await message.reply("❌ У вас нет доступа к этому заказу.", parse_mode="HTML")

        text = f"<b>Детали заказа #{order.id}:</b>\n"
        for item in order.items:
            text += f"{item.product.name} × {item.quantity} шт. — {item.unit_price:.2f}₽/шт.\n"
        text += f"\n<b>Итого:</b> {total_price:.2f}₽\n"
        text += f"Статус: <i>{order.status}</i>"

    await message.reply(text, parse_mode="HTML")
