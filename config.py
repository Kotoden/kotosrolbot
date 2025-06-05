from os import getenv

TOKEN: str = getenv("TELEGRAM_BOT_TOKEN", "6993240073:AAFHQ4Rk2RVXwjEakoxY5hCf1qrgIrIA-Ts")
DATABASE_URL: str = getenv("DATABASE_URL", "sqlite:///online_shop.db")
