import sys
import os

# Instalación silenciosa de paquetes de R solo si no están instalados
print("Preparando el entorno médico (esto puede tardar unos segundos la primera vez)... ", end="")
sys.stdout.flush()
os.system("Rscript -e 'if(!require(anthro)) install.packages(\"anthro\", repos=\"https://cloud.r-project.org\", quiet=TRUE)' > /dev/null 2>&1")
os.system("Rscript -e 'if(!require(anthroplus)) install.packages(\"anthroplus\", repos=\"https://cloud.r-project.org\", quiet=TRUE)' > /dev/null 2>&1")
print("¡Listo!")

from google.colab import files
import pandas as pd
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
import numpy as np
import datetime

# Activar la interfaz de R en Python y cargar anthro y anthroplus
pandas2ri.activate()
anthro = importr('anthro')
anthroplus = importr('anthroplus')

# @title 📝 Formulario de Registro de Usuario

# Inputs nativos con tipos asignados
Fecha_de_Nacimiento = "2009-01-20"  # @param {type:"date"}
Fecha_de_Visita = "2026-11-19"  # @param {type:"date"}
Género = "Hombre"  # @param ["Hombre", "Mujer"]
Peso = 64.4  # @param {type:"number"}
Talla = 170.5  # @param {type:"number"}

# Convertir el género al código que usan anthro/anthroplus (1 = Hombre, 2 = Mujer)
sex = 1 if Género == "Hombre" else 2

# Formatear fechas a DD/MM/YYYY
dob = datetime.datetime.strptime(Fecha_de_Nacimiento, "%Y-%m-%d").strftime("%d/%m/%Y")
dov = datetime.datetime.strptime(Fecha_de_Visita, "%Y-%m-%d").strftime("%d/%m/%Y")

# Crear el DataFrame
df = pd.DataFrame(
    [
        {
            "dob": dob,
            "dov": dov,
            "sex": int(sex),
            "weight": float(Peso),
            "height": float(Talla),
        }
    ]
)

df['dob_dt'] = pd.to_datetime(df['dob'], format='%d/%m/%Y')
df['dov_dt'] = pd.to_datetime(df['dov'], format='%d/%m/%Y')
df['age_days'] = (df['dov_dt'] - df['dob_dt']).dt.days
df['age_in_months'] = df['age_days'] / 30.4375

# Separar datos por grupo de edad
df_0_5 = df[df['age_in_months'] < 60].copy()
df_5_19 = df[df['age_in_months'] >= 60].copy()

# Procesar resultados consolidados
resultados_lista = []

if not df_0_5.empty:
    r_results_0_5 = anthro.anthro_zscores(
        sex = df_0_5["sex"],
        age = df_0_5["age_days"],
        weight = df_0_5["weight"],
        lenhei = df_0_5["height"],
    )
    z_scores_0_5 = pandas2ri.rpy2py(r_results_0_5)
    z_scores_0_5 = z_scores_0_5[['cbmi','zwfl','zlen']].copy()
    z_scores_0_5['Clasificación de Edad'] = "Menor de 5"
    z_scores_0_5.rename(columns={'cbmi': 'IMC', 'zwfl': 'Peso/Talla - IMC/Edad', 'zlen': 'Talla/Edad'}, inplace=True)
    resultados_lista.append(z_scores_0_5)

if not df_5_19.empty:
    r_results_5_19 = anthroplus.anthroplus_zscores(
        sex = df_5_19["sex"],
        age_in_months = df_5_19["age_in_months"],
        weight = df_5_19["weight"],
        height = df_5_19["height"]
    )
    z_scores_5_19 = pandas2ri.rpy2py(r_results_5_19)
    z_scores_5_19 = z_scores_5_19[['cbmi','zbfa','zhfa']].copy()
    z_scores_5_19['Clasificación de Edad'] = "Mayor de 5"
    z_scores_5_19.rename(columns={'cbmi': 'IMC', 'zbfa': 'Peso/Talla - IMC/Edad', 'zhfa': 'Talla/Edad'}, inplace=True)
    resultados_lista.append(z_scores_5_19)

