import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from antropometria import DATOS, zscores_mayor_5, zscores_menor_5

st.set_page_config(page_title="Valoración Antropométrica OMS", page_icon="📏", layout="wide")

st.markdown("""
<style>
.block-container { max-width: 1150px; padding-top: 2.5rem; }
.encabezado h1 { font-size: 1.6rem; font-weight: 700; margin: 0; padding: 0; }
.encabezado p { color: #64748b; margin: 0.2rem 0 1.2rem; }
.edad { background: #fff; border: 1px solid #e2e8f0; border-radius: 0.6rem; padding: 0.7rem 1rem; margin-bottom: 0.8rem; }
.edad b { font-size: 1.05rem; }
.edad span { color: #64748b; margin-left: 0.5rem; }
.tarjeta { background: #fff; border: 1px solid #e2e8f0; border-left: 5px solid var(--borde);
           border-radius: 0.6rem; padding: 0.8rem 1rem; height: 100%; }
.tarjeta .titulo { color: #64748b; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
.tarjeta .valor { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin: 0.15rem 0 0.4rem; }
.tarjeta .valor small { font-size: 0.85rem; font-weight: 400; color: #64748b; }
.etiqueta { display: inline-block; background: var(--fondo); color: var(--texto); font-weight: 600;
            font-size: 0.8rem; padding: 0.2rem 0.55rem; border-radius: 999px; }
.vacio { text-align: center; color: #64748b; border: 2px dashed #cbd5e1; border-radius: 0.6rem; padding: 4rem 2rem; }
.vacio div { font-size: 2.5rem; }
</style>
""", unsafe_allow_html=True)


# ---------- Clasificación antropométrica (Resolución 2465 de 2016) ----------
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


# ---------- Tarjetas de resultados ----------
# Colores por clasificación: (fondo, texto, borde)
VERDE = ('#dcfce7', '#166534', '#22c55e')
AMARILLO = ('#fef9c3', '#854d0e', '#eab308')
NARANJA = ('#ffedd5', '#9a3412', '#f97316')
ROJO = ('#fee2e2', '#991b1b', '#ef4444')
GRIS = ('#f1f5f9', '#475569', '#cbd5e1')
COLOR_CLASIF = {
    'Peso Adecuado para la Talla': VERDE, 'IMC Adecuado para la Edad': VERDE, 'Talla Adecuada para la Edad': VERDE,
    'Riesgo de Sobrepeso': AMARILLO, 'Riesgo de Desnutrición Aguda': AMARILLO, 'Riesgo de Delgadez': AMARILLO,
    'Riesgo de Talla Baja': AMARILLO, 'Riesgo de Retraso en Talla': AMARILLO,
    'Sobrepeso': NARANJA, 'Desnutrición Aguda Moderada': NARANJA, 'Delgadez': NARANJA,
    'Talla Baja para la Edad o Retraso en Talla': NARANJA,
    'Obesidad': ROJO, 'Desnutrición Aguda Severa': ROJO,
}

def tarjeta(titulo, valor, unidad, clasif=None):
    fondo, texto, borde = COLOR_CLASIF.get(clasif, GRIS)
    etiqueta = f'<span class="etiqueta">{clasif or "Fuera de rango OMS"}</span>' if unidad == 'DE' else ''
    valor_txt = '–' if pd.isna(valor) else (f'{valor:+.2f}' if unidad == 'DE' else f'{valor:.1f}')
    st.markdown(f"""
        <div class="tarjeta" style="--fondo:{fondo}; --texto:{texto}; --borde:{borde}">
          <div class="titulo">{titulo}</div>
          <div class="valor">{valor_txt} <small>{unidad}</small></div>
          {etiqueta}
        </div>""", unsafe_allow_html=True)


# ---------- Gráficas de crecimiento OMS ----------
COLORES_DE = {-3: '#334155', -2: '#ef4444', -1: '#f59e0b', 0: '#16a34a', 1: '#f59e0b', 2: '#ef4444', 3: '#334155'}

@st.cache_data
def tabla_oms(nombre):
    # Tablas LMS oficiales de la OMS (exportadas de anthro / anthroplus)
    return pd.read_csv(DATOS / f"{nombre}.csv")

def curvas_lms(tabla, col_x, sexo):
    t = tabla[tabla['sex'] == sexo].sort_values(col_x)
    L, M, S = t['l'].values, t['m'].values, t['s'].values
    with np.errstate(divide='ignore', invalid='ignore'):
        curvas = {z: np.where(L == 0, M * np.exp(S * z), M * (1 + L * S * z) ** (1 / L)) for z in range(-3, 4)}
    return t[col_x].values, curvas

