import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.title("🐘 Mi Aplicación con PostgreSQL y Streamlit")

# 1. Obtener la URL de la base de datos desde los Secrets de Streamlit
db_url = st.secrets["postgres"]["url"]

# 2. Crear el motor de conexión con SQLAlchemy
engine = create_engine(db_url)

# 3. Crear una tabla de prueba si no existe
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comentario TEXT
        );
    """))

st.subheader("📝 Añadir un nuevo registro")

# Formulario sencillo para insertar datos
with st.form("form_datos"):
    nombre_usuario = st.text_input("Tu nombre:")
    comentario_usuario = st.text_area("Escribe un comentario:")
    boton_enviar = st.form_submit_button("Guardar en la Base de Datos")

    if boton_enviar and nombre_usuario:
        # Insertar los datos en PostgreSQL de forma segura usando parámetros
        with engine.begin() as conn:
            query = text("INSERT INTO registros (nombre, comentario) VALUES (:nombre, :comentario)")
            conn.execute(query, {"nombre": nombre_usuario, "comentario": comentario_usuario})
        st.success("✅ ¡Datos guardados correctamente en PostgreSQL!")

st.divider()

st.subheader("📊 Registros actuales en la base de datos")

# 4. Leer los datos de la tabla usando Pandas para mostrarlos en una tabla interactiva
try:
    df = pd.read_sql("SELECT * FROM registros ORDER BY fecha DESC", con=engine)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros todavía. ¡Prueba a añadir el primero arriba!")
except Exception as e:
    st.error(f"Error al leer los datos: {e}")