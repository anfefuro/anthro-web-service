"""Compara los z-scores de antropometria.py contra los calculados por R.

Uso (desde la carpeta del proyecto):  python herramientas/validar.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from antropometria import zscores_mayor_5, zscores_menor_5

TOLERANCIA = 0.011  # R redondea a 2 decimales; permitimos 1 centésima de diferencia


def comparar(archivo, funcion, col_edad, columnas_r):
    casos = pd.read_csv(RAIZ / "datos_oms" / archivo)
    errores = 0
    for _, c in casos.iterrows():
        python = funcion(int(c["sex"]), c[col_edad], c["weight"], c["height"])
        r = [c[col] for col in columnas_r]
        for nombre, vp, vr in zip(columnas_r, python, r):
            ambos_vacios = pd.isna(vp) and pd.isna(vr)
            iguales = not pd.isna(vp) and not pd.isna(vr) and abs(vp - vr) <= TOLERANCIA
            if not (ambos_vacios or iguales):
                errores += 1
                print(f"  ✗ {archivo} sexo={int(c['sex'])} edad={c[col_edad]:.2f} "
                      f"peso={c['weight']} talla={c['height']} | {nombre}: Python={vp} R={vr}")
    print(f"{archivo}: {len(casos)} casos, {errores} diferencias")
    return errores


total = comparar("prueba_menores_5.csv", zscores_menor_5, "age_days", ["cbmi", "zwfl", "zlen"])
total += comparar("prueba_mayores_5.csv", zscores_mayor_5, "age_months", ["cbmi", "zbfa", "zhfa"])
print("\n✅ Python coincide con R en todos los casos" if total == 0 else f"\n❌ {total} diferencias")
sys.exit(1 if total else 0)
