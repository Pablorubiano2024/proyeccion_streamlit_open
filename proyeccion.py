import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import json

# ================================
# CONFIGURACIÓN Y ESTILOS
# ================================

st.set_page_config(
    page_title="💰 Job Match - Proyección Financiera",
    layout="wide",
    page_icon="💸",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        font-family: 'Inter', sans-serif;
    }
    
    .main-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
    }
    
    .metric-card { 
        background: linear-gradient(145deg, #ffffff, #f0f0f0);
        border-radius: 15px; 
        padding: 20px; 
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .positive { color: #28a745; font-weight: bold; }
    .negative { color: #dc3545; font-weight: bold; }
    .warning { color: #ffc107; font-weight: bold; }
    
    .header-title {
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .section-header {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 10px 20px;
        border-radius: 10px;
        margin: 20px 0 10px 0;
        font-weight: bold;
    }
    
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .sidebar .stSelectbox > div > div {
        background-color: #f8f9fa;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# FUNCIONES AUXILIARES
# ================================

def validate_inputs():
    """Valida las entradas del usuario"""
    errors = []
    warnings_list = []
    
    if precio_premium <= costo_variable:
        errors.append("⚠️ El precio premium debe ser mayor al costo variable")
    
    if precio_basica <= costo_variable:
        errors.append("⚠️ El precio básico debe ser mayor al costo variable")
    
    if usuarios_premium_inicio + usuarios_basica_inicio == 0:
        errors.append("⚠️ Debe tener al menos un usuario inicial")
    
    if inversion_inicial < sum(sueldos.values()) * 3:
        warnings_list.append("💭 La inversión inicial podría ser insuficiente para financiar al equipo durante 3 meses")
    
    return errors, warnings_list

@st.cache_data(ttl=3600)
def calcular_proyeccion_financiera(
    meses, usuarios_premium_inicio, usuarios_basica_inicio, 
    precio_premium, precio_basica, crecimiento_mensual,
    sueldos, gracia, costos_fijos, costo_variable,
    inversion_inicial, tasa_impuestos
):
    """Calcula la proyección financiera optimizada"""
    
    # Crear DataFrame base
    df = pd.DataFrame(index=range(1, meses + 1))
    df.index.name = 'Mes'
    
    # Cálculo de usuarios con crecimiento compuesto
    df['Usuarios_Premium'] = np.round(
        usuarios_premium_inicio * (1 + crecimiento_mensual) ** (df.index - 1)
    ).astype(int)
    
    df['Usuarios_Basicos'] = np.round(
        usuarios_basica_inicio * (1 + crecimiento_mensual) ** (df.index - 1)
    ).astype(int)
    
    df['Total_Usuarios'] = df['Usuarios_Premium'] + df['Usuarios_Basicos']
    
    # Cálculo de ingresos
    df['Ingresos_Premium'] = df['Usuarios_Premium'] * precio_premium
    df['Ingresos_Basicos'] = df['Usuarios_Basicos'] * precio_basica
    df['Ingresos_Totales'] = df['Ingresos_Premium'] + df['Ingresos_Basicos']
    
    # Cálculo de costos de personal (considerando período de gracia)
    costos_personal_por_mes = []
    for mes in df.index:
        costo_mes = sum([
            sueldos[rol] * cantidad if mes > gracia.get(rol, 0) else 0
            for rol, cantidad in [
                ("CEO", 1),
                ("CTO", 1),
                ("Dev Fullstack", 2),
                ("Diseñador UX/UI", 1),
                ("Growth Marketer", 1),
                ("Soporte", 1),
                ("Sales Manager", 2),
                ("CFO", 1)
            ]
        ])
        costos_personal_por_mes.append(costo_mes)
    
    df['Costos_Personal'] = costos_personal_por_mes
    df['Costos_Fijos'] = df['Costos_Personal'] + costos_fijos['total']
    df['Costos_Variables'] = df['Total_Usuarios'] * costo_variable
    df['Costos_Totales'] = df['Costos_Fijos'] + df['Costos_Variables']
    
    # Cálculo de utilidades
    df['Utilidad_Bruta'] = df['Ingresos_Totales'] - df['Costos_Totales']
    df['Impuestos'] = np.where(
        df['Utilidad_Bruta'] > 0, 
        df['Utilidad_Bruta'] * (tasa_impuestos / 100), 
        0
    )
    df['Utilidad_Neta'] = df['Utilidad_Bruta'] - df['Impuestos']
    
    # Flujo de efectivo y métricas
    df['Flujo_Efectivo'] = df['Utilidad_Neta']
    df['Efectivo_Acumulado'] = df['Flujo_Efectivo'].cumsum() + inversion_inicial
    
    # Métricas financieras
    df['Margen_Bruto'] = np.where(
        df['Ingresos_Totales'] > 0,
        df['Utilidad_Bruta'] / df['Ingresos_Totales'],
        0
    )
    
    df['Margen_Neto'] = np.where(
        df['Ingresos_Totales'] > 0,
        df['Utilidad_Neta'] / df['Ingresos_Totales'],
        0
    )
    
    df['ROI_Acumulado'] = np.where(
        inversion_inicial > 0,
        (df['Efectivo_Acumulado'] - inversion_inicial) / inversion_inicial,
        0
    )
    
    return df.reset_index()

def crear_graficos_principales(df):
    """Crea los gráficos principales del dashboard"""
    
    # Gráfico 1: Ingresos vs Costos vs Utilidad
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df['Mes'], y=df['Ingresos_Totales'],
        name='Ingresos', line=dict(color='#28a745', width=3),
        hovertemplate='<b>Ingresos</b><br>Mes %{x}<br>$%{y:,.0f}<extra></extra>'
    ))
    fig1.add_trace(go.Scatter(
        x=df['Mes'], y=df['Costos_Totales'],
        name='Costos', line=dict(color='#dc3545', width=3),
        hovertemplate='<b>Costos</b><br>Mes %{x}<br>$%{y:,.0f}<extra></extra>'
    ))
    fig1.add_trace(go.Scatter(
        x=df['Mes'], y=df['Utilidad_Neta'],
        name='Utilidad Neta', line=dict(color='#007bff', width=3),
        fill='tonexty', fillcolor='rgba(0,123,255,0.1)',
        hovertemplate='<b>Utilidad Neta</b><br>Mes %{x}<br>$%{y:,.0f}<extra></extra>'
    ))
    fig1.update_layout(
        title='📈 Evolución Financiera',
        xaxis_title='Mes',
        yaxis_title='USD',
        hovermode='x unified',
        template='plotly_white',
        height=450,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Gráfico 2: Crecimiento de Usuarios
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df['Mes'], y=df['Usuarios_Premium'],
        name='Premium', marker_color='#ffc107',
        hovertemplate='<b>Premium</b><br>Mes %{x}<br>%{y:,.0f} usuarios<extra></extra>'
    ))
    fig2.add_trace(go.Bar(
        x=df['Mes'], y=df['Usuarios_Basicos'],
        name='Básicos', marker_color='#6c757d',
        hovertemplate='<b>Básicos</b><br>Mes %{x}<br>%{y:,.0f} usuarios<extra></extra>'
    ))
    fig2.update_layout(
        title='👥 Evolución de Usuarios',
        xaxis_title='Mes',
        yaxis_title='Cantidad de Usuarios',
        hovermode='x unified',
        template='plotly_white',
        height=450,
        barmode='stack'
    )
    
    # Gráfico 3: Métricas Clave
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df['Mes'], y=df['Margen_Bruto'] * 100,
        name='Margen Bruto (%)', line=dict(color='#20c997', width=2),
        hovertemplate='<b>Margen Bruto</b><br>Mes %{x}<br>%{y:.1f}%<extra></extra>'
    ))
    fig3.add_trace(go.Scatter(
        x=df['Mes'], y=df['Margen_Neto'] * 100,
        name='Margen Neto (%)', line=dict(color='#6610f2', width=2),
        hovertemplate='<b>Margen Neto</b><br>Mes %{x}<br>%{y:.1f}%<extra></extra>'
    ))
    fig3.add_trace(go.Scatter(
        x=df['Mes'], y=df['ROI_Acumulado'] * 100,
        name='ROI Acumulado (%)', line=dict(color='#fd7e14', width=2),
        hovertemplate='<b>ROI Acumulado</b><br>Mes %{x}<br>%{y:.1f}%<extra></extra>'
    ))
    fig3.update_layout(
        title='📊 Métricas de Rentabilidad',
        xaxis_title='Mes',
        yaxis_title='Porcentaje (%)',
        hovermode='x unified',
        template='plotly_white',
        height=450
    )
    
    return fig1, fig2, fig3

def generar_reporte_ejecutivo(df):
    """Genera un reporte ejecutivo en markdown con explicación de la inversión inicial"""
    
    # Encontrar el mes de break-even
    try:
        break_even_mes = df[df['Utilidad_Neta'] > 0]['Mes'].iloc[0]
        break_even_text = f"Mes {break_even_mes}"
    except IndexError:
        break_even_text = "No alcanzado en el período"
    
    # Calcular métricas clave
    ingresos_totales = df['Ingresos_Totales'].sum()
    usuarios_promedio = df['Total_Usuarios'].mean()
    ltv_estimado = ingresos_totales / usuarios_promedio if usuarios_promedio > 0 else 0
    crecimiento_promedio = df['Total_Usuarios'].pct_change().mean() * 100
    
    return f"""
    ### 📋 REPORTE EJECUTIVO
    
    **🎯 Punto de Equilibrio:** {break_even_text}
    
    **📈 Métricas de Crecimiento:**
    - Crecimiento promedio mensual: {crecimiento_promedio:.1f}%
    - Usuarios finales proyectados: {df['Total_Usuarios'].iloc[-1]:,}
    
    **💰 Métricas Financieras:**
    - LTV estimado por usuario: ${ltv_estimado:.0f}
    - Margen neto final: {df['Margen_Neto'].iloc[-1]:.1%}
    - ROI total del proyecto: {df['ROI_Acumulado'].iloc[-1]:.1%}
    
    **💵 Flujo de Caja:**
    - Efectivo final proyectado: ${df['Efectivo_Acumulado'].iloc[-1]:,}
    - Mejor mes (utilidad): ${df['Utilidad_Neta'].max():,}
    - Peor mes (utilidad): ${df['Utilidad_Neta'].min():,}
    
    **🔍 Impacto de la Inversión Inicial:**
    La inversión inicial de **${inversion_inicial:,}** permite cubrir el flujo de caja de los primeros meses en que el proyecto genera pérdidas operativas. 
    - Durante el período de lanzamiento, los costos fijos y de nómina superan los ingresos, por lo que el capital inicial financia esas diferencias.
    - Conforme la adquisición de usuarios crece, el flujo de efectivo acumulado tiende a volverse positivo, recuperando gradualmente la inversión.
    - Si la inversión inicial es insuficiente, se requerirá financiamiento adicional para evitar riesgo de quiebra antes de alcanzar el punto de equilibrio.
    """

# ================================
# INTERFAZ PRINCIPAL
# ================================

# Header principal
st.markdown('<h1 class="header-title">💸 Job Match </h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Proyección Financiera Interactiva</p>', unsafe_allow_html=True)

# ================================
# SIDEBAR CON PARÁMETROS
# ================================

with st.sidebar:
    st.markdown("## ⚙️ CONFIGURACIÓN DEL MODELO")
    
    # Sección 1: Período y Precios
    with st.expander("📅 PERÍODO Y PRECIOS", expanded=True):
        meses = st.slider("Duración del modelo (meses)", 12, 60, 36, 
                         help="Horizonte de proyección financiera")
        
        col1, col2 = st.columns(2)
        with col1:
            precio_premium = st.number_input("💰 Precio Premium ($)", 1, 200, 99, 
                                           help="Precio mensual suscripción premium")
        with col2:
            precio_basica = st.number_input("💵 Precio Básico ($)", 1, 200, 9, 
                                          help="Precio mensual suscripción básica")
        
        crecimiento_mensual = st.slider("📈 Crecimiento usuarios/mes (%)", 
                                       0.0, 50.0, 12.0, step=0.5) / 100
    
    # Sección 2: Usuarios Iniciales
    with st.expander("👥 BASE DE USUARIOS", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            usuarios_premium_inicio = st.number_input("👑 Premium iniciales", 0, 50000, 15)
        with col2:
            usuarios_basica_inicio = st.number_input("👤 Básicos iniciales", 0, 50000, 30)
    
    # Sección 3: Equipo y Sueldos
    with st.expander("👨‍💼 EQUIPO Y NÓMINA"):
        roles_data = {
            "CEO": 0, "CTO": 0, "Dev Fullstack": 2800,
            "Diseñador UX/UI": 1000, "Growth Marketer": 1000,
            "Soporte": 1800, "Sales Manager": 0, "CFO": 0
        }
        
        sueldos = {}
        gracia = {}
        
        for rol, sueldo_base in roles_data.items():
            st.markdown(f"**{rol}**")
            col1, col2 = st.columns(2)
            with col1:
                sueldos[rol] = st.number_input(
                    f"Sueldo", 0, 20000, sueldo_base, 
                    key=f"sueldo_{rol}", help=f"Sueldo mensual para {rol}"
                )
            with col2:
                gracia_default = 0 if rol == "CEO" else 0
                gracia[rol] = st.number_input(
                    f"Gracia (meses)", 0, 12, gracia_default,
                    key=f"gracia_{rol}", help=f"Meses sin pago para {rol}"
                )
    
    # Sección 4: Costos Operativos
    with st.expander("💳 COSTOS OPERATIVOS"):
        st.markdown("**Costos Fijos Mensuales**")
        infraestructura = st.number_input("☁️ Infraestructura/Hosting", 0, 20000, 200)
        legales = st.number_input("⚖️ Legales/Contabilidad", 0, 10000, 100)
        appstore = st.number_input("📱 Comisiones App Stores", 0, 10000, 500)
        marketing = st.number_input("📢 Marketing/Publicidad", 0, 20000, 500)
        otros = st.number_input("📦 Otros gastos fijos", 0, 10000, 300)
        
        costos_fijos = {
            'infraestructura': infraestructura,
            'legales': legales,
            'appstore': appstore,
            'marketing': marketing,
            'otros': otros,
            'total': infraestructura + legales + appstore + marketing + otros
        }
        
        st.markdown("**Costos Variables**")
        costo_variable = st.number_input("👥 Costo por usuario/mes", 0.0, 50.0, 2.5, 
                                       step=0.1, help="Costo variable por usuario activo")
    
    # Sección 5: Financiamiento
    with st.expander("🏦 FINANCIAMIENTO E IMPUESTOS"):
        inversion_inicial = st.number_input("💵 Inversión inicial ($)", 0, 500000, 2500,
                                          help="Capital inicial disponible")
        tasa_impuestos = st.slider("🏛️ Tasa de impuestos (%)", 0.0, 50.0, 19.0, 
                                 step=0.5, help="Tasa impositiva sobre utilidades")

# ================================
# VALIDACIONES
# ================================

errors, warnings = validate_inputs()

if errors:
    for error in errors:
        st.error(error)
    st.stop()

if warnings:
    for warning in warnings:
        st.warning(warning)

# ================================
# CÁLCULOS PRINCIPALES
# ================================

with st.spinner("Calculando proyección financiera..."):
    df = calcular_proyeccion_financiera(
        meses, usuarios_premium_inicio, usuarios_basica_inicio,
        precio_premium, precio_basica, crecimiento_mensual,
        sueldos, gracia, costos_fijos, costo_variable,
        inversion_inicial, tasa_impuestos
    )

# ================================
# DASHBOARD PRINCIPAL
# ================================

# Pestañas principales
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 RESUMEN EJECUTIVO", "📈 VISUALIZACIONES", "🧮 DATOS DETALLADOS", 
    "🎯 ANÁLISIS AVANZADO", "📤 EXPORTAR"
])

# ================================
# TAB 1: RESUMEN EJECUTIVO
# ================================
with tab1:
    st.markdown("### 📈 MÉTRICAS CLAVE")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "👥 Usuarios Finales", 
            f"{df['Total_Usuarios'].iloc[-1]:,.0f}",
            delta=f"+{df['Total_Usuarios'].iloc[-1] - (usuarios_premium_inicio + usuarios_basica_inicio):,.0f}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        crecimiento_total = ((df['Total_Usuarios'].iloc[-1] / (usuarios_premium_inicio + usuarios_basica_inicio)) - 1) * 100
        st.metric("📈 Crecimiento Total", f"{crecimiento_total:.0f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "💰 Ingresos Mensuales", 
            f"${df['Ingresos_Totales'].iloc[-1]:,.0f}",
            delta=f"${df['Ingresos_Totales'].iloc[-1] - df['Ingresos_Totales'].iloc[0]:,.0f}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("💸 Costos Mensuales", f"${df['Costos_Totales'].iloc[-1]:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        utilidad_final = df['Utilidad_Neta'].iloc[-1]
        delta_color = "normal" if utilidad_final >= 0 else "inverse"
        st.metric(
            "🎯 Utilidad Mensual Final", 
            f"${abs(utilidad_final):,.0f}",
            delta=f"{'Positiva' if utilidad_final >= 0 else 'Negativa'}",
            delta_color=delta_color
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📊 Margen Neto Final", f"{df['Margen_Neto'].iloc[-1]:.1%}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        efectivo_final = df['Efectivo_Acumulado'].iloc[-1]
        st.metric(
            "💵 Efectivo Acumulado", 
            f"${abs(efectivo_final):,.0f}",
            delta=f"{'Positivo' if efectivo_final >= 0 else 'Negativo'}",
            delta_color="normal" if efectivo_final >= 0 else "inverse"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🚀 ROI Total", f"{df['ROI_Acumulado'].iloc[-1]:.1%}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Reporte ejecutivo con explicación del impacto de la inversión inicial
    st.markdown(generar_reporte_ejecutivo(df), unsafe_allow_html=True)
    
    # Estado del negocio según flujo e utilidad
    if df['Efectivo_Acumulado'].iloc[-1] > 0 and df['Utilidad_Neta'].iloc[-1] > 0:
        st.markdown(
            '<div class="alert-success">✅ <strong>Estado: SALUDABLE</strong> - El modelo es rentable y sostenible.</div>',
            unsafe_allow_html=True
        )
    elif df['Utilidad_Neta'].iloc[-1] > 0:
        st.markdown(
            '<div class="alert-success">⚠️ <strong>Estado: EN CRECIMIENTO</strong> - Rentable pero requiere gestión de capital.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="alert-danger">🚨 <strong>Estado: REQUIERE AJUSTES</strong> - El modelo necesita optimización.</div>',
            unsafe_allow_html=True
        )

# ================================
# TAB 2: VISUALIZACIONES
# ================================
with tab2:
    st.markdown("### 📊 ANÁLISIS VISUAL INTERACTIVO")
    
    fig1, fig2, fig3 = crear_graficos_principales(df)
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)
    
    st.markdown("### 💰 ANÁLISIS DE FLUJO DE EFECTIVO")
    fig4 = go.Figure()
    
    positive_mask = df['Efectivo_Acumulado'] >= 0
    negative_mask = df['Efectivo_Acumulado'] < 0
    
    if positive_mask.any():
        fig4.add_trace(go.Scatter(
            x=df.loc[positive_mask, 'Mes'],
            y=df.loc[positive_mask, 'Efectivo_Acumulado'],
            fill='tozeroy', fillcolor='rgba(40, 167, 69, 0.3)',
            line=dict(color='#28a745'), name='Efectivo Positivo',
            hovertemplate='<b>Efectivo Acumulado</b><br>Mes %{x}<br>$%{y:,.0f}<extra></extra>'
        ))
    if negative_mask.any():
        fig4.add_trace(go.Scatter(
            x=df.loc[negative_mask, 'Mes'],
            y=df.loc[negative_mask, 'Efectivo_Acumulado'],
            fill='tozeroy', fillcolor='rgba(220, 53, 69, 0.3)',
            line=dict(color='#dc3545'), name='Efectivo Negativo',
            hovertemplate='<b>Efectivo Acumulado</b><br>Mes %{x}<br>$%{y:,.0f}<extra></extra>'
        ))
    fig4.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig4.update_layout(
        title='💰 Evolución del Flujo de Efectivo Acumulado',
        xaxis_title='Mes',
        yaxis_title='Efectivo Acumulado (USD)',
        template='plotly_white',
        height=400,
        showlegend=True
    )
    st.plotly_chart(fig4, use_container_width=True)

# ================================
# TAB 3: DATOS DETALLADOS
# ================================
with tab3:
    st.markdown("### 🧮 DATOS DETALLADOS (Con Costo de Inversión Inicial)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        mostrar_desde = st.selectbox(
            "Mostrar desde mes:", 
            options=list(range(1, meses + 1)), 
            index=0
        )
    with col2:
        mostrar_hasta = st.selectbox(
            "Mostrar hasta mes:", 
            options=list(range(1, meses + 1)), 
            index=min(11, meses - 1)
        )
    with col3:
        formato_numeros = st.selectbox(
            "Formato números:", 
            ["Completos", "Miles (K)", "Millones (M)"]
        )
    
    # Filtrar y añadir columna de inversión inicial
    df_filtered = df[(df['Mes'] >= mostrar_desde) & (df['Mes'] <= mostrar_hasta)].copy()
    df_filtered['Costo_Inversion_Inicial'] = inversion_inicial
    
    # Ajustar formato
    if formato_numeros == "Miles (K)":
        cols_num = ['Ingresos_Totales', 'Costos_Totales', 'Utilidad_Neta', 
                    'Efectivo_Acumulado', 'Costos_Personal', 'Costos_Variables', 'Costo_Inversion_Inicial']
        for col in cols_num:
            if col in df_filtered.columns:
                df_filtered[col] = (df_filtered[col] / 1000).round(1)
    elif formato_numeros == "Millones (M)":
        cols_num = ['Ingresos_Totales', 'Costos_Totales', 'Utilidad_Neta', 
                    'Efectivo_Acumulado', 'Costos_Personal', 'Costos_Variables', 'Costo_Inversion_Inicial']
        for col in cols_num:
            if col in df_filtered.columns:
                df_filtered[col] = (df_filtered[col] / 1_000_000).round(2)
    
    # Mostrar tabla y descripción
    st.dataframe(
        df_filtered.style.format({
            'Margen_Bruto': '{:.1%}',
            'Margen_Neto': '{:.1%}',
            'ROI_Acumulado': '{:.1%}',
            'Usuarios_Premium': '{:,.0f}',
            'Usuarios_Basicos': '{:,.0f}',
            'Total_Usuarios': '{:,.0f}'
        }).background_gradient(subset=['Utilidad_Neta'], cmap='RdYlGn'),
        use_container_width=True,
        height=400
    )
    
    st.markdown("""
    **Descripción del Costo de Inversión Inicial**  
    - La columna **Costo_Inversion_Inicial** permanece constante en cada fila: representa el capital inicial que se destinó a cubrir gastos antes de alcanzar la rentabilidad.
    - Este monto acumula el flujo de caja negativo de los meses de lanzamiento y se “recupera” gradualmente conforme el Flujo de Efectivo acumulado se torne positivo.
    - Sirve para comparar mes a mes cuánto de la inversión inicial aún está “pendiente de retorno”.
    """)
    
    st.markdown("### 📊 ESTADÍSTICAS DESCRIPTIVAS")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ingresos y Costos**")
        stats_df = pd.DataFrame({
            'Ingresos Totales': df['Ingresos_Totales'].describe(),
            'Costos Totales': df['Costos_Totales'].describe(),
            'Utilidad Neta': df['Utilidad_Neta'].describe()
        }).round(0)
        st.dataframe(stats_df)
    with col2:
        st.markdown("**Usuarios y Métricas**")
        stats_df2 = pd.DataFrame({
            'Total Usuarios': df['Total_Usuarios'].describe(),
            'Margen Bruto (%)': (df['Margen_Bruto'] * 100).describe(),
            'ROI Acumulado (%)': (df['ROI_Acumulado'] * 100).describe()
        }).round(1)
        st.dataframe(stats_df2)

# ================================
# TAB 4: ANÁLISIS AVANZADO
# ================================
with tab4:
    st.markdown("### 🎯 ANÁLISIS DE SENSIBILIDAD Y ESCENARIOS")
    
    st.markdown("#### ⚖️ Análisis de Punto de Equilibrio")
    try:
        break_even_mes = df[df['Utilidad_Neta'] > 0]['Mes'].iloc[0]
        break_even_usuarios = df[df['Mes'] == break_even_mes]['Total_Usuarios'].iloc[0]
        break_even_ingresos = df[df['Mes'] == break_even_mes]['Ingresos_Totales'].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🗓️ Mes de Break-Even", break_even_mes)
        with col2:
            st.metric("👥 Usuarios necesarios", f"{break_even_usuarios:,.0f}")
        with col3:
            st.metric("💰 Ingresos necesarios", f"${break_even_ingresos:,.0f}")
    except IndexError:
        st.warning("⚠️ No se alcanza el punto de equilibrio en el período proyectado")
        costos_promedio = df['Costos_Totales'].mean()
        precio_promedio = (precio_premium + precio_basica) / 2
        usuarios_necesarios = costos_promedio / precio_promedio
        st.info(f"💡 Se necesitan aproximadamente {usuarios_necesarios:,.0f} usuarios para alcanzar el equilibrio")
    
    st.markdown("#### 📊 Análisis de Sensibilidad")
    sensibilidad_param = st.selectbox(
        "Seleccionar parámetro para análisis:",
        ["Precio Premium", "Precio Básico", "Crecimiento Mensual", "Costo Variable"]
    )
    if sensibilidad_param == "Precio Premium":
        base_value = precio_premium
        range_values = np.linspace(base_value * 0.5, base_value * 1.5, 11)
        param_key = 'precio_premium'
    elif sensibilidad_param == "Precio Básico":
        base_value = precio_basica
        range_values = np.linspace(base_value * 0.5, base_value * 1.5, 11)
        param_key = 'precio_basica'
    elif sensibilidad_param == "Crecimiento Mensual":
        base_value = crecimiento_mensual * 100
        range_values = np.linspace(0, base_value * 2, 11)
        param_key = 'crecimiento_mensual'
    else:
        base_value = costo_variable
        range_values = np.linspace(0, base_value * 2, 11)
        param_key = 'costo_variable'
    
    sensibilidad_results = []
    for value in range_values:
        temp_params = {
            'meses': meses,
            'usuarios_premium_inicio': usuarios_premium_inicio,
            'usuarios_basica_inicio': usuarios_basica_inicio,
            'precio_premium': precio_premium,
            'precio_basica': precio_basica,
            'crecimiento_mensual': crecimiento_mensual,
            'sueldos': sueldos,
            'gracia': gracia,
            'costos_fijos': costos_fijos,
            'costo_variable': costo_variable,
            'inversion_inicial': inversion_inicial,
            'tasa_impuestos': tasa_impuestos
        }
        if param_key == 'precio_premium':
            temp_params['precio_premium'] = value
        elif param_key == 'precio_basica':
            temp_params['precio_basica'] = value
        elif param_key == 'crecimiento_mensual':
            temp_params['crecimiento_mensual'] = value / 100
        else:
            temp_params['costo_variable'] = value
        
        temp_df = calcular_proyeccion_financiera(**temp_params)
        sensibilidad_results.append({
            'Parámetro': value,
            'Utilidad_Final': temp_df['Utilidad_Neta'].iloc[-1],
            'Efectivo_Final': temp_df['Efectivo_Acumulado'].iloc[-1],
            'ROI_Final': temp_df['ROI_Acumulado'].iloc[-1]
        })
    
    sens_df = pd.DataFrame(sensibilidad_results)
    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x=sens_df['Parámetro'],
        y=sens_df['Utilidad_Final'],
        mode='lines+markers',
        name='Utilidad Final',
        line=dict(color='#007bff', width=3),
        marker=dict(size=8)
    ))
    fig_sens.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    fig_sens.update_layout(
        title=f'📈 Sensibilidad: {sensibilidad_param} vs Utilidad Final',
        xaxis_title=sensibilidad_param,
        yaxis_title='Utilidad Final (USD)',
        template='plotly_white',
        height=400
    )
    st.plotly_chart(fig_sens, use_container_width=True)
    
    st.markdown("**Resultados del Análisis de Sensibilidad**")
    st.dataframe(
        sens_df.style.format({
            'Parámetro': '{:.2f}',
            'Utilidad_Final': '${:,.0f}',
            'Efectivo_Final': '${:,.0f}',
            'ROI_Final': '{:.1%}'
        }).background_gradient(subset=['Utilidad_Final'], cmap='RdYlGn'),
        use_container_width=True
    )
    
    st.markdown("#### ⚠️ Análisis de Riesgos")
    meses_negativos = len(df[df['Utilidad_Neta'] < 0])
    max_perdida = df['Utilidad_Neta'].min()
    efectivo_minimo = df['Efectivo_Acumulado'].min()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📉 Meses con pérdidas", meses_negativos)
    with col2:
        st.metric("💸 Pérdida máxima mensual", f"${abs(max_perdida):,.0f}")
    with col3:
        st.metric("⚠️ Efectivo mínimo", f"${efectivo_minimo:,.0f}")
    
    if efectivo_minimo < 0:
        st.error(f"🚨 **RIESGO ALTO**: Se requiere financiamiento adicional de al menos ${abs(efectivo_minimo):,.0f}")
    elif meses_negativos > meses * 0.5:
        st.warning("⚠️ **RIESGO MEDIO**: Más del 50% de los meses presentan pérdidas")
    else:
        st.success("✅ **RIESGO BAJO**: El modelo financiero es estable")

# ================================
# TAB 5: EXPORTAR
# ================================
with tab5:
    st.markdown("### 📤 EXPORTAR RESULTADOS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Exportar Datos")
        export_df = df.copy()
        export_df['Fecha'] = pd.date_range(start='2024-01-01', periods=len(export_df), freq='M')
        
        # CSV
        csv_buffer = BytesIO()
        export_df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv_buffer.getvalue(),
            file_name=f"jobmatch_proyeccion_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            help="Descarga todos los datos en formato CSV"
        )
        
        # Excel con hojas
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Proyección Financiera', index=False)
            params_df = pd.DataFrame({
                'Parámetro': [
                    'Duración (meses)', 'Usuarios Premium Inicial', 'Usuarios Básicos Inicial',
                    'Precio Premium', 'Precio Básico', 'Crecimiento Mensual (%)',
                    'Inversión Inicial', 'Tasa Impuestos (%)', 'Costo Variable'
                ],
                'Valor': [
                    meses, usuarios_premium_inicio, usuarios_basica_inicio,
                    precio_premium, precio_basica, crecimiento_mensual * 100,
                    inversion_inicial, tasa_impuestos, costo_variable
                ]
            })
            params_df.to_excel(writer, sheet_name='Parámetros', index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="📊 Descargar Excel",
            data=excel_buffer.getvalue(),
            file_name=f"jobmatch_completo_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Descarga datos completos en formato Excel con múltiples hojas"
        )
    
    with col2:
        st.markdown("#### 📋 Exportar Reporte")
        reporte_completo = f"""
# JOB MATCH - REPORTE FINANCIERO EJECUTIVO
*Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}*

## RESUMEN EJECUTIVO

### Parámetros del Modelo
- **Duración**: {meses} meses
- **Usuarios iniciales**: {usuarios_premium_inicio:,} Premium + {usuarios_basica_inicio:,} Básicos
- **Precios**: ${precio_premium} Premium / ${precio_basica} Básico
- **Crecimiento mensual**: {crecimiento_mensual:.1%}
- **Inversión inicial**: ${inversion_inicial:,}

### Resultados Clave
- **Usuarios finales proyectados**: {df['Total_Usuarios'].iloc[-1]:,}
- **Ingresos mensuales finales**: ${df['Ingresos_Totales'].iloc[-1]:,}
- **Utilidad mensual final**: ${df['Utilidad_Neta'].iloc[-1]:,}
- **Efectivo acumulado final**: ${df['Efectivo_Acumulado'].iloc[-1]:,}
- **ROI total**: {df['ROI_Acumulado'].iloc[-1]:.1%}
- **Margen neto final**: {df['Margen_Neto'].iloc[-1]:.1%}

### Punto de Equilibrio
"""
        try:
            break_even_mes = df[df['Utilidad_Neta'] > 0]['Mes'].iloc[0]
            reporte_completo += f"- **Mes de break-even**: {break_even_mes}\n"
            reporte_completo += f"- **Usuarios necesarios**: {df[df['Mes'] == break_even_mes]['Total_Usuarios'].iloc[0]:,}\n"
        except IndexError:
            reporte_completo += "- **Break-even**: No alcanzado en el período\n"
        
        reporte_completo += f"""
### Análisis de Riesgo
- **Meses con pérdidas**: {len(df[df['Utilidad_Neta'] < 0])}
- **Pérdida máxima mensual**: ${abs(df['Utilidad_Neta'].min()):,}
- **Efectivo mínimo**: ${df['Efectivo_Acumulado'].min():,}

### Recomendaciones
"""
        if df['Efectivo_Acumulado'].iloc[-1] > 0 and df['Utilidad_Neta'].iloc[-1] > 0:
            reporte_completo += "✅ **Modelo financiero saludable y sostenible**\n"
        elif df['Utilidad_Neta'].iloc[-1] > 0:
            reporte_completo += "⚠️ **Modelo rentable pero requiere gestión de capital**\n"
        else:
            reporte_completo += "🚨 **Modelo requiere optimización urgente**\n"
        
        st.download_button(
            label="📄 Descargar Reporte MD",
            data=reporte_completo,
            file_name=f"jobmatch_reporte_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            help="Descarga reporte ejecutivo en formato Markdown"
        )
        
        config_json = {
            "parametros": {
                "meses": meses,
                "usuarios_premium_inicio": usuarios_premium_inicio,
                "usuarios_basica_inicio": usuarios_basica_inicio,
                "precio_premium": precio_premium,
                "precio_basica": precio_basica,
                "crecimiento_mensual": crecimiento_mensual,
                "inversion_inicial": inversion_inicial,
                "tasa_impuestos": tasa_impuestos,
                "costo_variable": costo_variable
            },
            "sueldos": sueldos,
            "gracia": gracia,
            "costos_fijos": costos_fijos,
            "fecha_generacion": datetime.now().isoformat()
        }
        st.download_button(
            label="⚙️ Descargar Configuración",
            data=json.dumps(config_json, indent=2, ensure_ascii=False),
            file_name=f"jobmatch_config_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            help="Descarga la configuración actual para reutilizar"
        )