def grafica(x, curvas, px, py, z, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    ax.fill_between(x, curvas[-1], curvas[1], color='#16a34a', alpha=0.07, lw=0)
    for de, y in curvas.items():
        ax.plot(x, y, color=COLORES_DE[de], lw=1.8 if de == 0 else 1, alpha=1 if de == 0 else 0.8)
        ax.annotate('0' if de == 0 else f'{de:+d}', (x[-1], y[-1]), xytext=(4, 0), textcoords='offset points',
                    color=COLORES_DE[de], fontsize=8, va='center', fontweight='bold')
    if not pd.isna(z):
        ax.plot(px, py, 'o', color='#2563eb', ms=9, mec='white', mew=2, zorder=5)
        ax.annotate(f'{z:+.2f} DE', (px, py), xytext=(10, -18), textcoords='offset points', fontsize=8,
                    color='#1e3a8a', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.35', fc='white', ec='#93c5fd'), zorder=6)
    ax.set_xlabel(xlabel, fontsize=9, color='#475569')
    ax.set_ylabel(ylabel, fontsize=9, color='#475569')
    ax.tick_params(labelsize=8, colors='#475569')
    ax.grid(alpha=0.25)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color('#cbd5e1')
    fig.tight_layout()
    return fig

def graficas_crecimiento(sexo, edad_dias, meses, peso, talla, res):
    """Devuelve [(nombre de la pestaña, figura), ...]."""
    if meses < 60:
        if edad_dias < 731:
            x, c = curvas_lms(tabla_oms('wfl'), 'length', sexo)
            xlabel = 'Longitud (cm)'
        else:
            x, c = curvas_lms(tabla_oms('wfh'), 'height', sexo)
            xlabel = 'Talla (cm)'
        fig_peso = grafica(x, c, talla, peso, res['z_pt'], xlabel, 'Peso (kg)')
        x, c = curvas_lms(tabla_oms('len'), 'age', sexo)
        fig_talla = grafica(x / 30.4375, c, meses, talla, res['z_te'], 'Edad (meses)', 'Talla (cm)')
        return [('Peso para la Talla', fig_peso), ('Talla para la Edad', fig_talla)]
    x, c = curvas_lms(tabla_oms('bfa'), 'age', sexo)
    fig_imc = grafica(x / 12, c, meses / 12, res['imc'], res['z_pt'], 'Edad (años)', 'IMC (kg/m²)')
    x, c = curvas_lms(tabla_oms('hfa'), 'age', sexo)
    fig_talla = grafica(x / 12, c, meses / 12, talla, res['z_te'], 'Edad (años)', 'Talla (cm)')
    return [('IMC para la Edad', fig_imc), ('Talla para la Edad', fig_talla)]


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


# ---------- Página ----------
st.markdown("""
<div class="encabezado">
  <h1>📏 Valoración antropométrica</h1>
  <p>Patrones de crecimiento OMS · Clasificación según la Resolución 2465 de 2016 (Colombia)</p>
</div>""", unsafe_allow_html=True)

col_form, col_res = st.columns([1, 2.3], gap="large")

with col_form:
    with st.form("registro"):
        st.markdown("**Datos del paciente**")
        hoy = datetime.date.today()
        fecha_nacimiento = st.date_input("Fecha de nacimiento", value=datetime.date(2015, 1, 1),
                                         min_value=datetime.date(1990, 1, 1), max_value=hoy, format="DD/MM/YYYY")
        fecha_visita = st.date_input("Fecha de visita", value=hoy,
                                     min_value=datetime.date(1990, 1, 1), format="DD/MM/YYYY")
        genero = st.radio("Sexo", ["Hombre", "Mujer"], horizontal=True)
        c1, c2 = st.columns(2)
        peso = c1.number_input("Peso (kg)", min_value=0.5, max_value=250.0, value=30.0, step=0.1, format="%.1f")
        talla = c2.number_input("Talla (cm)", min_value=40.0, max_value=230.0, value=130.0, step=0.1, format="%.1f")
        calcular = st.form_submit_button("Calcular", type="primary", width="stretch")

with col_res:
    if not calcular:
        st.markdown("""
        <div class="vacio"><div>📋</div>
          Ingresa los datos del paciente y presiona <b>Calcular</b><br>para ver su valoración.
        </div>""", unsafe_allow_html=True)
        st.stop()

    sexo = 1 if genero == "Hombre" else 2
    edad_dias = (fecha_visita - fecha_nacimiento).days
    meses = edad_dias / 30.4375

    if edad_dias < 0:
        st.error("La fecha de visita no puede ser anterior a la fecha de nacimiento.")
        st.stop()
    if meses >= 228:
        st.error("Las tablas de la OMS solo cubren hasta los 19 años.")
        st.stop()

    if meses < 60:
        grupo, nombre_grupo, titulo_pt = "Menor de 5", "Menor de 5 años · OMS 2006", "Peso para la Talla"
        imc, z_pt, z_te = zscores_menor_5(sexo, edad_dias, peso, talla)
    else:
        grupo, nombre_grupo, titulo_pt = "Mayor de 5", "5 a 19 años · OMS 2007", "IMC para la Edad"
        imc, z_pt, z_te = zscores_mayor_5(sexo, meses, peso, talla)
    res = {'imc': imc, 'z_pt': z_pt, 'z_te': z_te}

    edad = relativedelta(fecha_visita, fecha_nacimiento)
    st.markdown(f"""
        <div class="edad">
          <b>{plural(edad.years, 'año', 'años')}, {plural(edad.months, 'mes', 'meses')} y {plural(edad.days, 'día', 'días')}</b>
          <span>{genero} · {nombre_grupo}</span>
        </div>""", unsafe_allow_html=True)

    t1, t2, t3 = st.columns(3)
    with t1:
        tarjeta(titulo_pt, z_pt, 'DE', clasificar_pt_imce(z_pt, grupo))
    with t2:
        tarjeta('Talla para la Edad', z_te, 'DE', clasificar_te(z_te, grupo))
    with t3:
        tarjeta('Índice de Masa Corporal', imc, 'kg/m²')

    if pd.isna(z_pt) or pd.isna(z_te):
        st.warning("Algún valor quedó fuera del rango de las tablas de la OMS (por ejemplo, una talla "
                   "menor a 45 cm o mayor a 120 cm en menores de 5 años). Revisa los datos ingresados.")

    st.write("")
    pestanas = graficas_crecimiento(sexo, edad_dias, meses, peso, talla, res)
    for tab, (_, fig) in zip(st.tabs([nombre for nombre, _ in pestanas]), pestanas):
        with tab:
            st.pyplot(fig)
