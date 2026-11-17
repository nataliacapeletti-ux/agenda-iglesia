#Python
import streamlit as st
import pandas as pd
from datetime import date, time, timedelta
from streamlit_calendar import calendar
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y CONEXIÓN GOOGLE SHEETS
# ---------------------------------------------------------
st.set_page_config(page_title="Agenda Iglesia", page_icon="📅", layout="wide")

COLORES_MINISTERIO = {
    "Culto General": "#2563EB",   # Azul
    "Pre-adolescentes": "#4F46E5",# Índigo
    "Club Bíblico": "#0D9488",    # Verde turquesa
    "Jóvenes": "#16A34A",         # Verde
    "Varones": "#0284C7",         # Celeste
    "Mujeres": "#EC4899",         # Rosa
    "Matrimonios": "#9333EA",     # Violeta
    "Alabanza": "#C084FC",        # Lila claro
    "Misiones": "#D97706",        # Naranja
    "Líderes": "#B45309",         # Marrón / Ámbar
    "Niños": "#F43F5E",           # Coral / Rojo claro
    "Mantenimiento": "#4B5563",   # Gris
    "Especial": "#DC2626"         # Rojo
}

LISTA_SALONES = ["Salón Arriba", "Salón Abajo", "Patio", "Fuera de la iglesia"]

def conectar_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Limpieza automática por si quedaron barras invertidas o saltos raros
    pk = creds_dict["private_key"]
    pk = pk.replace("\\n", "\n")
    creds_dict["private_key"] = pk
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Agenda_Iglesia_DB").sheet1
    return sheet

def obtener_datos_db():
    sheet = conectar_sheets()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Si la planilla está vacía, aseguramos las columnas mínimas
    columnas_esperadas = ["id", "titulo", "ministerio", "salon", "fecha", "fecha_fin", "hora", "hora_fin", "encargado", "notas"]
    if df.empty:
        return pd.DataFrame(columns=columnas_esperadas)
    
    for col in columnas_esperadas:
        if col not in df.columns:
            df[col] = ""
            
    # Asegurar que el id sea numérico si existe
    if not df.empty and "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        
    return df.sort_values(by=["fecha", "hora"], ascending=[True, True])

# ---------------------------------------------------------
# 2. GESTIÓN DE ESTADOS Y PERMISOS
# ---------------------------------------------------------
if "fecha_seleccionada" not in st.session_state:
    st.session_state["fecha_seleccionada"] = date.today()

if "id_evento_ver" not in st.session_state:
    st.session_state["id_evento_ver"] = None

if "id_evento_editar" not in st.session_state:
    st.session_state["id_evento_editar"] = None

if "modo_crear_arriba" not in st.session_state:
    st.session_state["modo_crear_arriba"] = False

st.sidebar.title("⚙️ Opciones")
modo_usuario = st.sidebar.radio("Modo de Vista", ["Administrador (Gestión total)", "Solo Lectura (Consultas)"], index=0)
es_admin = (modo_usuario == "Administrador (Gestión total)")

def subir_scroll():
    components.html("""
        <script>
            window.parent.window.scrollTo({top: 0, behavior: 'smooth'});
        </script>
    """, height=0)

# ---------------------------------------------------------
# 3. PANTALLA PRINCIPAL Y CALENDARIO
# ---------------------------------------------------------
st.title("📅 Agenda Compartida de la Iglesia")

if not es_admin:
    st.info("👁️ **Modo Solo Lectura**: Estás visualizando la agenda de la iglesia.")

df_eventos = obtener_datos_db()

# ---------------------------------------------------------
# PANELES SUPERIORES (DETALLE, EDICIÓN O CREACIÓN)
# ---------------------------------------------------------

