"""Cálculo de z-scores OMS en Python puro (sin R).

Replica los resultados de los paquetes de R `anthro` (0 a 5 años) y
`anthroplus` (5 a 19 años) usando las tablas LMS exportadas en datos_oms/.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATOS = Path(__file__).parent / "datos_oms"


def _cargar(nombre, col_x):
    """Diccionario {(sexo, x): (L, M, S)}; x se redondea para evitar errores de decimales."""
    tabla = pd.read_csv(DATOS / f"{nombre}.csv")
    return {
        (int(f.sex), round(float(getattr(f, col_x)), 1)): (f.l, f.m, f.s)
        for f in tabla.itertuples()
    }


TABLAS = {
    "wfl": _cargar("wfl", "length"),   # Peso para la longitud, 0 a 2 años
    "wfh": _cargar("wfh", "height"),   # Peso para la talla, 2 a 5 años
    "len": _cargar("len", "age"),      # Talla para la edad (días), 0 a 5 años
    "bfa": _cargar("bfa", "age"),      # IMC para la edad (meses), 5 a 19 años
    "hfa": _cargar("hfa", "age"),      # Talla para la edad (meses), 5 a 19 años
}


def _lms(tabla, sexo, x):
    """Devuelve (L, M, S) de la tabla para ese sexo y valor de x, o None si no existe."""
    return TABLAS[tabla].get((sexo, round(float(x), 1)))


def _lms_interpolado(tabla, sexo, edad_meses):
    """L, M y S para una edad en meses con decimales (como hace anthroplus).

    Ejemplo: 110.78 meses toma el 22% de la fila del mes 110 y el 78% del mes 111.
    """
    mes = int(edad_meses)
    fraccion = edad_meses - mes
    antes, despues = _lms(tabla, sexo, mes), _lms(tabla, sexo, mes + 1)
    if antes is None or despues is None:
        return None
    return tuple(a + (d - a) * fraccion for a, d in zip(antes, despues))


def _valor_en_z(L, M, S, z):
    """Medida que corresponde a un z-score dado (inverso de la fórmula LMS)."""
    return M * (1 + L * S * z) ** (1 / L)


def _zscore(y, lms, ajustar_extremos):
    """Fórmula LMS de la OMS.

    Para indicadores de peso (P/T, IMC/E) la OMS corrige los valores más allá
    de ±3 DE, porque la fórmula LMS deforma las colas de la distribución.
    """
    if lms is None:
        return np.nan
    L, M, S = lms
    z = ((y / M) ** L - 1) / (L * S)
    if ajustar_extremos and z > 3:
        sd3 = _valor_en_z(L, M, S, 3)
        sd23 = sd3 - _valor_en_z(L, M, S, 2)
        z = 3 + (y - sd3) / sd23
    elif ajustar_extremos and z < -3:
        sd3 = _valor_en_z(L, M, S, -3)
        sd23 = _valor_en_z(L, M, S, -2) - sd3
        z = -3 - (sd3 - y) / sd23
    return z


def zscores_menor_5(sexo, edad_dias, peso, talla):
    """Equivalente a anthro::anthro_zscores. Devuelve (IMC, z P/T, z T/E)."""
    imc = peso / (talla / 100) ** 2
    # Antes de 2 años (731 días) se usa la tabla de longitud; después, la de talla
    tabla_pt = "wfl" if edad_dias < 731 else "wfh"
    z_pt = _zscore(peso, _lms(tabla_pt, sexo, talla), ajustar_extremos=True)
    z_te = _zscore(talla, _lms("len", sexo, edad_dias), ajustar_extremos=False)
    return imc, round(z_pt, 2), round(z_te, 2)


def zscores_mayor_5(sexo, edad_meses, peso, talla):
    """Equivalente a anthroplus::anthroplus_zscores. Devuelve (IMC, z IMC/E, z T/E)."""
    imc = peso / (talla / 100) ** 2
    z_imc = _zscore(imc, _lms_interpolado("bfa", sexo, edad_meses), ajustar_extremos=True)
    z_te = _zscore(talla, _lms_interpolado("hfa", sexo, edad_meses), ajustar_extremos=False)
    return imc, round(z_imc, 2), round(z_te, 2)
