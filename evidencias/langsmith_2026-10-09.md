# Comprobación de trazas de LangSmith

Fecha: 9 de octubre de 2026.

Se realizó una consulta de solo lectura mediante el cliente de LangSmith, utilizando las credenciales locales sin imprimirlas.

- Proyecto consultado: `asteria-asi`.
- Muestra: cinco ejecuciones recientes.
- Nombres observados en la muestra: `create_maintenance_request`, `query_asset`, `search_knowledge_base`, `HumanInTheLoopMiddleware.after_model` y `ToolCallingFakeModel`.
- Ejecuciones con error en esa muestra: 0.

Esta comprobación confirma la recepción de trazas. No confirma que un tercero tenga permisos para abrirlas. Antes de incluir enlaces o capturas en la entrega, se debe revisar manualmente el panel y comprobar que no aparezca información sensible.
