# Arquitectura del prototipo

## Flujo principal

1. `app.py` crea el agente y un identificador de hilo por consulta.
2. Gemini decide si necesita consultar documentos, consultar SQLite o proponer
   una solicitud de mantenimiento.
3. `search_knowledge_base` genera embeddings y recupera fragmentos del corpus
   ficticio mediante Chroma en memoria.
4. `query_asset` realiza una consulta parametrizada sobre SQLite.
5. `create_maintenance_request` valida el activo y el motivo antes de escribir.
6. `HumanInTheLoopMiddleware` interrumpe siempre esa herramienta de escritura.
7. La ejecución se reanuda con una decisión humana: aprobar o rechazar.

## Componentes

| Componente | Responsabilidad | Persistencia |
|---|---|---|
| `app.py` | Agente, consola y aprobación humana | Memoria del proceso |
| `asteria_tools.py` | Herramientas documentales y operativas | Chroma en memoria y SQLite |
| `data_setup.py` | Corpus, esquema e inicialización idempotente | Markdown y SQLite local |
| `evaluation_runner.py` | Ejecución de P01-P08 y resultados | CSV y archivos de evidencia |
| LangSmith | Trazas opcionales del agente y las herramientas | Servicio externo |

## Fronteras de seguridad

- El modelo no recibe una herramienta de SQL libre.
- Las consultas de activos usan parámetros y un esquema limitado.
- Toda escritura valida el activo y el motivo.
- La escritura no se ejecuta hasta que exista una decisión humana.
- Los documentos recuperados se tratan como datos, no como instrucciones del
  sistema; P08 verifica este límite con un documento adversarial.
- Las claves se cargan desde `.env`, archivo excluido de Git.

## Decisiones de alcance

El prototipo no implementa autenticación, API web, almacenamiento vectorial
persistente, despliegue ni integración con sistemas productivos. Estas
capacidades están fuera del caso académico y no deben inferirse de las pruebas.
