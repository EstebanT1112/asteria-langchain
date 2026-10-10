import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

import asteria_tools
from app import (
    build_agent,
    format_human_decision_summary,
    get_pending_actions,
    invoke_agent,
    resume_agent,
)
from data_setup import connect_database, initialize_database


class ToolCallingFakeModel(FakeMessagesListChatModel):
    """Modelo determinista que acepta las herramientas enlazadas por create_agent."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


def request_count(db_path: Path) -> int:
    with connect_database(db_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM maintenance_requests"
        ).fetchone()
    return int(row["total"])


def write_request_model() -> ToolCallingFakeModel:
    return ToolCallingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_maintenance_request",
                        "args": {
                            "asset_id": "RB-1042",
                            "reason": "Revisión preventiva",
                        },
                        "id": "call-maintenance-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="La solicitud fue procesada."),
        ]
    )


class HumanApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment_patch = patch.dict(
            os.environ,
            {"LANGSMITH_TRACING": "false"},
        )
        self.environment_patch.start()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "hitl.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()
        self.environment_patch.stop()

    def test_write_pauses_before_sql_and_approval_executes_exactly_once(self) -> None:
        with patch.object(asteria_tools, "DEFAULT_DB_PATH", self.db_path):
            agent = build_agent(model=write_request_model())
            pending = invoke_agent(
                agent,
                "Creá una solicitud para RB-1042 por revisión preventiva.",
                thread_id="approval-case",
            )

            self.assertEqual(request_count(self.db_path), 0)
            self.assertEqual(
                get_pending_actions(pending),
                [
                    {
                        "name": "create_maintenance_request",
                        "args": {
                            "asset_id": "RB-1042",
                            "reason": "Revisión preventiva",
                        },
                    }
                ],
            )

            resumed = resume_agent(agent, thread_id="approval-case", approve=True)

        self.assertEqual(request_count(self.db_path), 1)
        with connect_database(self.db_path) as connection:
            row = connection.execute(
                "SELECT asset_id, reason FROM maintenance_requests"
            ).fetchone()
        self.assertEqual(tuple(row), ("RB-1042", "Revisión preventiva"))
        summary = format_human_decision_summary(resumed, [True])
        self.assertIn("Solicitud creada", summary)
        self.assertIn("ID: 1", summary)
        self.assertNotIn("pendiente", summary.lower())

    def test_rejection_resumes_same_thread_without_writing(self) -> None:
        with patch.object(asteria_tools, "DEFAULT_DB_PATH", self.db_path):
            agent = build_agent(model=write_request_model())
            pending = invoke_agent(
                agent,
                "Creá una solicitud para RB-1042 por revisión preventiva.",
                thread_id="rejection-case",
            )
            self.assertTrue(get_pending_actions(pending))

            resumed = resume_agent(agent, thread_id="rejection-case", approve=False)

        self.assertEqual(request_count(self.db_path), 0)
        summary = format_human_decision_summary(resumed, [False])
        self.assertIn("rechazada", summary.lower())
        self.assertIn("no se creó", summary.lower())

    def test_read_tool_executes_without_human_interruption(self) -> None:
        model = ToolCallingFakeModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "query_asset",
                            "args": {"asset_id": "RB-1042"},
                            "id": "call-read-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="RB-1042 está bloqueado en Planta A."),
            ]
        )

        with patch.object(asteria_tools, "DEFAULT_DB_PATH", self.db_path):
            result = invoke_agent(
                build_agent(model=model),
                "¿Cuál es el estado de RB-1042?",
                thread_id="read-case",
            )

        self.assertEqual(get_pending_actions(result), [])
        self.assertEqual(request_count(self.db_path), 0)


if __name__ == "__main__":
    unittest.main()
