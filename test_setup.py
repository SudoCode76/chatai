"""Script de prueba para verificar la configuración del chatbot."""
import os
from dotenv import load_dotenv

load_dotenv()

print("=== Verificación de Configuración ===\n")

# Verificar variables de entorno
gemini_key = os.getenv('GEMINI_API_KEY')
gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

print(f"✓ GEMINI_API_KEY está configurada: {'Sí' if gemini_key else 'No'}")
if gemini_key:
    print(f"  - Primeros 10 caracteres: {gemini_key[:10]}...")
print(f"✓ GEMINI_MODEL: {gemini_model}")

# Verificar importaciones
print("\n=== Verificación de Dependencias ===\n")

try:
    import flask
    print(f"✓ Flask instalado (versión: {flask.__version__})")
except ImportError:
    print("✗ Flask NO instalado")

try:
    import requests
    print(f"✓ Requests instalado (versión: {requests.__version__})")
except ImportError:
    print("✗ Requests NO instalado")

try:
    from google import genai
    print("✓ google-genai instalado")
except ImportError:
    print("✗ google-genai NO instalado")

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv instalado")
except ImportError:
    print("✗ python-dotenv NO instalado")

# Prueba de conexión con la API
if gemini_key:
    print("\n=== Prueba de Conexión con API ===\n")
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        print("✓ Cliente creado exitosamente")

        # Intentar una prueba simple
        try:
            response = client.models.generate_content(
                model=gemini_model,
                contents="Hola, responde solo con 'OK' si funciona"
            )
            reply = getattr(response, 'text', str(response))
            print(f"✓ API respondió correctamente")
            print(f"  - Respuesta: {reply[:100]}...")
        except Exception as e:
            print(f"✗ Error al llamar a la API: {str(e)[:200]}")
    except Exception as e:
        print(f"✗ Error al crear el cliente: {str(e)[:200]}")

print("\n=== Resumen ===\n")
print("Si todas las verificaciones son exitosas (✓), tu chatbot está listo.")
print("Para ejecutar la aplicación, usa: python app.py")
print("Luego abre http://127.0.0.1:5000 en tu navegador.")

