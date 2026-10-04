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
    st.subheader("Papelería Entre Ríos S.A.")

    tipo_seleccion = st.radio(
        "Seleccioná el tipo de reporte:",
        ("Detectar automáticamente", "Stock Puro", "Destinado a Clientes")
    )

    archivo_pdf = st.file_uploader("Subí el PDF del ERP", type=["pdf"])

    if archivo_pdf is not None:
        st.success("PDF cargado correctamente. Procesando...")

        file_bytes = archivo_pdf.read()
        lineas = extraer_lineas_pdf(file_bytes)

        tipo_detectado = detectar_tipo_reporte(lineas)

        if tipo_seleccion == "Stock Puro":
            tipo = "puro"
        elif tipo_seleccion == "Destinado a Clientes":
            tipo = "destinado"
        else:
            tipo = tipo_detectado

        if tipo == "puro":
            df = parsear_stock_puro(lineas)
        elif tipo == "destinado":
            df = parsear_stock_destinado(lineas)
        else:
            st.error("No se pudo detectar el tipo de reporte.")
            return

        if df.empty:
            st.warning("No se pudieron extraer registros del PDF.")
            return

        st.success("Datos procesados correctamente.")

        # ---------------------------------------------------------
        # KPIs
        # ---------------------------------------------------------

        st.header("📊 KPIs del reporte")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Kilos", f"{df['Kilos'].sum():,.0f}")
        col2.metric("Total Unidades", f"{df['Unidades'].sum():,.0f}")

        if tipo == "puro":
            col3.metric("Lotes distintos", df["Lote"].nunique())
            col4.metric("Gramajes distintos", df["Gramaje"].nunique())
        else:
            col3.metric("Clientes distintos", df["Cliente"].nunique())
            col4.metric("Productos distintos", df["Producto"].nunique())

        # ---------------------------------------------------------
        # FILTROS
        # ---------------------------------------------------------

        st.header("🔎 Filtros")

        if tipo == "puro":
            gramajes = sorted(df["Gramaje"].dropna().unique())
            cortes = sorted(df["Corte"].dropna().unique())

            g_sel = st.multiselect("Gramaje", gramajes, default=gramajes)
            c_sel = st.multiselect("Corte", cortes, default=cortes)

            df_filtrado = df[df["Gramaje"].isin(g_sel) & df["Corte"].isin(c_sel)]

        else:
            clientes = sorted(df["Cliente"].dropna().unique())
            productos = sorted(df["Producto"].dropna().unique())

            cli_sel = st.multiselect("Cliente", clientes, default=clientes)
            prod_sel = st.multiselect("Producto", productos, default=productos)

            df_filtrado = df[df["Cliente"].isin(cli_sel) & df["Producto"].isin(prod_sel)]

        st.dataframe(df_filtrado, use_container_width=True)

        # ---------------------------------------------------------
        # GRÁFICOS
        # ---------------------------------------------------------

        st.header("📈 Gráficos")

        if tipo == "puro":
            fig1 = px.bar(df_filtrado.groupby("Gramaje")["Kilos"].sum().reset_index(),
                          x="Gramaje", y="Kilos", title="Kilos por Gramaje")
            fig2 = px.bar(df_filtrado.groupby("Corte")["Kilos"].sum().reset_index(),
                          x="Corte", y="Kilos", title="Kilos por Corte")
        else:
            fig1 = px.bar(df_filtrado.groupby("Cliente")["Kilos"].sum().reset_index(),
                          x="Cliente", y="Kilos", title="Kilos por Cliente")
            fig2 = px.bar(df_filtrado.groupby("Producto")["Kilos"].sum().reset_index(),
                          x="Producto", y="Kilos", title="Kilos por Producto")

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

        # ---------------------------------------------------------
        # EXPORTACIÓN
        # ---------------------------------------------------------

        st.header("📥 Exportación")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Stock Completo")
            df_filtrado.to_excel(writer, index=False, sheet_name="Filtrado")

            if tipo == "destinado":
                df.groupby("Cliente").sum(numeric_only=True).to_excel(writer, sheet_name="Resumen por Cliente")
                df.groupby("Producto").sum(numeric_only=True).to_excel(writer, sheet_name="Resumen por Producto")

        buffer.seek(0)

        st.download_button(
            label="Descargar Excel completo",
            data=buffer,
            file_name="reporte_stock.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
