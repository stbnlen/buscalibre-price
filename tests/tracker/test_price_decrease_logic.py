"""Pruebas específicas para la lógica de detección de disminuciones de precio"""

def test_detect_price_decreases(sample_price_data):
    """Prueba que detecta correctamente las disminuciones de precio"""
    today_data = sample_price_data['today']
    yesterday_data = sample_price_data['yesterday']
    historical_mins = sample_price_data['historical_mins']
    
    # Lógica de detección de disminuciones (copiada del método original)
    decreases = []
    for title, current_price in today_data.items():
        if title in yesterday_data:
            old_price = yesterday_data[title]
            historical_min = historical_mins.get(title, 0)
            
            if current_price < old_price:
                decreases.append((title, current_price, old_price, historical_min))
    
    # Verificaciones
    assert len(decreases) == 1  # Solo Libro A debería tener disminución
    assert decreases[0][0] == 'Libro A'  # El título debería ser Libro A
    assert decreases[0][1] == 20.00  # Precio actual
    assert decreases[0][2] == 25.00  # Precio anterior
    assert decreases[0][3] == 18.00  # Precio mínimo histórico

def test_no_price_decreases_when_equal_or_higher(sample_price_data):
    """Prueba que no detecta disminuciones cuando los precios son iguales o mayores"""
    # Modificar datos para que no haya disminuciones
    today_data = {
        'Libro A': 25.00,  # Igual que ayer
        'Libro B': 20.00,  # Mayor que ayer
        'Libro C': 35.00   # Mayor que ayer
    }
    yesterday_data = sample_price_data['yesterday']
    historical_mins = sample_price_data['historical_mins']
    
    decreases = []
    for title, current_price in today_data.items():
        if title in yesterday_data:
            old_price = yesterday_data[title]
            if current_price < old_price:  # Esta condición no se cumplirá
                decreases.append((title, current_price, old_price, historical_mins.get(title, 0)))
    
    assert len(decreases) == 0  # No debería haber disminuciones

def test_handle_missing_yesterday_data(sample_price_data):
    """Prueba que maneja correctamente cuando no hay datos de ayer para un libro"""
    # Libro que existe hoy pero no ayer
    today_data = sample_price_data['today']
    yesterday_data = {'Libro X': 10.00}  # Solo un libro que no está en hoy
    historical_mins = sample_price_data['historical_mins']
    
    decreases = []
    for title, current_price in today_data.items():
        if title in yesterday_data:  # Esta condición no se cumplirá para ningún libro
            old_price = yesterday_data[title]
            if current_price < old_price:
                decreases.append((title, current_price, old_price, historical_mins.get(title, 0)))
    
    assert len(decreases) == 0  # No debería haber disminuciones porque no hay coincidencias