from os import getenv

TOKEN: str = getenv("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
DATABASE_URL: str = getenv("DATABASE_URL", "sqlite:///online_shop.db")
