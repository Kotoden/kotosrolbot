# Telegram Online-Shop Bot

Это репозиторий с кодом Telegram-бота онлайн-магазина, реализованного на Python с использованием Aiogram и SQLite (через SQLAlchemy). Бот позволяет пользователям просматривать категории, выбирать товары, оформлять заказы и отслеживать их. Администраторы могут добавлять, обновлять и удалять товары через специальные команды.

---

## 📋 Основные возможности

* **Регистрация пользователя** через команду `/start` (данные хранятся в таблице `users`).
* **Показ категорий** с помощью `/categories` и инлайн-кнопок (таблица `categories`).
* **Просмотр товаров** в выбранной категории (таблица `products`), оформление покупки одной кнопкой «Купить» (таблица `orders` + `order_items`).
* **Просмотр списка заказов** `/orders` и **детализация заказа** `/order <order_id>`.
* **Админские команды** (доступны только пользователям с `is_admin=1`):

  * `/add_product <name>|<description>|<price>|<quantity>|<category_id>`
  * `/update_product <product_id>|<name?>|<description?>|<price?>|<quantity?>|<category_id?>`
  * `/delete_product <product_id>`

---

## 📂 Структура проекта

```
tgbot/                           
├── bot.py                          # Точка входа: инициализация Bot, Dispatcher, подключение роутеров
├── config.py                       # Конфигурация (TOKEN и DATABASE_URL)
├── requirements.txt                # Список зависимостей
├── database/                       
│   ├── __init__.py                 
│   ├── db.py                       # SQLAlchemy: engine, SessionLocal, init_db()
│   ├── models.py                   # ORM-модели (Users, Categories, Products, Orders, OrderItems)
│   └── crud.py                     # Функции CRUD: создание/обновление/удаление/чтение
├── handlers/                       
│   ├── __init__.py                 
│   ├── user_handlers.py            # Хендлеры пользовательских команд + InlineKeyboard
│   └── admin_handlers.py           # Хендлеры админ-команд (add/update/delete product)
└── tests/                          
    ├── __init__.py                 
    ├── test_crud.py                # Юнит-тесты для CRUD-функций (минимум 2 теста на каждый запрос)
    └── test_bot_smoke.py           # «Смоук»-тесты: бот поднимается, Dispatcher работает, TOKEN задан
```

* **`bot.py`**

  * Инициализирует таблицы в БД (`init_db()`), создаёт объект `Bot(token)` и `Dispatcher()`.
  * Подключает роутеры из `handlers/` через `dp.include_router(...)`.
  * Запускает `dp.start_polling(bot)` в асинхронном цикле.

* **`config.py`**

  ```python
  from os import getenv

  TOKEN: str = getenv("TELEGRAM_BOT_TOKEN", "ВАШ_ТОКЕН_ТУТ")
  DATABASE_URL: str = getenv("DATABASE_URL", "sqlite:///online_shop.db")
  ```

  Нужно заменить `ВАШ_ТОКЕН_ТУТ` на токен бота (из BotFather). По умолчанию БД будет `online_shop.db` в корне проекта.

* **`database/db.py`**

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.ext.declarative import declarative_base
  from sqlalchemy.orm import sessionmaker
  import config

  engine = create_engine(config.DATABASE_URL, echo=False)
  SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
  Base = declarative_base()

  def init_db():
      from . import models
      Base.metadata.create_all(bind=engine)

  def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

  – Создаёт двигателей SQLAlchemy и базу, определяет `SessionLocal`.
  – `init_db()` создаёт таблицы из `models.py` при первом запуске.

