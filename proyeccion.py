import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# Configuration
st.set_page_config(
    page_title="Open Match - Modelo Financiero",
    layout="wide",
    page_icon="📊"
)
st.title("📊 Open Match - Modelo Financiero Interactivo")

# Sidebar Inputs
st.sidebar.title("⚙️ Supuestos del Modelo")

with st.sidebar.expander("📅 Período y Precios", expanded=True):
    meses = st.slider("Duración del modelo (meses)", 12, 60, 36)
    precio_premium = st.number_input("💰 Precio suscripción premium", 1, 100, 10)
    precio_basica = st.number_input("💵 Precio suscripción básica", 1, 100, 5)
    crecimiento_mensual = st.slider("📈 Crecimiento mensual usuarios (%)", 0.0, 50.0, 10.0) / 100

with st.sidebar.expander("👥 Usuarios Iniciales", expanded=True):
    usuarios_premium_inicio = st.number_input("👑 Usuarios premium iniciales", 0, 10000, 50)
    usuarios_basica_inicio = st.number_input("👤 Usuarios básicos iniciales", 0, 10000, 100)

with st.sidebar.expander("👨‍💼 Sueldos y Gracia", expanded=True):
    roles = [
        ("CEO", 3000), ("CTO", 3000), ("Dev", 2500), ("Diseñador", 2000),
        ("Marketing", 2000), ("Soporte", 1500),
        ("Gerentes Comerciales", 2500), ("Gerente Financiero", 3000)
    ]
    sueldos = {}
    gracia = {}
    for nombre, base in roles:
        col1, col2 = st.columns(2)
        with col1:
            sueldos[nombre] = st.number_input(f"{nombre}", 0, 20000, base, key=f"sueldo_{nombre}")
        with col2:
            gracia[nombre] = st.number_input(f"Gracia", 0, 12, 0, key=f"gracia_{nombre}")

with st.sidebar.expander("💸 Costos Operativos", expanded=True):
    infraestructura = st.number_input("☁️ Infraestructura en la nube", 0, 10000, 1000)
    legales = st.number_input("⚖️ Legales y contables", 0, 10000, 500)
    appstore = st.number_input("📱 Comisión App Stores", 0, 10000, 300)
    otros = st.number_input("📦 Otros gastos", 0, 10000, 200)
    costo_variable = st.number_input("👥 Costo variable por usuario", 0, 100, 3)

with st.sidebar.expander("🏦 Financiamiento", expanded=True):
    inversion_inicial = st.number_input("💳 Inversión inicial (USD)", 0, 50000, 15000)
    deuda_mensual = st.number_input("🏧 Cuota mensual deuda (USD)", 0, 10000, 1000)
    tasa_interes_anual = st.slider("📉 Tasa interés anual (%)", 0.0, 50.0, 12.0)
    tasa_impuestos = st.slider("🏛️ Tasa de impuestos (%)", 0.0, 50.0, 19.0)

