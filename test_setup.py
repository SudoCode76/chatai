"""
Script de prueba para verificar la conexión a MySQL y el funcionamiento básico.
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("VERIFICACIÓN DE CONFIGURACIÓN")
print("=" * 60)

# 1. Verificar pymysql
try:
    import pymysql
    print("✓ pymysql instalado correctamente")
except ImportError:
    print("✗ ERROR: pymysql no está instalado")
    print("  Ejecuta: pip install pymysql")
    exit(1)

# 2. Verificar configuración de la base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'chatai'),
}

print(f"\nConfiguración de la base de datos:")
print(f"  Host: {DB_CONFIG['host']}")
print(f"  Usuario: {DB_CONFIG['user']}")
print(f"  Base de datos: {DB_CONFIG['database']}")

# 3. Intentar conectar
print("\nIntentando conectar a MySQL...")
try:
    connection = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("✓ Conexión exitosa a MySQL")

    # 4. Verificar la tabla
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'informacion'")
        result = cursor.fetchone()
        if result:
            print("✓ Tabla 'informacion' encontrada")

            # Contar registros
            cursor.execute("SELECT COUNT(*) as count FROM informacion")
            count_result = cursor.fetchone()
            total = count_result['count'] if count_result else 0
            print(f"✓ Total de registros: {total:,}")

            # Mostrar estructura de la tabla
            cursor.execute("DESCRIBE informacion")
            columns = cursor.fetchall()
            print("\nEstructura de la tabla:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")

            # Mostrar ejemplos
            if total > 0:
                cursor.execute("SELECT * FROM informacion LIMIT 3")
                samples = cursor.fetchall()
                print(f"\nPrimeros 3 registros de ejemplo:")
                for i, row in enumerate(samples, 1):
                    print(f"\n  Registro {i}:")
                    for key, value in row.items():
                        if value:
                            display_value = str(value)[:50] + "..." if len(str(value)) > 50 else value
                            print(f"    {key}: {display_value}")
        else:
            print("✗ ERROR: La tabla 'informacion' no existe")
            print("  Crea la tabla usando el script SQL en README.md")

    connection.close()

except pymysql.err.OperationalError as e:
    print(f"✗ ERROR de conexión: {e}")
    print("\nPosibles soluciones:")
    print("  1. Verifica que XAMPP esté corriendo")
    print("  2. Verifica que MySQL esté activo (puerto 3306)")
    print("  3. Revisa las credenciales en el archivo .env")
except Exception as e:
    print(f"✗ ERROR: {e}")

# 5. Verificar Google Gemini
print("\n" + "=" * 60)
print("VERIFICACIÓN DE GOOGLE GEMINI AI")
print("=" * 60)

gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    print(f"✓ API Key configurada (termina en: ...{gemini_key[-10:]})")
else:
    print("✗ WARNING: GEMINI_API_KEY no está configurada")

try:
    from google import genai
    print("✓ google-genai instalado correctamente")
except ImportError:
    print("✗ WARNING: google-genai no está instalado")
    print("  Ejecuta: pip install google-genai")

print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)
print("Si todos los checks pasaron (✓), la aplicación está lista.")
print("Ejecuta: python app.py")
print("Luego visita: http://127.0.0.1:5000")
print("=" * 60)

