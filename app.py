import io
import re
import pdfplumber
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------------------------------------------------------
# CONFIGURACIÓN VISUAL (TEMA CLARO FORZADO)
# ---------------------------------------------------------

st.set_page_config(
    page_title="Procesador de Stock — Papelera Entre Ríos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Forzar tema claro en Streamlit Cloud
st.markdown("""
<style>
:root {
    color-scheme: light;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------

def extraer_lineas_pdf(file_bytes):
    lineas = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            for linea in texto.split("\n"):
                linea = linea.strip()
                if linea:
                    lineas.append(linea)
    return lineas


def detectar_tipo_reporte(lineas):
    texto = " ".join(lineas).upper()
    if "STOCK PURO" in texto:
        return "puro"
    if "DESTINADO A CLIENTES" in texto:
        return "destinado"
    return "desconocido"


# ---------------------------------------------------------
# PARSER STOCK PURO
# ---------------------------------------------------------

def dividir_lote_fecha(valor):
    partes = valor.split(" ", 1)
    if len(partes) == 1:
        return partes[0], None
    lote, fecha = partes
    if re.match(r"^\d{2}/\d{2}/\d{4}$",