# Generación de proyección
@st.cache_data(ttl=1)  # Cache for 1 second to allow updates
def generar_proyeccion():
    df = pd.DataFrame()
    deuda_total = deuda_mensual * meses
    interes_mensual = (tasa_interes_anual / 12) / 100

    for i in range(1, meses + 1):
        mes = f"Mes {i}"
        up = round(usuarios_premium_inicio * (1 + crecimiento_mensual) ** (i - 1))
        ub = round(usuarios_basica_inicio * (1 + crecimiento_mensual) ** (i - 1))
        ingresos = up * precio_premium + ub * precio_basica

        # Calculate staff costs
        costos_personal = sum([
            sueldos["CEO"] if i > gracia["CEO"] else 0,
            sueldos["CTO"] if i > gracia["CTO"] else 0,
            sueldos["Dev"] * 2 if i > gracia["Dev"] else 0,
            sueldos["Diseñador"] if i > gracia["Diseñador"] else 0,
            sueldos["Marketing"] if i > gracia["Marketing"] else 0,
            sueldos["Soporte"] if i > gracia["Soporte"] else 0,
            sueldos["Gerentes Comerciales"] * 2 if i > gracia["Gerentes Comerciales"] else 0,
            sueldos["Gerente Financiero"] if i > gracia["Gerente Financiero"] else 0
        ])
        
        costos_fijos = costos_personal + infraestructura + legales + appstore + otros
        costos_variable_total = (up + ub) * costo_variable
        intereses = deuda_total * interes_mensual
        total_costos = costos_fijos + costos_variable_total + intereses
        utilidad_bruta = ingresos - total_costos
        impuestos = max(utilidad_bruta, 0) * (tasa_impuestos / 100)
        utilidad_neta = utilidad_bruta - impuestos

        df = pd.concat([df, pd.DataFrame({
            "Mes": [mes],
            "Usuarios Premium": [up],
            "Usuarios Básicos": [ub],
            "Total Usuarios": [up + ub],
            "Ingresos Totales": [ingresos],
            "Costos Fijos": [costos_fijos],
            "Costos Variables": [costos_variable_total],
            "Intereses": [intereses],
            "Costos Totales": [total_costos],
            "Utilidad Bruta": [utilidad_bruta],
            "Impuestos": [impuestos],
            "Utilidad Neta": [utilidad_neta]
        })], ignore_index=True)

    df["Efectivo Acumulado"] = df["Utilidad Neta"].cumsum() - inversion_inicial
    df["Activos Intangibles"] = 20000
    df["Activo Total"] = df["Efectivo Acumulado"] + df["Activos Intangibles"]
    df["Pasivo"] = deuda_total
    df["Patrimonio"] = df["Efectivo Acumulado"]
    
    # Calculate financial metrics
    df["Margen Bruto"] = (df["Utilidad Bruta"] / df["Ingresos Totales"]).fillna(0)
    df["Margen Neto"] = (df["Utilidad Neta"] / df["Ingresos Totales"]).fillna(0)
    df["ROI"] = (df["Utilidad Neta"] / inversion_inicial).fillna(0)
    
    return df

df = generar_proyeccion()

# Main Dashboard
tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "📈 Gráficos", "📋 Detalles", "📤 Exportar"])

with tab1:
    st.subheader("📌 Resumen Ejecutivo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Usuarios Finales", f"{df['Total Usuarios'].iloc[-1]:,.0f}")
        st.metric("Ingresos Mensuales Finales", f"${df['Ingresos Totales'].iloc[-1]:,.0f}")
    
    with col2:
        st.metric("Utilidad Neta Final", f"${df['Utilidad Neta'].iloc[-1]:,.0f}")
        st.metric("Margen Neto Final", f"{df['Margen Neto'].iloc[-1]:.1%}")
    
    with col3:
        st.metric("Efectivo Acumulado", f"${df['Efectivo Acumulado'].iloc[-1]:,.0f}")
        st.metric("ROI Total", f"{df['ROI'].iloc[-1]:.1%}")
    
    st.subheader("📅 Proyección Mensual")
    st.dataframe(df[["Mes", "Usuarios Premium", "Usuarios Básicos", "Ingresos Totales", 
                    "Costos Totales", "Utilidad Neta"]].style.format({
        "Usuarios Premium": "{:,.0f}",
        "Usuarios Básicos": "{:,.0f}",
        "Ingresos Totales": "${:,.0f}",
        "Costos Totales": "${:,.0f}",
        "Utilidad Neta": "${:,.0f}"
    }), height=400)

