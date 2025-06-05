from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
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
        f"Здравствуйте, <b>{user.full_name or user.username or tg_id}</b>!\n"
        "Доступные команды:\n"
        "/categories — список категорий\n"
        "/products [category_id] — товары\n"
        "/buy <product_id> <quantity> — купить товар\n"
        "/orders — ваши заказы\n"
        "/order <order_id> — детали заказа\n"
        "/help — эта подсказка\n"
    )


@router.message(Command(commands=["categories"]))
async def cmd_categories(message: Message) -> None:
    with next(get_db()) as db:
        cats = crud.get_all_categories(db)
    if not cats:
        await message.reply("Пока нет категорий.")
        return
    text = "<b>Категории:</b>\n"
    for cat in cats:
        text += f"{cat.id}. {cat.name}\n"
    text += "\nЧтобы увидеть товары, введите /products <category_id>"
    await message.reply(text)


@router.message(Command(commands=["products"]))
async def cmd_products(message: Message) -> None:
    parts = message.text.split()
    category_id = None
    if len(parts) == 2 and parts[1].isdigit():
        category_id = int(parts[1])
    with next(get_db()) as db:
        products = crud.get_products(db, category_id)
    if not products:
        await message.reply("Товары не найдены.")
        return
    text = "<b>Товары:</b>\n"
    for p in products:
        text += (
            f"{p.id}. {p.name} — {p.price:.2f}₽ (в наличии: {p.quantity})\n"
            f"   Категория: {p.category.name}\n"
        )
    text += "\nЧтобы купить: /buy <product_id> <quantity>"
    await message.reply(text)


@router.message(Command(commands=["buy"]))
async def cmd_buy(message: Message) -> None:
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.reply("Использование: /buy <product_id> <quantity>")
        return
    product_id = int(parts[1])
    qty = int(parts[2])
    tg_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    with next(get_db()) as db:
        user = crud.get_or_create_user(db, tg_id, username, full_name)
        order = crud.create_order(db, user.id)
        try:
            item = crud.add_item_to_order(db, order.id, product_id, qty)
        except Exception as e:
            await message.reply(f"Ошибка: {e}")
            return
        order_db, total_price = crud.get_order_details(db, order.id)
    await message.reply(
        f"Ваш заказ #{order_db.id} создан!\n"
        f"Товар: {item.product.name}\n"
        f"Количество: {item.quantity}\n"
        f"Цена за шт.: {item.unit_price:.2f}₽\n"
        f"<b>Итого: {total_price:.2f}₽</b>\n"
        "Спасибо за покупку!"
    )


@router.message(Command(commands=["orders"]))
async def cmd_orders(message: Message) -> None:
    tg_id = message.from_user.id
    with next(get_db()) as db:
        user = db.query(models.User).filter(models.User.telegram_id == tg_id).one_or_none()
        if not user:
            await message.reply("Вы не зарегистрированы. Напишите /start.")
            return
        orders = crud.get_orders_by_user(db, user.id)
    if not orders:
        await message.reply("У вас нет заказов.")
        return
    text = "<b>Ваши заказы:</b>\n"
    for o in orders:
        ts = o.created_at.strftime("%Y-%m-%d %H:%M")
        text += f"#{o.id}: <i>{o.status}</i>, {ts}\n"
    text += "\nПодробнее: /order <order_id>"
    await message.reply(text)


@router.message(Command(commands=["order"]))
async def cmd_order_details(message: Message) -> None:
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply("Использование: /order <order_id>")
        return
    order_id = int(parts[1])
    tg_id = message.from_user.id
    with next(get_db()) as db:
        user = db.query(models.User).filter(models.User.telegram_id == tg_id).one_or_none()
        if not user:
            await message.reply("Вы не зарегистрированы. Напишите /start.")
            return
        try:
            order, total_price = crud.get_order_details(db, order_id)
        except Exception:
            await message.reply("Заказ не найден.")
            return
        if order.user_id != user.id:
            await message.reply("Этот заказ не ваш.")
            return
        text = f"<b>Детали заказа #{order.id}:</b>\n"
        for item in order.items:
            text += (
                f"{item.product.name} × {item.quantity} шт. — "
                f"{item.unit_price:.2f}₽/шт.\n"
            )
        text += f"\n<b>Итого:</b> {total_price:.2f}₽\n"
        text += f"Статус: <i>{order.status}</i>"
    await message.reply(text)
