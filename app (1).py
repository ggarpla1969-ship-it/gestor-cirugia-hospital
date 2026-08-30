import streamlit as st
import pandas as pd
import datetime
import calendar

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

# Diccionario exhaustivo de combinaciones permitidas (incluyendo G + Q)
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
            val = str(df.at[row, col])
            cell_style = ""
            if is_weekend:
                cell_style += "background-color: #f0f2f6; "
            if val.startswith("G"):
                cell_style += "color: #d32f2f; font-weight: bold; "
            elif " + Q" in val or val == "Q + Q":
                cell_style += "color: #1565c0; font-weight: bold; " 
            styles.at[row, col] = cell_style
    return styles

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
    
    st.subheader("Cargar Datos")
    uploaded_file = st.file_uploader("Sube tu matriz (Excel/CSV)", type=["xlsx", "csv", "ods"])
    if uploaded_file is not None:
        if st.button("📥 Confirmar Carga de Archivo", type="primary"):
            try:
                if uploaded_file.name.endswith('.csv'):
                    st.session_state.matrix_df = pd.read_csv(uploaded_file, index_col=0)
                else:
                    st.session_state.matrix_df = pd.read_excel(uploaded_file, index_col=0)
                st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                st.session_state.update_counter += 1
                st.success("Archivo cargado con éxito. Ya puedes modificarlo.")
            except Exception as e:
                st.error(f"Error al cargar: {e}")
            
    st.divider()
    
    st.subheader("Guardar Datos")
    csv = st.session_state.matrix_df.to_csv().encode('utf-8')
    st.download_button("Descargar Matriz (CSV)", data=csv, file_name=f"matriz_{selected_year}_{selected_month}.csv", mime='text/csv')

# ==========================================
# 5. INTERFAZ: PANEL CENTRAL
# ==========================================
st.title("Gestión del Servicio de Cirugía General (v2.3)")

tab1, tab2, tab3 = st.tabs(["🏥 A: Gestor de Quirófanos", "📊 B: Matriz General", "📋 Resumen y Disponibilidad"])

