import streamlit as st
import pandas as pd
import datetime
import calendar
import re

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
        st.write("Introduce tus credenciales para acceder al sistema local:")
        
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
# 1. CONSTANTES DEL SERVICIO
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

# ==========================================
# 2. FUNCIONES DE LÓGICA Y PROCESAMIENTO
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

def parsear_fecha_robusta(raw_date):
    if raw_date is None or str(raw_date).strip() in ["nan", "", "None", "NAT"]: return None
    raw_date = str(raw_date).strip()
    match_iso = re.search(r'^(\d{4})-(\d{2})-(\d{2})', raw_date)
    if match_iso: return f"{match_iso.group(3)}/{match_iso.group(2)}/{match_iso.group(1)}"
    match_eu = re.search(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})', raw_date)
    if match_eu: return f"{int(match_eu.group(1)):02d}/{int(match_eu.group(2)):02d}/{match_eu.group(3)}"
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
# 3. INICIALIZACIÓN DE ESTADO LOCAL
# ==========================================
now = datetime.datetime.now()
if 'matrix_df' not in st.session_state:
    st.session_state.current_year = now.year
    st.session_state.current_month = now.month
    st.session_state.matrix_df = generate_base_matrix(now.year, now.month)

if 'quirofanos_df' not in st.session_state:
    st.session_state.quirofanos_df = pd.DataFrame(columns=["Fecha", "Unidad", "Grupo", "Quirófano", "Turno", "HC", "Equipo"])

if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0

modo_escritura = st.session_state.get("modo_escritura", False)