* **`database/models.py`**
  5 таблиц, связанные через внешние ключи:

  ```python
  from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
  from sqlalchemy.orm import relationship
  from .db import Base

  class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True, index=True)
      telegram_id = Column(Integer, unique=True, nullable=False)
      username = Column(String, nullable=True)
      full_name = Column(String, nullable=True)
      is_admin = Column(Boolean, default=False, nullable=False)
      orders = relationship("Order", back_populates="user")

  class Category(Base):
      __tablename__ = "categories"
      id = Column(Integer, primary_key=True, index=True)
      name = Column(String, nullable=False)
      products = relationship("Product", back_populates="category")

  class Product(Base):
      __tablename__ = "products"
      id = Column(Integer, primary_key=True, index=True)
      name = Column(String, nullable=False)
      description = Column(String, nullable=True)
      price = Column(Float, nullable=False)
      quantity = Column(Integer, nullable=False)
      category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
      category = relationship("Category", back_populates="products")
      items = relationship("OrderItem", back_populates="product")

  class Order(Base):
      __tablename__ = "orders"
      id = Column(Integer, primary_key=True, index=True)
      user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
      status = Column(String, default="OPEN", nullable=False)
      created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
      user = relationship("User", back_populates="orders")
      items = relationship("OrderItem", back_populates="order")

  class OrderItem(Base):
      __tablename__ = "order_items"
      id = Column(Integer, primary_key=True, index=True)
      order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
      product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
      quantity = Column(Integer, nullable=False)
      unit_price = Column(Float, nullable=False)
      order = relationship("Order", back_populates="items")
      product = relationship("Product", back_populates="items")
  ```

* **`database/crud.py`**
  Содержит функции для:

  1. Создания и получения пользователя (`get_or_create_user`).
  2. Получения всех категорий (`get_all_categories`).
  3. Получения товаров (`get_products`).
  4. Создания заказа и добавления позиций (`create_order`, `add_item_to_order`, `get_order_details`, `get_orders_by_user`).
  5. Добавления/обновления/удаления товаров (`create_product`, `update_product`, `delete_product`).
     Каждая функция возвращает ORM-объекты или бросает исключение, если что-то не так (например, недостаточно товара, несуществующий ID и т. д.).

* **`handlers/user_handlers.py`**
  Основные пользовательские хендлеры:

  1. **`/start` и `/help`**

     * Регистрирует пользователя (или обновляет его имя/username), приветствует и показывает список команд.

  2. **`/categories` → InlineKeyboardMarkup**

     * Берёт список всех категорий из БД.
     * Формирует инлайн-клавиатуру: по две кнопки в ряду с `callback_data="show_cat_<id>"`.
     * Отправляет сообщение `<b>Выберите категорию:</b>` с этой клавиатурой.

  3. **`@router.callback_query(lambda c: c.data.startswith("show_cat_"))`**

     * Разбирает `cat_id` из `callback_data`.
     * Берёт товары данной категории.
     * Формирует текст:

       ```
       <b>Товары в категории #<cat_id>:</b>
       <list_of_products>
       ```
     * Собирает для каждого товара кнопку `InlineKeyboardButton(text=f"Купить {p.name}", callback_data=f"buy_{p.id}_1")`.
     * Отвечает (через `callback.answer()`) и отправляет новое сообщение с товарами + инлайн-клавиатурой «Купить».

  4. **`@router.callback_query(lambda c: c.data.startswith("buy_"))`**

     * Разбирает `product_id` и `quantity` (в данной реализации всегда `1`) из `callback_data="buy_<id>_<qty>"`.
     * Получает или создаёт пользователя (через `get_or_create_user`).
     * Создаёт новый заказ (`create_order`) и добавляет товар (`add_item_to_order`).
     * Если `quantity товара < запрошенного` – бросает исключение, бот отвечает `callback.answer("Ошибка", show_alert=True)`.
     * После успеха берёт детали заказа (`get_order_details`) и отправляет «чек»:

       ```
       ✅ <b>Заказ #<order_id> оформлен!</b>

       Товар: <b>{item.product.name}</b>
       Количество: <b>{item.quantity}</b>
       Цена за шт.: <b>{item.unit_price:.2f}₽</b>

       <b>Итого: {total_price:.2f}₽</b>
       Спасибо за покупку!
       ```

  5. **`/orders`**

     * Берёт из БД все заказы текущего пользователя (`get_orders_by_user`).
     * Если нет – «У вас нет заказов.»
     * Если есть – выводит:

       ```
       <b>Ваши заказы:</b>
       #1: <i>OPEN</i>, 2025-06-06 12:34
       #2: <i>OPEN</i>, 2025-06-06 12:35
       ...
       ```

       и подсказку «Чтобы посмотреть детали, введите `/order <i>order_id</i>`».

  6. **`/order <order_id>`**

     * Если формат неверный (не две части или вторая не число) – «Использование: /order <i>order\_id</i>».
     * Иначе берёт пользователя (`users.telegram_id = message.from_user.id`).
     * Берёт заказ и сумму (`get_order_details`). Если нет заказа – «Заказ не найден.»
     * Если заказ принадлежит другому пользователю – «У вас нет доступа к этому заказу.»
     * Иначе формирует:

       ```
       <b>Детали заказа #<order_id>:</b>
       <item1_name> × <item1_qty> шт. — <unit_price>₽/шт.
       <item2_name> × <item2_qty> шт. — <unit_price>₽/шт.
       ...
       <b>Итого:</b> <total_price>₽
       Статус: <i>OPEN</i>
       ```

