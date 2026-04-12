# BuscaLibre Price Tracker

Una aplicación para rastrear y monitorear los precios de libros en BuscaLibre.cl, específicamente enfocada en detectar disminuciones de precios y registrar el historial de precios para análisis.

## ¿Qué hace?

1. **Rastreo de precios diarios**: Extrae los precios actuales de libros de una lista específica en BuscaLibre.cl
2. **Almacenamiento histórico**: Guarda todos los precios recopilados en una base de datos SQLite
3. **Detección de cambios**: Identifica cuando los precios han cambiado respecto al último registro
4. **Análisis de mínimos históricos**: Determina qué libros están en su precio más bajo jamás registrado
5. **Reportes detallados**: Genera informes claros con tablas formateadas

## Arquitectura

- `main.py`: Punto de entrada de la aplicación
- `tracker/price_tracker.py`: Lógica de rastreo, almacenamiento y análisis
- `tracker/models.py`: Estructuras de datos
- `check_price_decreases.py`: Herramienta de diagnóstico para revisar la DB real
- `buscalibre_prices.sqlite`: Base de datos con el historial de precios

## Uso

```bash
pip install -r requirements.txt
python main.py
```

Se recomienda ejecutarlo diariamente (ej: cron) para capturar cambios de precio.

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

## Personalización

Modificar la constante `DEFAULT_URL` en `PriceTracker`:

```python
DEFAULT_URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
```

## Licencia

MIT