with tab2:
    st.subheader("📈 Tendencias Clave")
    
    # Calculate proper tick spacing
    tick_spacing = max(1, meses // 12)
    x_ticks = np.arange(0, meses, tick_spacing)
    x_labels = df["Mes"][::tick_spacing]
    
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(df["Mes"], df["Ingresos Totales"], label="Ingresos", color="green")
    ax1.plot(df["Mes"], df["Costos Totales"], label="Costos", color="red")
    ax1.plot(df["Mes"], df["Utilidad Neta"], label="Utilidad Neta", color="blue")
    ax1.axhline(0, linestyle="--", color="gray")
    ax1.set_xticks(x_ticks)
    ax1.set_xticklabels(x_labels, rotation=45)
    ax1.set_ylabel("USD")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.7)
    st.pyplot(fig1)
    
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(df["Mes"], df["Usuarios Premium"], label="Premium", color="gold")
    ax2.plot(df["Mes"], df["Usuarios Básicos"], label="Básicos", color="silver")
    ax2.set_xticks(x_ticks)
    ax2.set_xticklabels(x_labels, rotation=45)
    ax2.set_ylabel("Usuarios")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.7)
    st.pyplot(fig2)
    
    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.plot(df["Mes"], df["Margen Bruto"]*100, label="Margen Bruto", color="green")
    ax3.plot(df["Mes"], df["Margen Neto"]*100, label="Margen Neto", color="blue")
    ax3.set_xticks(x_ticks)
    ax3.set_xticklabels(x_labels, rotation=45)
    ax3.set_ylabel("Porcentaje (%)")
    ax3.legend()
    ax3.grid(True, linestyle="--", alpha=0.7)
    st.pyplot(fig3)

with tab3:
    st.subheader("📋 Detalle Financiero")
    st.dataframe(df)

with tab4:
    st.subheader("📤 Exportar Reporte")
    
    def create_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Title
        pdf.cell(200, 10, txt="Open Match - Reporte Financiero", ln=1, align="C")
        pdf.cell(200, 10, txt=f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align="C")
        
        # Summary
        pdf.cell(200, 10, txt="Resumen Ejecutivo", ln=1, align="L")
        pdf.cell(200, 10, txt=f"Duración: {meses} meses", ln=1)
        pdf.cell(200, 10, txt=f"Usuarios finales: {df['Total Usuarios'].iloc[-1]:,.0f}", ln=1)
        pdf.cell(200, 10, txt=f"Utilidad neta final: ${df['Utilidad Neta'].iloc[-1]:,.0f}", ln=1)
        
        # Data table
        pdf.cell(200, 10, txt="Datos Financieros:", ln=1)
        pdf.cell(40, 10, txt="Mes", border=1)
        pdf.cell(40, 10, txt="Ingresos", border=1)
        pdf.cell(40, 10, txt="Costos", border=1)
        pdf.cell(40, 10, txt="Utilidad", border=1)
        pdf.ln()
        
        for _, row in df.iterrows():
            pdf.cell(40, 10, txt=row["Mes"], border=1)
            pdf.cell(40, 10, txt=f"${row['Ingresos Totales']:,.0f}", border=1)
            pdf.cell(40, 10, txt=f"${row['Costos Totales']:,.0f}", border=1)
            pdf.cell(40, 10, txt=f"${row['Utilidad Neta']:,.0f}", border=1)
            pdf.ln()
        
        return pdf.output(dest="S").encode("latin1")
    
    if st.button("🖨️ Generar PDF"):
        pdf_data = create_pdf(df)
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_data,
            file_name=f"reporte_financiero_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    
    if st.button("📝 Exportar a Excel"):
        towrite = BytesIO()
        df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=towrite,
            file_name=f"datos_financieros_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Punto de equilibrio
st.subheader("⚖️ Análisis de Punto de Equilibrio")
if precio_premium > costo_variable:
    promedio_costos_fijos = df["Costos Fijos"].mean()
    pe = round(promedio_costos_fijos / (precio_premium - costo_variable))
    st.markdown(f"""
    **Punto de equilibrio:**  
    Necesitas **{pe:,} usuarios premium** para cubrir costos fijos.  
    Esto ocurriría aproximadamente en el **Mes {min(max(1, int(np.log(pe/max(1,usuarios_premium_inicio))/np.log(1+crecimiento_mensual)) + 1), meses)}**.
    """)
else:
    st.error("⚠️ El costo variable excede el precio de suscripción premium - el modelo no es sostenible")
    