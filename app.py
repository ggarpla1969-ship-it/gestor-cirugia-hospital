import streamlit as st
import pandas as pd
import datetime
import calendar
import re

try:
    from streamlit_gsheets import GsheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# ==========================================
# 0. CONFIGURACIÓN Y CONTROL DE ACCESO
# ==========================================
st.set_page_config(page_title="Gestor Servicio Cirugía General", layout="wide")

USUARIOS_ESCRITURA = {
    "jefe_servicio": "CirugiaJefe2026*",
    "seccion_1": "Sec1_2026*",
    "seccion_2": "Sec2_2026*",
    "seccion_3": "Sec3_2026*",
    "secretaria_1": "Secretaria1_2026*",
    "secretaria_2": "Secretaria2_2026*"
}

CLAVE_SOLO_LECTURA = "ServicioCG2026"

def check_authentication():
    def process_login():
        user_input = st.session_state.get("input_user", "").strip().lower()
        pass_input = st.session_state.get("input_pass", "")
        
        if user_input in USUARIOS_ESCRITURA and pass_input == USUARIOS_ESCRITURA[user_input]:
            st.session_state["authenticated"] = True
            st.session_state["modo_escritura"] = True
            st.session_state["usuario_actual"] = user_input
        elif pass_input == CLAVE_SOLO_LECTURA:
            st.session_state["authenticated"] = True
            st.session_state["modo_escritura"] = False
            st.session_state["usuario_actual"] = "Consulta General"
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔒 Acceso Restringido - Cirugía General")
        st.write("Introduce tus credenciales para acceder al sistema:")
        
        st.text_input("Usuario (Dejar en blanco si entras como Solo Lectura)", key="input_user", placeholder="Ej: jefe_servicio, secretaria_1...")
        st.text_input("Contraseña", type="password", key="input_pass", placeholder="Introduce tu clave...", on_change=process_login)
        
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            process_login()
            st.rerun()
            
        if "authenticated" in st.session_state and not st.session_state["authenticated"]:
            st.error("😕 Usuario o contraseña incorrectos.")
    return False

if not check_authentication():
    st.stop()

# ==========================================
# 1. CONSTANTES Y CONEXIÓN
# ==========================================
SURGEONS = [f"A{i}" for i in range(1, 8)] + [f"B{i}" for i in range(1, 10)] + \
           [f"C{i}" for i in range(1, 7)] + [f"D{i}" for i in range(1, 7)]
RESIDENTS = ["R1A", "R1B", "R2A", "R2B", "R3A", "R3B", "R4A", "R4B", 
             "R5A", "R5B", "RVASC", "RURO", "RCPL", "RGIN"]
ALL_STAFF = SURGEONS + RESIDENTS

STATUSES = ["Libre", "none", "Q", "G", "SG", "C. HOS M.", "C. HOS T.", "C.VEC.", 
            "C.TELD.", "C.PRUD. 1", "C.PRUD. 2", "VAC", "CUR-CONGR.", "BAJA"]

COMBO_Q = ["C. HOS T. + Q"]
COMBO_G = [f"G + {s}" for s in ["C. HOS M.", "C. HOS T.", "C.VEC.", "C.TELD.", "C.PRUD. 1", "C.PRUD. 2"]]
COMBO_G_Q = [f"G + C. HOS T. + Q"]
ALL_STATUSES = STATUSES + COMBO_Q + COMBO_G + COMBO_G_Q + ["Q + Q", "G + Q", "G + Q + Q"]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Inicializar conexión de forma segura
conn = None
if HAS_GSHEETS:
    try:
        conn = st.connection("gsheets", type=GsheetsConnection)
    except Exception:
        conn = None

# ==========================================
# 2. FUNCIONES DE LÓGICA
# ==========================================
def generate_base_matrix(year, month):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime.date(year, month, day) for day in range(1, num_days + 1)]
    df = pd.DataFrame(index=[f"{d.strftime('%d/%m/%Y')} ({DIAS_SEMANA[d.weekday()]})" for d in dates], columns=ALL_STAFF)
    
    for i, date_obj in enumerate(dates):
        weekday = date_obj.weekday()
        row_idx = df.index[i]
        default_status = "none" if weekday >= 5 else "Libre"
        for col in df.columns:
            df.at[row_idx, col] = default_status
    return df

