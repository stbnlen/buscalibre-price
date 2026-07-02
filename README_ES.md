# BuscaLibre Price Tracker

Una aplicación para rastrear y monitorear los precios de libros en BuscaLibre.cl, específicamente enfocada en detectar disminuciones de precios y registrar el historial de precios para análisis.

## ¿Qué hace?

1. **Rastreo de precios diarios**: Extrae los precios actuales de libros de una lista específica en BuscaLibre.cl
2. **Almacenamiento histórico**: Guarda todos los precios recopilados en una base de datos SQLite
3. **Detección de cambios**: Identifica cuando los precios han cambiado respecto al último registro
4. **Análisis de mínimos históricos**: Determina qué libros están en su precio más bajo jamás registrado
5. **Reportes detallados**: Genera informes claros con tablas formateadas

## Arquitectura

- `main.py`: Punto de entrada de la aplicación con soporte para argumentos de línea de comandos
- `tracker/price_tracker.py`: Orquestador del flujo de trabajo
- `tracker/scraper.py`: Lógica de scraping con reintentos automáticos
- `tracker/repository.py`: Acceso a la base de datos SQLite
- `tracker/analyzer.py`: Lógica pura de comparación de precios y detección de mínimos históricos
- `tracker/reporter.py`: Formateo de reportes como strings
- `tracker/models.py`: Estructuras de datos
- `tracker/config.py`: Configuración centralizada (variables de entorno + CLI)
- `tracker/exceptions.py`: Excepciones de dominio
- `tracker/check_price_decreases.py`: Herramienta de diagnóstico para revisar la DB real
- `tracker/create_test_data.py`: Genera datos de prueba deterministas
- `buscalibre_prices.sqlite`: Base de datos con el historial de precios

## Instalación

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

Se recomienda ejecutarlo diariamente (ej: cron) para capturar cambios de precio.

### Configuración

La configuración puede proporcionarse mediante variables de entorno o argumentos de línea de comandos. Los argumentos de CLI tienen prioridad sobre las variables de entorno.

Variables de entorno:

- `BUSCALIBRE_URL`: URL de la lista de BuscaLibre a scrapear
- `BUSCALIBRE_DB_PATH`: Ruta al archivo SQLite
- `BUSCALIBRE_TIMEOUT`: Timeout de las peticiones HTTP en segundos
- `BUSCALIBRE_RETRIES`: Cantidad de reintentos ante fallos HTTP

Argumentos de CLI:

```bash
python main.py --url https://www.buscalibre.cl/v2/pendientes_1722693_l.html \
               --db-path ./buscalibre_prices.sqlite \
               --timeout 20 \
               --retries 5
```

### Herramientas auxiliares

Verificar disminuciones de precio en la base de datos existente:

```bash
python -m tracker.check_price_decreases
```

Generar datos de prueba deterministas para ayer:

```bash
python -m tracker.create_test_data
```

## Tests

```bash
pytest
```

## Base de datos

### `book_prices`

- `id`, `title`, `price`, `date`, `created_at`
- Constraint único: `(title, date)`
- Índices en `date` y `(title, date)`

### `price_changes`

- `id`, `title`, `change_type`, `difference`, `new_price`, `date`, `created_at`
- Índice en `date`

## Notas importantes

- Los precios se comparan con el **último precio registrado** de cada libro, no solo con el de ayer. Si se salta un día, la comparación sigue funcionando.
- Si el scraping falla, la aplicación reporta un error. No se insertan datos falsos en la base de datos.
- El scraper incluye reintentos automáticos con backoff para errores transitorios (429, 500, 502, 503, 504).

## Licencia

MIT