# A. VISTA DE DETALLE
if st.session_state.get("id_evento_ver") and not st.session_state.get("id_evento_editar"):
    subir_scroll()
    ev_id_ver = st.session_state["id_evento_ver"]
    evento_actual = df_eventos[df_eventos["id"] == ev_id_ver]
    
    if not evento_actual.empty:
        fila_v = evento_actual.iloc[0]
        with st.container(border=True):
            st.markdown(f"### 📋 Detalle del Evento: **{fila_v['titulo']}**")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.write(f"🏷️ **Ministerio:** {fila_v['ministerio']}")
                st.write(f"📍 **Salón / Lugar:** {fila_v['salon']}")
                fechas_txt = f"{fila_v['fecha']}" if fila_v['fecha'] == fila_v['fecha_fin'] else f"{fila_v['fecha']} al {fila_v['fecha_fin']}"
                st.write(f"📆 **Fecha:** {fechas_txt}")
            with col_d2:
                h_fin_txt = f" a {fila_v['hora_fin']} hs" if pd.notna(fila_v['hora_fin']) and str(fila_v['hora_fin']).strip() != "" else ""
                st.write(f"⏰ **Horario:** {fila_v['hora']}{h_fin_txt}")
                st.write(f"👤 **Encargado:** {fila_v['encargado']}")
            
            if pd.notna(fila_v['notas']) and str(fila_v['notas']).strip() != "":
                st.info(f"📝 **Notas operativas:** {fila_v['notas']}")
            
            col_ba1, col_ba2, _ = st.columns([1, 1, 2])
            with col_ba1:
                if es_admin:
                    if st.button("✏️ Editar este evento"):
                        st.session_state["id_evento_editar"] = ev_id_ver
                        st.session_state["id_evento_ver"] = None
                        st.rerun()
            with col_ba2:
                if st.button("❌ Cerrar Detalle"):
                    st.session_state["id_evento_ver"] = None
                    st.rerun()

# B. VISTA DE CREACIÓN
elif st.session_state.get("modo_crear_arriba") and es_admin:
    subir_scroll()
    with st.container(border=True):
        st.markdown(f"### ➕ Agendar Nuevo Evento (Fecha seleccionada: {st.session_state['fecha_seleccionada']})")
        
        with st.form(key="form_crear_superior"):
            titulo_c = st.text_input("Título del evento *", placeholder="Ej: Culto Especial")
            min_c = st.selectbox("Ministerio / Área", list(COLORES_MINISTERIO.keys()))
            salon_c = st.selectbox("Salón / Lugar", LISTA_SALONES)
            
            col_fc1, col_fc2 = st.columns(2)
            with col_fc1:
                f_ini_c = st.date_input("Fecha Desde *", value=st.session_state["fecha_seleccionada"])
            with col_fc2:
                f_fin_c = st.date_input("Fecha Hasta *", value=f_ini_c)
                
            col_hc1, col_hc2 = st.columns(2)
            with col_hc1:
                h_ini_c = st.time_input("Hora Inicio *", value=time(19, 30))
            with col_hc2:
                h_fin_c = st.time_input("Hora Fin *", value=time(21, 30))
                
            enc_c = st.text_input("Encargado responsable *", placeholder="Ej: Carlos Gómez")
            notas_c = st.text_area("Notas operativas (Sonido, llaves, comida...)")
            
            col_bc1, col_bc2 = st.columns(2)
            with col_bc1:
                guardar_nuevo = st.form_submit_button("💾 Guardar Evento")
            with col_bc2:
                cancelar_nuevo = st.form_submit_button("❌ Cerrar Panel")

            if guardar_nuevo:
                if titulo_c.strip() and enc_c.strip():
                    if f_fin_c < f_ini_c:
                        st.error("⚠️ La fecha de fin no puede ser anterior a la de inicio.")
                    else:
                        sheet = conectar_sheets()
                        # Generar ID único basado en milisegundos o autoincremental seguro
                        df_actual = obtener_datos_db()
                        nuevo_id = int(df_eventos["id"].max() + 1) if not df_eventos.empty and df_eventos["id"].max() > 0 else 1
                        
                        nuevo_registro = [
                            nuevo_id,
                            titulo_c,
                            min_c,
                            salon_c,
                            str(f_ini_c),
                            str(f_fin_c),
                            h_ini_c.strftime("%H:%M"),
                            h_fin_c.strftime("%H:%M"),
                            enc_c,
                            notas_c
                        ]
                        sheet.append_row(nuevo_registro)
                        st.session_state["modo_crear_arriba"] = False
                        st.success("¡Evento agendado con éxito en Google Sheets!")
                        st.rerun()
                else:
                    st.error("⚠️ Completá al menos el Título y el Encargado.")

            if cancelar_nuevo:
                st.session_state["modo_crear_arriba"] = False
                st.rerun()