with tab1:
    st.header("Asignación de Quirófanos")
    
    c1, c_uni, c2, c3, c4, c5 = st.columns(6)
    q_date = c1.selectbox("Fecha", st.session_state.matrix_df.index)
    q_unidad = c_uni.selectbox("Unidad", ["A", "B", "C", "D"])
    q_grupo = c2.selectbox("Grupo", ["Insular", "Materno"])
    q_sala = c3.selectbox("Quirófano", [f"Q{i}" for i in range(1, 9)])
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
                        # Añade el "+ Q" a CUALQUIER estado no bloqueado que no tuviera Q (incluye a las "G")
                        st.session_state.matrix_df.at[q_date, p] = f"{estado_actual} + Q"
                    
                st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                st.session_state.update_counter += 1
                st.success(f"✅ Equipo ({equipo_str}) asignado correctamente para HC {q_hc}.")
                st.rerun()

    st.subheader("Registro de Quirófanos")
    st.dataframe(st.session_state.quirofanos_df, use_container_width=True, hide_index=True)
    
    if not st.session_state.quirofanos_df.empty:
        st.divider()
        st.subheader("⚙️ Gestionar Quirófanos Programados")
        
        opciones_gestion = []
        for idx, row in st.session_state.quirofanos_df.iterrows():
            hc_texto = f" (HC: {row.get('HC', '')})" if str(row.get('HC', '')) != "" else ""
            opciones_gestion.append(f"{idx} | {row['Fecha']} - Unidad {row['Unidad']} - {row['Quirófano']} ({row['Turno']}){hc_texto} - Equipo: {row['Equipo']}")
            
        tab_mod, tab_sus = st.tabs(["✏️ Modificar Equipo o HC", "❌ Suspender Quirófano"])
        
        with tab_mod:
            seleccion_mod = st.selectbox("Selecciona la asignación que quieres modificar:", opciones_gestion, key="sel_mod")
            idx_mod = int(seleccion_mod.split(" | ")[0])
            row_mod = st.session_state.quirofanos_df.loc[idx_mod]
            
            equipo_actual = row_mod['Equipo'].split(", ")
            adjuntos_actuales = [p for p in equipo_actual if p in SURGEONS]
            residentes_actuales = [p for p in equipo_actual if p in RESIDENTS]
            
            c_hc_m, c_adj_m, c_res_m = st.columns([1, 2, 2])
            nuevo_hc = c_hc_m.text_input("HC (Hist. Clínica)", value=row_mod.get("HC", ""), key="mod_hc")
            nuevos_adj = c_adj_m.multiselect("Adjunto(s)", SURGEONS, default=adjuntos_actuales, key="mod_adj")
            nuevos_res = c_res_m.multiselect("Residente(s)", RESIDENTS, default=residentes_actuales, key="mod_res")
            
            if st.button("🔄 Actualizar Datos", type="primary", key="btn_mod"):
                nuevo_equipo = nuevos_adj + nuevos_res
                
                if not nuevo_equipo:
                    st.warning("El equipo no puede estar vacío. Si quieres eliminar la sesión, usa la pestaña 'Suspender'.")
                else:
                    viejos_set = set(equipo_actual)
                    nuevos_set = set(nuevo_equipo)
                    añadidos = nuevos_set - viejos_set
                    quitados = viejos_set - nuevos_set
                    
                    errores_mod = []
                    for p in añadidos:
                        estado_actual = str(st.session_state.matrix_df.at[row_mod["Fecha"], p]).strip()
                        
                        restrict_matrix = False
                        if any(r in estado_actual for r in RESTRICCIONES_ABSOLUTAS):
                            restrict_matrix = True
                        elif row_mod["Turno"] == "Mañana" and any(r in estado_actual for r in RESTRICCIONES_MANANA):
                            restrict_matrix = True
                        elif row_mod["Turno"] == "Tarde" and any(r in estado_actual for r in RESTRICCIONES_TARDE):
                            restrict_matrix = True

                        if restrict_matrix:
                            errores_mod.append(f"🛑 **{p}**: Bloqueado ('{estado_actual}') para turno de {row_mod['Turno']}")
                        else:
                            ya_asignado = False
                            for i, r in st.session_state.quirofanos_df.iterrows():
                                if i != idx_mod and r["Fecha"] == row_mod["Fecha"] and r["Turno"] == row_mod["Turno"]:
                                    if p in r["Equipo"].split(", "):
                                        ya_asignado = True
                                        break
                            if ya_asignado:
                                errores_mod.append(f"⚠️ **{p}**: Ya está asignado a otro quirófano en turno de {row_mod['Turno']}.")
                    
                    if errores_mod:
                        st.error("No se ha podido actualizar por conflictos con los nuevos miembros:")
                        for e in errores_mod: st.write(e)
                    else:
                        for p in quitados:
                            turnos_q = sum(1 for i, r in st.session_state.quirofanos_df.iterrows() if i != idx_mod and r["Fecha"] == row_mod["Fecha"] and p in r["Equipo"].split(", "))
                            estado_actual = str(st.session_state.matrix_df.at[row_mod["Fecha"], p]).strip()
                            
                            if turnos_q == 0:
                                if estado_actual in ["Q", "Q + Q"]:
                                    es_finde = "(Sábado)" in row_mod["Fecha"] or "(Domingo)" in row_mod["Fecha"]
                                    st.session_state.matrix_df.at[row_mod["Fecha"], p] = "none" if es_finde else "Libre"
                                elif " + Q" in estado_actual:
                                    st.session_state.matrix_df.at[row_mod["Fecha"], p] = estado_actual.replace(" + Q", "").strip()
                            elif turnos_q == 1:
                                if estado_actual == "Q + Q":
                                    st.session_state.matrix_df.at[row_mod["Fecha"], p] = "Q"
                        
                        for p in añadidos:
                            estado_actual = str(st.session_state.matrix_df.at[row_mod["Fecha"], p]).strip()
                            if estado_actual in ["Libre", "none", ""]:
                                st.session_state.matrix_df.at[row_mod["Fecha"], p] = "Q"
                            elif estado_actual == "Q":
                                st.session_state.matrix_df.at[row_mod["Fecha"], p] = "Q + Q"
                            elif "Q" not in estado_actual:
                                st.session_state.matrix_df.at[row_mod["Fecha"], p] = f"{estado_actual} + Q"
                        
                        st.session_state.quirofanos_df.at[idx_mod, "HC"] = nuevo_hc
                        st.session_state.quirofanos_df.at[idx_mod, "Equipo"] = ", ".join(nuevo_equipo)
                        st.session_state.matrix_df = apply_guardia_rules(st.session_state.matrix_df)
                        st.session_state.update_counter += 1
                        st.success("✅ Asignación actualizada correctamente.")
                        st.rerun()

        with tab_sus:
            seleccion_sus = st.selectbox("Selecciona el Quirófano a suspender:", opciones_gestion, key="sel_sus")
            
            if st.button("❌ Suspender Asignación", type="primary", key="btn_sus"):
                idx_to_drop = int(seleccion_sus.split(" | ")[0])
                row_deleted = st.session_state.quirofanos_df.loc[idx_to_drop]
                
                st.session_state.quirofanos_df = st.session_state.quirofanos_df.drop(idx_to_drop).reset_index(drop=True)
                
                fecha_suspendida = row_deleted['Fecha']
                equipo_suspendido = row_deleted['Equipo'].split(", ")
                
                for personal_suspendido in equipo_suspendido:
                    turnos_q = sum(1 for _, r in st.session_state.quirofanos_df.iterrows() if r["Fecha"] == fecha_suspendida and personal_suspendido in r["Equipo"].split(", "))
                    estado_actual = str(st.session_state.matrix_df.at[fecha_suspendida, personal_suspendido]).strip()
                    
                    if turnos_q == 0:
                        if estado_actual in ["Q", "Q + Q"]:
                            es_finde = "(Sábado)" in fecha_suspendida or "(Domingo)" in fecha_suspendida
                            st.session_state.matrix_df.at[fecha_suspendida, personal_suspendido] = "none" if es_finde else "Libre"
                        elif " + Q" in estado_actual:
                            st.session_state.matrix_df.at[fecha_suspendida, personal_suspendido] = estado_actual.replace(" + Q", "").strip()
                    elif turnos_q == 1:
                        if estado_actual == "Q + Q":
                            st.session_state.matrix_df.at[fecha_suspendida, personal_suspendido] = "Q"
                
                st.session_state.update_counter += 1
                st.success("✅ Quirófano suspendido. El equipo vuelve a estar disponible.")
                st.rerun()

    if st.button("Limpiar Registro Quirófanos", type="secondary"):
        st.session_state.quirofanos_df = st.session_state.quirofanos_df.iloc[0:0]
        st.rerun()

