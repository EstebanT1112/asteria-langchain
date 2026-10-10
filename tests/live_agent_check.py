"""Comprobación manual con Gemini; usa una base temporal y consume cuota de API."""

from __future__ import annotations

import tempfile
from pathlib import Path

import asteria_tools
from app import (
    build_agent,
    get_last_response_text,
    get_pending_actions,
    invoke_agent,
    resume_agent,
)
from data_setup import connect_database, initialize_database


def request_count(db_path: Path) -> int:
    with connect_database(db_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM maintenance_requests"
        ).fetchone()
    return int(row["total"])


def main() -> None:
    original_db_path = asteria_tools.DEFAULT_DB_PATH
    with tempfile.TemporaryDirectory() as temporary_directory:
        db_path = Path(temporary_directory) / "live_agent.db"
        initialize_database(db_path)
        asteria_tools.DEFAULT_DB_PATH = db_path

        try:
            agent = build_agent()

            read_result = invoke_agent(
                agent,
                "¿Cuál es el estado y la ubicación del activo RB-1042?",
                thread_id="live-read",
            )
            assert not get_pending_actions(read_result)
            assert request_count(db_path) == 0
            print("LECTURA: PASS")
            print(get_last_response_text(read_result))

            approval_pending = invoke_agent(
                agent,
                (
                    "Creá una solicitud de mantenimiento para RB-1042 con el "
                    "motivo 'Revisión preventiva'."
                ),
                thread_id="live-approval",
            )
            assert get_pending_actions(approval_pending)
            assert request_count(db_path) == 0
            resume_agent(agent, thread_id="live-approval", approve=True)
            assert request_count(db_path) == 1
            print("APROBACIÓN: PASS")

            rejection_pending = invoke_agent(
                agent,
                (
                    "Creá una solicitud de mantenimiento para RB-1042 con el "
                    "motivo 'Control extraordinario'."
                ),
                thread_id="live-rejection",
            )
            assert get_pending_actions(rejection_pending)
            assert request_count(db_path) == 1
            resume_agent(agent, thread_id="live-rejection", approve=False)
            assert request_count(db_path) == 1
            print("RECHAZO: PASS")
            print("BASE PRINCIPAL: NO MODIFICADA")
        finally:
            asteria_tools.DEFAULT_DB_PATH = original_db_path


if __name__ == "__main__":
    main()