# C. VISTA DE EDICIÓN
elif st.session_state.get("id_evento_editar") and es_admin:
    subir_scroll()
    ev_id_act = st.session_state["id_evento_editar"]
    evento_actual = df_eventos[df_eventos["id"] == ev_id_act]
    
    if not evento_actual.empty:
        fila_ed = evento_actual.iloc[0]
        
        t_ini_val = time(19, 30)
        if pd.notna(fila_ed["hora"]) and ":" in str(fila_ed["hora"]):
            partes_h = str(fila_ed["hora"]).split(":")
            t_ini_val = time(int(partes_h[0]), int(partes_h[1]))
            
        t_fin_val = time(21, 30)
        if pd.notna(fila_ed["hora_fin"]) and ":" in str(fila_ed["hora_fin"]):
            partes_hf = str(fila_ed["hora_fin"]).split(":")
            t_fin_val = time(int(partes_hf[0]), int(partes_hf[1]))

        with st.container(border=True):
            st.markdown(f"### ✏️ Editando Evento (ID: {ev_id_act})")
            with st.form(key=f"form_edicion_superior_{ev_id_act}"):
                nuevo_titulo = st.text_input("Título", value=fila_ed["titulo"])
                
                min_idx = list(COLORES_MINISTERIO.keys()).index(fila_ed["ministerio"]) if fila_ed["ministerio"] in COLORES_MINISTERIO else 0
                nuevo_min = st.selectbox("Ministerio / Área", list(COLORES_MINISTERIO.keys()), index=min_idx)
                
                salon_idx = LISTA_SALONES.index(fila_ed["salon"]) if fila_ed["salon"] in LISTA_SALONES else 0
                nuevo_salon = st.selectbox("Salón / Lugar", LISTA_SALONES, index=salon_idx)
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    nueva_f_inicio = st.date_input("Fecha Desde", value=date.fromisoformat(str(fila_ed["fecha"])))
                with col_e2:
                    f_fin_val = date.fromisoformat(str(fila_ed["fecha_fin"])) if pd.notna(fila_ed["fecha_fin"]) and str(fila_ed["fecha_fin"]) != "" else date.fromisoformat(str(fila_ed["fecha"]))
                    nueva_f_fin = st.date_input("Fecha Hasta", value=f_fin_val)
                    
                col_eh1, col_eh2 = st.columns(2)
                with col_eh1:
                    nueva_h_ini = st.time_input("Hora Inicio", value=t_ini_val)
                with col_eh2:
                    nueva_h_fin = st.time_input("Hora Fin", value=t_fin_val)

                nuevo_encargado = st.text_input("Encargado", value=fila_ed["encargado"])
                nuevas_notas = st.text_area("Notas", value=fila_ed["notas"] if pd.notna(fila_ed["notas"]) else "")
                
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    guardar = st.form_submit_button("💾 Guardar Cambios")
                with col_b2:
                    borrar = st.form_submit_button("🗑️ Borrar Evento")
                with col_b3:
                    cerrar = st.form_submit_button("❌ Cancelar")

                if guardar:
                    sheet = conectar_sheets()
                    cell = sheet.find(str(ev_id_act))
                    if cell:
                        fila_num = cell.row
                        sheet.update(values=[[
                            int(ev_id_act), nuevo_titulo, nuevo_min, nuevo_salon, 
                            str(nueva_f_inicio), str(nueva_f_fin), 
                            nueva_h_ini.strftime("%H:%M"), nueva_h_fin.strftime("%H:%M"), 
                            nuevo_encargado, nuevas_notas
                        ]], range_name=f"A{fila_num}:J{fila_num}")
                    
                    st.session_state["id_evento_editar"] = None
                    st.success("¡Actualizado con éxito en Google Sheets!")
                    st.rerun()

                if borrar:
                    sheet = conectar_sheets()
                    cell = sheet.find(str(ev_id_act))
                    if cell:
                        sheet.delete_rows(cell.row)
                        
                    st.session_state["id_evento_editar"] = None
                    st.success("¡Evento eliminado de Google Sheets!")
                    st.rerun()

                if cerrar:
                    st.session_state["id_evento_editar"] = None
                    st.rerun()

# Botón superior para crear nuevo evento
if es_admin:
    col_btn_crear, _ = st.columns([1, 4])
    with col_btn_crear:
        if not st.session_state.get("modo_crear_arriba") and not st.session_state.get("id_evento_editar") and not st.session_state.get("id_evento_ver"):
            if st.button("➕ Nuevo Evento", type="primary"):
                st.session_state["modo_crear_arriba"] = True
                st.session_state["id_evento_editar"] = None
                st.session_state["id_evento_ver"] = None
                st.session_state["fecha_seleccionada"] = date.today()
                st.rerun()

# Filtros rápidos
col1, col2 = st.columns(2)
with col1:
    filtro_min = st.multiselect("Filtrar por Ministerio", options=list(COLORES_MINISTERIO.keys()))
with col2:
    salones_disp = df_eventos["salon"].unique() if not df_eventos.empty else []
    filtro_salon = st.multiselect("Filtrar por Salón", options=salones_disp)