* **`handlers/admin_handlers.py`**
  Команды, доступные только `is_admin=True`:

  1. **`/add_product <name>|<description>|<price>|<quantity>|<category_id>`**

     * Проверяет, что `telegram_id` администратора. Если нет – «🚫 Доступно только администраторам.»
     * Разбивает текст по `|`. Если не 5 частей – «Использование: /add\_product <name>|<description>|<price>|<quantity>|\<category\_id>».
     * Парсит `price = float()`, `quantity = int()`, `category_id = int()`. Если `ValueError` – «Неверные числовые параметры.»
     * Пытается `create_product(db, ...)`. Если FK или иные ошибки – «Ошибка при создании товара: <текст\_исключения>».
     * Иначе отвечает:

       ```
       ✅ Товар «<b>{prod.name}</b>» создан (ID={prod.id}).
       ```

  2. **`/update_product <product_id>|<name?>|<description?>|<price?>|<quantity?>|<category_id?>`**

     * Проверяет админа.
     * Разбивает текст по `|`. Если частей не 6 или `product_id` не число – сообщение «Использование…».
     * Парсит, где поля не пустые: `price = float(parts[3]) if parts[3] != "" else None`, и т. д.
     * Вызывает `update_product(db, product_id, name, description, price, quantity, category_id)`. Если ошибка – «Ошибка при обновлении: <…>».
     * Иначе отвечает:

       ```
       ✅ Товар #<id> изменён.
       Название: <новое имя>, Цена: <новая_цена>₽, Количество: <новое_количество>, Категория ID: <новый_cat_id>
       ```

  3. **`/delete_product <product_id>`**

     * Проверяет админа.
     * Если формат неверный (не 2 части или вторая не число) – «Использование: /delete\_product \<product\_id>».
     * Вызывает `delete_product(db, product_id)`. Если ошибка (продукт не найден) – «Ошибка при удалении: <…>».
     * Иначе – «✅ Товар #\<product\_id> удалён.»

---

## 🔧 Установка и запуск

1. **Клонировать репозиторий** (или скопировать папки/файлы):

   ```bash
   git clone https://github.com/ваш_логин/TGBOTKhalturin.git
   cd TGBOTKhalturin
   ```

