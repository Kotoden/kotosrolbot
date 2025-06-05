# handlers/admin_handlers.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_db
from database import crud, models

router = Router()

async def is_admin_user(telegram_id: int) -> bool:
    with next(get_db()) as db:
        user = db.query(models.User).filter(models.User.telegram_id == telegram_id).one_or_none()
        return bool(user and user.is_admin)

@router.message(Command(commands=["add_product"]))
async def cmd_add_product(message: Message) -> None:
    tg_id = message.from_user.id
    if not await is_admin_user(tg_id):
        return await message.reply("🚫 Доступно только администраторам.", parse_mode="HTML")

    args = message.text[len("/add_product"):].strip()
    parts = args.split("|")
    if len(parts) != 5:
        return await message.reply(
            "❗️ Использование: /add_product "
            "<название>|<описание>|<цена>|<количество>|<category_id>\n"
            "Пример: /add_product Ноутбук|Игровой ноутбук|1500.0|10|1",
            parse_mode="HTML"
        )

    name, description, price_str, qty_str, cat_id_str = [p.strip() for p in parts]
    try:
        price = float(price_str)
        quantity = int(qty_str)
        category_id = int(cat_id_str)
    except ValueError:
        return await message.reply("❗️ Неверные числовые параметры.", parse_mode="HTML")

    with next(get_db()) as db:
        try:
            prod = crud.create_product(db, name, description, price, quantity, category_id)
        except Exception as e:
            return await message.reply(f"❗️ Ошибка при создании товара: {e}", parse_mode="HTML")

    await message.reply(f"✅ Товар «<b>{prod.name}</b>» создан (ID={prod.id}).", parse_mode="HTML")


@router.message(Command(commands=["update_product"]))
async def cmd_update_product(message: Message) -> None:
    tg_id = message.from_user.id
    if not await is_admin_user(tg_id):
        return await message.reply("🚫 Доступно только администраторам.", parse_mode="HTML")

    args = message.text[len("/update_product"):].strip()
    parts = args.split("|")
    if len(parts) != 6 or not parts[0].isdigit():
        return await message.reply(
            "❗️ Использование:\n"
            "/update_product <product_id>|<name?>|<description?>|<price?>|<quantity?>|<category_id?>\n"
            "Пример: /update_product 5|Ноутбук Pro||2000.0|15|2",
            parse_mode="HTML"
        )

    product_id = int(parts[0])
    name = parts[1].strip() or None
    description = parts[2].strip() or None

    try:
        price = float(parts[3]) if parts[3].strip() else None
        quantity = int(parts[4]) if parts[4].strip() else None
        category_id = int(parts[5]) if parts[5].strip() else None
    except ValueError:
        return await message.reply("❗️ Неверные числовые поля.", parse_mode="HTML")

    with next(get_db()) as db:
        try:
            updated = crud.update_product(db, product_id, name, description, price, quantity, category_id)
        except Exception as e:
            return await message.reply(f"❗️ Ошибка при обновлении: {e}", parse_mode="HTML")

    await message.reply(
        f"✅ Товар #{updated.id} изменён.\n"
        f"Название: {updated.name}, Цена: {updated.price:.2f}₽, "
        f"Количество: {updated.quantity}, Категория ID: {updated.category_id}",
        parse_mode="HTML"
    )


@router.message(Command(commands=["delete_product"]))
async def cmd_delete_product(message: Message) -> None:
    tg_id = message.from_user.id
    if not await is_admin_user(tg_id):
        return await message.reply("🚫 Доступно только администраторам.", parse_mode="HTML")

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("❗️ Использование: /delete_product <product_id>", parse_mode="HTML")

    product_id = int(parts[1])
    with next(get_db()) as db:
        try:
            crud.delete_product(db, product_id)
        except Exception as e:
            return await message.reply(f"❗️ Ошибка при удалении: {e}", parse_mode="HTML")

    await message.reply(f"✅ Товар #{product_id} удалён.", parse_mode="HTML")
