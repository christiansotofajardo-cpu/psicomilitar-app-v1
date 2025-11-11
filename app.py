# -*- coding: utf-8 -*-
import io
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

APP_TITLE = "PsicoMilitar – Cuestionario Breve"
PROJECT_CODE = "psicomilitar-app-v1"

LIKERT = {
    "1 = En total desacuerdo": 1,
    "2 = En desacuerdo": 2,
    "3 = Ni de acuerdo ni en desacuerdo": 3,
    "4 = De acuerdo": 4,
    "5 = Totalmente de acuerdo": 5,
}

ITEMS = [
    "He notado que la persona maneja mejor sus emociones.",
    "Se relaciona de manera más respetuosa y pacífica con su entorno.",
    "Muestra mayor autonomía y confianza para asumir responsabilidades.",
    "Aplica en su vida algunas estrategias aprendidas.",
    "La participación en el proceso ha sido beneficiosa para su desarrollo.",
]

def _init_state():
    if "responses" not in st.session_state:
        st.session_state.responses = pd.DataFrame(
            columns=[
                "timestamp", "id_sujeto", *[f"item_{i+1}" for i in range(len(ITEMS))],
                "comentarios", "consentimiento", "proyecto"
            ]
        )

def save_response(row: Dict[str, Any]):
    st.session_state.responses = pd.concat(
        [st.session_state.responses, pd.DataFrame([row])],
        ignore_index=True
    )

def download_bytes_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue().encode("utf-8")

def resumen_tabla(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = [c for c in df.columns if c.startswith("item_")]
    desc = df[cols].describe().T
    desc = desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    desc.index.name = "ítem"
    return desc.round(2)

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="✅", layout="centered")
    _init_state()

    st.title(APP_TITLE)
    st.caption("App simple de captura y síntesis de respuestas. Construida con Streamlit.")

    with st.sidebar:
        st.markdown("### Navegación")
        view = st.radio(
            "Secciones",
            ["Aplicar cuestionario", "Cargar/descargar datos", "Resumen"],
            index=0
        )
        st.divider()
        st.markdown("**Proyecto:**")
        st.code(PROJECT_CODE, language="markdown")

    if view == "Aplicar cuestionario":
        st.header("Aplicar cuestionario (Likert 1–5)")
        with st.form("form_respuestas", clear_on_submit=False):
            id_sujeto = st.text_input("ID sujeto / código interno", max_chars=64)

            valores: List[int] = []
            for i, item in enumerate(ITEMS, start=1):
                sel = st.select_slider(
                    f"{i}. {item}",
                    options=list(LIKERT.keys()),
                    value="3 = Ni de acuerdo ni en desacuerdo",
                    help="Arrastra para elegir el grado de acuerdo."
                )
                valores.append(LIKERT[sel])

            comentarios = st.text_area("Comentarios (opcional)", max_chars=1500)
            consentimiento = st.checkbox(
                "Declaro consentimiento informado para registrar y analizar estas respuestas.",
                value=False
            )

            submit = st.form_submit_button("Guardar respuesta")

        if submit:
            if not id_sujeto.strip():
                st.error("Por favor, ingresa un **ID de sujeto**.")
            elif not consentimiento:
                st.error("Debes marcar el **consentimiento** para guardar.")
            else:
                row = {
                    "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "id_sujeto": id_sujeto.strip(),
                    **{f"item_{i+1}": v for i, v in enumerate(valores)},
                    "comentarios": comentarios.strip(),
                    "consentimiento": bool(consentimiento),
                    "proyecto": PROJECT_CODE,
                }
                save_response(row)
                st.success("✅ Respuesta guardada correctamente.")
                st.toast("Guardado", icon="✅")

        st.divider()
        if not st.session_state.responses.empty:
            st.subheader("Últimas respuestas (vista rápida)")
            st.dataframe(st.session_state.responses.tail(10), use_container_width=True, height=280)

    elif view == "Cargar/descargar datos":
        st.header("Cargar/descargar datos")

        st.subheader("Descargar CSV")
        if st.session_state.responses.empty:
            st.info("Aún no hay respuestas para descargar.")
        else:
            st.download_button(
                "⬇️ Descargar respuestas (CSV)",
                data=download_bytes_csv(st.session_state.responses),
                mime="text/csv",
                file_name=f"{PROJECT_CODE}_respuestas.csv",
            )

        st.divider()
        st.subheader("Cargar CSV y fusionar")
        st.caption("Debes subir un CSV con el mismo esquema de columnas.")
        up = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
        if up is not None:
            try:
                df_new = pd.read_csv(up)
                required_cols = set(st.session_state.responses.columns)
                if not required_cols.issubset(set(df_new.columns)):
                    st.error("El CSV no tiene el mismo esquema de columnas que la app.")
                else:
                    before = len(st.session_state.responses)
                    st.session_state.responses = pd.concat(
                        [st.session_state.responses, df_new[st.session_state.responses.columns]],
                        ignore_index=True
                    ).drop_duplicates().reset_index(drop=True)
                    after = len(st.session_state.responses)
                    st.success(f"✅ Carga exitosa. Filas agregadas: {after - before}.")
            except Exception as e:
                st.exception(e)

        st.divider()
        st.subheader("Vista de datos completa")
        st.dataframe(st.session_state.responses, use_container_width=True, height=360)

    else:  # Resumen
        st.header("Resumen de resultados")
        df = st.session_state.responses.copy()

        if df.empty:
            st.info("Aún no hay datos para resumir.")
            return

        # Puntaje total simple por sujeto (promedio de ítems)
        item_cols = [c for c in df.columns if c.startswith("item_")]
        df["puntaje_promedio"] = df[item_cols].mean(axis=1)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Respuestas totales", len(df))
            st.metric("Promedio global (1–5)", round(df["puntaje_promedio"].mean(), 2))
        with c2:
            st.metric("Desv. estándar global", round(df["puntaje_promedio"].std(ddof=0), 2))
            st.metric("Ítems por respuesta", len(item_cols))

        st.subheader("Estadísticos por ítem")
        tabla = resumen_tabla(df)
        st.dataframe(tabla, use_container_width=True, height=320)

        st.subheader("Distribución de puntaje promedio")
        st.caption("Histograma simple (bin = 0.5)")
        st.bar_chart(
            df["puntaje_promedio"]
            .round(1)
            .value_counts()
            .sort_index()
        )

        st.divider()
        st.subheader("Muestra de comentarios")
        muestra = df[df["comentarios"].notna() & (df["comentarios"].str.strip() != "")]
        if muestra.empty:
            st.write("No hay comentarios registrados.")
        else:
            for _, r in muestra.tail(8).iterrows():
                st.markdown(
                    f"**{r['id_sujeto']}** — *{r['timestamp']}*  \n"
                    f"{r['comentarios']}"
                )

if __name__ == "__main__":
    main()
