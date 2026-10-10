# Evidencia de componentes separados

Fecha: 9 de octubre de 2026.

## Entorno

- Proveedor: Gemini Developer API, nivel gratuito configurado por el usuario.
- Integración: `langchain-google-genai==4.4.0`.
- Modelo solicitado para chat: `gemini-3.7-flash`.
- Modelo informado en la respuesta válida: `gemini-3.8-flash`.
- Embeddings: `gemini-embedding-2`, 768 dimensiones.
- Almacén vectorial: Chroma en memoria.
- Base operativa: SQLite local.
- Trazas: LangSmith habilitado mediante variables de entorno.

## Comprobación de conexión

El primer intento directo con `gemini-3.8-flash` devolvió `503 UNAVAILABLE` por alta demanda. No se ocultó ni se interpretó como un error de autenticación.

El intento posterior solicitando `gemini-3.7-flash` respondió `OK`; los metadatos indicaron que la solicitud fue atendida por `gemini-3.8-flash`. La generación de embeddings devolvió un vector no nulo de 768 dimensiones.

## Comprobación de herramientas

- `query_asset` devolvió `RB-1042`, estado `bloqueado`, ubicación `Planta A`.
- `search_knowledge_base` recuperó primero `manual_xr7` para la pregunta sobre la frecuencia de inspección.
- El documento recuperado conservó la fuente `manual_xr7.md` y el contenido incluyó `30 días`.
- La herramienta de escritura se verificó únicamente contra una base temporal.
- La base principal conservó cero solicitudes al cerrar esta etapa.

## Límite de esta evidencia

Estas comprobaciones validan los componentes por separado. Todavía no validan selección autónoma de herramientas, respuestas finales del agente ni interrupción humana antes de escribir.
