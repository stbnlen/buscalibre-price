# BuscaLibre Price Tracker

Una aplicación para rastrear y monitorear los precios de libros en BuscaLibre.cl, específicamente enfocada en detectar disminuciones de precios y registrar el historial de precios para análisis.

## ¿Qué hace?

Esta aplicación realiza las siguientes funciones principales:

1. **Rastreo de precios diarios**: Extrae los precios actuales de libros de una lista específica en BuscaLibre.cl
2. **Almacenamiento histórico**: Guarda todos los precios recopilados en una base de datos SQLite para mantener un historial completo
3. **Detección de cambios**: Identifica cuando los precios de los libros han disminuido respecto al día anterior
4. **Análisis de mínimos históricos**: Determina qué libros están actualmente en su precio más bajo jamás registrado
5. **Reportes detallados**: Genera informes claros sobre las disminuciones de precios y los mínimos históricos

## ¿Cómo funciona?

### Arquitectura

La aplicación está estructurada en los siguientes componentes principales:

- `main.py`: Punto de entrada de la aplicación
- `tracker/price_tracker.py`: Contiene la lógica principal de rastreo, almacenamiento y análisis
- `tracker/models.py`: Define las estructuras de datos utilizadas (actualmente vacía, mantenida para futura expansión)
- `buscalibre_prices.sqlite`: Base de datos SQLite que almacena todo el historial de precios
- `test_price_decreases.py`: Script de prueba para validar la lógica de detección de disminuciones

### Flujo de trabajo

1. **Inicialización**: Al ejecutar la aplicación, se inicializa la base de datos SQLite si no existe
2. **Extracción de datos**: La aplicación obtiene los datos actuales de precios desde BuscaLibre.cl mediante web scraping
3. **Almacenamiento**: Los precios se guardan en la tabla `book_prices` con la fecha actual
4. **Comparación**: Se comparan los precios de hoy con los de ayer para detectar cambios
5. **Detección de disminuciones**: Se identifican los libros cuyo precio ha bajado respecto al día anterior
6. **Análisis histórico**: Se verifica qué libros están en su precio mínimo histórico jamás registrado
7. **Reporte**: Se muestra un resumen de los hallazgos en consola

### Base de datos

La aplicación utiliza una base de datos SQLite (`buscalibre_prices.sqlite`) con dos tablas principales:

#### `book_prices`
- `id`: Clave primaria
- `title`: Título del libro
- `price`: Precio registrado
- `date`: Fecha del registro
- `created_at`: Timestamp de creación
- Constraint único: `(title, date)` para evitar duplicados del mismo libro en la misma fecha

#### `price_changes`
- `id`: Clave primaria
- `title`: Título del libro
- `change_type`: Tipo de cambio ("Subió", "Bajó", "Nuevo producto")
- `difference`: Diferencia absoluta en precio
- `new_price`: Nuevo precio después del cambio
- `date`: Fecha del cambio
- `created_at`: Timestamp de creación

## Requisitos

- Python 3.x
- Bibliotecas de Python:
  - requests
  - beautifulsoup4 (bs4)
  - sqlite3 (incluido en Python estándar)

Para instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Uso

Ejecutar la aplicación:
```bash
python main.py
```

Ejecutar las pruebas de validación:
```bash
python test_price_decreases.py
```

## Notas importantes

1. **Datos históricos**: La base de datos SQLite contiene datos irreproducibles (precios históricos), por lo que es esencial mantenerla versionada en Git para preservar el historial al cambiar entre equipos.

2. **Archivos de debug**: La aplicación crea un archivo `debug.html` durante la ejecución para facilitar la depuración del scraping. Este archivo está intencionalmente excluido del versionado mediante `.gitignore`.

3. **Frecuencia de ejecución**: Para obtener el máximo valor de esta aplicación, se recomienda ejecutarla diariamente (por ejemplo, mediante cron o Task Scheduler) para capturar los cambios de precio día a día.

4. **Manejo de errores**: Si el sitio web no está disponible o cambia su estructura, la aplicación tiene un modo de respaldo que utiliza datos de demostración para mostrar que el sistema funciona correctamente.

## Personalización

Para monitorear una lista diferente de libros en BuscaLibre.cl, modifique la constante `URL` en la clase `PriceTracker` dentro de `tracker/price_tracker.py`:

```python
URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
```

## Licencia

Este proyecto está bajo licencia MIT - ve el archivo LICENSE para más detalles.
