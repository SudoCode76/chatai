# Chatbot Flask + Gemini Studio (demo)

Este proyecto muestra un chatbot en Flask que usa el SDK oficial `google-genai` si está disponible (recomendado) o hace llamadas HTTP directas a un `GEMINI_API_URL` si prefieres no usar el SDK.

Requisitos
- Python 3.9+

Instalación

1. Crear y activar un entorno virtual (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate
```

2. Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

Configuración (.env)
- Crea un archivo `.env` en la raíz del proyecto con tu clave:

```dotenv
GEMINI_API_KEY=AlzaSyAMom0MaigWhnaPMOmnmCIfzbSlefADCJA
# Opcional: modelo por defecto
GEMINI_MODEL=gemini-2.5-flash
# Si prefieres llamar a una URL concreta con la key como query param:
# GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta2/projects/715827378861/locations/global/models/text-bison-001:generate
# GEMINI_USE_KEY_IN_QUERY=1
```

Uso

```powershell
python app.py
```

Abre http://127.0.0.1:5000 en tu navegador.

Detalles
- Si `google-genai` está instalado y `GEMINI_API_KEY` está definido, la app usará el SDK (`client.models.generate_content`) que es la forma recomendada por la documentación.
- Si no usas el SDK, puedes definir `GEMINI_API_URL` y `GEMINI_API_KEY` y la app hará un POST con JSON al endpoint (soporta enviar la key con header Authorization o como query param si pones `GEMINI_USE_KEY_IN_QUERY=1`).

Notas de seguridad
- No subas `.env` al repositorio. Añade tu `.env` a `.gitignore`.

Próximos pasos posibles
- Añadir tests automáticos.
- Soporte de streaming para respuestas incrementales.
- Mejor manejo de errores y logs.
