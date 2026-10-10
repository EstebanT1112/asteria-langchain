import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document

import asteria_tools
from data_setup import connect_database, initialize_database


class OperationalFunctionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "asteria_tools.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lookup_asset_returns_existing_asset_and_explicit_absence(self) -> None:
        existing = asteria_tools.lookup_asset("RB-1042", self.db_path)
        missing = asteria_tools.lookup_asset("RB-INEXISTENTE", self.db_path)

        self.assertEqual(
            existing,
            {
                "found": True,
                "asset_id": "RB-1042",
                "status": "bloqueado",
                "location": "Planta A",
            },
        )
        self.assertEqual(missing["found"], False)
        self.assertEqual(missing["asset_id"], "RB-INEXISTENTE")

    def test_insert_request_validates_and_persists_only_valid_data(self) -> None:
        empty_reason = asteria_tools.insert_maintenance_request(
            "RB-1042", "   ", self.db_path
        )
        missing_asset = asteria_tools.insert_maintenance_request(
            "RB-INEXISTENTE", "Revisión preventiva", self.db_path
        )
        created = asteria_tools.insert_maintenance_request(
            "RB-1042", "  Revisión preventiva  ", self.db_path
        )

        with connect_database(self.db_path) as connection:
            rows = connection.execute(
                "SELECT id, asset_id, reason FROM maintenance_requests ORDER BY id"
            ).fetchall()

        self.assertEqual(empty_reason["created"], False)
        self.assertEqual(missing_asset["created"], False)
        self.assertEqual(created["created"], True)
        self.assertEqual(created["request_id"], rows[0]["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]), (created["request_id"], "RB-1042", "Revisión preventiva"))

    def test_langchain_database_tools_use_the_configured_database(self) -> None:
        with patch.object(asteria_tools, "DEFAULT_DB_PATH", self.db_path):
            query_result = json.loads(
                asteria_tools.query_asset.invoke({"asset_id": "RB-1042"})
            )
            create_result = json.loads(
                asteria_tools.create_maintenance_request.invoke(
                    {"asset_id": "RB-1042", "reason": "Inspección programada"}
                )
            )

        self.assertEqual(query_result["status"], "bloqueado")
        self.assertEqual(create_result["created"], True)


class KnowledgeBaseToolTests(unittest.TestCase):
    def test_search_tool_returns_content_and_traceable_metadata(self) -> None:
        class FakeVectorStore:
            def similarity_search(self, query: str, k: int) -> list[Document]:
                self.query = query
                self.k = k
                return [
                    Document(
                        page_content="El XR-7 se inspecciona cada 30 días.",
                        metadata={
                            "document_id": "manual_xr7",
                            "title": "Manual XR-7",
                            "version": "1.0",
                            "source": "manual_xr7.md",
                        },
                    )
                ]

        fake_store = FakeVectorStore()
        with patch.object(asteria_tools, "get_vector_store", return_value=fake_store):
            result = json.loads(
                asteria_tools.search_knowledge_base.invoke(
                    {"query": "inspección del XR-7"}
                )
            )

        self.assertEqual(fake_store.query, "inspección del XR-7")
        self.assertEqual(fake_store.k, 2)
        self.assertEqual(result["matches"][0]["document_id"], "manual_xr7")
        self.assertEqual(result["matches"][0]["version"], "1.0")
        self.assertIn("30 días", result["matches"][0]["content"])


if __name__ == "__main__":
    unittest.main()
