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
    if re.match(r"^\d{2}/\d{2}/\d{4}$", fecha):
        return lote, fecha
    return lote, None


def parsear_stock_puro(lineas):
    registros = []
    patron_fecha = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")

    for linea in lineas:
        partes = linea.split()
        if len(partes) < 6:
            continue

        fechas = [p for p in partes if patron_fecha.match(p)]
        if not fechas:
            continue

        fecha = fechas[0]
        idx_fecha = partes.index(fecha)

        lote, fecha_real = dividir_lote_fecha(f"{partes[0]} {fecha}")
        alist = partes[1]
        produc_calidad = " ".join(partes[2:idx_fecha])

        resto = partes[idx_fecha + 1:]
        if len(resto) < 6:
            continue

        observ = resto[0]

        try:
            kilos = float(resto[1].replace(".", "").replace(",", "."))
        except:
            kilos = None

        try:
            unid = int(resto[2])
        except:
            unid = None

        gram = resto[3]
        corte = resto[4]
        diam = resto[5]

        registros.append({
            "Tipo reporte": "Stock Puro",
            "Lote": lote,
            "Fecha": fecha_real,
            "Alist": alist,
            "Producto + Calidad": produc_calidad,
            "Observación": observ,
            "Kilos": kilos,
            "Unidades": unid,
            "Gramaje": gram,
            "Corte": corte,
            "Diámetro": diam,
        })

    return pd.DataFrame(registros)


# ---------------------------------------------------------
# PARSER STOCK DESTINADO
# ---------------------------------------------------------

def parsear_stock_destinado(lineas):
    registros = []
    patron_fecha = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")

    cliente_actual = None

    for linea in lineas:

        if "CLIENTE" in linea.upper():
            cliente_actual = linea.strip()
            continue

        partes = linea.split()
        if len(partes) < 8:
            continue

        fechas = [p for p in partes if patron_fecha.match(p)]
        if not fechas:
            continue

        fecha = fechas[0]
        idx_fecha = partes.index(fecha)

        lote = partes[0]
        alist = partes[2] if idx_fecha >= 3 else ""
        produc = " ".join(partes[3:idx_fecha])

        resto = partes[idx_fecha + 1:]
        if len(resto) < 8:
            continue

        calidad = resto[0]
        observ = resto[1]

        try:
            unid = int(resto[2])
        except:
            unid = None

        try:
            kilos = float(resto[3].replace(".", "").replace(",", "."))
        except:
            kilos = None

        gram = resto[4]
        corte = resto[5]
        diam = resto[6]
        precio = resto[7] if len(resto) > 7 else ""
        pedido = resto[8] if len(resto) > 8 else ""

        registros.append({
            "Tipo reporte": "Destinado a Clientes",
            "Cliente": cliente_actual,
            "Lote / O.Fabr": lote,
            "Fecha": fecha,
            "Alist": alist,
            "Producto": produc,
            "Calidad": calidad,
            "Observación": observ,
            "Unidades": unid,
            "Kilos": kilos,
            "Gramaje": gram,
            "Corte": corte,
            "Diámetro": diam,
            "Precio": precio,
            "Pedido": pedido,
        })

    return pd.DataFrame(registros)


# ---------------------------------------------------------
# STREAMLIT APP
# ---------------------------------------------------------

def main():
    st.title("📦 Procesador de Reportes de Stock")
    st.subheader