import sqlite3
import tempfile
import unittest
from pathlib import Path

from data_setup import connect_database, initialize_database, load_corpus


class CorpusTests(unittest.TestCase):
    def test_minimum_corpus_has_versioned_expected_facts(self) -> None:
        documents = load_corpus()
        documents_by_id = {document.document_id: document for document in documents}

        self.assertEqual(
            set(documents_by_id),
            {"manual_xr7", "politica_seguridad"},
        )
        self.assertEqual(documents_by_id["manual_xr7"].version, "1.0")
        self.assertIn("cada 30 días", documents_by_id["manual_xr7"].content)
        self.assertEqual(documents_by_id["politica_seguridad"].version, "1.0")
        self.assertIn(
            "Un activo bloqueado no puede operar",
            documents_by_id["politica_seguridad"].content,
        )
        for document in documents:
            self.assertTrue(document.source.exists())
            self.assertTrue(document.content.strip())


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "asteria_test.db"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialization_creates_schema_and_seed_asset(self) -> None:
        initialize_database(self.db_path)

        with connect_database(self.db_path) as connection:
            asset = connection.execute(
                "SELECT asset_id, status, location FROM assets WHERE asset_id = ?",
                ("RB-1042",),
            ).fetchone()
            request_count = connection.execute(
                "SELECT COUNT(*) FROM maintenance_requests"
            ).fetchone()[0]
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_list(maintenance_requests)"
            ).fetchall()

        self.assertEqual(tuple(asset), ("RB-1042", "bloqueado", "Planta A"))
        self.assertEqual(request_count, 0)
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(foreign_keys[0][2], "assets")

    def test_reinitialization_is_idempotent_and_preserves_current_state(self) -> None:
        initialize_database(self.db_path)
        with connect_database(self.db_path) as connection:
            connection.execute(
                "UPDATE assets SET status = ? WHERE asset_id = ?",
                ("en mantenimiento", "RB-1042"),
            )

        initialize_database(self.db_path)

        with connect_database(self.db_path) as connection:
            assets = connection.execute(
                "SELECT asset_id, status FROM assets WHERE asset_id = ?",
                ("RB-1042",),
            ).fetchall()

        self.assertEqual(len(assets), 1)
        self.assertEqual(tuple(assets[0]), ("RB-1042", "en mantenimiento"))

    def test_database_rejects_invalid_maintenance_requests(self) -> None:
        initialize_database(self.db_path)

        with connect_database(self.db_path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO maintenance_requests (asset_id, reason) VALUES (?, ?)",
                    ("RB-1042", "   "),
                )

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO maintenance_requests (asset_id, reason) VALUES (?, ?)",
                    ("RB-INEXISTENTE", "Revisión preventiva"),
                )


if __name__ == "__main__":
    unittest.main()
