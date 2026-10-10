# Datos locales

`asteria.db` se genera ejecutando:

```powershell
.\.venv\Scripts\python.exe .\data_setup.py
```

La base generada se excluye de Git porque conserva el estado entre ejecuciones. El inicializador crea las tablas `assets` y `maintenance_requests`, y agrega `RB-1042` solamente cuando todavía no existe.

Para las pruebas automatizadas se utilizan bases temporales independientes; no se modifica `asteria.db`.
