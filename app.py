"""Agente LangChain de Asteria Robotics con aprobación humana para escrituras."""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from asteria_tools import TOOLS
from data_setup import initialize_database


SYSTEM_PROMPT = """
Sos el asistente operativo de Asteria Robotics. Respondé en español y seguí estas
reglas:

- Para preguntas sobre manuales o políticas, consultá search_knowledge_base y
  citá el documento por título, identificador y versión.
- Para conocer el estado o la ubicación de un activo, usá query_asset.
- Si una consulta combina conocimiento documental y datos operativos, usá ambas
  fuentes antes de responder.
- No inventes datos. Si la información no aparece en las fuentes disponibles,
  indicá explícitamente que no está disponible.
- Solo proponé create_maintenance_request cuando el usuario pida explícitamente
  crear una solicitud. Esa escritura queda pendiente de aprobación humana.
- La propuesta deja de estar pendiente cuando llega la decisión humana. Si el
  resultado de la herramienta contiene `created: true`, la solicitud ya fue
  aprobada y creada: nunca digas que sigue pendiente.
- Cada pedido explícito de creación es independiente. No rechaces una solicitud
  nueva basándote solamente en pedidos anteriores; proponé la herramienta y dejá
  que la aprobación humana y SQLite determinen el resultado.
- Después de una decisión humana, no repitas dentro del mismo pedido una escritura
  rechazada ni vuelvas a ejecutar una escritura ya aprobada.
""".strip()


def build_agent(model: Any | None = None):
    """Construye un agente nuevo con memoria de conversación en proceso."""

    load_dotenv()
    selected_model = model or ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_ID", "gemini-3.1-flash-lite"),
        temperature=0,
        retries=2,
        request_timeout=30,
    )

    return create_agent(
        model=selected_model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "create_maintenance_request": {
                        "allowed_decisions": ["approve", "reject"],
                    }
                },
                description_prefix=(
                    "Solicitud de mantenimiento pendiente de aprobación"
                ),
            )
        ],
        checkpointer=InMemorySaver(),
    )


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    if not thread_id.strip():
        raise ValueError("thread_id no puede estar vacío")
    return {"configurable": {"thread_id": thread_id}}


def invoke_agent(agent: Any, prompt: str, thread_id: str):
    """Inicia un turno y devuelve también las interrupciones de HITL."""

    if not prompt.strip():
        raise ValueError("La consulta no puede estar vacía")
    return agent.invoke(
        {"messages": [{"role": "user", "content": prompt.strip()}]},
        config=_config(thread_id),
        version="v2",
    )


def resume_agent(agent: Any, thread_id: str, *, approve: bool | list[bool]):
    """Reanuda el mismo hilo con una decisión por cada acción pendiente."""

    approvals = [approve] if isinstance(approve, bool) else approve
    if not approvals:
        raise ValueError("Se requiere al menos una decisión humana")

    decisions = []
    for approved in approvals:
        if approved:
            decisions.append({"type": "approve"})
        else:
            decisions.append(
                {
                    "type": "reject",
                    "message": (
                        "El usuario rechazó la escritura. No vuelvas a intentarla."
                    ),
                }
            )

    return agent.invoke(
        Command(resume={"decisions": decisions}),
        config=_config(thread_id),
        version="v2",
    )


def get_pending_actions(result: Any) -> list[dict[str, Any]]:
    """Extrae solo nombre y argumentos de las acciones sometidas a revisión."""

    actions: list[dict[str, Any]] = []
    for interruption in getattr(result, "interrupts", ()):
        value = getattr(interruption, "value", {})
        for action in value.get("action_requests", []):
            actions.append({"name": action["name"], "args": action["args"]})
    return actions


def get_last_response_text(result: Any) -> str:
    """Obtiene el último texto del asistente de una salida GraphOutput."""

    value = getattr(result, "value", {})
    for message in reversed(value.get("messages", [])):
        if getattr(message, "type", None) == "ai" and not message.tool_calls:
            return message.text
    return ""


def _get_maintenance_results(result: Any) -> list[dict[str, Any]]:
    """Recupera resultados reales de la herramienta de escritura."""

    results: list[dict[str, Any]] = []
    value = getattr(result, "value", {})
    for message in value.get("messages", []):
        if getattr(message, "type", None) != "tool":
            continue
        if getattr(message, "name", None) != "create_maintenance_request":
            continue
        try:
            payload = json.loads(message.content)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict) and "created" in payload:
            results.append(payload)
    return results


def format_human_decision_summary(result: Any, approvals: list[bool]) -> str:
    """Describe decisiones y escrituras usando resultados verificables, no al LLM."""

    lines: list[str] = []
    for payload in _get_maintenance_results(result):
        if payload.get("created"):
            lines.append(
                "Solicitud creada "
                f"(ID: {payload['request_id']}, activo: {payload['asset_id']}, "
                f"motivo: {payload['reason']})."
            )
        else:
            lines.append(
                "No se pudo crear la solicitud: "
                f"{payload.get('error', 'resultado no válido')}."
            )

    for _ in range(approvals.count(False)):
        lines.append("Solicitud rechazada por el usuario; no se creó ningún registro.")

    if approvals.count(True) > len(_get_maintenance_results(result)):
        lines.append("La acción fue aprobada, pero no devolvió un resultado verificable.")
    return "\n".join(lines)


def main() -> None:
    initialize_database()
    agent = build_agent()

    print("Asistente Asteria (cada consulta es aislada; escribí 'salir' para terminar).")
    while True:
        prompt = input("\nConsulta: ").strip()
        if prompt.lower() in {"salir", "exit"}:
            break
        if not prompt:
            continue

        thread_id = str(uuid4())
        human_decisions: list[bool] = []
        result = invoke_agent(agent, prompt, thread_id)
        while pending_actions := get_pending_actions(result):
            approvals: list[bool] = []
            for action in pending_actions:
                print(f"Acción pendiente: {action['name']}")
                print(f"Argumentos: {action['args']}")
                answer = input("¿Aprobar esta escritura? [si/NO]: ").strip().lower()
                approvals.append(answer in {"si", "sí", "s"})
            human_decisions.extend(approvals)
            result = resume_agent(
                agent,
                thread_id,
                approve=approvals,
            )

        response = (
            format_human_decision_summary(result, human_decisions)
            if human_decisions
            else get_last_response_text(result)
        )
        print(f"Asistente: {response or '[sin respuesta textual]'}")


if __name__ == "__main__":
    main()