def apply_guardia_rules(df):
    for col in df.columns:
        for i in range(len(df) - 1):
            current_status = str(df.iloc[i][col]).strip().upper()
            if current_status == "G" or current_status.startswith("G +"):
                df.iat[i+1, df.columns.get_loc(col)] = "SG"
    return df

def style_matrix(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for row in df.index:
        is_weekend = "(Sábado)" in str(row) or "(Domingo)" in str(row)
        for col in df.columns:
            val = str(df.at[row, col]).strip().upper()
            cell_style = ""
            if is_weekend: cell_style += "background-color: #f0f2f6; "
            if val.startswith("G"): cell_style += "color: #d32f2f; font-weight: bold; "
            elif " + Q" in val or val == "Q + Q": cell_style += "color: #1565c0; font-weight: bold; " 
            elif val in ["VAC", "BAJA", "CUR-CONGR."]: cell_style += "background-color: #ffcdd2; color: #b71c1c; font-weight: bold; "
            styles.at[row, col] = cell_style
    return styles

# ==========================================
# 3. INICIALIZACIÓN DE ESTADO
# ==========================================
now = datetime.datetime.now()
if 'matrix_df' not in st.session_state:
    st.session_state.current_year = now.year
    st.session_state.current_month = now.month
    loaded = False
    if conn is not None:
        try:
            df_cloud = conn.read(worksheet="Matriz", ttl=0)
            if not df_cloud.empty:
                df_cloud.set_index(df_cloud.columns[0], inplace=True)
                st.session_state.matrix_df = df_cloud
                loaded = True
        except Exception:
            loaded = False
    if not loaded:
        st.session_state.matrix_df = generate_base_matrix(now.year, now.month)

if 'quirofanos_df' not in st.session_state:
    q_loaded = False
    if conn is not None:
        try:
            q_cloud = conn.read(worksheet="Quirofanos", ttl=0)
            if not q_cloud.empty:
                st.session_state.quirofanos_df = q_cloud
                q_loaded = True
        except Exception:
            q_loaded = False
    if not q_loaded:
        st.session_state.quirofanos_df = pd.DataFrame(columns=["Fecha", "Unidad", "Grupo", "Quirófano", "Turno", "HC", "Equipo"])

if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0

modo_escritura = st.session_state.get("modo_escritura", False)

def guardar_en_nube():
    if conn is not None:
        try:
            conn.update(worksheet="Matriz", data=st.session_state.matrix_df.reset_index())
            conn.update(worksheet="Quirofanos", data=st.session_state.quirofanos_df)
            st.success("☁️ ¡Cambios guardados en la nube!")
        except Exception as e:
            st.error(f"Error al sincronizar: {e}")
    else:
        st.warning("⚠️ Conexión a Google Sheets no disponible. Cambios guardados solo localmente.")

# ==========================================
# 4. SIDEBAR Y PANEL CENTRAL
# ==========================================
with st.sidebar:
    st.header("📅 Calendario y Sincronización")
    if modo_escritura:
        st.success(f"🔓 Modo: **Escritura** ({st.session_state.get('usuario_actual', 'Admin')})")
        if st.button("☁️ Sincronizar Cambios a la Nube", type="primary"):
            guardar_en_nube()
    else:
        st.info("👁️ Modo: **Solo Lectura**")

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

st.title("Gestión del Servicio de Cirugía General (v6.1 Cloud)")

tab1, tab2, tab3 = st.tabs(["🏥 A: Gestor de Quirófanos", "📊 B: Matriz General", "📋 Resumen y Disponibilidad"])

with tab1:
    st.header("Asignación de Quirófanos")
    st.dataframe(st.session_state.quirofanos_df, use_container_width=True, hide_index=True)

with tab2:
    st.header("Matriz de Personal")
    df_adj = st.session_state.matrix_df[SURGEONS]
    st.dataframe(df_adj.style.apply(lambda x: style_matrix(df_adj), axis=None), use_container_width=True, height=600)

with tab3:
    st.header("📋 Resumen y Disponibilidad")
    disp_date = st.selectbox("Selecciona la fecha:", st.session_state.matrix_df.index, key="sel_disp_date")
    if disp_date:
        disponibles = [staff for staff, estado in st.session_state.matrix_df.loc[disp_date].items() if str(estado) == "Libre"]
        if disponibles: 
            st.success(f"**Personal disponible el {disp_date}:** " + ", ".join(disponibles))
        else: 
            st.warning("Sin personal Libre.")
