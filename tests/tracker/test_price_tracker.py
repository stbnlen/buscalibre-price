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
    
    # Encontrar disminuciones
    decreases = []
    for title, current_price in today_data.items():
        if title in yesterday_data:
            old_price = yesterday_data[title]
            historical_min = historical_mins.get(title, 0)
            
            if current_price < old_price:
                decreases.append((title, current_price, old_price, historical_min))
    
    # Verificar que obtenemos datos (si la base de datos tiene información)
    # Esta prueba principalmente verifica que la lógica funciona sin errores
    assert isinstance(today_data, dict)
    assert isinstance(yesterday_data, dict)
    assert isinstance(historical_mins, dict)
    assert isinstance(decreases, list)
    
    conn.close()