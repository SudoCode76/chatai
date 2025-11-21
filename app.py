from flask import Flask, render_template, request, jsonify
import os
import pymysql
from typing import List, Dict, Any

# Intentamos importar el SDK oficial de Google GenAI si está instalado
try:
    from google import genai
except Exception:
    genai = None

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'chatai'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db_connection():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None


def search_in_database(query: str, limit: int = 10) -> List[Dict[str, Any]]:

    connection = get_db_connection()
    if not connection:
        return []

    STOP_WORDS = {
        'el', 'la', 'de', 'del', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'es', 'son', 'esta', 'este', 'esa', 'ese', 'cual', 'que', 'quien',
        'como', 'donde', 'cuando', 'por', 'para', 'con', 'sin', 'sobre',
        'en', 'al', 'a', 'y', 'o', 'pero', 'si', 'no', 'me', 'te', 'se',
        'cual', 'cuales', 'cuanto', 'cuantos', 'tiene', 'tienen', 'hay',
        'eres', 'soy', 'somos', 'tengo', 'tienes', 'ser', 'estar',
        'empresa', 'empresas', 'empresarial', 'empresariales',
        'compania', 'compañia', 'companias', 'compañias',
        'sociedad', 'sociedades', 'sa', 'srl', 'ltda',
        'informacion', 'información', 'datos', 'dato',
        'caedec', 'caeded', 'codigo', 'código', 'numero', 'número',
        'nombre', 'llamada', 'llama', 'llamado', 'llamados'
    }

    try:
        with connection.cursor() as cursor:
            # Extraer palabras clave de la consulta y convertir a mayúsculas
            keywords = query.upper().split()

            # Detectar si hay números (posible CAEDEC)
            numbers = [k for k in keywords if k.isdigit()]
            # Filtrar palabras de texto: longitud >= 2, no números, no stop words
            text_keywords = [k for k in keywords if len(k) >= 2 and not k.isdigit() and k.lower() not in STOP_WORDS]

            # Si hay números, buscar por CAEDEC exacto primero
            if numbers and not text_keywords:
                caedec_conditions = []
                caedec_params = []
                for num in numbers:
                    try:
                        caedec_value = int(num)
                        caedec_conditions.append("caedec = %s")
                        caedec_params.append(caedec_value)
                    except ValueError:
                        pass

                if caedec_conditions:
                    sql = f"SELECT * FROM informacion WHERE {' OR '.join(caedec_conditions)} LIMIT %s"
                    cursor.execute(sql, caedec_params + [limit])
                    return cursor.fetchall()

            # Construir búsqueda por texto
            if not text_keywords and not numbers:
                # Si no hay palabras clave válidas, devolver registros aleatorios
                sql = "SELECT * FROM informacion ORDER BY RAND() LIMIT %s"
                cursor.execute(sql, (limit,))
                return cursor.fetchall()

            # Construir cálculo de relevancia dinámico y condiciones de búsqueda
            # Usar UPPER() para hacer la búsqueda case-insensitive
            relevance_parts = []
            search_conditions = []
            all_params = []
            relevance_params = []

            # Procesar palabras de texto
            for keyword in text_keywords:
                search_param = f"%{keyword}%"

                # Condición de búsqueda (OR) - case-insensitive usando UPPER()
                search_conditions.append(
                    "(UPPER(nombre) LIKE %s OR UPPER(nombreLargo) LIKE %s OR UPPER(descripcion) LIKE %s)"
                )
                all_params.extend([search_param, search_param, search_param])

                # Puntuación por relevancia (usando parámetros) - case-insensitive
                relevance_parts.append("(CASE WHEN UPPER(nombre) LIKE %s THEN 3 ELSE 0 END)")
                relevance_parts.append("(CASE WHEN UPPER(nombreLargo) LIKE %s THEN 2 ELSE 0 END)")
                relevance_parts.append("(CASE WHEN UPPER(descripcion) LIKE %s THEN 1 ELSE 0 END)")
                relevance_params.extend([search_param, search_param, search_param])

            # Procesar números (CAEDEC)
            if numbers:
                for num in numbers:
                    try:
                        caedec_value = int(num)
                        search_conditions.append("caedec = %s")
                        all_params.append(caedec_value)
                        relevance_parts.append("(CASE WHEN caedec = %s THEN 10 ELSE 0 END)")
                        relevance_params.append(caedec_value)
                    except ValueError:
                        pass

            if not search_conditions:
                sql = "SELECT * FROM informacion ORDER BY RAND() LIMIT %s"
                cursor.execute(sql, (limit,))
                return cursor.fetchall()

            relevance_sql = " + ".join(relevance_parts)

            sql = f"""
                SELECT *, 
                ({relevance_sql}) as relevancia
                FROM informacion
                WHERE {' OR '.join(search_conditions)}
                ORDER BY relevancia DESC
                LIMIT %s
            """

            # Combinar todos los parámetros: relevancia + búsqueda + limit
            final_params = relevance_params + all_params + [limit]
            cursor.execute(sql, final_params)
            results = cursor.fetchall()
            return results

    except Exception as e:
        print(f"Error buscando en la base de datos: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        connection.close()


def format_db_results(results: List[Dict[str, Any]]) -> str:
    """Formatea los resultados de la base de datos en un texto legible."""
    if not results:
        return "No se encontró información relevante en la base de datos."

    formatted = "Información encontrada en la base de datos:\n\n"
    for i, row in enumerate(results, 1):
        formatted += f"{i}. "
        if row.get('nombre'):
            formatted += f"Nombre: {row['nombre']}"
        if row.get('nombreLargo'):
            formatted += f" ({row['nombreLargo']})"
        if row.get('caedec'):
            formatted += f" - CAEDEC: {row['caedec']}"
        if row.get('descripcion'):
            formatted += f"\n   Descripción: {row['descripcion']}"
        formatted += "\n\n"

    return formatted


def generate_ai_response_with_context(user_question: str, db_results: List[Dict[str, Any]]) -> str:
    """
    Genera una respuesta conversacional usando la IA de Gemini con datos de la base de datos.
    La IA responde de forma natural, pero SOLO con información de la BD.
    """
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    if not genai or not gemini_key:
        # Si no hay API disponible, devolver respuesta simple
        if not db_results:
            return "No encontré información sobre eso en la base de datos."
        # Formatear una respuesta básica
        first = db_results[0]
        return f"Encontré información sobre {first.get('nombre', 'este registro')}: {first.get('descripcion', 'Sin descripción')}"

    try:
        os.environ.setdefault('GEMINI_API_KEY', gemini_key)
        try:
            client = genai.Client(api_key=gemini_key)
        except TypeError:
            client = genai.Client()

        # Preparar los datos en formato estructurado para el prompt
        db_info = ""
        for row in db_results:
            db_info += f"\n- Nombre: {row.get('nombre', 'N/A')}"
            if row.get('nombreLargo'):
                db_info += f"\n  Nombre completo: {row.get('nombreLargo')}"
            if row.get('caedec'):
                db_info += f"\n  CAEDEC: {row.get('caedec')}"
            if row.get('descripcion'):
                db_info += f"\n  Descripción: {row.get('descripcion')}"
            db_info += "\n"

        # Prompt optimizado para conversación natural
        system_prompt = f"""Eres un asistente conversacional que ayuda a los usuarios con información de una base de datos de empresas y actividades económicas.

REGLAS IMPORTANTES:
1. Responde de forma NATURAL y CONVERSACIONAL, como si fueras un asistente humano amigable.
2. SOLO usa la información que se te proporciona del contexto de la base de datos a continuación.
3. NO inventes datos ni uses información externa o conocimiento general.
4. Si te preguntan sobre temas NO relacionados con la base de datos (clima, fecha actual, noticias, recetas, programación, matemáticas, etc.), responde amablemente: "Lo siento, solo tengo acceso a información de empresas y actividades económicas en mi base de datos. No puedo ayudarte con ese tema debido a las restricciones de la aplicación."
5. Si NO encuentras información relevante en los datos proporcionados, di: "No encontré información sobre eso en la base de datos."
6. Responde de forma DIRECTA y CONCISA, sin listar todos los registros a menos que te lo pidan explícitamente.
7. Si te preguntan por un dato específico (como CAEDEC, descripción, nombre), proporciona SOLO ese dato de forma clara.
8. Mantén un tono amable y profesional.

DATOS DISPONIBLES DE LA BASE DE DATOS:
{db_info}

PREGUNTA DEL USUARIO:
{user_question}

Responde de forma natural y conversacional, usando ÚNICAMENTE la información proporcionada arriba."""

        response = client.models.generate_content(
            model=gemini_model,
            contents=system_prompt
        )

        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "No pude generar una respuesta en este momento."

    except Exception as e:
        print(f"Error al generar respuesta con IA: {e}")
        if not db_results:
            return "No encontré información sobre eso en la base de datos."
        # Respuesta de emergencia
        first = db_results[0]
        return f"Encontré que {first.get('nombre', 'este registro')} tiene el CAEDEC {first.get('caedec', 'desconocido')}: {first.get('descripcion', 'Sin descripción')}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """
    Recibe una pregunta del usuario y responde usando SOLO información de la base de datos.
    """
    data = request.get_json() or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400

    try:
        # Buscar información relevante en la base de datos
        db_results = search_in_database(message, limit=5)

        if not db_results:
            return jsonify({
                'reply': 'Lo siento, no encontré información relevante en la base de datos para responder tu pregunta. Por favor, intenta reformular tu pregunta o pregunta sobre empresas o actividades económicas que puedan estar en nuestros registros.'
            })

        # Generar respuesta con IA usando los resultados de la base de datos
        ai_response = generate_ai_response_with_context(message, db_results)

        return jsonify({'reply': ai_response})

    except Exception as e:
        print(f"Error en el endpoint /chat: {e}")
        return jsonify({
            'error': 'Error al procesar tu pregunta',
            'detail': str(e)
        }), 500
        return jsonify({
            'error': 'Error al procesar tu pregunta',
            'detail': str(e)
        }), 500


@app.route('/status')
def status():
    """Devuelve información de diagnóstico sobre la configuración."""
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    sdk_installed = genai is not None
    has_key = bool(gemini_key)

    # Verificar conexión a la base de datos
    db_connected = False
    db_records = 0
    try:
        connection = get_db_connection()
        if connection:
            db_connected = True
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM informacion")
                result = cursor.fetchone()
                db_records = result['count'] if result else 0
            connection.close()
    except Exception as e:
        print(f"Error verificando base de datos: {e}")

    # Determinar el modo: 'sdk' si tiene API key y SDK, sino 'echo'
    mode = 'sdk' if (sdk_installed and has_key) else 'echo'

    return jsonify({
        'sdk_installed': sdk_installed,
        'has_key': has_key,
        'gemini_model': gemini_model,
        'db_connected': db_connected,
        'db_records': db_records,
        'mode': mode
    })


@app.route('/test_db')
def test_db():
    """Endpoint de prueba para verificar la conexión a la base de datos."""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM informacion")
            result = cursor.fetchone()
            count = result['count'] if result else 0

            cursor.execute("SELECT * FROM informacion LIMIT 3")
            samples = cursor.fetchall()

        connection.close()

        return jsonify({
            'status': 'connected',
            'total_records': count,
            'sample_records': samples
        })
    except Exception as e:
        return jsonify({
            'error': 'Error al conectar con la base de datos',
            'detail': str(e)
        }), 500


# Print minimal startup diagnostics
print('__STARTUP__: SDK_installed=' + str(genai is not None) +
      ", GEMINI_API_KEY_set=" + str(bool(os.getenv('GEMINI_API_KEY'))) +
      ", DB_configured=" + str(DB_CONFIG['database']))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

