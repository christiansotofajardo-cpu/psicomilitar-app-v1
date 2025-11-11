
# app.py — Psicomilitar v1.2 (Streamlit, flujo simple sin API)
# Modo candidate: captura respuestas, NO muestra resultados.
# Modo admin: bandeja, cálculo TRPMI-20 + Raven, IGIM y PDF.
#
# Variables de entorno:
#   APP_MODE=candidate | admin
#   ADMIN_PASSWORD=tu_clave  (solo en admin)
#   DATA_FILE=submissions.csv (opcional)

import os, io, json
from datetime import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

APP_MODE = os.getenv("APP_MODE", "candidate").lower()  # 'candidate' | 'admin'
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATA_FILE = os.getenv("DATA_FILE", "submissions.csv")

st.set_page_config(page_title="Psicomilitar v1.2", page_icon="🛡️", layout="wide")

# ------- Especificación de test -------
LIKERT_BIN = [{"label": "No", "score": 0}, {"label": "Sí", "score": 1}]

TESTS = {
    "TRPMI-20 (Riesgo Psicológico Militar)": {
        "etiqueta": "TRPMI-20 (Tamizaje clínico)",
        "descripcion": "SRQ‑20 adaptado (20 ítems Sí/No). Corte: 0–6 Apto; 7–10 Apto con observación; ≥11 No apto.",
        "opciones": LIKERT_BIN,
        "items": [
            "¿Se ha sentido nervioso/a o en tensión en los últimos días?",
            "¿Ha sentido preocupación persistente difícil de controlar?",
            "¿Ha notado tristeza, desánimo o pérdida de esperanza?",
            "¿Ha perdido interés o placer en actividades habituales?",
            "¿Ha tenido dificultad para disfrutar o sentir ánimo?",
            "¿Ha tenido problemas para concentrarse en tareas simples?",
            "¿Se le olvidan cosas con mayor frecuencia de lo habitual?",
            "¿Ha presentado irritabilidad que afecta su convivencia?",
            "¿Ha sentido dolores físicos (cabeza/estómago) sin causa clara?",
            "¿Ha tenido molestias corporales relacionadas con el estrés?",
            "¿Dificultad para relajarse o sentirse en calma?",
            "¿Problemas de sueño (insomnio, despertar frecuente)?",
            "¿Ha tenido conductas impulsivas con riesgo operacional?",
            "¿Le cuesta interactuar/coordinarse con su equipo?",
            "¿Ha tenido sensación de inutilidad o culpa excesiva?",
            "¿Pensamientos negativos persistentes sobre sí mismo/a?",
            "¿Sensación de vigilancia/alerta excesiva en todo momento?",
            "¿Miedo a que ocurra algo malo sin motivo concreto?",
            "¿Dificultad para seguir instrucciones bajo presión?",
            "¿Ha pensado que no podría controlar una situación crítica?",
        ],
        "cutoffs": [(0,6,"Apto"), (7,10,"Apto con observación"), (11,20,"No apto")],
    },
}

def calcular_puntaje(respuestas, opciones):
    return sum(opciones[r]["score"] for r in respuestas if r is not None)

def interpretar_cutoffs(total, cutoffs):
    for lo, hi, label in cutoffs:
        if lo <= total <= hi:
            return label
    return "Sin interpretación"

def exportar_pdf(datos_generales, resultado_dict, igim_label=None, filename_prefix="reporte_psicomilitar"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, h-2*cm, "Reporte Psicomilitar – Evaluación")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, h-2.6*cm, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')} hrs")
    y = h - 3.4*cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Datos del evaluado")
    y -= 0.5*cm
    c.setFont("Helvetica", 10)
    for k, v in datos_generales.items():
        c.drawString(2*cm, y, f"{k}: {v}")
        y -= 0.45*cm

    if igim_label:
        y -= 0.2*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2*cm, y, "Índice Global de Idoneidad Militar (IGIM)")
        y -= 0.5*cm
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, y, f"IGIM: {igim_label}")
        y -= 0.6*cm

    y -= 0.2*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Resultados por instrumento")
    y -= 0.5*cm
    c.setFont("Helvetica", 10)
    for test_name, res in resultado_dict.items():
        line = f"• {test_name}: Puntaje {res.get('total','-')} / Nivel: {res.get('nivel','-')}"
        c.drawString(2*cm, y, line)
        y -= 0.45*cm
        if y < 3*cm:
            c.showPage()
            y = h - 2*cm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer, f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

def _ensure_store(file):
    if not os.path.exists(file):
        pd.DataFrame([]).to_csv(file, index=False)

