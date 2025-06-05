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
        await message.reply("Доступно только администраторам.")
        return
    args = message.text[len("/add_product"):].strip()
    parts = args.split("|")
    if len(parts) != 5:
        await message.reply(
            "Использование:\n"
            "/add_product <name>|<description>|<price>|<quantity>|<category_id>"
        )
        return
    name, description, price_str, qty_str, cat_id_str = [p.strip() for p in parts]
    try:
        price = float(price_str)
        quantity = int(qty_str)
        category_id = int(cat_id_str)
    except ValueError:
        await message.reply("Неверные числовые параметры.")
        return
    with next(get_db()) as db:
        try:
            prod = crud.create_product(db, name, description, price, quantity, category_id)
        except Exception as e:
            await message.reply(f"Ошибка: {e}")
            return
    await message.reply(f"Товар '{prod.name}' создан (ID={prod.id}).")


@router.message(Command(commands=["update_product"]))
async def cmd_update_product(message: Message) -> None:
    tg_id = message.from_user.id
    if not await is_admin_user(tg_id):
        await message.reply("Доступно только администраторам.")
        return
    args = message.text[len("/update_product"):].strip()
    parts = args.split("|")
    if len(parts) != 6 or not parts[0].isdigit():
        await message.reply(
            "Использование:\n"
            "/update_product <product_id>|<name?>|<description?>|<price?>|<quantity?>|<category_id?>"
        )
        return
    product_id = int(parts[0])
    name = parts[1].strip() or None
    description = parts[2].strip() or None
    try:
        price = float(parts[3]) if parts[3].strip() else None
        quantity = int(parts[4]) if parts[4].strip() else None
        category_id = int(parts[5]) if parts[5].strip() else None
    except ValueError:
        await message.reply("Неверные числовые поля.")
        return
    with next(get_db()) as db:
        try:
            crud.update_product(db, product_id, name, description, price, quantity, category_id)
        except Exception as e:
            await message.reply(f"Ошибка: {e}")
            return
    await message.reply(f"Товар #{product_id} обновлён.")


@router.message(Command(commands=["delete_product"]))
async def cmd_delete_product(message: Message) -> None:
    tg_id = message.from_user.id
    if not await is_admin_user(tg_id):
        await message.reply("Доступно только администраторам.")
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply("Использование: /delete_product <product_id>")
        return
    product_id = int(parts[1])
    with next(get_db()) as db:
        try:
            crud.delete_product(db, product_id)
        except Exception as e:
            await message.reply(f"Ошибка: {e}")
            return
    await message.reply(f"Товар #{product_id} удалён.")