with tab2:
    st.header("Matriz de Personal")
    
    df_adjuntos = st.session_state.matrix_df[SURGEONS]
    df_residentes = st.session_state.matrix_df[RESIDENTS]
    
    st.subheader("👨‍⚕️ Adjuntos")
    dropdown_adj = {col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in SURGEONS}
    styled_adj = df_adjuntos.style.apply(lambda x: style_matrix(df_adjuntos), axis=None)
    
    edited_adj = st.data_editor(
        styled_adj, 
        column_config=dropdown_adj, 
        use_container_width=True, 
        height=1200,
        key=f"editor_adj_{st.session_state.update_counter}" 
    )
    
    st.divider()
    
    st.subheader("📚 Residentes")
    dropdown_res = {col: st.column_config.SelectboxColumn(options=ALL_STATUSES, required=False) for col in RESIDENTS}
    styled_res = df_residentes.style.apply(lambda x: style_matrix(df_residentes), axis=None)
    
    edited_res = st.data_editor(
        styled_res, 
        column_config=dropdown_res, 
        use_container_width=True, 
        height=1200,
        key=f"editor_res_{st.session_state.update_counter}" 
    )
    
    combined_df = pd.concat([edited_adj, edited_res], axis=1)
    combined_df = combined_df[ALL_STAFF]
    
    processed_df = apply_guardia_rules(combined_df.copy())
    
    if not processed_df.equals(st.session_state.matrix_df):
        st.session_state.matrix_df = processed_df
        st.session_state.update_counter += 1
        st.rerun()