# Clasificación antropométrica (Resolución 2465 de 2016)
def clasificar_pt_imce(z, grupo):
    if pd.isna(z):
        return None
    if grupo == "Menor de 5":  # Peso para la Talla (P/T) - Cuadro No. 2
        if z > 3: return "Obesidad"
        if z > 2: return "Sobrepeso"
        if z > 1: return "Riesgo de Sobrepeso"
        if z >= -1: return "Peso Adecuado para la Talla"
        if z >= -2: return "Riesgo de Desnutrición Aguda"
        if z >= -3: return "Desnutrición Aguda Moderada"
        return "Desnutrición Aguda Severa"
    else:  # IMC para la Edad (IMC/E) - Cuadro No. 3
        if z > 2: return "Obesidad"
        if z > 1: return "Sobrepeso"
        if z >= -1: return "IMC Adecuado para la Edad"
        if z >= -2: return "Riesgo de Delgadez"
        return "Delgadez"

def clasificar_te(z, grupo):  # Talla para la Edad (T/E) - Cuadros No. 2 y 3
    if pd.isna(z):
        return None
    if z >= -1: return "Talla Adecuada para la Edad"
    if z >= -2: return "Riesgo de Talla Baja" if grupo == "Menor de 5" else "Riesgo de Retraso en Talla"
    return "Talla Baja para la Edad o Retraso en Talla"

# ---------- Tabla de resultados con estilo ----------
# Colores por clasificación: (fondo, texto)
VERDE, AMARILLO, NARANJA, ROJO = ('#c6efce', '#006100'), ('#ffeb9c', '#7f6000'), ('#f8cbad', '#843c0c'), ('#ff9b9b', '#7a0000')
COLOR_CLASIF = {
    'Peso Adecuado para la Talla': VERDE, 'IMC Adecuado para la Edad': VERDE, 'Talla Adecuada para la Edad': VERDE,
    'Riesgo de Sobrepeso': AMARILLO, 'Riesgo de Desnutrición Aguda': AMARILLO, 'Riesgo de Delgadez': AMARILLO,
    'Riesgo de Talla Baja': AMARILLO, 'Riesgo de Retraso en Talla': AMARILLO,
    'Sobrepeso': NARANJA, 'Desnutrición Aguda Moderada': NARANJA, 'Delgadez': NARANJA,
    'Talla Baja para la Edad o Retraso en Talla': NARANJA,
    'Obesidad': ROJO, 'Desnutrición Aguda Severa': ROJO,
}

def estilo_clasif(clasif):
    if clasif not in COLOR_CLASIF:
        return ''
    fondo, texto = COLOR_CLASIF[clasif]
    return f'background-color: {fondo}; color: {texto}; font-weight: bold;'

def tabla_bonita(tabla):
    tabla = tabla.reset_index(drop=True)
    return (tabla.style
        .format({'IMC': '{:.2f}', 'Peso/Talla - IMC/Edad': '{:+.2f}', 'Talla/Edad': '{:+.2f}'}, na_rep='-')
        .set_properties(**{'background-color': '#ffffff', 'color': '#222222'})
        .apply(lambda col: [estilo_clasif(c) for c in tabla['Clasificación P/T - IMC/E']],
               subset=['Peso/Talla - IMC/Edad', 'Clasificación P/T - IMC/E'])
        .apply(lambda col: [estilo_clasif(c) for c in tabla['Clasificación T/E']],
               subset=['Talla/Edad', 'Clasificación T/E'])
        .hide(axis='index')
        .set_table_styles([
            {'selector': '', 'props': 'border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px; margin: 8px 0;'},
            {'selector': 'th', 'props': 'background-color: #1f4e79; color: white; padding: 10px 14px; border: 1px solid #8ea9c1; text-align: center;'},
            {'selector': 'td', 'props': 'padding: 10px 14px; border: 1px solid #8ea9c1; text-align: center;'},
        ]))

# ---------- Gráficas de crecimiento OMS ----------
import matplotlib.pyplot as plt

COLORES_DE = {-3: 'black', -2: 'red', -1: 'orange', 0: 'green', 1: 'orange', 2: 'red', 3: 'black'}

def tabla_r(nombre):
    # Tablas LMS oficiales de la OMS incluidas en los paquetes anthro / anthroplus
    return pandas2ri.rpy2py(robjects.r(nombre))

def curvas_lms(tabla, col_x, sexo):
    t = tabla[tabla['sex'] == sexo].sort_values(col_x)
    L, M, S = t['l'].values, t['m'].values, t['s'].values
    with np.errstate(divide='ignore', invalid='ignore'):
        curvas = {z: np.where(L == 0, M * np.exp(S * z), M * (1 + L * S * z) ** (1 / L)) for z in range(-3, 4)}
    return t[col_x].values, curvas

