"""Configuración y fixtures para las pruebas de pytest"""

import pytest
import sqlite3
from datetime import date, timedelta
from pathlib import Path
import tempfile
import os

@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para pruebas"""
    # Crear un archivo temporal
    fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)  # Cerrar el descriptor de archivo
    
    # Crear la base de datos y tablas
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE book_prices (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(title, date)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE price_changes (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            change_type TEXT NOT NULL,
            difference REAL NOT NULL,
            new_price REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insertar datos de prueba
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Datos de ayer (precios más altos)
    cursor.execute('''
        INSERT INTO book_prices (title, price, date) VALUES
        ('Libro A', 25.00, ?),
        ('Libro B', 15.50, ?),
        ('Libro C', 30.00, ?)
    ''', (yesterday, yesterday, yesterday))
    
    # Datos de hoy (algunos precios disminuyeron)
    cursor.execute('''
        INSERT INTO book_prices (title, price, date) VALUES
        ('Libro A', 20.00, ?),  -- Precio disminuyó
        ('Libro B', 15.50, ?),  -- Precio igual
        ('Libro C', 35.00, ?),  -- Precio aumentó
        ('Libro D', 12.00, ?)   -- Libro nuevo
    ''', (today, today, today, today))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Limpiar después de la prueba
    os.unlink(db_path)

@pytest.fixture
def db_connection(temp_db):
    """Proporciona una conexión a la base de datos de prueba"""
    conn = sqlite3.connect(temp_db)
    yield conn
    conn.close()

@pytest.fixture
def sample_price_data():
    """Datos de muestra para pruebas que no requieren base de datos"""
    return {
        'today': {
            'Libro A': 20.00,
            'Libro B': 15.50,
            'Libro C': 35.00,
            'Libro D': 12.00
        },
        'yesterday': {
            'Libro A': 25.00,
            'Libro B': 15.50,
            'Libro C': 30.00
        },
        'historical_mins': {
            'Libro A': 18.00,
            'Libro B': 14.00,
            'Libro C': 28.00,
            'Libro D': 12.00
        }
    }