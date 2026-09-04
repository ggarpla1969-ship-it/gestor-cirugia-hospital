import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.title("🏥 Gestión del Servicio de Cirugía")

# --- SISTEMA DE INICIO DE SESIÓN ---
# 1. Crear una variable para recordar quién ha entrado
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

# 2. Pantalla de login (si no hay nadie logueado)
if st.session_state.usuario_actual is None:
    st.subheader("Acceso Restringido")
    
    # Formulario para pedir credenciales
    usuario = st.text_input("Usuario (ej. jefe_servicio):")
    clave = st.text_input("Contraseña:", type="password")
    
    if st.button("Entrar"):
        # Comprobar si el usuario existe y la clave es correcta en los Secrets
        if usuario in st.secrets["passwords"] and st.secrets["passwords"][usuario] == clave:
            st.session_state.usuario_actual = usuario
            st.rerun() # Recarga la página y oculta el login
        else:
            st.error("❌ Usuario o contraseña incorrectos.")
            
    st.stop() # Detiene la aplicación aquí si no hay sesión iniciada

# --- APLICACIÓN PRINCIPAL ---
# 3. Mostrar quién está conectado y botón de salir
st.success(f"Bienvenido/a al sistema, **{st.session_state.usuario_actual}**")
if st.button("Cerrar Sesión"):
    st.session_state.usuario_actual = None
    st.rerun()

st.divider()

# 4. Conectar a PostgreSQL (Supabase)
db_url = st.secrets["postgres"]["url"]
engine = create_engine(db_url)

# 5. Crear la tabla de registros si es la primera vez
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comentario TEXT
        );
    """))

# 6. Formulario para añadir datos a la base de datos
st.subheader("📝 Añadir un nuevo registro")
with st.form("form_datos"):
    # Pre-rellenamos el nombre con el usuario actual
    nombre_usuario = st.text_input("Usuario que registra:", value=st.session_state.usuario_actual, disabled=True)
    comentario_usuario = st.text_area("Escribe aquí el comentario o registro operativo:")
    boton_enviar = st.form_submit_button("Guardar en Base de Datos")

    if boton_enviar and comentario_usuario:
        with engine.begin() as conn:
            query = text("INSERT INTO registros (nombre, comentario) VALUES (:nombre, :comentario)")
            conn.execute(query, {"nombre": nombre_usuario, "comentario": comentario_usuario})
        st.success("✅ ¡Datos guardados correctamente!")

# 7. Mostrar la tabla con los datos guardados
st.subheader("📊 Registros del Servicio")
try:
    df = pd.read_sql("SELECT * FROM registros ORDER BY fecha DESC", con=engine)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros todavía en la base de datos.")
except Exception as e:
    st.error(f"Error al leer los datos de PostgreSQL: {e}")
