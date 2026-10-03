import streamlit as st
import pdfplumber
import pandas as pd
import io

# ---------------------------
# CONFIGURACIÓN DE LA APP
# ---------------------------
st.set_page_config(
    page_title="Reporte de Stock - Papelera Entre Ríos",
    page_icon="📄",
    layout="wide"
)

# Logo / encabezado
st.markdown(
    """
    <style>
    .main {
        background-color: #f5f5f5;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📄 Procesador de Reportes de Stock (PDF → Excel)")
st.subheader("Papelera Entre Ríos S.A. - Reporte de Stock de Producto Elaborado - Stock Puro")
st.write("Subí el PDF del ERP y genera automáticamente el Excel estructurado, KPIs y gráficos.")

uploaded_file = st.file_uploader("Subir PDF del ERP", type=["pdf"])

# ---------------------------
# FUNCIÓN PRINCIPAL DE PROCESO
# ---------------------------
def procesar_pdf(file):
    detalle = []
    totales_corte = []
    totales_calidad = []

    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() or ""

        # Validación básica: verificar que sea un reporte de stock
        if "Reporte de Stock de Producto Elaborado - Stock Puro" not in texto_completo:
            st.warning("El PDF no parece ser un reporte de stock esperado. Revisá que sea el archivo correcto.")
        
        for page in pdf.pages:
            tablas = page.extract_tables()

            for tabla in tablas:
                for fila in tabla:
                    if len(fila) < 10:
                        fila += [""] * (10 - len(fila))

                    lote, alist, calidad, observ, kilos, unid, gram, corte, diam, obs2 = fila

                    # Subtotales por corte
                    if lote and "Total por Corte" in lote:
                        totales_corte.append({
                            "Corte": corte,
                            "Kilos": pd.to_numeric(kilos, errors="coerce"),
                            "Unid": pd.to_numeric(unid, errors="coerce")
                        })
                        continue

                    # Totales por calidad
                    if lote and "Total por Calidad" in lote:
                        totales_calidad.append({
                            "Kilos": pd.to_numeric(kilos, errors="coerce"),
                            "Unid": pd.to_numeric(unid, errors="coerce")
                        })
                        continue

                    # Encabezados / filas vacías
                    if lote in ["Lote Fecha", "Lote", None, ""]:
                        continue

                    detalle.append({
                        "Lote Fecha": lote,
                        "Alist": alist,
                        "Produc Calidad": calidad,
                        "Observ": observ,
                        "Kilos": pd.to_numeric(kilos, errors="coerce"),
                        "Unid": pd.to_numeric(unid, errors="coerce"),
                        "Gram": pd.to_numeric(gram, errors="coerce"),
                        "Corte": pd.to_numeric(corte, errors="coerce"),
                        "Diam": pd.to_numeric(diam, errors="coerce"),
                        "Observacione": obs2
                    })

    df_detalle = pd.DataFrame(detalle)
    df_totales_corte = pd.DataFrame(totales_corte)
    df_totales_calidad = pd.DataFrame(totales_calidad)

    return df_detalle, df_totales_corte, df_totales_calidad

# ---------------------------
# INTERFAZ PRINCIPAL
# ---------------------------
if uploaded_file:
    st.success("PDF cargado correctamente. Procesando datos...")

    df_detalle, df_totales_corte, df_totales_calidad = procesar_pdf(uploaded_file)

    if df_detalle.empty:
        st.error("No se encontraron datos de detalle en el PDF.")
    else:
        st.success("Datos procesados correctamente.")

        # ---------------------------
        # KPIs
        # ---------------------------
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Kilos", f"{df_detalle['Kilos'].sum():,.0f}")
        with col2:
            st.metric("Total Unidades", f"{df_detalle['Unid'].sum():,.0f}")
        with col3:
            st.metric("Cantidad de Lotes", f"{df_detalle['Lote Fecha'].nunique():,.0f}")
        with col4:
            st.metric("Gramajes distintos", f"{df_detalle['Gram'].nunique():,.0f}")

        st.markdown("---")

        # ---------------------------
        # FILTROS
        # ---------------------------
        st.subheader("Filtros")

        gramajes = sorted(df_detalle["Gram"].dropna().unique())
        cortes = sorted(df_detalle["Corte"].dropna().unique())
        calidades = sorted(df_detalle["Produc Calidad"].dropna().unique())

        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            gramaje_sel = st.multiselect("Gramaje (Gram)", gramajes, default=gramajes)
        with col_f2:
            corte_sel = st.multiselect("Corte", cortes, default=cortes)
        with col_f3:
            calidad_sel = st.multiselect("Calidad", calidades, default=calidades)

        df_filtrado = df_detalle[
            df_detalle["Gram"].isin(gramaje_sel) &
            df_detalle["Corte"].isin(corte_sel) &
            df_detalle["Produc Calidad"].isin(calidad_sel)
        ]

        st.subheader("Detalle filtrado")
        st.dataframe(df_filtrado, use_container_width=True)

        st.markdown("---")

        # ---------------------------
        # GRÁFICOS
        # ---------------------------
        st.subheader("Gráficos")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.write("Kilos por Gramaje")
            graf_gram = df_filtrado.groupby("Gram")["Kilos"].sum().reset_index()
            st.bar_chart(graf_gram.set_index("Gram"))

        with col_g2:
            st.write("Kilos por Corte")
            graf_corte = df_filtrado.groupby("Corte")["Kilos"].sum().reset_index()
            st.bar_chart(graf_corte.set_index("Corte"))

        st.markdown("---")

        # ---------------------------
        # DESCARGAS (EXCEL / CSV)
        # ---------------------------
        st.subheader("Descargas")

        # Excel
        output_excel = io.BytesIO()
        writer = pd.ExcelWriter(output_excel, engine="openpyxl")

        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)
        df_totales_corte.to_excel(writer, sheet_name="Totales por Corte", index=False)
        df_totales_calidad.to_excel(writer, sheet_name="Totales por Calidad", index=False)

        writer.save()
        output_excel.seek(0)

        st.download_button(
            label="📥 Descargar Excel completo",
            data=output_excel,
            file_name="reporte_stock.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # CSV
        csv_data = df_detalle.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar CSV (Detalle)",
            data=csv_data,
            file_name="reporte_stock_detalle.csv",
            mime="text/csv"
        )
else:
    st.info("Subí un PDF para comenzar el procesamiento.")
