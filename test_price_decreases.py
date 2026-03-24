#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def test_price_decreases():
    """Prueba la lógica de detección de disminuciones de precio"""
    db_path = Path("buscalibre_prices.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener fecha actual y ayer
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    print(f"Fecha actual: {today}")
    print(f"Fecha ayer: {yesterday}")
    
    # Obtener precios de hoy
    cursor.execute('''
        SELECT title, price FROM book_prices WHERE date = ?
    ''', (today,))
    today_data = dict(cursor.fetchall())
    
    # Obtener precios de ayer
    cursor.execute('''
        SELECT title, price FROM book_prices WHERE date = ?
    ''', (yesterday,))
    yesterday_data = dict(cursor.fetchall())
    
    # Obtener precios mínimos históricos
    cursor.execute('''
        SELECT title, MIN(price) FROM book_prices GROUP BY title
    ''')
    historical_mins = dict(cursor.fetchall())
    
    print(f"\nLibros con datos de hoy: {len(today_data)}")
    print(f"Libros con datos de ayer: {len(yesterday_data)}")
    
    # Encontrar disminuciones
    decreases = []
    for title, current_price in today_data.items():
        if title in yesterday_data:
            old_price = yesterday_data[title]
            historical_min = historical_mins.get(title, 0)
            
            if current_price < old_price:
                decreases.append((title, current_price, old_price, historical_min))
    
    print(f"\nLibros con precio disminuido: {len(decreases)}")
    
    if decreases:
        print("\n" + "="*90)
        print("LIBROS CON PRECIO DISMINUIDO RESPECTO AL DÍA ANTERIOR:")
        print("="*90)
        for title, current_price, previous_price, historical_min in decreases[:10]:  # Mostrar solo los primeros 10
            print(f"Título: {title}")
            print(f"  Precio actual: ${current_price:,.2f}")
            print(f"  Precio del día anterior: ${previous_price:,.2f}")
            print(f"  Precio mínimo histórico: ${historical_min:,.2f}")
            print()
    else:
        print("No se encontraron libros con precio disminuido respecto al día anterior.")
    
    conn.close()

if __name__ == "__main__":
    test_price_decreases()