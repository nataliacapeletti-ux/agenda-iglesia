#Python
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta
from streamlit_calendar import calendar
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y BASE DE DATOS
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

def conectar_db():
    return sqlite3.connect("agenda_iglesia.db", check_same_thread=False)

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            ministerio TEXT NOT NULL,
            salon TEXT NOT NULL,
            fecha TEXT NOT NULL,
            fecha_fin TEXT,
            hora TEXT NOT NULL,
            hora_fin TEXT,
            encargado TEXT NOT NULL,
            notas TEXT
        )
    """)
    
    cursor.execute("PRAGMA table_info(eventos)")
    columnas = [info[1] for info in cursor.fetchall()]
    if "fecha_fin" not in columnas:
        cursor.execute("ALTER TABLE eventos ADD COLUMN fecha_fin TEXT")
    if "hora_fin" not in columnas:
        cursor.execute("ALTER TABLE eventos ADD COLUMN hora_fin TEXT")
        
    conn.commit()
    conn.close()

inicializar_db()

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

# Selector de modo en la barra lateral
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

conn = conectar_db()
df_eventos = pd.read_sql("SELECT * FROM eventos ORDER BY fecha ASC, hora ASC", conn)
conn.close()

# ---------------------------------------------------------
# PANELES SUPERIORES (DETALLE, EDICIÓN O CREACIÓN)
# ---------------------------------------------------------

# A. VISTA DE DETALLE (Al hacer clic en un evento)
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
                h_fin_txt = f" a {fila_v['hora_fin']} hs" if pd.notna(fila_v['hora_fin']) and fila_v['hora_fin'] != "" else ""
                st.write(f"⏰ **Horario:** {fila_v['hora']}{h_fin_txt}")
                st.write(f"👤 **Encargado:** {fila_v['encargado']}")
            
            if pd.notna(fila_v['notas']) and fila_v['notas'].strip() != "":
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

# B. VISTA DE CREACIÓN DE EVENTO NUEVO (Con fecha sincronizada)
elif st.session_state.get("modo_crear_arriba") and es_admin:
    subir_scroll()
    with st.container(border=True):
        st.markdown(f"### ➕ Agendar Nuevo Evento (Fecha seleccionada: {st.session_state['fecha_seleccionada']})")
        
        with st.form(key="form_crear_superior"):
            titulo_c = st.text_input("Título del evento *", placeholder="Ej: Culto Especial")
            min_c = st.selectbox("Ministerio / Área", list(COLORES_MINISTERIO.keys()))
            salon_c = st.selectbox("Salón / Lugar", LISTA_SALONES)
            
            # Fechas con sincronización automática
            col_fc1, col_fc2 = st.columns(2)
            with col_fc1:
                f_ini_c = st.date_input("Fecha Desde *", value=st.session_state["fecha_seleccionada"])
            with col_fc2:
                # Por defecto toma la misma fecha de inicio seleccionada
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
                        conn = conectar_db()
                        conn.execute("""
                            INSERT INTO eventos (titulo, ministerio, salon, fecha, fecha_fin, hora, hora_fin, encargado, notas)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (titulo_c, min_c, salon_c, str(f_ini_c), str(f_fin_c), h_ini_c.strftime("%H:%M"), h_fin_c.strftime("%H:%M"), enc_c, notas_c))
                        conn.commit()
                        conn.close()
                        st.session_state["modo_crear_arriba"] = False
                        st.success("¡Evento agendado con éxito!")
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
            partes_h = fila_ed["hora"].split(":")
            t_ini_val = time(int(partes_h[0]), int(partes_h[1]))
            
        t_fin_val = time(21, 30)
        if pd.notna(fila_ed["hora_fin"]) and ":" in str(fila_ed["hora_fin"]):
            partes_hf = fila_ed["hora_fin"].split(":")
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
                    nueva_f_inicio = st.date_input("Fecha Desde", value=date.fromisoformat(fila_ed["fecha"]))
                with col_e2:
                    f_fin_val = date.fromisoformat(fila_ed["fecha_fin"]) if pd.notna(fila_ed["fecha_fin"]) and fila_ed["fecha_fin"] != "" else date.fromisoformat(fila_ed["fecha"])
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
                    conn = conectar_db()
                    conn.execute("""
                        UPDATE eventos 
                        SET titulo = ?, ministerio = ?, salon = ?, fecha = ?, fecha_fin = ?, hora = ?, hora_fin = ?, encargado = ?, notas = ?
                        WHERE id = ?
                    """, (nuevo_titulo, nuevo_min, nuevo_salon, str(nueva_f_inicio), str(nueva_f_fin), nueva_h_ini.strftime("%H:%M"), nueva_h_fin.strftime("%H:%M"), nuevo_encargado, nuevas_notas, ev_id_act))
                    conn.commit()
                    conn.close()
                    st.session_state["id_evento_editar"] = None
                    st.success("¡Actualizado con éxito!")
                    st.rerun()

                if borrar:
                    conn = conectar_db()
                    conn.execute("DELETE FROM eventos WHERE id = ?", (ev_id_act,))
                    conn.commit()
                    conn.close()
                    st.session_state["id_evento_editar"] = None
                    st.success("¡Evento eliminado!")
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
                # Si se usa este botón directo, toma la fecha de hoy
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
    f_fin_db = fila["fecha_fin"] if pd.notna(fila["fecha_fin"]) and fila["fecha_fin"] != "" else fila["fecha"]
    h_ini = fila["hora"] if pd.notna(fila["hora"]) and fila["hora"] != "" else "19:30"
    h_fin = fila["hora_fin"] if pd.notna(fila["hora_fin"]) and fila["hora_fin"] != "" else "23:59"

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
    "selectable": es_admin, # Activamos de nuevo la selección por clic limpio en los días
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

# Captura de clics en espacios vacíos del calendario (Tocar una fecha para crear directo ahí)
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
                    h_fin_txt = f" a {fila['hora_fin']} hs" if pd.notna(fila['hora_fin']) and fila['hora_fin'] != "" else ""
                    st.write(f"📆 {fechas_txt} | ⏰ {fila['hora']}{h_fin_txt}")
                    st.write(f"👤 {fila['encargado']}")
                with c3:
                    if st.button("Ver detalle", key=f"ver_{fila['id']}"):
                        st.session_state["id_evento_ver"] = int(fila['id'])
                        st.session_state["modo_crear_arriba"] = False
                        st.session_state["id_evento_editar"] = None
                        st.rerun()