2. **Создать виртуальное окружение (рекомендуется)**:

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   # source venv/bin/activate
   ```

3. **Установить зависимости**:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   Пример `requirements.txt`:

   ```
   aiogram>=3.7.0
   SQLAlchemy>=2.0
   ```

4. **Настроить `config.py`**:

   * Откройте файл `config.py`.
   * Вставьте туда ваш токен от BotFather:

     ```python
     TOKEN = "ВАШ_ТОКЕН_ТУТ"
     DATABASE_URL = "sqlite:///online_shop.db"
     ```
   * Безопаснее всего хранить токен в переменных окружения, но для простоты можно прямо вписать строку.

5. **Инициализировать базу данных**:

   * При первом запуске `bot.py` метод `init_db()` создаст таблицы автоматически, если их нет.
   * Либо заранее зайдите в `DB Browser for SQLite` и выполните SQL-скрипт из раздела «Структура проекта → create table…» (см. выше) на вкладке **Execute SQL**:

     ```sql
     CREATE TABLE IF NOT EXISTS categories (...);
     CREATE TABLE IF NOT EXISTS users (...);
     CREATE TABLE IF NOT EXISTS products (...);
     CREATE TABLE IF NOT EXISTS orders (...);
     CREATE TABLE IF NOT EXISTS order_items (...);
     ```
   * Затем нажмите **Write Changes**.

6. **Запустить бота**:

   ```bash
   python bot.py
   ```

   * Если всё в порядке, в консоли появится:

     ```
     INFO:__main__:Bot is starting...
     INFO:aiogram.dispatcher:Start polling
     ```
   * Бот готов к приёму сообщений в Telegram.

---

## 🛠 Использование и тестирование

Ниже приведён пошаговый план, как вручную протестировать все ключевые сценарии. **При этом данные в БД (категории, товары, пользователи-админы) можно добавлять исключительно через SQL** (вкладка **Execute SQL** в DB Browser for SQLite или любым другим клиентом SQLite).

---

### 1. Через Execute SQL подготовка базовых данных

1. **Создать таблицы** (если БД пустая). Вставьте в **Execute SQL** следующую схему и нажмите **Execute SQL**, затем **Write Changes**:

   ```sql
   -- Таблица категорий
   CREATE TABLE IF NOT EXISTS categories (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL
   );

   -- Таблица пользователей
   CREATE TABLE IF NOT EXISTS users (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     telegram_id INTEGER UNIQUE NOT NULL,
     username TEXT,
     full_name TEXT,
     is_admin BOOLEAN NOT NULL DEFAULT 0
   );

   -- Таблица заказов
   CREATE TABLE IF NOT EXISTS orders (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     user_id INTEGER NOT NULL,
     status TEXT NOT NULL DEFAULT 'OPEN',
     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
   );

   -- Таблица товаров
   CREATE TABLE IF NOT EXISTS products (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL,
     description TEXT,
     price REAL NOT NULL,
     quantity INTEGER NOT NULL,
     category_id INTEGER NOT NULL,
     FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
   );

   -- Таблица позиций заказа
   CREATE TABLE IF NOT EXISTS order_items (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     order_id INTEGER NOT NULL,
     product_id INTEGER NOT NULL,
     quantity INTEGER NOT NULL,
     unit_price REAL NOT NULL,
     FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
     FOREIGN KEY (product_id) REFERENCES products(id)
   );
   ```

2. **Вставить тестовые категории**:

   ```sql
   INSERT INTO categories (name) VALUES ('Electronics');
   INSERT INTO categories (name) VALUES ('Books');
   ```

   Затем **Write Changes**.

3. **Вставить тестовые товары** (предполагая, что `Electronics.id = 1`, `Books.id = 2`):

   ```sql
   INSERT INTO products (name, description, price, quantity, category_id)
   VALUES
     ('Laptop', 'Gaming laptop', 1500.00, 5, 1),
     ('Smartphone', 'Android flagship', 800.00, 10, 1),
     ('PythonBook', 'Учебник по Python', 25.00, 20, 2);
   ```

   Затем **Write Changes**.

4. **Добавить себя как администратора**:

   1. В Telegram найдите бота `@userinfobot` (или любой, который покажет ваш Telegram ID).
   2. Отправьте этому боту `/start` → он покажет ваш числовой `telegram_id`. Допустим, он равен `123456789`.
   3. Через **Execute SQL** вставьте (или обновите) запись в `users`:

      ```sql
      INSERT OR REPLACE INTO users (telegram_id, username, full_name, is_admin)
      VALUES (123456789, 'ваш_username', 'Ваше Имя', 1);
      ```

      Если запись уже была (появилась после `/start`), достаточно:

      ```sql
      UPDATE users
      SET is_admin = 1
      WHERE telegram_id = 123456789;
      ```
   4. Нажмите **Execute SQL** → **Write Changes**.

---

### 2. Ручное тестирование пользовательских сценариев

1. **/start**

   * Отправьте `/start` в чат с ботом (из вашего аккаунта `123456789`).
   * Должно прийти приветствие:

     ```
     👋 Здравствуйте, <b>Ваше Имя</b>!

     📋 <b>Доступные команды:</b>
     /categories — выбрать категорию товаров
     /orders — посмотреть ваши заказы
     /order <i>order_id</i> — детали заказа
     /help — эта подсказка
     ```
   * Если вы видите своё имя жирным — HTML-разметка работает.
   * Запись в `users` в таблице БД уже существует (проверьте через Browse Data).

2. **/categories → выбор категории через кнопки**

   * Отправьте `/categories`.
   * **Ожидается**: сообщение

     ```
     <b>Выберите категорию:</b>
     ```

     с инлайн-клавиатурой:

     ```
     [Electronics] [Books]
     ```
   * Нажмите **Electronics**. (Это отправит callback\_data=`show_cat_1`.)

3. **show\_cat\_1 → просмотр товаров и кнопок «Купить»**

   * После нажатия должно появиться сообщение:

     ```
     <b>Товары в категории #1:</b>
     1. Laptop — 1500.00₽ (в наличии: 5)
     2. Smartphone — 800.00₽ (в наличии: 10)

     ```

     и инлайн-кнопки (каждая в своей строке):

     ```
     [Купить Laptop]
     [Купить Smartphone]
     ```
   * Если видите обе позиции и кнопки «Купить», значит хендлер `process_category_callback` сработал правильно.

4. **buy\_1\_1 → оформление заказа Laptop**

   * Нажмите кнопку **Купить Laptop** (`callback_data = buy_1_1`).
   * **Ожидается**: бот пришлёт «чек»:

     ```
     ✅ <b>Заказ #1 оформлен!</b>

     Товар: <b>Laptop</b>
     Количество: <b>1</b>
     Цена за шт.: <b>1500.00₽</b>

     <b>Итого: 1500.00₽</b>
     Спасибо за покупку!
     ```
   * Проверьте в БД:

     1. В таблице `orders`: должна быть строка `(1, user_id=1, status='OPEN', created_at=…)`.
     2. В таблице `order_items`: `(1, order_id=1, product_id=1, quantity=1, unit_price=1500.00)`.
     3. В таблице `products`: запись `id=1 (Laptop)` должна иметь `quantity = 4` (было 5, выкупили 1).

5. **buy\_2\_1 → оформление заказа Smartphone**

   * Вернитесь к списку категорий (нажмите `/categories` → **Electronics**), затем нажмите **Купить Smartphone** (`buy_2_1`).
   * **Ожидается**: чек «Заказ #2», `Smartphone`, price 800.00, quantity 1, итого 800.00₽.
   * В БД: в `products` у `id=2` (`Smartphone`) поле `quantity` уменьшилось до `9`.

6. **Покупки до исчерпания запаса**

   * Нажмите «Купить Laptop» ещё 4 раза, пока `Laptop.quantity` не станет `0`.
   * После 5-й покупки бот выпишет чек, а `Laptop.quantity = 0`.
   * При попытке 6-й покупки (`buy_1_1`), в `crud.add_item_to_order` должно бросаться исключение (либо вручную возвращаться ошибка), и бот ответит:

     ```
     ❗️ Ошибка: Недостаточно товара
     ```
   * Если видите это сообщение, значит критическая ситуация «товар закончился» обработана.

7. **Books → покупка PythonBook**

   * Отправьте `/categories` → нажмите **Books**.
   * **Ожидается**:

     ```
     <b>Товары в категории #2:</b>
     3. PythonBook — 25.00₽ (в наличии: 20)

     [Купить PythonBook]
     ```
   * Нажмите **Купить PythonBook** (`buy_3_1`).
   * **Ожидается**: чек «Заказ #N» (третий заказ), `PythonBook`, price 25.00, quantity 1, итого 25.00₽.
   * В БД: у `PythonBook` (`id=3`) стало `quantity = 19`.

---

### 3. Ручное тестирование `/orders` и `/order`

1. **/orders**

   * Отправьте `/orders`.
   * **Ожидается** (если вы купили три товара подряд):

     ```
     <b>Ваши заказы:</b>
     #1: <i>OPEN</i>, 2025-06-06 12:34
     #2: <i>OPEN</i>, 2025-06-06 12:35
     #3: <i>OPEN</i>, 2025-06-06 12:36
     ```
   * Если у вас ещё нет заказов (например, сразу после очистки БД), бот должен ответить:

     ```
     У вас нет заказов.
     ```

2. **/order \<order\_id>**

   * Отправьте `/order 1`.
   * **Ожидается**:

     ```
     <b>Детали заказа #1:</b>
     Laptop × 1 шт. — 1500.00₽/шт.

     <b>Итого:</b> 1500.00₽
     Статус: <i>OPEN</i>
     ```
   * Если `order_id` не найден (`/order 9999`), бот:

     ```
     ❗️ Заказ не найден.
     ```
   * Если ввод неверный формат (`/order abc`), бот:

     ```
     ❗️ Использование: /order <i>order_id</i>
     ```
   * **Проверка доступа к чужому заказу** (при условии, что у вас несколько пользователей):

     1. В таблице `users` через SQL добавьте нового пользователя `(telegram_id = 111111111, is_admin=0)`.
     2. В Telegram переключитесь на аккаунт с `telegram_id = 111111111`.
     3. Отправьте `/order 1` (где заказ #1 принадлежит `123456789`).
     4. **Ожидается**:

        ```
        ❌ У вас нет доступа к этому заказу.
        ```

---

### 4. Ручное тестирование админ-части

---

#### 4.1. `/add_product <…>`

1. **Корректный пример**

   ```text
   /add_product Новинка|Тестовая новинка|99.99|7|1
   ```

   * `1` – `category_id` «Electronics».
   * **Ожидается**:

     ```
     ✅ Товар «<b>Новинка</b>» создан (ID=4).
     ```
   * После этого в `products` появится `(4, 'Новинка', 'Тестовая новинка', 99.99, 7, 1)`.

2. **Неверное количество аргументов**

   ```text
   /add_product ТолькоИмя|Описание|100.00|5
   ```

   * **Ожидается**:

     ```
     ❗️ Использование: /add_product <название>|<описание>|<цена>|<количество>|<category_id>
     ```

3. **Неверные числовые параметры**

   ```text
   /add_product Ошибка|Описание|нечисло|5|1
   ```

   * **Ожидается**:

     ```
     ❗️ Неверные числовые параметры.
     ```

4. **Несуществующий category\_id**

   ```text
   /add_product Тест|Текст|50.00|5|999
   ```

   * **Ожидается** (любой текст ошибки):

     ```
     ❗️ Ошибка при создании товара: FOREIGN KEY constraint failed
     ```

     или другой исходящий из вашей реализации `crud.create_product`.

5. **Проверка прав**

   * В Telegram переключитесь на аккаунт, у которого `is_admin = 0` (например, создайте `(telegram_id = 111111111, is_admin = 0)` в БД).
   * Отправьте:

     ```
     /add_product ЧтоТо|Описание|10.00|5|1
     ```
   * **Ожидается**:

     ```
     🚫 Доступно только администраторам.
     ```

---

#### 4.2. `/update_product <…>`

Пусть в `products` есть товар `(id=4, name='Новинка', price=99.99, quantity=7, category_id=1)`.

1. **Полное обновление**

   ```text
   /update_product 4|НовинкаV2|Новое описание|120.00|5|2
   ```

   * **Ожидается**:

     ```
     ✅ Товар #4 изменён.
     Название: НовинкаV2, Цена: 120.00₽, Количество: 5, Категория ID: 2
     ```
   * В таблице `products` проверяем, что `(4, 'НовинкаV2', 'Новое описание', 120.00, 5, 2)`.

2. **Частичное обновление (оставляем части полей пустыми)**

   ```text
   /update_product 4|||130.00||
   ```

   (меняем только цену).

   * **Ожидается**:

     ```
     ✅ Товар #4 изменён.
     Название: НовинкаV2, Цена: 130.00₽, Количество: 5, Категория ID: 2
     ```
   * Проверяем в БД: цена стала `130.00`, остальные поля не тронуты.

3. **Неверный формат**

   ```text
   /update_product 4|ТолькоИмя
   ```

   * **Ожидается**:

     ```
     ❗️ Использование: /update_product <product_id>|<name?>|<description?>|<price?>|<quantity?>|<category_id?>
     ```

4. **Несуществующий ID**

   ```text
   /update_product 999|Имя|||10.00||
   ```

   * **Ожидается**:

     ```
     ❗️ Ошибка при обновлении: … (product not found)
     ```

5. **Проверка прав**

   * Из-под `telegram_id=111111111 (is_admin=0)` отправьте:

     ```
     /update_product 4|ЧтоТо|||||
     ```
   * **Ожидается**:

     ```
     🚫 Доступно только администраторам.
     ```

---

#### 4.3. `/delete_product <product_id>`

Пусть в таблице `products` есть `(id=4, name='Новинка').`

1. **Корректное удаление**

   ```text
   /delete_product 4
   ```

   * **Ожидается**:

     ```
     ✅ Товар #4 удалён.
     ```
   * Проверяем в БД: `SELECT * FROM products WHERE id=4;` → пусто.

2. **Неверный формат**

   ```text
   /delete_product abc
   ```

   * **Ожидается**:

     ```
     ❗️ Использование: /delete_product <product_id>
     ```

3. **Несуществующий ID**

   ```text
   /delete_product 999
   ```

   * **Ожидается**:

     ```
     ❗️ Ошибка при удалении: …
     ```

4. **Проверка прав**

   * В аккаунте с `is_admin=0` отправьте:

     ```
     /delete_product 4
     ```
   * **Ожидается**:

     ```
     🚫 Доступно только администраторам.
     ```

---

### 5. Дополнительные граничные случаи

1. **Нет категорий**

   * Через **Execute SQL**:

     ```sql
     DELETE FROM categories;
     DELETE FROM products;
     ```
   * Отправьте `/categories`.
   * **Ожидается**:

     ```
     Пока нет категорий.
     ```

2. **Нет товаров в категории**

   * В таблице `categories` оставьте, например, `(id=10, name='Тест')`, а в `products` удалите все с `category_id=10`.
   * `/categories` → нажмите **Тест**.
   * **Ожидается** (всплывающее окно alert):

     ```
     В этой категории нет товаров.
     ```

3. **Некорректный `callback_data`**

   * Попробуйте с помощью Bot API (или стороннего клинера) отправить `callback_data="show_cat_abc"` в чат.
   * **Ожидается**:

     ```
     Неверный формат категории.
     ```
   * Аналогично для `callback_data="buy_xyz_1"`, бот → «Неверный ID товара или количество.»

4. **Доступ к чужому заказу**

   * Аккаунт `111111111` (не-админ), у которого есть свои заказы.
   * Запросите чужой заказ `/order 1`, где `#1` принадлежит другому пользователю.
   * **Ожидается**:

     ```
     ❌ У вас нет доступа к этому заказу.
     ```

