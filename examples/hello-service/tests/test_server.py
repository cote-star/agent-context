"""Unit tests for hello-service."""

from __future__ import annotations

import unittest

from src.config import Config
from src.server import _extract_name, HelloHandler


class ExtractNameTests(unittest.TestCase):
    def test_defaults_to_world(self) -> None:
        self.assertEqual(_extract_name(""), "world")

    def test_reads_name_param(self) -> None:
        self.assertEqual(_extract_name("name=alice"), "alice")


class ConfigTests(unittest.TestCase):
    def test_from_env_has_defaults(self) -> None:
        config = Config.from_env()
        self.assertTrue(config.host)
        self.assertIsInstance(config.port, int)
        self.assertTrue(config.greeting)


class HelloHandlerContractTests(unittest.TestCase):
    def test_handler_declares_config_attribute(self) -> None:
        self.assertTrue(hasattr(HelloHandler, "config"))


if __name__ == "__main__":
    unittest.main()
