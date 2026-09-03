import streamlit as st
import pandas as pd
import datetime
import calendar
import re

# ==========================================
# 0. CONFIGURACIÓN Y CONTROL DE ACCESO POR ROLES (v6.0)
# ==========================================
st.set_page_config(page_title="Gestor Servicio Cirugía General", layout="wide")

# Diccionario de usuarios permitidos con capacidad de ESCRITURA/MODIFICACIÓN
# (Jefe de Servicio, 3 Jefes de Sección y 2 Secretarias)
USUARIOS_ESCRITURA = {
    "jefe_servicio": "CirugiaJefe2026*",
    "seccion_1": "Sec1_2026*",
    "seccion_2": "Sec2_2026*",
    "seccion_3": "Sec3_2026*",
    "secretaria_1": "Secretaria1_2026*",
    "secretaria_2": "Secretaria2_2026*"
}

# Clave genérica o de servicio para el resto del personal (SOLO LECTURA)
CLAVE_SOLO_LECTURA = "ServicioCG2026"

def check_authentication():
    """Gestiona el login y determina si el usuario tiene permisos de escritura."""
    def process_login():
        user_input = st.session_state.get("input_user", "").strip().lower()
        pass_input = st.session_state.get("input_pass", "")
        
        # Comprobar si es un usuario con permisos de escritura
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

    # Pantalla de Login
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔒 Acceso Restringido - Cirugía General")
        st.write("Introduce tus credenciales para acceder al sistema:")
        
        st.text_input("Usuario (Opcional si entras en modo consulta)", key="input_user", placeholder="Ej: secretaria_1, jefe_servicio...")
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
# 1. CONFIGURACIÓN Y CONSTANTES (v6.0)
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

RESTRICCIONES_ABSOLUTAS = ["SG", "VAC", "CUR-CONGR.", "BAJA"]
RESTRICCIONES_MANANA = ["C. HOS M.", "C.VEC.", "C.TELD.", "C.PRUD. 1", "C.PRUD. 2"]
RESTRICCIONES_TARDE = ["C. HOS T."]

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ==========================================
# 2. FUNCIONES DE LÓGICA DE NEGOCIO
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
        
        if weekday == 0: 
            for doc in ["D1", "A4", "A5", "D6", "D2", "D4"]: 
                if doc in df.columns: df.at[row_idx, doc] = "C. HOS M."
            if "A7" in df.columns: df.at[row_idx, "A7"] = "C. HOS T."
        elif weekday == 1: 
            for doc in ["B4", "B5", "B6", "B7", "B9"]: 
                if doc in df.columns: df.at[row_idx, doc] = "C. HOS M."
        elif weekday == 2: 
            for doc in ["A1", "B5", "D2", "D3", "D4", "D6"]:
                if doc in df.columns: df.at[row_idx, doc] = "C. HOS M."
        elif weekday == 3: 
            for doc in ["B3", "C1", "C3", "C4", "C5", "C6"]:
                if doc in df.columns: df.at[row_idx, doc] = "C. HOS M."
        elif weekday == 4: 
            for doc in ["B1", "A2", "A3", "A6"]:
                if doc in df.columns: df.at[row_idx, doc] = "C. HOS M."
            
            nth_friday = (date_obj.day - 1) // 7 + 1
            if nth_friday == 1 and "C2" in df.columns:
                df.at[row_idx, "C2"] = "C. HOS M."
            elif nth_friday in [2, 3, 4] and "B8" in df.columns:
                df.at[row_idx, "B8"] = "C. HOS M."

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
            if is_weekend:
                cell_style += "background-color: #f0f2f6; "
            
            if val.startswith("G"):
                cell_style += "color: #d32f2f; font-weight: bold; "
            elif " + Q" in val or val == "Q + Q":
                cell_style += "color: #1565c0; font-weight: bold; " 
            elif val in ["VAC", "BAJA", "CUR-CONGR."]:
                cell_style += "background-color: #ffcdd2; color: #b71c1c; font-weight: bold; "
                
            styles.at[row, col] = cell_style
    return styles

