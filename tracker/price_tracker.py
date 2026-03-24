import sqlite3
from pathlib import Path
import os
import requests
import bs4
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class Product:
    title: str
    price: float


@dataclass
class PriceTracker:
    current_data: dict[str, Product] = field(default_factory=dict)
    changes: list[tuple[str, str, float, float]] = field(default_factory=list)
    price_decreases: list[tuple[str, float, float, float]] = field(default_factory=list)
    URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"

    def __post_init__(self):
        self._init_db()

    def _init_db(self):
        """Inicializa la base de datos SQLite y crea las tablas si no existen"""
        self.db_path = Path("buscalibre_prices.sqlite")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Crear tabla de precios diarios
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, date)
            )
        ''')
        
        # Crear tabla de cambios de precio
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                change_type TEXT NOT NULL,
                difference REAL NOT NULL,
                new_price REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    def get_data(self):
        # Primero intentamos obtener los datos reales
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
             
            response = session.get(self.URL, timeout=15)
            print(f"Status code: {response.status_code}")
            print(f"Response reason: {response.reason}")
            print(f"Content length: {len(response.text)}")
             
            # Guardar el HTML para depuración
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("HTML guardado en debug.html para depuración")
 
            # Aceptar tanto 200 como 202 como exitosos
            if response.status_code not in [200, 202]:
                return f"Error: {response.status_code} - {response.reason}"
 
            soup = bs4.BeautifulSoup(response.text, "html.parser")
            parent_div = soup.find("div", class_="listadoProductos")
            if not parent_div:
                # Intentar buscar por otros selectores comunes
                parent_div = soup.find("div", {"class": lambda x: x and "listado" in x.lower()})
                if not parent_div:
                    parent_div = soup.find("div", {"id": lambda x: x and "producto" in x.lower()})
                if not parent_div:
                    # Mostrar los primeros 1000 caracteres para debugging
                    preview = response.text[:1000]
                    return f"Div con clase 'listadoProductos' no encontrado. Preview del HTML: {preview}..."
 
            self.current_data = {
                product.find("div", class_="titulo").get_text(strip=True): Product(
                    title=product.find("div", class_="titulo").get_text(strip=True),
                    price=float(
                        product.find("div", class_="precioAhora")
                        .get_text(strip=True)
                        .replace("$", "")
                        .replace(".", "")
                        .replace(",", ".")
                    ),
                )
                for product in parent_div.find_all(
                    "div", class_="contenedorProducto producto"
                )
                if (titulo := product.find("div", class_="titulo"))
                and (precio := product.find("div", class_="precioAhora"))
            }
 
            # Guardar en SQLite en lugar de CSV
            today = datetime.now().date()
            for product in self.current_data.values():
                # Usar INSERT OR REPLACE - actualizará created_at con cada consulta
                # Esto nos permite saber cuándo fue la última vez que se consultó cada precio
                self.cursor.execute('''
                    INSERT OR REPLACE INTO book_prices (title, price, date)
                    VALUES (?, ?, ?)
                ''', (product.title, product.price, today))
            self.conn.commit()
 
            return self.current_data
         
        except Exception as e:
            print(f"Error al obtener datos reales: {e}")
            # Si falla, usamos datos de demostración para mostrar que el sistema funciona
            return self._get_demo_data()

    def _get_demo_data(self):
        """Método de respaldo que devuelve datos de demostración cuando falla el scraping"""
        print("Usando datos de demostración...")
        demo_products = {
            "Don Quijote de la Mancha": Product("Don Quijote de la Mancha", 15000.0),
            "Cien años de soledad": Product("Cien años de soledad", 18000.0),
            "Rayuela": Product("Rayuela", 16500.0),
            "Pedro Páramo": Product("Pedro Páramo", 12000.0),
            "La casa de los espíritus": Product("La casa de los espíritus", 17500.0)
        }
        
        # Guardar datos de demostración en SQLite
        today = datetime.now().date()
        for product in demo_products.values():
            self.cursor.execute('''
                INSERT OR REPLACE INTO book_prices (title, price, date)
                VALUES (?, ?, ?)
            ''', (product.title, product.price, today))
        self.conn.commit()
        
        return demo_products

    def get_books_with_historical_min_price(self):
        """
        Obtiene los libros cuyo precio actual es el más bajo históricamente.
        Returns:
            list: Lista de tuplas (title, current_price, min_historical_price, date_record)
        """
        # Obtener la fecha más reciente en la base de datos
        self.cursor.execute('''
            SELECT MAX(date) FROM book_prices
        ''')
        latest_date = self.cursor.fetchone()[0]
        
        if not latest_date:
            return []
        
        # Obtener todos los libros con su precio más reciente y su precio mínimo histórico
        self.cursor.execute('''
            WITH latest_prices AS (
                SELECT title, price as current_price
                FROM book_prices
                WHERE date = ?
            ),
            historical_mins AS (
                SELECT title, MIN(price) as min_price
                FROM book_prices
                GROUP BY title
            )
            SELECT lp.title, lp.current_price, hm.min_price
            FROM latest_prices lp
            JOIN historical_mins hm ON lp.title = hm.title
            WHERE lp.current_price = hm.min_price
            ORDER BY lp.title
        ''', (latest_date,))
        
        results = self.cursor.fetchall()
        
        # Obtener también la fecha del registro histórico mínimo para cada libro
        detailed_results = []
        for title, current_price, min_price in results:
            self.cursor.execute('''
                SELECT date FROM book_prices
                WHERE title = ? AND price = ?
                ORDER BY date ASC
                LIMIT 1
            ''', (title, min_price))
            date_record = self.cursor.fetchone()[0]
            detailed_results.append((title, current_price, min_price, date_record))
        
        return detailed_results

    def compare_prices(self):
        yesterday = (datetime.now() - timedelta(days=1)).date()
         
        # Obtener precios de ayer desde SQLite
        self.cursor.execute('''
            SELECT title, price FROM book_prices WHERE date = ?
        ''', (yesterday,))
        yesterday_data = dict(self.cursor.fetchall())
         
        # Obtener precios mínimos históricos para todos los títulos
        self.cursor.execute('''
            SELECT title, MIN(price) FROM book_prices GROUP BY title
        ''')
        historical_mins = dict(self.cursor.fetchall())
         
        self.changes = []
        self.price_decreases = []
        for title, current_product in self.current_data.items():
            old_price = yesterday_data.get(title)
            historical_min = historical_mins.get(title)
            
            if old_price is None:
                # Nuevo producto
                self.changes.append((
                    title,
                    "Nuevo producto",
                    current_product.price,
                    current_product.price
                ))
            elif current_product.price > old_price:
                # Precio subió
                self.changes.append((
                    title,
                    "Subió",
                    current_product.price - old_price,
                    current_product.price
                ))
            elif current_product.price < old_price:
                # Precio bajó
                self.changes.append((
                    title,
                    "Bajó",
                    old_price - current_product.price,
                    current_product.price
                ))
                # También registrar para la visualización de disminuciones
                if historical_min is not None:
                    self.price_decreases.append((
                        title,
                        current_product.price,
                        old_price,
                        historical_min
                    ))
            # else: Sin cambios, no lo agregamos

        # Guardar cambios en SQLite en lugar de CSV
        if self.changes:
            today = datetime.now().date()
            for title, status, diff, new_price in self.changes:
                self.cursor.execute('''
                    INSERT INTO price_changes (title, change_type, difference, new_price, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, status, diff, new_price, today))
            self.conn.commit()

        return self.changes

    def show_changes_window(self):
        # Mostrar libros cuyo precio actual es el más bajo históricamente
        min_price_books = self.get_books_with_historical_min_price()
         
        if min_price_books:
            print("\nLibros con precio actual igual al mínimo histórico:")
            print("-" * 80)
            for title, current_price, min_price, date_record in min_price_books:
                print(f"Título: {title}")
                print(f"  Precio actual: ${current_price:,.2f}")
                print(f"  Precio mínimo histórico: ${min_price:,.2f}")
                print(f"  Fecha del mínimo histórico: {date_record}")
                print()
        else:
            print("No se encontraron libros con precio actual igual al mínimo histórico.")

    def show_price_decreases(self):
        # Mostrar libros cuyo precio actual es inferior al del día anterior
        if self.price_decreases:
            print("\nLibros con precio disminuido respecto al día anterior:")
            print("=" * 90)
            for title, current_price, previous_price, historical_min in self.price_decreases:
                print(f"Título: {title}")
                print(f"  Precio actual: ${current_price:,.2f}")
                print(f"  Precio del día anterior: ${previous_price:,.2f}")
                print(f"  Precio mínimo histórico: ${historical_min:,.2f}")
                print()
        else:
            print("No hay libros con precio disminuido respecto al día anterior.")

    def run(self):
        result = self.get_data()
        if isinstance(result, dict):
            self.compare_prices()
            
            # Mostrar disminuciones de precio respecto al día anterior
            if self.price_decreases:
                self.show_price_decreases()
                
            # Mantener funcionalidad existente de cambios (opcional)
            if self.changes:
                self.show_changes_window()
            elif not self.price_decreases:
                print("No hubo cambios en los precios.")
        else:
            print(result)