
import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import json
import time

st.set_page_config(page_title="Movies Dashboard", page_icon="🎬", layout="wide")

# ---- Autenticación via Secrets (Streamlit Cloud) ----
# En Settings > Secrets define:
# textkey = """
# { ... TU JSON COMPLETO DE SERVICE ACCOUNT ... }
# """
key_dict = json.loads(st.secrets["textkey"])
project_id = key_dict["project_id"]  # <-- Toma el proyecto correcto del JSON
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project=project_id)

# ---- Diagnóstico rápido de conexión (sidebar) ----
with st.sidebar:
    st.header("⚙️ Estado")
    try:
        it = db.collection("movies").limit(1).stream()
        ok = any(True for _ in it)
        st.success("Conexión a Firestore OK")
        if not ok:
            st.info("Colección 'movies' vacía.")
    except Exception as e:
        st.error(f"Fallo conexión Firestore: {e}")

# ---- Carga de datos con cache y límite opcional ----
@st.cache_data(ttl=300)  # refresca cada 5 minutos
def load_movies(limit=None):
    try:
        ref = db.collection('movies')
        if limit:
            docs = ref.limit(limit).stream()
        else:
            docs = ref.stream()
        data = [doc.to_dict() for doc in docs]
        df = pd.DataFrame(data)
        # Normaliza columnas esperadas
        for col in ["title", "year", "director", "genre"]:
            if col not in df.columns:
                df[col] = pd.NA
        return df
    except Exception as e:
        # Muestra error en UI pero devuelve DF vacío para que el app no se caiga
        st.error(f"Error al leer de Firestore: {e}")
        return pd.DataFrame(columns=["title", "year", "director", "genre"])

# Carga inicial (usa límite si tu colección es muy grande)
movies_df = load_movies(limit=None)

st.title("🎬 Movies Dashboard")

# ---- Mostrar todos (opcional) ----
with st.sidebar:
    st.header("Panel")
    show_all = st.checkbox("Mostrar todos los filmes")

if show_all:
    st.subheader("Todos los filmes")
    st.dataframe(movies_df, use_container_width=True)

# ---- Buscar por título (case-insensitive, contains) ----
with st.sidebar:
    st.subheader("Buscar por título")
    search_title = st.text_input("Título:")
    btn_search = st.button("Buscar por título")

if btn_search and search_title:
    mask = movies_df["title"].astype(str).str.lower().str.contains(search_title.lower(), na=False)
    results = movies_df[mask]
    st.subheader(f"Resultados de búsqueda para '{search_title}'")
    st.write(f"Total de filmes encontrados: {results.shape[0]}")
    st.dataframe(results, use_container_width=True)

# ---- Filtrar por director ----
with st.sidebar:
    st.subheader("Filtrar por director")
    if "director" in movies_df.columns and not movies_df.empty:
        directors = sorted(movies_df["director"].dropna().astype(str).unique())
    else:
        directors = []
    selected_director = st.selectbox("Selecciona director:", directors) if directors else None
    btn_filter_director = st.button("Filtrar por director")

if btn_filter_director and selected_director:
    director_films = movies_df[movies_df["director"].astype(str) == str(selected_director)]
    st.subheader(f"Filmes dirigidos por {selected_director}")
    st.write(f"Total de filmes: {director_films.shape[0]}")
    st.dataframe(director_films, use_container_width=True)

# ---- Alta de nuevo filme (sidebar form) ----
with st.sidebar:
    st.markdown("---")
    st.header("Agregar nuevo filme")
    with st.form("add_movie_form"):
        new_title = st.text_input("Título del filme", key="new_title")
        new_year = st.text_input("Año", key="new_year")
        new_director = st.text_input("Director", key="new_director")
        new_genre = st.text_input("Género", key="new_genre")
        submitted = st.form_submit_button("Agregar filme")

        if submitted:
            if new_title and new_year and new_director and new_genre:
                new_movie = {
                    "title": new_title,
                    "year": new_year,
                    "director": new_director,
                    "genre": new_genre,
                    "created_at": int(time.time())
                }
                try:
                    db.collection('movies').add(new_movie)
                    st.success("Filme agregado correctamente.")
                    st.cache_data.clear()   # refresca el dataset en la próxima lectura
                except Exception as e:
                    st.error(f"No se pudo insertar: {e}")
            else:
                st.error("¡Por favor, llena todos los campos!")