def parsear_fecha_robusta(raw_date):
    if raw_date is None or str(raw_date).strip() in ["nan", "", "None", "NAT"]:
        return None
    raw_date = str(raw_date).strip()
    match_iso = re.search(r'^(\d{4})-(\d{2})-(\d{2})', raw_date)
    if match_iso:
        return f"{match_iso.group(3)}/{match_iso.group(2)}/{match_iso.group(1)}"
    
    match_eu = re.search(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})', raw_date)
    if match_eu:
        return f"{int(match_eu.group(1)):02d}/{int(match_eu.group(2)):02d}/{match_eu.group(3)}"
    
    try:
        date_obj = pd.to_datetime(raw_date, dayfirst=True)
        return date_obj.strftime('%d/%m/%Y')
    except:
        return None

def process_guardias_ods(uploaded_file, matrix_df):
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.ods'): df_g = pd.read_excel(uploaded_file, engine='odf')
    elif file_name.endswith(('.xlsx', '.xls')): df_g = pd.read_excel(uploaded_file)
    elif file_name.endswith('.csv'): df_g = pd.read_csv(uploaded_file)
    else: raise ValueError("Formato no soportado")

    index_map = {re.search(r'\d{2}/\d{2}/\d{4}', str(idx)).group(0): idx for idx in matrix_df.index if re.search(r'\d{2}/\d{2}/\d{4}', str(idx))}
    actualizados = 0
    informe = []
    staff_map = {str(col).strip().upper(): col for col in matrix_df.columns}

    for fila_num, row in df_g.iterrows():
        raw_date = str(row.iloc[0]).strip()
        if raw_date in ["nan", "", "None"] or "FECHA" in raw_date.upper(): continue
        parsed_date_str = parsear_fecha_robusta(raw_date)

        if parsed_date_str and parsed_date_str in index_map:
            row_idx = index_map[parsed_date_str]
            for i in range(1, len(row)):
                c_raw = str(row.iloc[i]).strip().upper()
                if c_raw in ["NAN", "", "NONE"]: continue
                if c_raw in staff_map:
                    col_real = staff_map[c_raw]
                    est_actual = str(matrix_df.at[row_idx, col_real]).strip()
                    if est_actual in ["Libre", "none", "", "nan"]:
                        matrix_df.at[row_idx, col_real] = "G"
                    elif "G" not in est_actual:
                        matrix_df.at[row_idx, col_real] = f"G + {est_actual}"
                    actualizados += 1
                else:
                    informe.append(f"⚠️ Fila {fila_num + 2}: Código '{c_raw}' no reconocido.")
        else:
            informe.append(f"❌ Fila {fila_num + 2}: Fecha '{raw_date}' no procesada.")

    matrix_df = apply_guardia_rules(matrix_df)
    return matrix_df, actualizados, informe

