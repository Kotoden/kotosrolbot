import unittest
from aiogram import Bot, Dispatcher
import config
from bot import dp, bot as telegram_bot


class TestBotInitialization(unittest.TestCase):
    def test_bot_token_set(self) -> None:
        self.assertIsNotNone(config.TOKEN)
        self.assertNotEqual(config.TOKEN, "ENTER_YOUR_TOKEN_HERE")

    def test_dispatcher_instance(self) -> None:
        self.assertIsInstance(dp, Dispatcher)

    def test_bot_instance(self) -> None:
        self.assertIsInstance(telegram_bot, Bot)


if __name__ == "__main__":
    unittest.main()
