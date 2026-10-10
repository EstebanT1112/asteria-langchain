"""Componentes y herramientas LangChain del caso Asteria Robotics."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from data_setup import DEFAULT_DB_PATH, connect_database, load_corpus


def lookup_asset(asset_id: str, db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Consulta un activo sin inventar información cuando no existe."""

    normalized_asset_id = asset_id.strip().upper()
    if not normalized_asset_id:
        return {
            "found": False,
            "asset_id": normalized_asset_id,
            "error": "El identificador del activo no puede estar vacío.",
        }

    with connect_database(db_path) as connection:
        row = connection.execute(
            "SELECT asset_id, status, location FROM assets WHERE asset_id = ?",
            (normalized_asset_id,),
        ).fetchone()

    if row is None:
        return {
            "found": False,
            "asset_id": normalized_asset_id,
            "error": "Activo no encontrado.",
        }

    return {
        "found": True,
        "asset_id": row["asset_id"],
        "status": row["status"],
        "location": row["location"],
    }


def insert_maintenance_request(
    asset_id: str,
    reason: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Valida y crea una solicitud; no implementa por sí sola la aprobación humana."""

    normalized_asset_id = asset_id.strip().upper()
    normalized_reason = reason.strip()

    if not normalized_reason:
        return {
            "created": False,
            "asset_id": normalized_asset_id,
            "error": "El motivo de mantenimiento no puede estar vacío.",
        }

    with connect_database(db_path) as connection:
        asset = connection.execute(
            "SELECT 1 FROM assets WHERE asset_id = ?",
            (normalized_asset_id,),
        ).fetchone()
        if asset is None:
            return {
                "created": False,
                "asset_id": normalized_asset_id,
                "error": "Activo no encontrado; no se creó la solicitud.",
            }

        cursor = connection.execute(
            """
            INSERT INTO maintenance_requests (asset_id, reason)
            VALUES (?, ?)
            """,
            (normalized_asset_id, normalized_reason),
        )
        request_id = cursor.lastrowid

    return {
        "created": True,
        "request_id": request_id,
        "asset_id": normalized_asset_id,
        "reason": normalized_reason,
    }


@lru_cache(maxsize=1)
def get_vector_store() -> Chroma:
    """Construye una única colección Chroma en memoria para el proceso actual."""

    load_dotenv()
    embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=embedding_model,
        output_dimensionality=768,
    )
    documents = [
        Document(page_content=document.content, metadata=document.metadata)
        for document in load_corpus()
    ]
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name="asteria_corpus_v1",
    )


@tool
def search_knowledge_base(query: str) -> str:
    """Busca evidencia en los documentos técnicos ficticios de Asteria."""

    normalized_query = query.strip()
    if not normalized_query:
        return json.dumps(
            {"query": normalized_query, "matches": [], "error": "Consulta vacía."},
            ensure_ascii=False,
        )

    matches = get_vector_store().similarity_search(normalized_query, k=2)
    payload = {
        "query": normalized_query,
        "matches": [
            {
                "document_id": match.metadata.get("document_id"),
                "title": match.metadata.get("title"),
                "version": match.metadata.get("version"),
                "source": match.metadata.get("source"),
                "content": match.page_content,
            }
            for match in matches
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def query_asset(asset_id: str) -> str:
    """Consulta estado y ubicación de un activo por su identificador."""

    return json.dumps(lookup_asset(asset_id, DEFAULT_DB_PATH), ensure_ascii=False)


@tool
def create_maintenance_request(asset_id: str, reason: str) -> str:
    """Crea una solicitud de mantenimiento para un activo existente."""

    return json.dumps(
        insert_maintenance_request(asset_id, reason, DEFAULT_DB_PATH),
        ensure_ascii=False,
    )


TOOLS = [search_knowledge_base, query_asset, create_maintenance_request]