---

## 🧪 Автоматические тесты

1. **`tests/test_crud.py`**

   * Содержит unit-тесты по каждому методу из `database/crud.py`.
   * Минимум **2 теста** на каждую CRUD-функцию:

     * Позитивный случай (корректное значение).
     * Негативный случай (например, неверный ID, отсутствие записи, нехватка товара).

2. **`tests/test_bot_smoke.py`**

   * Проверка «дымовых тестов»:

     1. Бот создаётся без ошибок (`bot = Bot(token=...)` не кидает `TypeError`).
     2. Dispatcher регистрируется (`dp.include_router(...)`).
     3. Конфигурационный токен (`config.TOKEN`) присутствует (не пустая строка).
     4. При запуске `init_db()` таблицы создаются (подключение к SQLite отрабатывает).

Запуск всех тестов:

```bash
pytest --maxfail=1 --disable-warnings -q
```

* Если все тесты прошли, значит базовый функционал CRUD и возможности бота корректно покрыты.

---

## 🎯 Итог

1. **Склонировать репо, создать виртуальное окружение, установить зависимости**
2. **Настроить `config.py`** (токен и путь к SQLite).
3. **Запустить `python bot.py`** – бот создаёт таблицы автоматически (если их нет).
4. **Через Execute SQL** добавить:

   * Категории (`INSERT INTO categories ...`),
   * Товары (`INSERT INTO products ...`),
   * Админа (`INSERT INTO users ...`)
5. **В Telegram** протестировать:

   * `/start`, `/help`
   * `/categories` → выбрать категорию → «купить» → оформить заказы → `/orders`, `/order <id>`
   * Админ-команды `/add_product`, `/update_product`, `/delete_product`

README содержит:

* Описание проекта и его возможностей
* Структуру папок и краткое описание каждого файла
* Инструкции по установке, запуску и конфигурации
* Пошаговый ручной план тестирования с SQL-запросами через **Execute SQL**
* Информацию об автоматических тестах (`pytest`)

Теперь вы можете легко развернуть локально этот Telegram-онлайн-магазин, наполнить БД данными через SQL и протестировать полный цикл работы бота! Удачной разработки и тестирования 😊.
