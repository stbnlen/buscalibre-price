import requests
import bs4
import pandas as pd
from datetime import datetime

URL = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"

def get_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        parent_div = soup.find('div', class_='listadoProductos')
        if not parent_div:
            return "Div con clase 'listadoProductos' no encontrado."

        product_divs = parent_div.find_all('div', class_='contenedorProducto producto')
        products = {}

        for product in product_divs:
            title = product.find('div', class_='textosProducto')
            title = title.find('div', class_='titulo').get_text(strip=True) if title and title.find('div', class_='titulo') else None

            price = product.find('div', class_='marcoPrecios')
            price = price.find('div', class_='precioAhora').get_text(strip=True) if price and price.find('div', class_='precioAhora') else None

            if title and price:
                products[title] = price

        return products
    else:
        return f"Error: {response.status_code} - {response.reason}"

result = get_data()

if isinstance(result, dict):
    df = pd.DataFrame(list(result.items()), columns=['Title', 'Price'])
    current_date = datetime.now().strftime('%m-%d-%Y')
    filename = f"books_{current_date}.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
else:
    print(result)
