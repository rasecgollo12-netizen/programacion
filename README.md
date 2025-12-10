# programacion

Herramientas y ejemplos en Python y R.

## Análisis de saltos y tendencias (solo tablas)

El script `analisis_saltos.py` reproduce el flujo mostrado en el cuaderno de ejemplo
para detectar saltos y tendencias en series de precipitación usando únicamente tablas.

### Requisitos

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

### Uso

Ejecuta el análisis sobre un archivo CSV o XLSX que contenga columnas mensuales `ene` a
`dic` y, opcionalmente, la columna `Año`:

```bash
python analisis_saltos.py ruta/al/archivo.csv
```

La salida incluye la tabla resumen con Pettitt, Mann-Kendall y t-Student+F, además de la
serie mensual corregida según la prueba de Pettitt (sin valores negativos).
