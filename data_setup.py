"""Preparación determinista del corpus y la base SQLite de Asteria Robotics."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DOCS_DIR = PROJECT_ROOT / "docs"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "asteria.db"


@dataclass(frozen=True)
class CorpusDocument:
    """Documento ficticio con metadatos suficientes para citar su procedencia."""

    document_id: str
    title: str
    version: str
    source: Path
    content: str

    @property
    def metadata(self) -> dict[str, str]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "version": self.version,
            "source": self.source.name,
        }


DOCUMENT_SPECS = (
    {
        "document_id": "manual_xr7",
        "title": "Manual de mantenimiento preventivo del XR-7",
        "version": "1.0",
        "filename": "manual_xr7.md",
    },
    {
        "document_id": "politica_seguridad",
        "title": "Política de seguridad operacional",
        "version": "1.0",
        "filename": "politica_seguridad.md",
    },
)


def load_corpus(docs_dir: Path | None = None) -> list[CorpusDocument]:
    """Carga el corpus mínimo y falla si falta un documento o está vacío."""

    source_directory = docs_dir or DEFAULT_DOCS_DIR
    documents: list[CorpusDocument] = []

    for spec in DOCUMENT_SPECS:
        source = source_directory / spec["filename"]
        content = source.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"El documento está vacío: {source}")

        documents.append(
            CorpusDocument(
                document_id=spec["document_id"],
                title=spec["title"],
                version=spec["version"],
                source=source,
                content=content,
            )
        )

    return documents


@contextmanager
def connect_database(
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Iterator[sqlite3.Connection]:
    """Abre SQLite con claves foráneas activas y cierra siempre la conexión."""

    resolved_path = Path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    """Crea el esquema y agrega los datos semilla sin sobrescribir cambios."""

    resolved_path = Path(db_path)

    with connect_database(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (length(trim(status)) > 0),
                location TEXT NOT NULL CHECK (length(trim(location)) > 0)
            );

            CREATE TABLE IF NOT EXISTS maintenance_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT NOT NULL,
                reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO assets (asset_id, status, location)
            VALUES (?, ?, ?)
            """,
            ("RB-1042", "bloqueado", "Planta A"),
        )

    return resolved_path


def main() -> None:
    documents = load_corpus()
    db_path = initialize_database()
    print(f"Corpus preparado: {len(documents)} documentos (versión 1.0).")
    print(f"Base SQLite preparada: {db_path}")


if __name__ == "__main__":
    main()
