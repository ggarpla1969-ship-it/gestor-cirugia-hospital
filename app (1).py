import streamlit as st
import pandas as pd
import datetime
import calendar
import re

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
st.set_page_config(page_title="Gestor Servicio Cirugía General", layout="wide")

SURGEONS = [f"A{i}" for i in range(1, 8)] + [f"B{i}" for i in range(1, 10)] + \
           [f"C{i}" for i in range(1, 7)] + [f"D{i}" for i in range(1, 7)]
RESIDENTS = ["R1A", "R1B", "R2A", "R2B", "R3A", "R3B", "R4A", "R4B", 
             "R5A", "R5B", "RVASC", "RURO", "RCPL", "RGIN"]
ALL_STAFF = SURGEONS + RESIDENTS

STATUSES = ["Libre", "none", "Q", "G", "SG", "C. HOS M.", "C. HOS T.", "C.VEC.", 
            "C.TELD.", "C.PRUD. 1", "C.PRUD. 2", "VAC", "CUR-CONGR.", "BAJA"]

COMBO_Q = [f"{s} + Q" for s in ["C. HOS M.", "C. HOS T.", "C.VEC.", "C.TELD.", "C.PRUD. 1", "C.PRUD. 2"]]
COMBO_G = [f"G + {s}" for s in ["C. HOS M.", "C.VEC.", "C.TELD.", "C.PRUD. 1", "C.PRUD. 2"]]
COMBO_G_Q = [f"G + {s} + Q" for s in ["C. HOS M.", "C.VEC.", "C.TELD.", "C.PRUD. 1", "C.PRUD. 2"]]
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
        raise ValueError("El archivo de ausencias debe tener al menos 4 columnas: Médico, Fecha Inicio, Fecha Fin, Motivo")

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

        if not inicio_str or not fin_str:
            continue

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