df_mostrar = df_eventos.copy()
if filtro_min:
    df_mostrar = df_mostrar[df_mostrar["ministerio"].isin(filtro_min)]
if filtro_salon:
    df_mostrar = df_mostrar[df_mostrar["salon"].isin(filtro_salon)]

# Transformamos los datos al formato del calendario
eventos_calendario = []
for _, fila in df_mostrar.iterrows():
    f_inicio = fila["fecha"]
    f_fin_db = fila["fecha_fin"] if pd.notna(fila["fecha_fin"]) and str(fila["fecha_fin"]).strip() != "" else fila["fecha"]
    h_ini = fila["hora"] if pd.notna(fila["hora"]) and str(fila["hora"]).strip() != "" else "19:30"
    h_fin = fila["hora_fin"] if pd.notna(fila["hora_fin"]) and str(fila["hora_fin"]).strip() != "" else "23:59"

    eventos_calendario.append({
        "id": str(fila["id"]),
        "title": f"{fila['titulo']} ({fila['salon']})",
        "start": f"{f_inicio}T{h_ini}:00",
        "end": f"{f_fin_db}T{h_fin}:00",
        "backgroundColor": COLORES_MINISTERIO.get(fila["ministerio"], "#2563EB"),
        "borderColor": COLORES_MINISTERIO.get(fila["ministerio"], "#2563EB"),
        "extendedProps": {
            "ministerio": fila["ministerio"],
            "salon": fila["salon"],
            "encargado": fila["encargado"],
            "fecha_fin": f_fin_db,
            "hora_fin": h_fin,
            "notas": fila["notas"] or "Sin notas adicionales"
        }
    })

opciones_calendario = {
    "locale": "es",
    "initialView": "dayGridMonth",
    "selectable": es_admin,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth"
    },
    "buttonText": {
        "today": "Hoy",
        "month": "Mes",
        "week": "Semana",
        "list": "Lista"
    },
    "height": 600
}

# CONTENEDOR EXCLUSIVO PARA EL CALENDARIO
container_calendario = st.empty()
with container_calendario.container():
    estado_calendario = calendar(
        events=eventos_calendario,
        options=opciones_calendario,
        key="agenda_iglesia"
    )

# Captura de clics en espacios vacíos
if es_admin:
    if estado_calendario.get("dateClick"):
        clicked_date_str = estado_calendario["dateClick"]["date"][:10]
        st.session_state["fecha_seleccionada"] = date.fromisoformat(clicked_date_str)
        st.session_state["modo_crear_arriba"] = True
        st.session_state["id_evento_editar"] = None
        st.session_state["id_evento_ver"] = None
        st.rerun()

    if estado_calendario.get("select"):
        selected_start_str = estado_calendario["select"]["start"][:10]
        st.session_state["fecha_seleccionada"] = date.fromisoformat(selected_start_str)
        st.session_state["modo_crear_arriba"] = True
        st.session_state["id_evento_editar"] = None
        st.session_state["id_evento_ver"] = None
        st.rerun()

# Captura de clics en eventos existentes
if estado_calendario.get("eventClick"):
    evento_sel = estado_calendario["eventClick"]["event"]
    st.session_state["id_evento_ver"] = int(evento_sel.get("id"))
    st.session_state["modo_crear_arriba"] = False
    st.session_state["id_evento_editar"] = None
    st.rerun()

# ---------------------------------------------------------
# 4. LISTADO INFERIOR
# ---------------------------------------------------------
with st.expander("📋 Ver listado completo de eventos", expanded=False):
    if df_mostrar.empty:
        st.write("No hay eventos para mostrar con los filtros actuales.")
    else:
        for _, fila in df_mostrar.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.write(f"**{fila['titulo']}**")
                    st.write(f"🏷️ {fila['ministerio']} | 📍 {fila['salon']}")
                with c2:
                    fechas_txt = f"{fila['fecha']}" if fila['fecha'] == fila['fecha_fin'] else f"{fila['fecha']} al {fila['fecha_fin']}"
                    h_fin_txt = f" a {fila['hora_fin']} hs" if pd.notna(fila['hora_fin']) and str(fila['hora_fin']).strip() != "" else ""
                    st.write(f"📆 {fechas_txt} | ⏰ {fila['hora']}{h_fin_txt}")
                    st.write(f"👤 {fila['encargado']}")
                with c3:
                    if st.button("Ver detalle", key=f"ver_{fila['id']}"):
                        st.session_state["id_evento_ver"] = int(fila['id'])
                        st.session_state["modo_crear_arriba"] = False
                        st.session_state["id_evento_editar"] = None
                        st.rerun()
