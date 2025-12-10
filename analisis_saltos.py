"""Herramienta de línea de comandos para analizar saltos y tendencias en series de precipitación.

Lee un archivo CSV o XLSX con columnas mensuales (ene-dic) y, opcionalmente, una columna
"Año". Calcula la precipitación anual, aplica las pruebas de Pettitt, Mann-Kendall y
saltos con t-Student+F, y genera tablas de resumen y una versión corregida de la serie.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import pymannkendall as mk
import pyhomogeneity as hg

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def cargar_datos(ruta: Path) -> pd.DataFrame:
    """Carga el archivo de entrada (CSV o XLSX) y calcula la precipitación anual.

    Si no existe la columna "Año", se crea una numeración incremental.
    """
    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta)
    elif ruta.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(ruta)
    else:
        raise ValueError("Formato no soportado. Use CSV o XLSX.")

    faltantes = [mes for mes in MESES if mes not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas mensuales: {', '.join(faltantes)}")

    df = df.copy()
    df["ppt"] = df[MESES].sum(axis=1)

    if "Año" not in df.columns:
        df["Año"] = range(1, len(df) + 1)

    return df[["Año", *MESES, "ppt"]]


def detectar_salto_t_f(data: pd.DataFrame, alpha: float = 0.05) -> List[Tuple[int, float, float]]:
    """Detecta saltos combinando pruebas t-Student y F.

    Devuelve una lista de tuplas (año, estadístico t, estadístico F).
    """
    n = len(data)
    saltos: List[Tuple[int, float, float]] = []
    for i in range(2, n - 2):
        g1 = data["ppt"].iloc[:i]
        g2 = data["ppt"].iloc[i:]

        t_stat, p_t = stats.ttest_ind(g1, g2, equal_var=False)
        f_stat = np.var(g1, ddof=1) / np.var(g2, ddof=1)
        p_f = 1 - stats.f.cdf(f_stat, len(g1) - 1, len(g2) - 1)

        if p_t < alpha and p_f < alpha:
            saltos.append((int(data["Año"].iloc[i]), round(t_stat, 2), round(f_stat, 2)))
    return saltos


def resumen_pruebas(data: pd.DataFrame) -> Tuple[pd.DataFrame, hg.pettittResult, mk.Mann_Kendall_Test]:
    """Ejecuta Pettitt, Mann-Kendall y t-Student+F y construye una tabla resumen."""
    mk_result = mk.original_test(data["ppt"])
    pettitt_result = hg.pettitt_test(data["ppt"].values)
    pettitt_significativo = bool(pettitt_result.h)
    saltos_tf = detectar_salto_t_f(data)

    tabla_resumen = pd.DataFrame(
        {
            "Método": ["Pettitt", "Mann-Kendall", "t-Student + F"],
            "Resultado": [
                "Salto detectado" if pettitt_significativo else "No salto",
                mk_result.trend if mk_result.trend != "no trend" else "Estable",
                "Saltos detectados" if saltos_tf else "No saltos",
            ],
            "Año / Detalle": [
                int(data["Año"].iloc[pettitt_result.cp]) if pettitt_significativo else "-",
                "-",
                ", ".join(str(s[0]) for s in saltos_tf) if saltos_tf else "-",
            ],
            "Comentario": [
                (
                    f"Magnitud cambio: {round(data['ppt'].iloc[pettitt_result.cp] - data['ppt'].iloc[pettitt_result.cp - 1], 2)}"
                    if pettitt_significativo
                    else ""
                ),
                f"Z={round(mk_result.z, 2)}, p={round(mk_result.p, 3)}",
                ", ".join(f"t={s[1]}, F={s[2]}" for s in saltos_tf),
            ],
        }
    )

    return tabla_resumen, pettitt_result, mk_result


def corregir_serie(df: pd.DataFrame, pettitt_result: hg.pettittResult) -> pd.DataFrame:
    """Aplica corrección de salto según Pettitt y evita negativos."""
    data_corregida = df.copy()

    if pettitt_result.h and pettitt_result.cp is not None:
        mean_pre = data_corregida[MESES].iloc[: pettitt_result.cp].mean().mean()
        mean_post = data_corregida[MESES].iloc[pettitt_result.cp :].mean().mean()
        offset = mean_pre - mean_post
        data_corregida.loc[pettitt_result.cp :, MESES] += offset

    data_corregida[MESES] = data_corregida[MESES].clip(lower=0)
    return data_corregida[["Año", *MESES]]


def mostrar_tablas(tabla_resumen: pd.DataFrame, data_corregida: pd.DataFrame) -> None:
    """Imprime las tablas de resumen y la serie corregida."""
    print("=== Tabla resumen de saltos y tendencias ===")
    print(tabla_resumen.to_string(index=False))
    print()
    print("=== Datos de precipitación corregida (mensual) ===")
    print(data_corregida.to_string(index=False))


def analizar_archivo(ruta: Path) -> None:
    df = cargar_datos(ruta)
    tabla_resumen, pettitt_result, _ = resumen_pruebas(df[["Año", "ppt"]])
    data_corregida = corregir_serie(df, pettitt_result)
    mostrar_tablas(tabla_resumen, data_corregida)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Análisis de saltos y tendencias en precipitación.")
    parser.add_argument(
        "ruta",
        type=Path,
        help="Ruta al archivo CSV o XLSX con columnas mensuales (ene-dic) y opcionalmente 'Año'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analizar_archivo(args.ruta)


if __name__ == "__main__":
    main()
