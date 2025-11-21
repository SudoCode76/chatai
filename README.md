# Chat con base de datos mysql(chatai)

Proyecto Flask que ofrece una interfaz de chat para buscar y consultar información de una base de datos de empresas/actividades económicas (tabla `informacion`) y generar respuestas conversacionales usando, opcionalmente, el SDK de Google GenAI (Gemini) o una respuesta local.



Estructura principal

- `app.py` — Aplicación Flask principal (endpoints: `/`, `/chat`, `/status`, `/test_db`).
- `requirements.txt` — Dependencias Python.
- `templates/index.html` — Interfaz web del chat (HTML + estilos).
- `static/chat.js` — Lógica cliente para la UI (envía peticiones a `/chat`).
- `script.sql` — Script SQL para crear la base de datos y la tabla `informacion`.
- `CAEDEC1.csv` — Dataset (csv) con registros de actividades/empresas (puede ser grande).
- `.env.example` — Ejemplo de variables de entorno.

Descripción rápida

La aplicación busca coincidencias en la tabla `informacion` usando la función `search_in_database` (en `app.py`). Busca por palabras clave en `nombre`, `nombreLargo` y `descripcion`, y por coincidencia exacta en `caedec` cuando la consulta incluye números. Los resultados se formatean y se envían al generador de respuestas: si está disponible el SDK de Google GenAI y la variable `GEMINI_API_KEY`, se usa Gemini; si no, la aplicación devuelve una respuesta local básica.

Requisitos

- Python 3.9+ (probado con 3.10+)
- MySQL (o MariaDB) accesible desde la máquina (puede usar XAMPP en Windows)
- Cuenta/clave para Google GenAI y el SDK `google-genai` instalado

Instalación (Windows - cmd.exe)

1. Crear y activar entorno virtual (recomendado):

```bat
python -m venv .venv
.venv\Scripts\activate
```

2. Instalar dependencias:

```bat
pip install -r requirements.txt
```

Variables de entorno

Crea un archivo `.env` en la raíz (puedes copiar `.env.example`) y define al menos:

- GEMINI_API_KEY — (opcional) clave para usar el SDK de Gemini. Si no la pones, la app funcionará en modo local/echo.
- GEMINI_MODEL — modelo de Gemini a usar (por defecto `gemini-2.5-flash`).
- DB_HOST — host de la base de datos (por ejemplo `localhost`).
- DB_USER — usuario MySQL (ej. `root`).
- DB_PASSWORD — contraseña MySQL.
- DB_NAME — nombre de la base de datos (por defecto `chatai`).

Importante: NO comites tu `.env` con claves. Usa `.env.example` como plantilla.

Configurar la base de datos

1. Crear la base de datos y la tabla (usa `script.sql`):

- Si tienes acceso a la línea de comandos de MySQL:

```bat
mysql -u root -p < script.sql
```

- O importar el contenido de `script.sql` desde tu cliente MySQL preferido.

2. Cargar `CAEDEC1.csv` a la tabla `informacion`.

Ejemplo (MySQL) usando `LOAD DATA LOCAL INFILE` — ajustar separador y orden de columnas según tu CSV:

```sql
LOAD DATA LOCAL INFILE 'D:/Trabajando/Python/chatai/CAEDEC1.csv'
INTO TABLE informacion
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(nombre, nombreLargo, caedec, descripcion);
```

Notas:
- Si MySQL rechaza `LOCAL` debes activar `local_infile=1` en la configuración o usar una herramienta (MySQL Workbench, DBeaver) para importar.
- Asegúrate del orden y número de columnas en el CSV. Si tiene más columnas, crea un script Python para parsear y hacer INSERTs.



Ejecutar la aplicación

Desde cmd.exe (con entorno virtual activado):

```bat
python app.py
```

La aplicación escuchará por defecto en `http://127.0.0.1:5000/`.


Comportamiento y reglas de la IA

- Si está configurado el SDK y la clave (GEMINI_API_KEY), `generate_ai_response_with_context` enviará un prompt con los datos de la BD y pedirá una respuesta natural.
- Si el SDK o la clave no están presentes, la aplicación devuelve una respuesta local simple usando el primer registro encontrado.
- La IA (cuando se usa) está instruida a NO inventar información y a responder SOLO con los datos de la base de datos.

Notas de desarrollo y mantenimiento

- `app.py` usa `pymysql` con `DictCursor`.
- `search_in_database` construye una puntuación de relevancia para ordenar resultados. Revisa SQL y parámetros si vas a migrar a otro motor o tabla con otros nombres.
- El frontend es estático (no requiere build); solo sirve los archivos en `templates/` y `static/`.


