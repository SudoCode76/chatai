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

# Configuración de la base de datos MySQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'chatai'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db_connection():
    """Obtiene una conexión a la base de datos MySQL."""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None


def search_in_database(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Busca información en la base de datos basándose en la consulta del usuario.
    Utiliza búsqueda por palabras clave en todos los campos de texto.
    """
    connection = get_db_connection()
    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            # Extraer palabras clave de la consulta
            keywords = query.lower().split()

            # Construir la consulta SQL con búsqueda LIKE para cada palabra clave
            search_conditions = []
            params = []

            for keyword in keywords:
                if len(keyword) > 2:  # Ignorar palabras muy cortas
                    search_param = f"%{keyword}%"
                    search_conditions.append(
                        "(nombre LIKE %s OR nombreLargo LIKE %s OR descripcion LIKE %s)"
                    )
                    params.extend([search_param, search_param, search_param])

            if not search_conditions:
                # Si no hay palabras clave válidas, devolver registros aleatorios
                sql = "SELECT * FROM informacion ORDER BY RAND() LIMIT %s"
                cursor.execute(sql, (limit,))
            else:
                # Buscar registros que coincidan con las palabras clave
                sql = f"""
                    SELECT *, 
                    (
                        (CASE WHEN nombre LIKE %s THEN 3 ELSE 0 END) +
                        (CASE WHEN nombreLargo LIKE %s THEN 2 ELSE 0 END) +
                        (CASE WHEN descripcion LIKE %s THEN 1 ELSE 0 END)
                    ) as relevancia
                    FROM informacion
                    WHERE {' OR '.join(search_conditions)}
                    ORDER BY relevancia DESC
                    LIMIT %s
                """
                # Agregar parámetros para el cálculo de relevancia
                first_keyword = f"%{keywords[0]}%" if keywords else "%%"
                relevance_params = [first_keyword, first_keyword, first_keyword]
                cursor.execute(sql, relevance_params + params + [limit])

            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Error buscando en la base de datos: {e}")
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


def generate_ai_response_with_context(user_question: str, db_context: str) -> str:
    """
    Genera una respuesta usando la IA de Gemini con el contexto de la base de datos.
    La IA está restringida a responder SOLO con la información proporcionada.
    """
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')

    if not genai or not gemini_key:
        # Si no hay API disponible, devolver solo el contexto formateado
        return db_context

    try:
        os.environ.setdefault('GEMINI_API_KEY', gemini_key)
        try:
            client = genai.Client(api_key=gemini_key)
        except TypeError:
            client = genai.Client()

        # Crear un prompt muy restrictivo para que la IA solo use la información proporcionada
        system_prompt = f"""Eres un asistente que SOLO puede responder preguntas usando la información proporcionada de una base de datos.

REGLAS ESTRICTAS:
1. SOLO puedes usar la información que aparece en el "CONTEXTO DE LA BASE DE DATOS" que se te proporciona a continuación.
2. Si la pregunta del usuario NO se puede responder con la información disponible, debes decir: "Lo siento, no tengo información sobre eso en mi base de datos."
3. Si el usuario pregunta sobre temas no relacionados con la información de la base de datos (como el clima, noticias, recetas, programación, etc.), debes decir: "Lo siento, solo puedo responder preguntas relacionadas con la información almacenada en mi base de datos. No tengo permitido ayudarte con otros temas."
4. NO inventes información.
5. NO uses conocimiento general que no esté en el contexto proporcionado.
6. Responde de forma clara, natural y conversacional, usando solo los datos que se te proporcionan.
7. Si encuentras información relevante, preséntala de manera organizada y fácil de entender.

CONTEXTO DE LA BASE DE DATOS:
{db_context}

PREGUNTA DEL USUARIO:
{user_question}

Responde la pregunta usando ÚNICAMENTE la información del contexto anterior. Si no hay información relevante, indícalo claramente."""

        response = client.models.generate_content(
            model=gemini_model,
            contents=system_prompt
        )

        if response and hasattr(response, 'text'):
            return response.text
        else:
            return db_context

    except Exception as e:
        print(f"Error al generar respuesta con IA: {e}")
        # En caso de error, devolver el contexto formateado
        return db_context


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
        db_results = search_in_database(message, limit=8)

        if not db_results:
            return jsonify({
                'reply': 'Lo siento, no encontré información relevante en la base de datos para responder tu pregunta. Por favor, intenta reformular tu pregunta o pregunta sobre algo que pueda estar en nuestros registros.'
            })

        # Formatear los resultados
        db_context = format_db_results(db_results)

        # Generar respuesta con IA usando el contexto de la base de datos
        ai_response = generate_ai_response_with_context(message, db_context)

        return jsonify({'reply': ai_response})

    except Exception as e:
        print(f"Error en el endpoint /chat: {e}")
        return jsonify({
            'error': 'Error al procesar tu pregunta',
            'detail': str(e)
        }), 500


@app.route('/status')
def status():
    """Devuelve información de diagnóstico sobre la configuración."""
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')

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

    mode = 'database + ai' if (sdk_installed and has_key and db_connected) else 'database only' if db_connected else 'error'

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

