#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def create_test_data():
    """Create some test data to verify yesterday vs today comparisons"""
    db_path = Path("buscalibre_prices.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get today and yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    print(f"Fecha actual: {today}")
    print(f"Fecha ayer: {yesterday}")
    
    # Check if we have any books in today's data
    cursor.execute('''
        SELECT title, price FROM book_prices WHERE date = ? LIMIT 5
    ''', (today,))
    today_books = cursor.fetchall()
    
    if today_books:
        print(f"Insertando datos de prueba para ayer basado en {len(today_books)} libros de hoy...")
        
        # Insert yesterday's data with slightly modified prices
        for title, price in today_books:
            # Vary the price slightly for yesterday (some higher, some lower)
            import random
            variation = random.uniform(-0.1, 0.1)  # +/- 10%
            yesterday_price = price * (1 + variation)
            
            # Insert yesterday's price
            cursor.execute('''
                INSERT OR REPLACE INTO book_prices (title, price, date)
                VALUES (?, ?, ?)
            ''', (title, yesterday_price, yesterday))
            
            print(f"  {title}: Hoy=${price:.2f}, Ayer={yesterday_price:.2f}")
        
        conn.commit()
        print("Datos de prueba insertados correctamente.")
    else:
        print("No hay datos de hoy para crear datos de prueba.")
    
    conn.close()

if __name__ == "__main__":
    create_test_data()