def process_consultas_ods(uploaded_file, matrix_df):
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.ods'): df_c = pd.read_excel(uploaded_file, engine='odf')
    elif file_name.endswith(('.xlsx', '.xls')): df_c = pd.read_excel(uploaded_file)
    elif file_name.endswith('.csv'): df_c = pd.read_csv(uploaded_file)
    else: raise ValueError("Formato no soportado")

    index_map = {re.search(r'\d{2}/\d{2}/\d{4}', str(idx)).group(0): idx for idx in matrix_df.index if re.search(r'\d{2}/\d{2}/\d{4}', str(idx))}
    actualizados = 0
    informe = []
    staff_map = {str(col).strip().upper(): col for col in matrix_df.columns}

    for fila_num, row in df_c.iterrows():
        raw_date = str(row.iloc[0]).strip()
        if raw_date in ["nan", "", "None"] or "FECHA" in raw_date.upper(): continue
        parsed_date_str = parsear_fecha_robusta(raw_date)

        if parsed_date_str and parsed_date_str in index_map:
            row_idx = index_map[parsed_date_str]
            for col_name in df_c.columns[1:]:
                c_raw = str(row[col_name]).strip().upper()
                if c_raw in ["NAN", "", "NONE"]: continue
                
                estado_asignar = str(col_name).strip().upper()
                if "VEC" in estado_asignar: val_estado = "C.VEC."
                elif "TELD" in estado_asignar: val_estado = "C.TELD."
                elif "PRUD" in estado_asignar and "1" in estado_asignar: val_estado = "C.PRUD. 1"
                elif "PRUD" in estado_asignar and "2" in estado_asignar: val_estado = "C.PRUD. 2"
                elif "M" in estado_asignar: val_estado = "C. HOS M."
                elif "T" in estado_asignar: val_estado = "C. HOS T."
                else: val_estado = str(col_name).strip()

                if c_raw in staff_map:
                    col_real = staff_map[c_raw]
                    est_actual = str(matrix_df.at[row_idx, col_real]).strip()
                    
                    if est_actual.startswith("G"):
                        if val_estado not in est_actual:
                            matrix_df.at[row_idx, col_real] = f"G + {val_estado}"
                    else:
                        if est_actual in ["Libre", "none", "", "nan"]:
                            matrix_df.at[row_idx, col_real] = val_estado
                        elif val_estado not in est_actual:
                            matrix_df.at[row_idx, col_real] = f"{est_actual} + {val_estado}"
                    actualizados += 1
                else:
                    informe.append(f"⚠️ Fila {fila_num + 2}: Código '{c_raw}' no reconocido.")
        else:
            informe.append(f"❌ Fila {fila_num + 2}: Fecha '{raw_date}' no procesada.")

    return matrix_df, actualizados, informe

def process_ausencias_ods(uploaded_file, matrix_df):
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.ods'): df_a = pd.read_excel(uploaded_file, engine='odf')
    elif file_name.endswith(('.xlsx', '.xls')): df_a = pd.read_excel(uploaded_file)
    elif file_name.endswith('.csv'): df_a = pd.read_csv(uploaded_file)
    else: raise ValueError("Formato no soportado")

    if df_a.shape[1] < 4:
        raise ValueError("El archivo de ausencias debe tener al menos 4 columnas.")

    df_a.columns = ['Medico', 'Inicio', 'Fin', 'Motivo']
    staff_map = {str(col).strip().upper(): col for col in matrix_df.columns}
    
    matrix_dates = {}
    for idx in matrix_df.index:
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(idx))
        if match:
            d_parts = match.group(0).split('/')
            matrix_dates[datetime.date(int(d_parts[2]), int(d_parts[1]), int(d_parts[0]))] = idx

    actualizados = 0
    informe = []

    for fila_num, row in df_a.iterrows():
        med_raw = str(row['Medico']).strip().upper()
        ini_raw = row['Inicio']
        fin_raw = row['Fin']
        mot_raw = row['Motivo']

        if med_raw in ["NAN", "", "NONE", "MEDICO"] and pd.isna(ini_raw) and pd.isna(fin_raw):
            continue

        inicio_str = parsear_fecha_robusta(ini_raw)
        fin_str = parsear_fecha_robusta(fin_raw)
        motivo = str(mot_raw).strip().upper() if not pd.isna(mot_raw) else "VAC"

        if not inicio_str or not fin_str: continue
        if med_raw not in staff_map:
            informe.append(f"⚠️ Fila {fila_num + 2}: Médico '{med_raw}' no reconocido.")
            continue

        col_real = staff_map[med_raw]
        p_ini = datetime.date(int(inicio_str.split('/')[2]), int(inicio_str.split('/')[1]), int(inicio_str.split('/')[0]))
        p_fin = datetime.date(int(fin_str.split('/')[2]), int(fin_str.split('/')[1]), int(fin_str.split('/')[0]))

        for d_obj, row_idx in matrix_dates.items():
            if p_ini <= d_obj <= p_fin:
                matrix_df.at[row_idx, col_real] = motivo
                actualizados += 1

        informe.append(f"✅ Rango procesado para {med_raw} ({inicio_str} al {fin_str}): {motivo}")

    return matrix_df, actualizados, informe