# ==========================================
# 4. INTERFAZ: PANEL IZQUIERDO (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("📅 Calendario y Gestión")
    
    if modo_escritura:
        st.success(f"🔓 Modo: **Escritura** ({st.session_state.get('usuario_actual', 'Admin')})")
    else:
        st.info("👁️ Modo: **Solo Lectura**")

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
            st.session_state.update_counter += 1
            st.success("Plantilla generada correctamente.")
            
        st.divider()
        st.subheader("📂 Restaurar Sesión Anterior")
        st.caption("Sube los archivos CSV que descargaste para continuar donde lo dejaste.")
        
        # Subir Matriz
        uploaded_csv_matriz = st.file_uploader("1. Cargar Matriz Guardada (CSV)", type=["csv"], key="up_csv_mat")
        if uploaded_csv_matriz is not None and st.button("Restaurar Matriz", type="primary"):
            try:
                df_cargado = pd.read_csv(uploaded_csv_matriz, index_col=0) # Asume que la primera columna son las fechas
                # Para evitar problemas de tipos de datos, convertimos todo a string y limpiamos nans
                df_cargado = df_cargado.fillna("") 
                st.session_state.matrix_df = df_cargado
                st.session_state.update_counter += 1
                st.success("✅ Matriz restaurada con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar la matriz: {e}")
                
        # Subir Quirófanos
        uploaded_csv_quiro = st.file_uploader("2. Cargar Quirófanos Guardados (CSV)", type=["csv"], key="up_csv_qui")
        if uploaded_csv_quiro is not None and st.button("Restaurar Quirófanos", type="primary"):
            try:
                df_q_cargado = pd.read_csv(uploaded_csv_quiro)
                st.session_state.quirofanos_df = df_q_cargado
                st.session_state.update_counter += 1
                st.success("✅ Quirófanos restaurados con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar quirófanos: {e}")
        
        st.divider()
        st.subheader("📥 Cargar Datos Diarios (Importar)")

        uploaded_guardias = st.file_uploader("1. Sube Guardias (.ods/.xlsx/.csv)", type=["ods", "xlsx", "csv"], key="up_guardias")
        if uploaded_guardias is not None and st.button("🚨 Importar Guardias"):
            try:
                matriz_actualizada, count, informe = process_guardias_ods(uploaded_guardias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Guardias importadas con éxito! ({count})")
            except Exception as e:
                st.error(f"Error: {e}")

        uploaded_consultas = st.file_uploader("2. Sube Consultas (.ods/.xlsx/.csv)", type=["ods", "xlsx", "csv"], key="up_consultas")
        if uploaded_consultas is not None and st.button("🩺 Importar Consultas"):
            try:
                matriz_actualizada, count, informe = process_consultas_ods(uploaded_consultas, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Consultas importadas con éxito! ({count})")
            except Exception as e:
                st.error(f"Error: {e}")

        uploaded_ausencias = st.file_uploader("3. Sube Ausencias (.ods/.xlsx/.csv)", type=["ods", "xlsx", "csv"], key="up_ausencias")
        if uploaded_ausencias is not None and st.button("🌴 Importar Ausencias"):
            try:
                matriz_actualizada, count, informe = process_ausencias_ods(uploaded_ausencias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success("✅ ¡Ausencias importadas con éxito!")
            except Exception as e:
                st.error(f"Error: {e}")
                
        st.divider()
        st.subheader("💾 Guardar Datos (Exportar CSV)")
        st.caption("Descarga tus datos al terminar para no perderlos.")
        
        csv_matrix = st.session_state.matrix_df.to_csv().encode('utf-8')
        st.download_button(
            label="📥 Descargar Matriz (CSV)",
            data=csv_matrix,
            file_name=f"matriz_cirugia_{selected_year}_{selected_month:02d}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        csv_quirofanos = st.session_state.quirofanos_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Quirófanos (CSV)",
            data=csv_quirofanos,
            file_name=f"quirofanos_cirugia_{selected_year}_{selected_month:02d}.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.info("🔒 Los paneles de importación y exportación están desactivados en modo Solo Lectura.")

# ==========================================
# 5. PANEL CENTRAL Y PESTAÑAS
# ==========================================
st.title("Gestión del Servicio de Cirugía General")

tab1, tab2, tab3 = st.tabs(["🏥 A: Gestor de Quirófanos", "📊 B: Matriz General", "📋 Resumen y Disponibilidad"])

with tab1:
    st.header("Asignación de Quirófanos")
    if not modo_escritura:
        st.warning("⚠️ **Modo de Solo Lectura:** Visualización de quirófanos.")
    
    c1, c_uni, c2, c3, c4, c5 = st.columns(6)
    q_date = c1.selectbox("Fecha", st.session_state.matrix_df.index, disabled=not modo_escritura)
    q_unidad = c_uni.selectbox("Unidad", ["A", "B", "C", "D"], disabled=not modo_escritura)
    q_grupo = c2.selectbox("Grupo", ["Insular", "Materno"], disabled=not modo_escritura)
    lista_salas = [f"Q{i}" for i in range(1, 16)] if q_grupo == "Insular" else [f"Q{i}" for i in range(1, 9)]
    q_sala = c3.selectbox("Quirófano", lista_salas, disabled=not modo_escritura)
    q_turno = c4.selectbox("Turno", ["Mañana", "Tarde"], disabled=not modo_escritura)
    q_hc = c5.text_input("Nº HC", disabled=not modo_escritura)
    
    st.divider()
    c_adj, c_res = st.columns(2)
    selected_adjuntos = c_adj.multiselect("Adjunto(s)", SURGEONS, disabled=not modo_escritura)
    selected_residentes = c_res.multiselect("Residente(s)", RESIDENTS, disabled=not modo_escritura)
    
    if modo_escritura and st.button("Asignar Equipo al Quirófano", type="primary", use_container_width=True):
        equipo_nombres = selected_adjuntos + selected_residentes
        if not equipo_nombres:
            st.warning("Selecciona al menos un miembro.")
        else:
            equipo_str = ", ".join(equipo_nombres)
            nueva_asignacion = pd.DataFrame([{
                "Fecha": q_date, 
                "Unidad": q_unidad, 
                "Grupo": q_grupo, 
                "Quirófano": q_sala, 
                "Turno": q_turno, 
                "HC": q_hc, 
                "Equipo": equipo_str
            }])
            st.session_state.quirofanos_df = pd.concat([st.session_state.quirofanos_df, nueva_asignacion], ignore_index=True)
            for p in equipo_nombres:
                est = str(st.session_state.matrix_df.at[q_date, p]).strip()
                if est in ["Libre", "none", ""]: 
                    st.session_state.matrix_df.at[q_date, p] = "Q"
                elif est == "Q": 
                    st.session_state.matrix_df.at[q_date, p] = "Q + Q"
                elif "Q" not in est: 
                    st.session_state.matrix_df.at[q_date, p] = f"{est} + Q"
            st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
            st.rerun()

    st.subheader("Registro de Quirófanos")
    st.dataframe(st.session_state.quirofanos_df, use_container_width=True, hide_index=True)

with tab2:
    st.header("Matriz de Personal")
    df_adjuntos = st.session_state.matrix_df[SURGEONS]
    df_residentes = st.session_state.matrix_df[RESIDENTS]
    
    st.subheader("👨‍⚕️ Adjuntos")
    if modo_escritura:
        edited_adj = st.data_editor(
            df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None), 
            column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in SURGEONS}, 
            use_container_width=True, 
            height=600, 
            key=f"ed_adj_{st.session_state.update_counter}"
        )
    else:
        st.dataframe(df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None), use_container_width=True, height=600)
    
    st.divider()
    st.subheader("📚 Residentes")
    if modo_escritura:
        edited_res = st.data_editor(
            df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None), 
            column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in RESIDENTS}, 
            use_container_width=True, 
            height=600, 
            key=f"ed_res_{st.session_state.update_counter}"
        )
        combined_df = pd.concat([edited_adj, edited_res], axis=1)[ALL_STAFF]
        processed_df = apply_guardia_rules(combined_df.copy())
        if not processed_df.equals(st.session_state.matrix_df):
            st.session_state.matrix_df = processed_df
    else:
        st.dataframe(df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None), use_container_width=True, height=600)

