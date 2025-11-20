from flask import Flask, render_template, request, jsonify
import os

# Intentamos importar requests de forma segura
try:
    import requests
except Exception:
    requests = None

# Intentamos importar el SDK oficial de Google GenAI si está instalado
try:
    from google import genai
except Exception:
    genai = None

try:
    from dotenv import load_dotenv
except Exception:
    # Definimos un stub si python-dotenv no está disponible
    def load_dotenv(*args, **kwargs):
        return

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Recibe JSON {"message": "..."} y devuelve {"reply": "..."}.

    Lógica:
    - Si está disponible el SDK `genai` y hay `GEMINI_API_KEY`, usar el SDK (no necesita URL).
    - Si no, si hay `GEMINI_API_URL` y `GEMINI_API_KEY`, usar requests para llamar al endpoint (soporta key en query o header).
    - Si no hay credenciales/url, usar fallback local (Echo).
    """
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'No message provided'}), 400

    gemini_url = os.getenv('GEMINI_API_URL')
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    def local_fallback_reply(message: str) -> str:
        """Genera una respuesta local simple (reglas heurísticas) cuando la API externa no está disponible.

        Esto mejora la UX temporalmente mientras se resuelve la cuota.
        """
        m = message.lower()
        if any(g in m for g in ['hola', 'buenas', 'buenos']):
            return '¡Hola! Puedo responder preguntas simples, resumir texto y darte ideas. (Respuesta local en modo offline)'
        if 'que puedes' in m or 'qué puedes' in m or 'puedes hacer' in m:
            return 'Puedo responder preguntas generales, explicar conceptos, y ayudarte a escribir código. Para respuestas más completas usa una API con cuota disponible.'
        if any(q in m for q in ['?', 'cómo', 'como', 'por qué', 'qué', 'quién', 'cuando', 'cuándo']):
            return 'Lo siento, ahora no puedo acceder al modelo remoto por límites de cuota; de todos modos puedo dar una respuesta breve: intenta preguntar de nuevo o pide aumento de cuota en Google Cloud.'
        # default
        return f"Lo siento, no puedo acceder al modelo remoto en este momento. (Respuesta local): {message}"

    # 1) Intentar usar SDK oficial si está presente y hay API key
    if genai is not None and gemini_key:
        try:
            # Asegurarnos de que el SDK pueda leer la key desde env si lo necesita
            os.environ.setdefault('GEMINI_API_KEY', gemini_key)
            try:
                client = genai.Client(api_key=gemini_key)
            except TypeError:
                # versiones antiguas del SDK pueden no aceptar api_key como arg
                client = genai.Client()

            # Intentar con reintentos suaves si hay fallos temporales (no para cuota 0)
            max_retries = 2
            backoff = 1
            last_exc = None
            response = None
            for attempt in range(max_retries + 1):
                try:
                    response = client.models.generate_content(model=gemini_model, contents=message)
                    break
                except Exception as e:
                    last_exc = e
                    serr = str(e)
                    # Si detectamos cuota explícita con valor 0, no reintentamos
                    if 'quota_limit_value' in serr and "'0'" in serr:
                        break
                    # Si es claramente quota exhausted, no insistir mucho
                    if 'RESOURCE_EXHAUSTED' in serr or 'Quota exceeded' in serr or 'quota' in serr.lower():
                        # fallamos rápido
                        break
                    if attempt < max_retries:
                        import time
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        break

            if response is None:
                # No se obtuvo respuesta válida
                serr = str(last_exc) if last_exc is not None else 'Unknown error'
                # Detectar si es error de cuota para devolver status 429 y link útil
                if 'RESOURCE_EXHAUSTED' in serr or 'Quota exceeded' in serr or 'quota' in serr.lower():
                    help_url = 'https://cloud.google.com/docs/quotas/help/request_increase'
                    # intentar extraer project id si aparece en el mensaje
                    import re
                    m = re.search(r"projects/(\d+)", serr)
                    consumer_project = m.group(1) if m else None
                    return jsonify({
                        'error': 'Quota exceeded',
                        'detail': serr,
                        'consumer_project': consumer_project,
                        'help': f'Request more quota at {help_url}',
                        'quota_action': 'request_increase',
                        'fallback_reply': local_fallback_reply(message)
                    }), 429
                return jsonify({'error': 'Error contacting Gemini via SDK', 'detail': serr, 'fallback_reply': local_fallback_reply(message)}), 500

            # El SDK expone la respuesta en response.text según la doc
            # response está garantizado a no ser None aquí por el if anterior
            if response is not None:
                reply = getattr(response, 'text', None)
                if not reply:
                    # Fallback: intentar representar el objeto
                    reply = str(response)
                return jsonify({'reply': reply})
            else:
                return jsonify({'error': 'No response from SDK', 'fallback_reply': local_fallback_reply(message)}), 500
        except Exception as e:
            # Manejo final por si surge alguna excepción no prevista
            serr = str(e)
            if 'RESOURCE_EXHAUSTED' in serr or 'Quota exceeded' in serr or 'quota' in serr.lower():
                help_url = 'https://cloud.google.com/docs/quotas/help/request_increase'
                return jsonify({
                    'error': 'Quota exceeded',
                    'detail': serr,
                    'help': f'Request more quota at {help_url}',
                    'quota_action': 'request_increase',
                    'fallback_reply': local_fallback_reply(message)
                }), 429
            return jsonify({'error': 'Error contacting Gemini via SDK', 'detail': serr, 'fallback_reply': local_fallback_reply(message)}), 500

    # 2) Si no hay SDK, intentar usar requests con GEMINI_API_URL + GEMINI_API_KEY
    if gemini_url and gemini_key:
        if requests is None:
            return jsonify({'error': 'Server misconfigured: requests library not installed. Run `pip install requests`'}), 500
        try:
            headers = {
                'Content-Type': 'application/json'
            }

            # Opción para usar la key como query param
            use_key_in_query = os.getenv('GEMINI_USE_KEY_IN_QUERY', '0') in ['1', 'true', 'True']
            url = gemini_url
            if use_key_in_query:
                if 'key=' not in url:
                    sep = '&' if '?' in url else '?'
                    url = f"{url}{sep}key={gemini_key}"
            else:
                headers['Authorization'] = f'Bearer {gemini_key}'

            payload = {
                'prompt': message
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            j = None
            try:
                j = resp.json()
            except Exception:
                # no json
                pass

            reply = None
            if j is not None and isinstance(j, dict):
                if 'candidates' in j and isinstance(j.get('candidates'), list) and j['candidates']:
                    candidates = j['candidates']
                    first = candidates[0]
                    if isinstance(first, dict):
                        reply = first.get('content') or first.get('message') or None
                if not reply and 'output' in j:
                    reply = j.get('output')
                if not reply and 'reply' in j:
                    reply = j.get('reply')
                if not reply and 'choices' in j and isinstance(j.get('choices'), list) and j['choices']:
                    choices = j['choices']
                    ch = choices[0]
                    if isinstance(ch, dict):
                        msg = ch.get('message')
                        if isinstance(msg, dict):
                            reply = msg.get('content')
                        reply = reply or ch.get('text')
            if not reply:
                reply = resp.text

            return jsonify({'reply': reply})
        except Exception as e:
            return jsonify({'error': 'Error contacting Gemini API', 'detail': str(e)}), 500

    # 3) Fallback local
    fallback = local_fallback_reply(message)
    return jsonify({'reply': fallback})


@app.route('/status')
def status():
    """Devuelve información de diagnóstico sobre la configuración (no expone la clave)."""
    gemini_url = os.getenv('GEMINI_API_URL')
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    sdk_installed = genai is not None
    has_key = bool(gemini_key)
    mode = 'echo'
    if sdk_installed and has_key:
        mode = 'sdk'
    elif gemini_url and has_key:
        mode = 'rest'

    return jsonify({
        'sdk_installed': sdk_installed,
        'has_key': has_key,
        'gemini_model': gemini_model,
        'gemini_url_set': bool(gemini_url),
        'mode': mode
    })


@app.route('/debug/set_key', methods=['POST'])
def debug_set_key():
    """Establece GEMINI_API_KEY en tiempo de ejecución (solo localhost). Útil para pruebas locales sin reiniciar.

    POST JSON: {"api_key": "..."}
    """
    # Aceptar solo peticiones desde localhost para mayor seguridad
    remote = request.remote_addr or ''
    if not (remote.startswith('127.') or remote == '::1' or remote == 'localhost'):
        return jsonify({'error': 'forbidden', 'detail': 'only allowed from localhost'}), 403

    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': 'no api_key provided'}), 400

    os.environ['GEMINI_API_KEY'] = api_key
    # reload dotenv if present (no-op if not)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass

    return jsonify({'status': 'ok', 'gemini_key_set': True})


@app.route('/debug/clear_key', methods=['POST'])
def debug_clear_key():
    """Elimina GEMINI_API_KEY en tiempo de ejecución (solo localhost)."""
    remote = request.remote_addr or ''
    if not (remote.startswith('127.') or remote == '::1' or remote == 'localhost'):
        return jsonify({'error': 'forbidden', 'detail': 'only allowed from localhost'}), 403

    os.environ.pop('GEMINI_API_KEY', None)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    return jsonify({'status': 'ok', 'gemini_key_set': False})


# Print minimal startup diagnostics (no key value)
print('__STARTUP__: SDK_installed=' + str(genai is not None) + ", GEMINI_API_URL_set=" + str(bool(os.getenv('GEMINI_API_URL'))) + ", GEMINI_API_KEY_set=" + str(bool(os.getenv('GEMINI_API_KEY'))))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