with tab3:
    st.header("📋 Resumen y Disponibilidad")
    
    st.subheader("A) Actividad de Quirófanos")
    
    q_df = st.session_state.quirofanos_df
    if not q_df.empty:
        q_df_sorted = q_df.sort_values(by=["Fecha", "Unidad", "Grupo", "Turno", "Quirófano"])
        st.markdown("**Desglose de Asignaciones por Fecha:**")
        st.dataframe(q_df_sorted, hide_index=True, use_container_width=True)
        
        st.markdown("**Total de Quirófanos Asignados al Mes por Unidad:**")
        resumen_unidad = q_df.groupby("Unidad").size().reset_index(name="Nº Quirófanos")
        st.dataframe(resumen_unidad, hide_index=True)
    else:
        st.info("Aún no hay quirófanos programados en este mes.")
    
    st.divider()
    
    st.subheader("B) Actividad por Profesional")
    
    profesional = st.selectbox("Selecciona un Cirujano o Residente:", ALL_STAFF)
    
    if profesional:
        actividades_mes = st.session_state.matrix_df[profesional].value_counts()
        conteo = {
            "Guardias (G)": 0, "Quirófano (Q)": 0, "C. HOS M.": 0, "C. HOS T.": 0,
            "C.VEC.": 0, "C.TELD.": 0, "C.PRUD. 1": 0, "C.PRUD. 2": 0,
            "VAC (Vacaciones)": 0, "CUR-CONGR.": 0, "BAJA": 0
        }
        
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
            
        resumen_prof_df = pd.DataFrame(list(conteo.items()), columns=["Actividad", "Días en el Mes"])
        resumen_prof_df = resumen_prof_df[resumen_prof_df["Días en el Mes"] > 0]
        
        if not resumen_prof_df.empty:
            st.dataframe(resumen_prof_df, hide_index=True)
        else:
            st.info(f"{profesional} no tiene actividad especial registrada este mes.")

    st.divider()
    
    st.subheader("C) Personal Disponible (Imprevistos / Retén)")
    st.write("Selecciona una fecha para ver quién está en estado **Libre**.")
    
    disp_date = st.selectbox("Fecha para consultar disponibilidad:", st.session_state.matrix_df.index)
    if disp_date:
        dia_datos = st.session_state.matrix_df.loc[disp_date]
        disponibles = [staff for staff, estado in dia_datos.items() if str(estado) == "Libre"]
        
        if disponibles:
            st.success(f"**Personal disponible ('Libre') el {disp_date}:**\n\n" + ", ".join(disponibles))
        else:
            st.warning("No hay personal en estado 'Libre' este día.")
            
    st.divider()
    
    st.subheader("D) Cuadrante Mensual de Guardias")
    
    guardias_list = []
    for date_idx, row in st.session_state.matrix_df.iterrows():
        adjuntos_guardia = [p for p in SURGEONS if str(row[p]).strip().upper().startswith("G")]
        residentes_guardia = [p for p in RESIDENTS if str(row[p]).strip().upper().startswith("G")]
        
        guardias_list.append({
            "Fecha": date_idx,
            "Adjuntos de Guardia": ", ".join(adjuntos_guardia),
            "Residentes de Guardia": ", ".join(residentes_guardia)
        })
        
    guardias_df = pd.DataFrame(guardias_list)
    st.dataframe(guardias_df, hide_index=True, use_container_width=True)
