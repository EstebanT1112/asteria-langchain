# Corrección de la consola después de aprobación

Fecha: 9 de octubre de 2026.

## Comportamiento observado

Después de aprobar una solicitud, Gemini informó correctamente que el registro se había creado, pero también dijo de forma contradictoria que seguía pendiente de aprobación. Al reutilizar el mismo hilo, la siguiente solicitud heredó esa interpretación y fue rechazada por el modelo sin proponer la herramienta.

## Causa

- La confirmación final dependía de una narración libre del modelo, aunque SQLite ya había devuelto un resultado estructurado y definitivo.
- Todas las consultas de la consola compartían el mismo `thread_id`, por lo que el texto contradictorio quedaba en el contexto de la siguiente prueba.

## Corrección

- Cada consulta de consola recibe un hilo nuevo.
- La propuesta y su decisión siguen usando el mismo hilo para que LangGraph pueda reanudarla.
- Después de aprobar o rechazar, la consola informa el resultado estructurado de la herramienta: ID, activo y motivo, o rechazo sin creación.
- Las pruebas deterministas no envían trazas ficticias a LangSmith.

## Verificación

La prueba local de regresión confirmó aprobación y rechazo sobre SQLite temporal. La comprobación con Gemini real produjo:

- `LECTURA: PASS`.
- `APROBACIÓN: PASS`.
- `RECHAZO: PASS`.
- `BASE PRINCIPAL: NO MODIFICADA`.
