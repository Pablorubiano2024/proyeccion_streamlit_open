import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

# Configuración de página
st.set_page_config(page_title="Open Match - Modelo Financiero", layout="wide")

st.sidebar.title("🎛️ Supuestos del Modelo")

# --- Supuestos generales ---
meses = st.sidebar.slider("Duración del modelo (meses)", 12, 60, 36)
precio_premium = st.sidebar.number_input("💰 Precio suscripción premium (USD)", 1, 100, 10)
precio_basica = st.sidebar.number_input("💵 Precio suscripción básica (USD)", 1, 100, 5)
crecimiento_mensual = st.sidebar.slider("📈 Crecimiento mensual usuarios (%)", 0.0, 50.0, 10.0) / 100

# --- Supuestos de suscripciones ---
usuarios_premium_inicio = st.sidebar.number_input("👥 Usuarios premium iniciales", 0, 10000, 50)
usuarios_basica_inicio = st.sidebar.number_input("👤 Usuarios básicos iniciales", 0, 10000, 100)

# --- Sueldos ---
st.sidebar.markdown("## 🧑‍💼 Sueldos Mensuales (USD)")
salario_ceo = st.sidebar.number_input("CEO", 0, 20000, 3000)
salario_cto = st.sidebar.number_input("CTO", 0, 20000, 3000)
salario_dev = st.sidebar.number_input("Fullstack Dev (c/u)", 0, 20000, 2500)
salario_disenador = st.sidebar.number_input("Diseñador UI/UX", 0, 20000, 2000)
salario_mkt = st.sidebar.number_input("Marketing", 0, 20000, 2000)
salario_soporte = st.sidebar.number_input("Soporte/Operaciones", 0, 20000, 1500)
salario_gerentes_comerciales = st.sidebar.number_input("Gerentes Comerciales (c/u)", 0, 20000, 2500)
salario_gerente_financiero = st.sidebar.number_input("Gerente Financiero", 0, 20000, 3000)

# --- Costos fijos adicionales ---
st.sidebar.markdown("## 🧾 Otros Costos Mensuales")
infraestructura = st.sidebar.number_input("Infraestructura en la nube", 0, 10000, 1000)
legales = st.sidebar.number_input("Legales y contables", 0, 10000, 500)
appstore = st.sidebar.number_input("Comisión App Stores", 0, 10000, 300)
otros = st.sidebar.number_input("Otros gastos fijos", 0, 10000, 200)
costo_variable = st.sidebar.number_input("Costo variable por usuario", 0, 100, 3)

# --- Cálculos ---
periodos = range(1, meses + 1)
usuarios_premium = [usuarios_premium_inicio * ((1 + crecimiento_mensual) ** (i - 1)) for i in periodos]
usuarios_basica = [usuarios_basica_inicio * ((1 + crecimiento_mensual) ** (i - 1)) for i in periodos]

ingresos_premium = [round(p * precio_premium, 2) for p in usuarios_premium]
ingresos_basica = [round(b * precio_basica, 2) for b in usuarios_basica]
ingresos_totales = [round(a + b, 2) for a, b in zip(ingresos_premium, ingresos_basica)]

costos_fijos = (
    salario_ceo + salario_cto + salario_dev * 2 + salario_disenador +
    salario_mkt + salario_soporte + salario_gerentes_comerciales * 2 +
    salario_gerente_financiero + infraestructura + legales + appstore + otros
)
costos_fijos_mensuales = [costos_fijos] * meses
costos_variables = [round((p + b) * costo_variable, 2) for p, b in zip(usuarios_premium, usuarios_basica)]
costos_totales = [round(f + v, 2) for f, v in zip(costos_fijos_mensuales, costos_variables)]

utilidades = [ing - cost for ing, cost in zip(ingresos_totales, costos_totales)]

# --- Mostrar tabla
df = pd.DataFrame({
    "Mes": [f"Mes {i}" for i in periodos],
    "Usuarios Premium": usuarios_premium,
    "Usuarios Básicos": usuarios_basica,
    "Ingresos Totales (USD)": ingresos_totales,
    "Costos Totales (USD)": costos_totales,
    "Utilidad Neta (USD)": utilidades
})

st.title("📊 Open Match - Modelo Financiero Interactivo")
st.dataframe(df, use_container_width=True)

# --- Gráficos ---
st.subheader("📈 Gráfico de Ingresos, Costos y Utilidad")
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(df["Mes"], df["Ingresos Totales (USD)"], label="Ingresos")
ax.plot(df["Mes"], df["Costos Totales (USD)"], label="Costos")
ax.plot(df["Mes"], df["Utilidad Neta (USD)"], label="Utilidad")
ax.axhline(0, linestyle="--", color="gray")
ax.set_ylabel("USD")
ax.set_xticks(np.arange(0, meses, max(1, meses // 12)))
ax.set_xticklabels(df["Mes"][::max(1, meses // 12)], rotation=45)
ax.legend()
st.pyplot(fig)

# --- Punto de equilibrio ---
st.subheader("⚖️ Punto de Equilibrio")
if precio_premium > costo_variable:
    punto_equilibrio = round(costos_fijos / (precio_premium - costo_variable))
    st.markdown(f"Para cubrir los **costos fijos mensuales de USD {costos_fijos:,.0f}**, necesitas aproximadamente **{punto_equilibrio} usuarios premium** al mes.")
else:
    st.warning("El costo variable es mayor al precio de venta. Ajusta los valores para calcular el punto de equilibrio.")

# --- Exportar a Excel con formato europeo ---
st.subheader("📥 Exportar resultados a Excel")

# Convertir al formato europeo
df_formateado = df.copy()
cols_monedas = ["Usuarios Premium", "Usuarios Básicos", "Ingresos Totales (USD)", "Costos Totales (USD)", "Utilidad Neta (USD)"]
for col in cols_monedas:
    df_formateado[col] = df_formateado[col].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

# Guardar en un buffer de Excel
output = BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_formateado.to_excel(writer, sheet_name='Proyección', index=False)

st.download_button(
    label="📊 Descargar Excel",
    data=output.getvalue(),
    file_name="Open_Match_Modelo_Financiero.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)