with tab3:
    st.header("📋 Resumen y Disponibilidad")
    
    st.markdown("### **<u>A) LISTADO DE DISPONIBLE ELIGIENDO LA FECHA</u>**", unsafe_allow_html=True)
    disp_date = st.selectbox("Selecciona la fecha:", st.session_state.matrix_df.index, key="sel_disp_date")
    if disp_date:
        disponibles = [staff for staff, estado in st.session_state.matrix_df.loc[disp_date].items() if str(estado) == "Libre"]
        if disponibles: 
            st.success(f"**Personal disponible el {disp_date}:** " + ", ".join(disponibles))
        else: 
            st.warning("Sin personal Libre en esta fecha.")
            
    st.divider()
    st.markdown("### **<u>B) LISTADO DE QUIRÓFANOS POR FECHAS DEL MES</u>**", unsafe_allow_html=True)
    q_df = st.session_state.quirofanos_df
    if not q_df.empty:
        st.dataframe(q_df.sort_values(by=["Fecha", "Unidad", "Grupo", "Turno", "Quirófano"]), hide_index=True, use_container_width=True)
    else: 
        st.info("Sin quirófanos programados actualmente.")
    
    st.divider()
    st.markdown("### **<u>C) LISTADO DE GUARDIAS DE ADJUNTOS Y RESIDENTES</u>**", unsafe_allow_html=True)
    guardias_list = [
        {
            "Fecha": idx, 
            "Adjuntos de Guardia": ", ".join([p for p in SURGEONS if str(row[p]).strip().upper().startswith("G")]), 
            "Residentes de Guardia": ", ".join([p for p in RESIDENTS if str(row[p]).strip().upper().startswith("G")])
        } 
        for idx, row in st.session_state.matrix_df.iterrows()
    ]
    st.dataframe(pd.DataFrame(guardias_list), hide_index=True, use_container_width=True)
    
    st.divider()
    st.markdown("### **<u>D) ACTIVIDAD DE CADA ADJUNTO MENSUALMENTE</u>**", unsafe_allow_html=True)
    profesional = st.selectbox("Selecciona un Cirujano o Residente:", ALL_STAFF, key="sel_prof_resumen")
    if profesional:
        conteo = {
            "G": 0, "SG": 0, "Q": 0, "C. HOS M.": 0, "C. HOS T.": 0, 
            "C.VEC.": 0, "C.TELD.": 0, "C.PRUD. 1": 0, "C.PRUD. 2": 0, 
            "VAC": 0, "CUR-CONGR.": 0, "BAJA": 0
        }
        for celda in st.session_state.matrix_df[profesional]:
            celda_str = str(celda).strip().upper()
            if celda_str in ["", "NONE", "LIBRE", "NAN"]: 
                continue
            for parte in [p.strip() for p in celda_str.split("+")]:
                if parte.startswith("G"): 
                    conteo["G"] += 1
                elif parte in conteo: 
                    conteo[parte] += 1
        resumen_prof_df = pd.DataFrame(list(conteo.items()), columns=["Actividad", "Total Días / Turnos en el Mes"]).query("`Total Días / Turnos en el Mes` > 0")
        if not resumen_prof_df.empty: 
            st.dataframe(resumen_prof_df, hide_index=True, use_container_width=True)
        else: 
            st.info(f"{profesional} sin actividad especial registrada este mes.")