# ==========================================
# 4. INTERFAZ: PANEL IZQUIERDO (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("📅 Calendario y Carga")
    
    col1, col2 = st.columns(2)
    selected_year = col1.number_input("Año", min_value=2020, max_value=2050, value=st.session_state.current_year)
    selected_month = col2.number_input("Mes", min_value=1, max_value=12, value=st.session_state.current_month)
    
    if st.button("Generar Plantilla Mensual"):
        st.session_state.matrix_df = generate_base_matrix(selected_year, selected_month)
        st.session_state.current_year = selected_year
        st.session_state.current_month = selected_month
        st.session_state.update_counter += 1
        st.success("Plantilla generada.")
    
    st.divider()
    
    st.subheader("📥 Cargar Datos (Recuperar)")
    
    uploaded_file = st.file_uploader("1a. Sube tu Matriz General", type=["xlsx", "csv", "ods"], key="up_matriz")
    if uploaded_file is not None:
        if st.button("📥 Cargar Matriz", type="primary"):
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

    uploaded_guardias = st.file_uploader("1b. Sube Guardias (Adjuntos/Residentes)", type=["ods", "xlsx", "csv"], key="up_guardias")
    if uploaded_guardias is not None:
        if st.button("🚨 Importar Guardias", type="primary"):
            try:
                matriz_actualizada, count, informe = process_guardias_ods(uploaded_guardias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Guardias importadas! ({count} asignadas)")
                with st.expander("🔍 INFORME DE GUARDIAS", expanded=True):
                    for lin in informe: st.write(lin)
            except Exception as e:
                st.error(f"Error al procesar el archivo de guardias: {e}")

    uploaded_consultas = st.file_uploader("1c. Sube Consultas Extrahospitalarias", type=["ods", "xlsx", "csv"], key="up_consultas")
    if uploaded_consultas is not None:
        if st.button("🩺 Importar Consultas", type="primary"):
            try:
                matriz_actualizada, count, informe = process_consultas_ods(uploaded_consultas, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Consultas importadas! ({count} asignadas)")
                with st.expander("🔍 INFORME DE CONSULTAS", expanded=True):
                    for lin in informe: st.write(lin)
            except Exception as e:
                st.error(f"Error al procesar el archivo de consultas: {e}")

    uploaded_ausencias = st.file_uploader("1d. Sube Ausencias (Vacaciones/Bajas)", type=["ods", "xlsx", "csv"], key="up_ausencias")
    if uploaded_ausencias is not None:
        if st.button("🌴 Importar Ausencias", type="primary"):
            try:
                matriz_actualizada, count, informe = process_ausencias_ods(uploaded_ausencias, st.session_state.matrix_df)
                st.session_state.matrix_df = matriz_actualizada
                st.session_state.update_counter += 1
                st.success(f"✅ ¡Ausencias importadas!")
                with st.expander("🔍 INFORME DE AUSENCIAS", expanded=True):
                    for lin in informe: st.write(lin)
            except Exception as e:
                st.error(f"Error al procesar el archivo de ausencias: {e}")

    uploaded_q = st.file_uploader("2. Sube tu Registro Quirófanos", type=["xlsx", "csv", "ods"], key="up_q")
    if uploaded_q is not None:
        if st.button("📥 Cargar Quirófanos", type="primary"):
            try:
                if uploaded_q.name.endswith('.csv'):
                    st.session_state.quirofanos_df = pd.read_csv(uploaded_q)
                elif uploaded_q.name.endswith('.ods'):
                    st.session_state.quirofanos_df = pd.read_excel(uploaded_q, engine='odf')
                else:
                    st.session_state.quirofanos_df = pd.read_excel(uploaded_q)
                
                if 'HC' not in st.session_state.quirofanos_df.columns:
                    st.session_state.quirofanos_df['HC'] = ""
                st.session_state.quirofanos_df['HC'] = st.session_state.quirofanos_df['HC'].astype(str).replace("nan", "")
                
                st.session_state.update_counter += 1
                st.success("✅ Quirófanos cargados con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar quirófanos: {e}")
            
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
st.title("Gestión del Servicio de Cirugía General (v5.2)")

tab1, tab2, tab3 = st.tabs(["🏥 A: Gestor de Quirófanos", "📊 B: Matriz General", "📋 Resumen y Disponibilidad"])

with tab1:
    st.header("Asignación de Quirófanos")
    
    c1, c_uni, c2, c3, c4, c5 = st.columns(6)
    q_date = c1.selectbox("Fecha", st.session_state.matrix_df.index)
    q_unidad = c_uni.selectbox("Unidad", ["A", "B", "C", "D"])
    q_grupo = c2.selectbox("Grupo", ["Insular", "Materno"])
    
    lista_salas = [f"Q{i}" for i in range(1, 16)] if q_grupo == "Insular" else [f"Q{i}" for i in range(1, 9)]
    q_sala = c3.selectbox("Quirófano", lista_salas)
    
    q_turno = c4.selectbox("Turno", ["Mañana", "Tarde"])
    q_hc = c5.text_input("Nº HC (Hist. Clínica)")
    
    st.divider()
    
    c_adj, c_res = st.columns(2)
    selected_adjuntos = c_adj.multiselect("Seleccionar Adjunto(s)", SURGEONS, placeholder="Elige uno o varios...")
    selected_residentes = c_res.multiselect("Seleccionar Residente(s)", RESIDENTS, placeholder="Elige uno o varios...")
    
    if st.button("Asignar Equipo al Quirófano", type="primary", use_container_width=True):
        equipo_nombres = selected_adjuntos + selected_residentes
        
        if len(equipo_nombres) == 0:
            st.warning("⚠️ Debes seleccionar al menos un adjunto o residente.")
        else:
            errores = []
            for personal in equipo_nombres:
                estado_actual = str(st.session_state.matrix_df.at[q_date, personal]).strip()
                
                restrict_matrix = False
                if any(r in estado_actual for r in RESTRICCIONES_ABSOLUTAS):
                    restrict_matrix = True
                elif q_turno == "Mañana" and any(r in estado_actual for r in RESTRICCIONES_MANANA):
                    restrict_matrix = True
                elif q_turno == "Tarde" and any(r in estado_actual for r in RESTRICCIONES_TARDE):
                    restrict_matrix = True
                
                ya_asignado = False
                for _, row in st.session_state.quirofanos_df.iterrows():
                    if row["Fecha"] == q_date and row["Turno"] == q_turno:
                        if personal in row["Equipo"].split(", "):
                            ya_asignado = True
                            break
                
                if restrict_matrix:
                    errores.append(f"🛑 **{personal}**: Bloqueado ('{estado_actual}') para el turno de {q_turno}")
                elif ya_asignado:
                    errores.append(f"⚠️ **{personal}**: Ya está asignado a otro quirófano en turno de {q_turno}.")
            
            if errores:
                st.error("Conflictos detectados en el equipo:")
                for e in errores: st.write(e)
            else:
                equipo_str = ", ".join(equipo_nombres)
                nueva_asignacion = pd.DataFrame([{
                    "Fecha": q_date, "Unidad": q_unidad, "Grupo": q_grupo, 
                    "Quirófano": q_sala, "Turno": q_turno, "HC": q_hc, "Equipo": equipo_str
                }])
                st.session_state.quirofanos_df = pd.concat([st.session_state.quirofanos_df, nueva_asignacion], ignore_index=True)
                
                for p in equipo_nombres:
                    estado_actual = str(st.session_state.matrix_df.at[q_date, p]).strip()
                    if estado_actual in ["Libre", "none", ""]:
                        st.session_state.matrix_df.at[q_date, p] = "Q"
                    elif estado_actual == "Q":
                        st.session_state.matrix_df.at[q_date, p] = "Q + Q"
                    elif "Q" not in estado_actual:
                        st.session_state.matrix_df.at[q_date, p] = f"{estado_actual} + Q"
                    
                st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                st.session_state.update_counter += 1
                st.success(f"✅ Equipo ({equipo_str}) asignado correctamente.")
                st.rerun()

    st.subheader("Registro de Quirófanos")
    st.dataframe(st.session_state.quirofanos_df, use_container_width=True, hide_index=True)
    
    if not st.session_state.quirofanos_df.empty:
        st.divider()
        st.subheader("⚙️ Gestionar Quirófanos Programados")
        opciones_gestion = [f"{idx} | {row['Fecha']} - Unidad {row['Unidad']} - {row['Quirófano']} ({row['Turno']}) - Equipo: {row['Equipo']}" for idx, row in st.session_state.quirofanos_df.iterrows()]
        
        tab_mod, tab_sus = st.tabs(["✏️ Modificar Equipo o HC", "❌ Suspender Quirófano"])
        with tab_mod:
            seleccion_mod = st.selectbox("Selecciona la asignación:", opciones_gestion, key="sel_mod")
            idx_mod = int(seleccion_mod.split(" | ")[0])
            row_mod = st.session_state.quirofanos_df.loc[idx_mod]
            
            equipo_actual = row_mod['Equipo'].split(", ")
            adjuntos_actuales = [p for p in equipo_actual if p in SURGEONS]
            residentes_actuales = [p for p in equipo_actual if p in RESIDENTS]
            
            c_hc_m, c_adj_m, c_res_m = st.columns([1, 2, 2])
            nuevo_hc = c_hc_m.text_input("HC", value=row_mod.get("HC", ""), key="mod_hc")
            nuevos_adj = c_adj_m.multiselect("Adjunto(s)", SURGEONS, default=adjuntos_actuales, key="mod_adj")
            nuevos_res = c_res_m.multiselect("Residente(s)", RESIDENTS, default=residentes_actuales, key="mod_res")
            
            if st.button("🔄 Actualizar", type="primary", key="btn_mod"):
                nuevo_equipo = nuevos_adj + nuevos_res
                if not nuevo_equipo:
                    st.warning("El equipo no puede estar vacío.")
                else:
                    st.session_state.quirofanos_df.at[idx_mod, "HC"] = nuevo_hc
                    st.session_state.quirofanos_df.at[idx_mod, "Equipo"] = ", ".join(nuevo_equipo)
                    st.session_state.update_counter += 1
                    st.success("✅ Actualizado.")
                    st.rerun()

        with tab_sus:
            seleccion_sus = st.selectbox("Selecciona Quirófano a suspender:", opciones_gestion, key="sel_sus")
            if st.button("❌ Suspender", type="primary", key="btn_sus"):
                idx_to_drop = int(seleccion_sus.split(" | ")[0])
                st.session_state.quirofanos_df = st.session_state.quirofanos_df.drop(idx_to_drop).reset_index(drop=True)
                st.session_state.update_counter += 1
                st.success("✅ Suspendido.")
                st.rerun()

    if st.button("Limpiar Registro Quirófanos", type="secondary"):
        st.session_state.quirofanos_df = st.session_state.quirofanos_df.iloc[0:0]
        st.rerun()

with tab2:
    st.header("Matriz de Personal")
    df_adjuntos = st.session_state.matrix_df[SURGEONS]
    df_residentes = st.session_state.matrix_df[RESIDENTS]
    
    st.subheader("👨‍⚕️ Adjuntos")
    edited_adj = st.data_editor(df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None), column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in SURGEONS}, use_container_width=True, height=1200, key=f"ed_adj_{st.session_state.update_counter}")
    
    st.divider()
    st.subheader("📚 Residentes")
    edited_res = st.data_editor(df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None), column_config={col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in RESIDENTS}, use_container_width=True, height=1200, key=f"ed_res_{st.session_state.update_counter}")
    
    combined_df = pd.concat([edited_adj, edited_res], axis=1)[ALL_STAFF]
    processed_df = apply_guardia_rules(combined_df.copy())
    if not processed_df.equals(st.session_state.matrix_df):
        st.session_state.matrix_df = processed_df
        st.session_state.update_counter += 1
        st.rerun()

