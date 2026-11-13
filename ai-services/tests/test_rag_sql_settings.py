import unittest
from unittest.mock import patch

from app.rag.config import Settings


class RagSqlSettingsTests(unittest.TestCase):
    def test_defaults_are_disabled_and_staging_port(self):
        settings = Settings()
        self.assertEqual(settings.sql_host, "127.0.0.1")
        self.assertEqual(settings.sql_port, 13306)
        self.assertEqual(settings.sql_database, "")
        self.assertFalse(settings.sql_enabled)

    def test_production_port_requires_explicit_flag(self):
        with self.assertRaisesRegex(ValueError, "3306"):
            Settings(sql_port=3306)

    def test_environment_overrides_are_read(self):
        with patch.dict("os.environ", {
            "RAG_SQL_ENABLED": "true",
            "RAG_SQL_PORT": "13306",
            "RAG_SQL_DATABASE": "smartprop_staging",
            "RAG_DB_USER": "rag_reader",
            "RAG_DB_PASSWORD": "test-only",
        }, clear=False):
            settings = Settings.from_env()
        self.assertTrue(settings.sql_enabled)
        self.assertEqual(settings.sql_port, 13306)
        self.assertEqual(settings.sql_database, "smartprop_staging")
        self.assertEqual(settings.db_user, "rag_reader")

    def test_invalid_database_name_is_rejected(self):
        with self.assertRaises(ValueError):
            Settings(sql_database="smartprop; DROP TABLE properties")


if __name__ == "__main__":
    unittest.main()
