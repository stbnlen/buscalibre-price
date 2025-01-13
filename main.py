import os
import requests
import bs4
import pandas as pd
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field

@dataclass
class Product:
    title: str
    price: float

@dataclass
class PriceTracker:
    current_data: dict[str, Product] = field(default_factory=dict)
    changes: list[tuple[str, str, float]] = field(default_factory=list)
    URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"

    def get_data(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        }
        response = requests.get(self.URL, headers=headers)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.reason}"

        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        parent_div = soup.find('div', class_='listadoProductos')
        if not parent_div:
            return "Div con clase 'listadoProductos' no encontrado."

        self.current_data = {
            product.find('div', class_='titulo').get_text(strip=True): Product(
                title=product.find('div', class_='titulo').get_text(strip=True),
                price=float(
                    product.find('div', class_='precioAhora').get_text(strip=True).replace('$', '').replace('.', '').replace(',', '.')
                )
            )
            for product in parent_div.find_all('div', class_='contenedorProducto producto')
            if (titulo := product.find('div', class_='titulo')) and (precio := product.find('div', class_='precioAhora'))
        }

        today_file = f"books_{datetime.now().strftime('%m-%d-%Y')}.csv"
        df = pd.DataFrame(
            [{"Title": product.title, "Price": product.price} for product in self.current_data.values()]
        )
        df.to_csv(today_file, index=False, encoding='utf-8')
    
        return self.current_data
    
    def compare_prices(self):
        yesterday_file = f"books_{(datetime.now() - timedelta(days=1)).strftime('%m-%d-%Y')}.csv"

        if os.path.exists(yesterday_file):
            yesterday_data = pd.read_csv(yesterday_file).set_index('Title')['Price'].to_dict()
            self.changes = [
                (title, "Nuevo producto", current_product.price, current_product.price) if old_price is None else
                (title, "Subió", current_product.price - old_price, current_product.price) if current_product.price > old_price else
                (title, "Bajó", old_price - current_product.price, current_product.price) if current_product.price < old_price else
                (title, "Sin cambios", 0, current_product.price)
                for title, current_product in self.current_data.items()
                for old_price in [yesterday_data.get(title)]
            ]
        else:
            print(f"No se encontró archivo para {yesterday_file}. No se pueden comparar precios.")

        self.changes = [change for change in self.changes if change[1] != "Sin cambios"]

        if self.changes:
            pd.DataFrame(self.changes, columns=['Title', 'Status', 'Difference', 'Current Price']).to_csv(
                f"price_changes_{datetime.now().strftime('%m-%d-%Y')}.csv", index=False, encoding='utf-8'
            )

        return self.changes
    
    def show_changes_window(self):
        window = tk.Tk()
        window.title("Cambios de Precios")

        tree = ttk.Treeview(window, columns=('Title', 'Status', 'Difference','Current Price'), show='headings')
        tree.heading('Title', text='Producto')
        tree.heading('Status', text='Estado')
        tree.heading('Current Price', text='Precio Actual')
        tree.heading('Difference', text='Diferencia')

        for change in self.changes:
            tree.insert('', 'end', values=change)

        tree.pack(fill=tk.BOTH, expand=True)
        window.mainloop()

    def run(self):
        result = self.get_data()
        if isinstance(result, dict):
            self.compare_prices()
            if self.changes:
                self.show_changes_window()
            else:
                print("No hubo cambios en los precios.")
        else:
            print(result)

if __name__ == "__main__":
    tracker = PriceTracker()
    tracker.run()