with tab3:
    st.header("📋 Resumen y Disponibilidad")
    q_df = st.session_state.quirofanos_df
    if not q_df.empty:
        st.dataframe(q_df.sort_values(by=["Fecha", "Unidad", "Grupo", "Turno", "Quirófano"]), hide_index=True, use_container_width=True)
        st.dataframe(q_df.groupby("Unidad").size().reset_index(name="Nº Quirófanos"), hide_index=True)
    else:
        st.info("Sin quirófanos programados.")
    
    st.divider()
    profesional = st.selectbox("Selecciona Profesional:", ALL_STAFF)
    if profesional:
        actividades_mes = st.session_state.matrix_df[profesional].value_counts()
        conteo = {"Guardias (G)": 0, "Quirófano (Q)": 0, "C. HOS M.": 0, "C. HOS T.": 0, "C.VEC.": 0, "C.TELD.": 0, "C.PRUD. 1": 0, "C.PRUD. 2": 0, "VAC (Vacaciones)": 0, "CUR-CONGR.": 0, "BAJA": 0}
        for estado, count in actividades_mes.items():
            estado = str(estado)
            if estado in ["", "none", "Libre"]: continue
            if estado.startswith("G"): conteo["Guardias (G)"] += count
            if "Q" in estado: conteo["Quirófano (Q)"] += count * estado.count("Q")
            if "C. HOS M." in estado: conteo["C. HOS M."] += count
            if "C. HOS T." in estado: conteo["C. HOS T."] += count
            if "C.VEC." in estado: conteo["C.VEC."] += count
            if "C.TELD." in estado: conteo["C.TELD."] += count
            if "C.PRUD. 1" in estado: conteo["C.PRUD. 1"] += count
            if "C.PRUD. 2" in estado: conteo["C.PRUD. 2"] += count
            if "VAC" in estado: conteo["VAC (Vacaciones)"] += count
            if "CUR-CONGR." in estado: conteo["CUR-CONGR."] += count
            if "BAJA" in estado: conteo["BAJA"] += count
        
        res_df = pd.DataFrame(list(conteo.items()), columns=["Actividad", "Días"]).query("Días > 0")
        if not res_df.empty: st.dataframe(res_df, hide_index=True)
        else: st.info(f"{profesional} sin actividad especial.")

    st.divider()
    disp_date = st.selectbox("Fecha disponibilidad:", st.session_state.matrix_df.index)
    if disp_date:
        disp = [s for s, e in st.session_state.matrix_df.loc[disp_date].items() if str(e) == "Libre"]
        if disp: st.success(f"Disponibles el {disp_date}: {', '.join(disp)}")
        else: st.warning("Sin personal Libre.")
            
    st.divider()
    guardias_list = [{"Fecha": idx, "Adjuntos": ", ".join([p for p in SURGEONS if str(row[p]).upper().startswith("G")]), "Residentes": ", ".join([p for p in RESIDENTS if str(row[p]).upper().startswith("G")])} for idx, row in st.session_state.matrix_df.iterrows()]
    st.dataframe(pd.DataFrame(guardias_list), hide_index=True, use_container_width=True)