# ==========================================
# 3. INICIALIZACIÓN DEL ESTADO
# ==========================================
if 'matrix_df' not in st.session_state:
    now = datetime.datetime.now()
    st.session_state.current_year = now.year
    st.session_state.current_month = now.month
    st.session_state.matrix_df = generate_base_matrix(now.year, now.month)

if 'quirofanos_df' not in st.session_state:
    st.session_state.quirofanos_df = pd.DataFrame(columns=["Fecha", "Unidad", "Grupo", "Quirófano", "Turno", "HC", "Equipo"])
elif 'HC' not in st.session_state.quirofanos_df.columns:
    st.session_state.quirofanos_df['HC'] = "" 

if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0

modo_escritura = st.session_state.get("modo_escritura", False)

# ==========================================
# 4. INTERFAZ: PANEL IZQUIERDO (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("📅 Calendario y Carga")
    
    # Indicador de Rol en Sidebar
    if modo_escritura:
        st.success(f"🔓 Modo: **Escritura** ({st.session_state.get('usuario_actual', 'Admin')})")
    else:
        st.info("👁️ Modo: **Solo Lectura** (Consulta)")

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    st.divider()
    
    col1, col2 = st.columns(2)
    selected_year = col1.number_input("Año", min_value=2020, max_value=2050, value=st.session_state.current_year)
    selected_month = col2.number_input("Mes", min_value=1, max_value=12, value=st.session_state.current_month)
    
    if modo_escritura:
        if st.button("Generar Plantilla Mensual"):
            st.session_state.matrix_df = generate_base_matrix(selected_year, selected_month)
            st.session_state.current_year = selected_year
            st.session_state.current_month = selected_month
            st.session_state.update_counter += 1
            st.success("Plantilla generada.")
        
        st.divider()
        st.subheader("📥 Cargar Datos (Recuperar)")
        
        uploaded_file = st.file_uploader("1a. Sube tu Matriz General", type=["xlsx", "csv", "ods"], key="up_matriz")
        if uploaded_file is not None and st.button("📥 Cargar Matriz", type="primary"):
            try:
                if uploaded_file.name.endswith('.csv'):
                    st.session_state.matrix_df = pd.read_csv(uploaded_file, index_col=0)
                elif uploaded_file.name.endswith('.ods'):
                    st.session_state.matrix_df = pd.read_excel(uploaded_file, index_col=0, engine='odf')
                else:
                    st.session_state.matrix_df = pd.read_excel(uploaded_file, index_col=0)
                st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                st.session_state.update_counter += 1
                st.success("✅ Matriz cargada con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar matriz: {e}")

        uploaded_guardias = st.file_uploader("1b. Sube Guardias", type=["ods", "xlsx", "csv"], key="up_guardias")
        if uploaded_guardias is not None and st.button("🚨 Importar Guardias", type="primary"):
            try:
                matriz_actualizada, count, informe = process_guardias_ods(uploaded_guardias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Guardias importadas! ({count})")
            except Exception as e:
                st.error(f"Error: {e}")

        uploaded_consultas = st.file_uploader("1c. Sube Consultas", type=["ods", "xlsx", "csv"], key="up_consultas")
        if uploaded_consultas is not None and st.button("🩺 Importar Consultas", type="primary"):
            try:
                matriz_actualizada, count, informe = process_consultas_ods(uploaded_consultas, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Consultas importadas! ({count})")
            except Exception as e:
                st.error(f"Error: {e}")

        uploaded_ausencias = st.file_uploader("1d. Sube Ausencias", type=["ods", "xlsx", "csv"], key="up_ausencias")
        if uploaded_ausencias is not None and st.button("🌴 Importar Ausencias", type="primary"):
            try:
                matriz_actualizada, count, informe = process_ausencias_ods(uploaded_ausencias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success("✅ ¡Ausencias importadas!")
            except Exception as e:
                st.error(f"Error: {e}")

        uploaded_q = st.file_uploader("2. Sube Registro Quirófanos", type=["xlsx", "csv", "ods"], key="up_q")
        if uploaded_q is not None and st.button("📥 Cargar Quirófanos", type="primary"):
            try:
                if uploaded_q.name.endswith('.csv'):
                    st.session_state.quirofanos_df = pd.read_csv(uploaded_q)
                elif uploaded_q.name.endswith('.ods'):
                    st.session_state.quirofanos_df = pd.read_excel(uploaded_q, engine='odf')
                else:
                    st.session_state.quirofanos_df = pd.read_excel(uploaded_q)
                if 'HC' not in st.session_state.quirofanos_df.columns:
                    st.session_state.quirofanos_df['HC'] = ""
                st.session_state.update_counter += 1
                st.success("✅ Quirófanos cargados.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("🔒 Los paneles de importación y modificación de ficheros están desactivados en tu perfil de Solo Lectura.")
            
    st.divider()
    st.subheader("💾 Guardar Datos (Descargar)")
    csv_matriz = st.session_state.matrix_df.to_csv().encode('utf-8')
    st.download_button("1. Descargar Matriz General (CSV)", data=csv_matriz, file_name=f"matriz_{selected_year}_{selected_month}.csv", mime='text/csv')

    if not st.session_state.quirofanos_df.empty:
        csv_q = st.session_state.quirofanos_df.to_csv(index=False).encode('utf-8')
        st.download_button("2. Descargar Reg. Quirófanos (CSV)", data=csv_q, file_name=f"quirofanos_{selected_year}_{selected_month}.csv", mime='text/csv')

# ==========================================
# 5. INTERFAZ: PANEL CENTRAL
# ==========================================
st.title("Gestión del Servicio de Cirugía General (v6.0)")

tab1, tab2, tab3 = st.tabs(["🏥 A: Gestor de Quirófanos", "📊 B: Matriz General", "📋 Resumen y Disponibilidad"])

with tab1:
    st.header("Asignación de Quirófanos")
    
    if not modo_escritura:
        st.warning("⚠️ **Modo de Solo Lectura:** No tienes permisos para programar ni modificar quirófanos. Puedes visualizar los registros actuales en la parte inferior.")
    
    c1, c_uni, c2, c3, c4, c5 = st.columns(6)
    q_date = c1.selectbox("Fecha", st.session_state.matrix_df.index, disabled=not modo_escritura)
    q_unidad = c_uni.selectbox("Unidad", ["A", "B", "C", "D"], disabled=not modo_escritura)
    q_grupo = c2.selectbox("Grupo", ["Insular", "Materno"], disabled=not modo_escritura)
    
    lista_salas = [f"Q{i}" for i in range(1, 16)] if q_grupo == "Insular" else [f"Q{i}" for i in range(1, 9)]
    q_sala = c3.selectbox("Quirófano", lista_salas, disabled=not modo_escritura)
    
    q_turno = c4.selectbox("Turno", ["Mañana", "Tarde"], disabled=not modo_escritura)
    q_hc = c5.text_input("Nº HC (Hist. Clínica)", disabled=not modo_escritura)
    
    st.divider()
    
    c_adj, c_res = st.columns(2)
    selected_adjuntos = c_adj.multiselect("Seleccionar Adjunto(s)", SURGEONS, placeholder="Elige...", disabled=not modo_escritura)
    selected_residentes = c_res.multiselect("Seleccionar Residente(s)", RESIDENTS, placeholder="Elige...", disabled=not modo_escritura)
    
    if modo_escritura:
        if st.button("Asignar Equipo al Quirófano", type="primary", use_container_width=True):
            equipo_nombres = selected_adjuntos + selected_residentes
            if len(equipo_nombres) == 0:
                st.warning("⚠️ Debes seleccionar al menos un adjunto o residente.")
            else:
                errores = []
                for personal in equipo_nombres:
                    estado_actual = str(st.session_state.matrix_df.at[q_date, personal]).strip()
                    restrict_matrix = any(r in estado_actual for r in RESTRICCIONES_ABSOLUTAS) or any(r in estado_actual for r in RESTRICCIONES_MANANA) or (q_turno == "Tarde" and any(r in estado_actual for r in RESTRICCIONES_TARDE))
                    
                    ya_asignado = any(row["Fecha"] == q_date and row["Turno"] == q_turno and personal in row["Equipo"].split(", ") for _, row in st.session_state.quirofanos_df.iterrows())
                    
                    if restrict_matrix: errores.append(f"🛑 **{personal}**: Bloqueado ('{estado_actual}')")
                    elif ya_asignado: errores.append(f"⚠️ **{personal}**: Ya asignado a otro quirófano en turno de {q_turno}.")
                
                if errores:
                    st.error("Conflictos detectados:")
                    for e in errores: st.write(e)
                else:
                    equipo_str = ", ".join(equipo_nombres)
                    nueva_asignacion = pd.DataFrame([{"Fecha": q_date, "Unidad": q_unidad, "Grupo": q_grupo, "Quirófano": q_sala, "Turno": q_turno, "HC": q_hc, "Equipo": equipo_str}])
                    st.session_state.quirofanos_df = pd.concat([st.session_state.quirofanos_df, nueva_asignacion], ignore_index=True)
                    
                    for p in equipo_nombres:
                        est = str(st.session_state.matrix_df.at[q_date, p]).strip()
                        if est in ["Libre", "none", ""]: st.session_state.matrix_df.at[q_date, p] = "Q"
                        elif est == "Q": st.session_state.matrix_df.at[q_date, p] = "Q + Q"
                        elif "Q" not in est: st.session_state.matrix_df.at[q_date, p] = f"{est} + Q"
                        
                    st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                    st.session_state.update_counter += 1
                    st.success("✅ Asignado correctamente.")
                    st.rerun()

    st.subheader("Registro de Quirófanos")
    st.dataframe(st.session_state.quirofanos_df, use_container_width=True, hide_index=True)
    
    if modo_escritura and not st.session_state.quirofanos_df.empty:
        st.divider()
        st.subheader("⚙️ Gestionar Quirófanos Programados")
        opciones_gestion = [f"{idx} | {row['Fecha']} - Unidad {row['Unidad']} - {row['Quirófano']} ({row['Turno']}) - Equipo: {row['Equipo']}" for idx, row in st.session_state.quirofanos_df.iterrows()]
        
        tab_mod, tab_sus = st.tabs(["✏️ Modificar Equipo o HC", "❌ Suspender Quirófano"])
        with tab_mod:
            seleccion_mod = st.selectbox("Selecciona:", opciones_gestion, key="sel_mod")
            idx_mod = int(seleccion_mod.split(" | ")[0])
            row_mod = st.session_state.quirofanos_df.loc[idx_mod]
            equipo_actual = row_mod['Equipo'].split(", ")
            
            nuevo_hc = st.text_input("HC", value=row_mod.get("HC", ""), key="mod_hc")
            nuevos_adj = st.multiselect("Adjunto(s)", SURGEONS, default=[p for p in equipo_actual if p in SURGEONS], key="mod_adj")
            nuevos_res = st.multiselect("Residente(s)", RESIDENTS, default=[p for p in equipo_actual if p in RESIDENTS], key="mod_res")
            
            if st.button("🔄 Actualizar", type="primary", key="btn_mod"):
                nuevo_equipo = nuevos_adj + nuevos_res
                if not nuevo_equipo: st.warning("Equipo vacío.")
                else:
                    st.session_state.quirofanos_df.at[idx_mod, "HC"] = nuevo_hc
                    st.session_state.quirofanos_df.at[idx_mod, "Equipo"] = ", ".join(nuevo_equipo)
                    st.session_state.update_counter += 1
                    st.success("✅ Actualizado.")
                    st.rerun()

with tab2:
    st.header("Matriz de Personal")
    if not modo_escritura:
        st.info("👁️ Estás visualizando la matriz en **modo solo lectura**.")
    
    df_adjuntos = st.session_state.matrix_df[SURGEONS]
    df_residentes = st.session_state.matrix_df[RESIDENTS]
    
    st.subheader("👨‍⚕️ Adjuntos")
    if modo_escritura:
        edited_adj = st.data_editor(df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None), column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in SURGEONS}, use_container_width=True, height=1200, key=f"ed_adj_{st.session_state.update_counter}")
    else:
        st.dataframe(df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None), use_container_width=True, height=600)
    
    st.divider()
    st.subheader("📚 Residentes")
    if modo_escritura:
        edited_res = st.data_editor(df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None), column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in RESIDENTS}, use_container_width=True, height=1200, key=f"ed_res_{st.session_state.update_counter}")
        
        combined_df = pd.concat([edited_adj, edited_res], axis=1)[ALL_STAFF]
        processed_df = apply_guardia_rules(combined_df.copy())
        if not processed_df.equals(st.session_state.matrix_df):
            st.session_state.matrix_df = processed_df
            st.session_state.update_counter += 1
            st.rerun()
    else:
        st.dataframe(df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None), use_container_width=True, height=600)

