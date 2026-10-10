# Seguridad y credenciales

## Claves locales

El proyecto utiliza `GOOGLE_API_KEY` y, de forma opcional,
`LANGSMITH_API_KEY`. Deben almacenarse únicamente en `.env`, que está excluido
por Git. `.env.example` contiene solo nombres de variables y valores no secretos.

No se deben incluir claves en commits, incidencias, capturas, registros ni
documentos. Si una clave se publica accidentalmente, debe revocarse en el
proveedor correspondiente antes de volver a ejecutar el proyecto.

## Datos y acciones

Los activos, documentos y solicitudes incluidos son ficticios. La herramienta
de escritura modifica una base SQLite local y está protegida por una
interrupción de aprobación humana en el flujo normal de `app.py`.

Las trazas de LangSmith pueden contener consultas, argumentos y respuestas.
Antes de compartir un proyecto o una traza, revisar su contenido y sus permisos.

## Alcance

Este es un prototipo académico. No incluye autenticación, autorización por
usuario, aislamiento multiusuario, cifrado de base de datos ni controles de
despliegue productivo.