def save_submission(payload: dict):
    _ensure_store(DATA_FILE)
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception:
        df = pd.DataFrame([])
    df = pd.concat([df, pd.DataFrame([payload])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# Sidebar
mode_badge = "CANDIDATO" if APP_MODE == "candidate" else "ADMINISTRADOR"
st.sidebar.markdown(f"### 🛡️ Psicomilitar v1.2  \n**Modo:** {mode_badge}")
if APP_MODE == "candidate":
    st.sidebar.info("Complete sus cuestionarios. Sus resultados serán revisados por el equipo evaluador.")
else:
    st.sidebar.warning("Acceso restringido a personal autorizado.")

# =================== MODO CANDIDATO ===================
if APP_MODE == "candidate":
    st.title("🧾 Evaluación Psicomilitar – Candidato")
    st.caption("Sus respuestas serán tratadas de forma confidencial y revisadas por profesionales autorizados.")

    with st.expander("Identificación (requerido)", expanded=True):
        colA, colB, colC, colD = st.columns([1.2,1.2,1.2,1])
        with colA:
            nombre = st.text_input("Nombre completo")
        with colB:
            rut = st.text_input("RUT / ID")
        with colC:
            unidad = st.text_input("Unidad/Regimiento")
        with colD:
            edad = st.number_input("Edad", min_value=16, max_value=80, value=25)

    st.subheader("TRPMI-20 – Responda Sí/No")
    spec = TESTS["TRPMI-20 (Riesgo Psicológico Militar)"]
    trp_resps = []
    for i, texto in enumerate(spec["items"], start=1):
        idx = st.radio(
            f"{i}. {texto}",
            options=[0,1],
            format_func=lambda x: spec["opciones"][x]["label"],
            key=f"TRPMI_{i}",
            horizontal=True,
        )
        trp_resps.append(idx)

    st.subheader("Raven – Captura de datos (sin mostrar clasificación)")
    colr1, colr2, colr3 = st.columns([1,1,1])
    with colr1:
        raven_version = st.selectbox("Versión", ["SPM‑R", "APM‑R"], key="RAVEN_ver")
    with colr2:
        total_items = st.number_input("Nº ítems (36–60)", min_value=10, max_value=60, value=36, step=1, key="RAVEN_n")
    with colr3:
        raw_correct = st.number_input("Aciertos (raw)", min_value=0, max_value=60, value=0, step=1, key="RAVEN_raw")
    pct_known = st.checkbox("Tengo percentil oficial (entregado por el evaluador)")
    pct_value = st.number_input("Percentil (0–99)", min_value=0, max_value=99, value=50, step=1, disabled=not pct_known)

    if st.button("Enviar evaluación"):
        if not (nombre and rut):
            st.warning("Completa Nombre y RUT/ID antes de enviar.")
        else:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "nombre": nombre,
                "rut": rut,
                "unidad": unidad,
                "edad": edad,
                "TRPMI20_answers": trp_resps,
                "Raven_version": raven_version,
                "Raven_items": int(total_items),
                "Raven_raw": int(raw_correct),
                "Raven_pct": int(pct_value) if pct_known else None,
            }
            save_submission(payload)
            st.success("Gracias, su evaluación ha sido enviada. Un profesional revisará sus resultados.")
            st.stop()

# =================== MODO ADMIN ===================
if APP_MODE == "admin":
    st.title("🛡️ Consola Psicomilitar – Administrador")

    with st.sidebar:
        st.subheader("Acceso")
        pwd = st.text_input("Contraseña", type="password")
        logged = st.button("Ingresar")
    if not (logged and pwd == ADMIN_PASSWORD):
        st.info("Ingrese su contraseña para acceder a la bandeja de casos.")
        st.stop()

    st.subheader("Bandeja de evaluaciones recibidas")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception:
        df = pd.DataFrame([])
    if df.empty:
        st.warning("Sin evaluaciones aún.")
        st.stop()

    colf1, colf2 = st.columns([1,1])
    with colf1:
        f_unidad = st.text_input("Filtrar por Unidad/Regimiento")
    with colf2:
        f_rut = st.text_input("Filtrar por RUT/ID")

    view = df.copy()
    if f_unidad:
        view = view[view["unidad"].astype(str).str.contains(f_unidad, case=False, na=False)]
    if f_rut:
        view = view[view["rut"].astype(str).str.contains(f_rut, case=False, na=False)]

    st.dataframe(view.fillna(""))

    st.markdown("---")
    st.subheader("Ficha de caso")
    sel_idx = st.number_input("Índice de fila (0..N)", min_value=0, max_value=max(0, len(view)-1), value=0, step=1)

    if len(view) > 0:
        row = view.iloc[int(sel_idx)]
        colA, colB, colC, colD = st.columns([1.2,1.2,1.2,1])
        with colA:
            st.text_input("Nombre", value=str(row.get("nombre","")), disabled=True)
        with colB:
            st.text_input("RUT/ID", value=str(row.get("rut","")), disabled=True)
        with colC:
            st.text_input("Unidad", value=str(row.get("unidad","")), disabled=True)
        with colD:
            st.number_input("Edad", value=int(row.get("edad",0) or 0), disabled=True)

        # TRPMI
        spec = TESTS["TRPMI-20 (Riesgo Psicológico Militar)"]
        # leer lista desde CSV (string) de forma robusta
        trp_answers = []
        raw = str(row.get("TRPMI20_answers", "[]"))
        try:
            trp_answers = [int(x) for x in json.loads(raw.replace("'", "\""))]
        except Exception:
            try:
                trp_answers = [int(x) for x in eval(raw)]
            except Exception:
                trp_answers = []
        trp_total = calcular_puntaje(trp_answers, spec["opciones"]) if trp_answers else 0
        trp_nivel = interpretar_cutoffs(trp_total, spec["cutoffs"]) if trp_answers else "N/A"

        # Raven
        raven_version = row.get("Raven_version", "SPM‑R")
        raven_items = int(row.get("Raven_items", 36) or 36)
        raven_raw = int(row.get("Raven_raw", 0) or 0)
        pct_from_store = row.get("Raven_pct", None)
        try:
            pct_from_store = int(pct_from_store)
        except Exception:
            pct_from_store = None

        st.markdown("#### Raven – Puntuación y clasificación")
        colr1, colr2, colr3 = st.columns([1,1,1])
        with colr1:
            st.text_input("Versión", value=str(raven_version), disabled=True)
        with colr2:
            st.number_input("Nº ítems", value=int(raven_items), disabled=True)
        with colr3:
            st.number_input("Aciertos", value=int(raven_raw), disabled=True)

        use_official = st.checkbox("Ingresar/usar percentil oficial", value=pct_from_store is not None)
        if use_official:
            pct = st.number_input("Percentil (0–99)", min_value=0, max_value=99, value=int(pct_from_store or 50))
        else:
            pct = int(round((raven_raw / max(raven_items,1)) * 100))
            st.caption(f"Estimación preliminar de percentil ≈ {pct}")

        if pct >= 90:
            raven_label = "Superior"
        elif 75 <= pct <= 89:
            raven_label = "Promedio Alto"
        elif 25 <= pct <= 74:
            raven_label = "Promedio"
        elif 10 <= pct <= 24:
            raven_label = "Promedio Bajo"
        else:
            raven_label = "Inferior"

        st.success(f"**Clasificación Raven:** {raven_label} (pctl {pct}) • Aciertos {raven_raw}/{raven_items} – {raven_version}")

        # IGIM simple
        igim = "N/A"
        if trp_nivel != "N/A":
            if trp_nivel == "No apto":
                igim = "No apto"
            elif trp_nivel == "Apto con observación":
                igim = "Apto con observación" if raven_label in ["Promedio", "Promedio Alto", "Superior"] else "Derivar/Observar"
            else:  # Apto
                igim = "Apto" if raven_label in ["Promedio Bajo", "Promedio", "Promedio Alto", "Superior"] else "Apto con observación"

        st.markdown("#### Síntesis clínica-cognitiva (IGIM v1)")
        st.info(f"TRPMI-20: {trp_total} → {trp_nivel}  |  Raven: {raven_label} (pctl {pct})  |  **IGIM**: {igim}")

        resultados = {
            "TRPMI-20 (Riesgo Psicológico Militar)": {"total": trp_total, "nivel": trp_nivel},
            "Raven (SPM‑R/APM‑R) — Puntuación": {"total": raven_raw, "nivel": raven_label, "percentil": pct, "version": raven_version},
        }

        st.markdown("---")
        st.subheader("Exportar reporte PDF (solo admin)")
        if st.button("Generar PDF oficial"):
            datos = {"Nombre": row.get("nombre",""), "RUT/ID": row.get("rut",""), "Unidad": row.get("unidad",""), "Edad": row.get("edad","")}
            pdf_buffer, fname = exportar_pdf(datos, resultados, igim_label=igim)
            st.download_button("Descargar PDF", data=pdf_buffer, file_name=fname, mime="application/pdf")

st.caption("© Psicomilitar v1.2 – Núcleo modular; resultados solo visibles en consola admin. Cumplimiento: sin reproducción de ítems Raven; se captura aciertos/percentil.")