def graficar(ax, x, curvas, px, py, z, clasif, titulo, xlabel, ylabel):
    ax.fill_between(x, curvas[-1], curvas[1], color='green', alpha=0.08)
    for de, y in curvas.items():
        ax.plot(x, y, color=COLORES_DE[de], lw=2 if de == 0 else 1)
        ax.annotate('0' if de == 0 else f'{de:+d}', (x[-1], y[-1]), xytext=(4, 0), textcoords='offset points',
                    color=COLORES_DE[de], fontsize=9, va='center', fontweight='bold')
    ax.plot(px, py, 'o', color='royalblue', ms=10, mec='white', mew=2, zorder=5)
    ax.annotate(f'{z:+.2f} DE\n{clasif}', (px, py), xytext=(10, -28), textcoords='offset points', fontsize=9,
                bbox=dict(boxstyle='round', fc='white', ec='royalblue'), zorder=6)
    ax.set_title(titulo, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)

def graficas_crecimiento(fila, res):
    sexo = int(fila['sex'])
    nombre_sexo = 'Hombre' if sexo == 1 else 'Mujer'
    meses = fila['age_in_months']
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    if meses < 60:
        if fila['age_days'] < 731:
            x, c = curvas_lms(tabla_r('anthro:::growthstandards_wflanthro'), 'length', sexo)
            xlabel = 'Longitud (cm)'
        else:
            x, c = curvas_lms(tabla_r('anthro:::growthstandards_wfhanthro'), 'height', sexo)
            xlabel = 'Talla (cm)'
        graficar(axes[0], x, c, fila['height'], fila['weight'], res['Peso/Talla - IMC/Edad'], res['Clasificación P/T - IMC/E'],
                 f'Peso para la Talla (P/T) - {nombre_sexo}, 0 a 5 años', xlabel, 'Peso (kg)')
        x, c = curvas_lms(tabla_r('anthro:::growthstandards_lenanthro'), 'age', sexo)
        graficar(axes[1], x / 30.4375, c, meses, fila['height'], res['Talla/Edad'], res['Clasificación T/E'],
                 f'Talla para la Edad (T/E) - {nombre_sexo}, 0 a 5 años', 'Edad (meses)', 'Talla (cm)')
    else:
        x, c = curvas_lms(tabla_r('anthroplus:::bfa_growth_standards'), 'age', sexo)
        graficar(axes[0], x / 12, c, meses / 12, res['IMC'], res['Peso/Talla - IMC/Edad'], res['Clasificación P/T - IMC/E'],
                 f'IMC para la Edad (IMC/E) - {nombre_sexo}, 5 a 19 años', 'Edad (años)', 'IMC (kg/m²)')
        x, c = curvas_lms(tabla_r('anthroplus:::hfa_growth_standards'), 'age', sexo)
        graficar(axes[1], x / 12, c, meses / 12, fila['height'], res['Talla/Edad'], res['Clasificación T/E'],
                 f'Talla para la Edad (T/E) - {nombre_sexo}, 5 a 19 años', 'Edad (años)', 'Talla (cm)')
    plt.tight_layout()
    plt.show()

if resultados_lista:
    concat_base = pd.concat(resultados_lista)
    grupos = concat_base['Clasificación de Edad']
    concat_base.insert(concat_base.columns.get_loc('Peso/Talla - IMC/Edad') + 1, 'Clasificación P/T - IMC/E',
                       [clasificar_pt_imce(z, g) for z, g in zip(concat_base['Peso/Talla - IMC/Edad'], grupos)])
    concat_base.insert(concat_base.columns.get_loc('Talla/Edad') + 1, 'Clasificación T/E',
                       [clasificar_te(z, g) for z, g in zip(concat_base['Talla/Edad'], grupos)])
    print("\n--- RESULTADOS DE LAS DESVIACIONES ---")
    # Edad exacta en años, meses y días (calendario)
    from dateutil.relativedelta import relativedelta
    def plural(n, singular, plural_):
        return f"{n} {singular if n == 1 else plural_}"
    for _, fila in df.iterrows():
        edad = relativedelta(fila['dov_dt'], fila['dob_dt'])
        print(f"Edad: {plural(edad.years, 'año', 'años')} y {plural(edad.months, 'mes', 'meses')} (con {plural(edad.days, 'día', 'días')})")
    display(tabla_bonita(concat_base[~concat_base['IMC'].isna()]))
    # Gráficas (formulario individual: una sola persona)
    if not pd.isna(concat_base['IMC'].iloc[0]):
        graficas_crecimiento(df.iloc[0], concat_base.iloc[0])
else:
    print("No se ingresaron datos válidos para procesar.")