with tab3:
    st.header("📋 Resumen y Disponibilidad")
    
    st.markdown("### **<u>A) LISTADO DE DISPONIBLE ELIGIENDO LA FECHA</u>**", unsafe_allow_html=True)
    disp_date = st.selectbox("Selecciona la fecha:", st.session_state.matrix_df.index, key="sel_disp_date")
    if disp_date:
        dia_datos = st.session_state.matrix_df.loc[disp_date]
        disponibles = [staff for staff, estado in dia_datos.items() if str(estado) == "Libre"]
        if disponibles: st.success(f"**Personal disponible el {disp_date}:** " + ", ".join(disponibles))
        else: st.warning("Sin personal Libre.")
            
    st.divider()
    st.markdown("### **<u>B) LISTADO DE QUIRÓFANOS POR FECHAS DEL MES</u>**", unsafe_allow_html=True)
    q_df = st.session_state.quirofanos_df
    if not q_df.empty:
        st.dataframe(q_df.sort_values(by=["Fecha", "Unidad", "Grupo", "Turno", "Quirófano"]), hide_index=True, use_container_width=True)
        st.dataframe(q_df.groupby("Unidad").size().reset_index(name="Nº Quirófanos"), hide_index=True)
    else: st.info("Sin quirófanos programados.")
    
    st.divider()
    st.markdown("### **<u>C) LISTADO DE GUARDIAS DE ADJUNTOS Y RESIDENTES</u>**", unsafe_allow_html=True)
    guardias_list = [{"Fecha": idx, "Adjuntos de Guardia": ", ".join([p for p in SURGEONS if str(row[p]).strip().upper().startswith("G")]), "Residentes de Guardia": ", ".join([p for p in RESIDENTS if str(row[p]).strip().upper().startswith("G")])} for idx, row in st.session_state.matrix_df.iterrows()]
    st.dataframe(pd.DataFrame(guardias_list), hide_index=True, use_container_width=True)
    
    st.divider()
    st.markdown("### **<u>D) ACTIVIDAD DE CADA ADJUNTO MENSUALMENTE</u>**", unsafe_allow_html=True)
    profesional = st.selectbox("Selecciona un Cirujano o Residente:", ALL_STAFF, key="sel_prof_resumen")
    if profesional:
        columna_prof = st.session_state.matrix_df[profesional]
        conteo = {"G": 0, "SG": 0, "Q": 0, "C. HOS M.": 0, "C. HOS T.": 0, "C.VEC.": 0, "C.TELD.": 0, "C.PRUD. 1": 0, "C.PRUD. 2": 0, "VAC": 0, "CUR-CONGR.": 0, "BAJA": 0}
        for celda in columna_prof:
            celda_str = str(celda).strip().upper()
            if celda_str in ["", "NONE", "LIBRE", "NAN"]: continue
            for parte in [p.strip() for p in celda_str.split("+")]:
                if parte.startswith("G"): conteo["G"] += 1
                elif parte in conteo: conteo[parte] += 1
        resumen_prof_df = pd.DataFrame(list(conteo.items()), columns=["Actividad", "Total Días / Turnos en el Mes"]).query("`Total Días / Turnos en el Mes` > 0")
        if not resumen_prof_df.empty: st.dataframe(resumen_prof_df, hide_index=True, use_container_width=True)
        else: st.info(f"{profesional} sin actividad especial registrada.")
