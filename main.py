import os
import requests
import bs4
import pandas as pd
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk

URL = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"

def get_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.reason}"

    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    parent_div = soup.find('div', class_='listadoProductos')
    if not parent_div:
        return "Div con clase 'listadoProductos' no encontrado."

    products = {
        product.find('div', class_='titulo').get_text(strip=True): float(
            product.find('div', class_='precioAhora').get_text(strip=True).replace('$', '').replace('.', '').replace(',', '.')
        )
        for product in parent_div.find_all('div', class_='contenedorProducto producto')
        if (titulo := product.find('div', class_='titulo')) and (precio := product.find('div', class_='precioAhora'))
    }

    return products

def compare_prices(current_data):
    yesterday_file = f"books_{(datetime.now() - timedelta(days=1)).strftime('%m-%d-%Y')}.csv"
    changes = []

    if os.path.exists(yesterday_file):
        yesterday_data = pd.read_csv(yesterday_file).set_index('Title')['Price'].to_dict()
        for title, current_price in current_data.items():
            old_price = yesterday_data.get(title)
            if old_price is None:
                changes.append((title, "Nuevo producto", current_price))
            else:
                status = "Subió" if current_price > old_price else "Bajó" if current_price < old_price else "Sin cambios"
                changes.append((title, status, abs(current_price - old_price) if status != "Sin cambios" else 0))

    filtered_changes = [change for change in changes if change[1] != "Sin cambios"]
    if filtered_changes:
        pd.DataFrame(filtered_changes, columns=['Title', 'Status', 'Difference']).to_csv(
            f"price_changes_{datetime.now().strftime('%m-%d-%Y')}.csv", index=False, encoding='utf-8'
        )

    return filtered_changes

def show_changes_window(changes):
    window = tk.Tk()
    window.title("Cambios de Precios")

    tree = ttk.Treeview(window, columns=('Title', 'Status', 'Difference'), show='headings')
    tree.heading('Title', text='Producto')
    tree.heading('Status', text='Estado')
    tree.heading('Difference', text='Diferencia')

    for change in changes:
        tree.insert('', 'end', values=change)

    tree.pack(fill=tk.BOTH, expand=True)
    window.mainloop()

def main():
    result = get_data()
    if isinstance(result, dict):
        changes = compare_prices(result)
        if changes:
            show_changes_window(changes)
        else:
            print("No hubo cambios en los precios.")
    else:
        print(result)

if __name__ == "__main__":
    main()
