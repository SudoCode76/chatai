"""
Script de prueba para buscar el registro específico mencionado por el usuario
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import search_in_database, generate_ai_response_with_context

print("=" * 80)
print("PRUEBA CON REGISTRO ESPECÍFICO")
print("=" * 80)

# Test 1: Buscar "SERV HOLANDES DE COOP AL DESARROLLO"
print("\n1. Buscando 'SERV HOLANDES' o 'HOLANDES'...")
print("-" * 80)
results = search_in_database("HOLANDES", limit=10)
if results:
    print(f"✓ Encontrados {len(results)} registros:")
    for i, row in enumerate(results[:5], 1):
        print(f"\n  {i}. Nombre: {row.get('nombre', 'N/A')}")
        print(f"     Nombre Largo: {row.get('nombreLargo', 'N/A')}")
        print(f"     CAEDEC: {row.get('caedec', 'N/A')}")
        print(f"     Descripción: {row.get('descripcion', 'N/A')}")
else:
    print("✗ No se encontraron resultados")

# Test 2: Pregunta específica como en la captura
print("\n\n2. Pregunta: 'hola'")
print("-" * 80)
query = "hola"
results = search_in_database(query, limit=5)
print(f"Resultados encontrados: {len(results)}")
if results:
    print("\nPrimeros resultados:")
    for i, row in enumerate(results[:3], 1):
        print(f"  {i}. {row.get('nombre', 'N/A')} - CAEDEC: {row.get('caedec', 'N/A')}")

    # Generar respuesta con IA
    print("\nGenerando respuesta con IA...")
    response = generate_ai_response_with_context(query, results)
    print(f"Respuesta: {response}")

# Test 3: Pregunta sobre versión de Gemini (fuera de contexto)
print("\n\n3. Pregunta fuera de contexto: 'que version de gemini eres'")
print("-" * 80)
query = "que version de gemini eres"
results = search_in_database(query, limit=5)
print(f"Resultados encontrados en BD: {len(results)}")
if results:
    print("(La IA debería rechazar esta pregunta aunque haya resultados)")
    response = generate_ai_response_with_context(query, results)
    print(f"Respuesta: {response}")
else:
    print("No hay resultados, la IA rechazará la pregunta")

# Test 4: Pregunta específica sobre CAEDEC
print("\n\n4. Pregunta: 'el caedec 74990 a que corresponde?'")
print("-" * 80)
query = "caedec 74990"
results = search_in_database(query, limit=5)
print(f"Resultados encontrados: {len(results)}")
if results:
    print("\nPrimeros resultados:")
    for i, row in enumerate(results[:3], 1):
        print(f"  {i}. {row.get('nombre', 'N/A')} - CAEDEC: {row.get('caedec', 'N/A')}")
        print(f"      Descripción: {row.get('descripcion', 'N/A')}")

    print("\nGenerando respuesta con IA...")
    response = generate_ai_response_with_context("el caedec 74990 a que corresponde?", results)
    print(f"Respuesta: {response}")

print("\n" + "=" * 80)
print("PRUEBAS COMPLETADAS")
print("=" * 80)

