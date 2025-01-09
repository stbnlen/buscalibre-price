import requests
import bs4

URL = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"

def get_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        parent_div = soup.find('div', class_='listadoProductos')  # Busca el div padre
        if not parent_div:
            return "Div con clase 'listadoProductos' no encontrado."

        # Buscar los hijos con clase 'contenedorProducto producto'
        product_divs = parent_div.find_all('div', class_='contenedorProducto producto')
        titles = []

        for product in product_divs:
            textos_producto = product.find('div', class_='textosProducto')
            if textos_producto:
                titulo_div = textos_producto.find('div', class_='titulo')
                if titulo_div:
                    titles.append(titulo_div.get_text(strip=True))  # Extrae el texto y elimina espacios extra

        return titles
    else:
        return f"Error: {response.status_code} - {response.reason}"

result = get_data()
print(result)
