
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud import firestore
from google.oauth2 import service_account
import json

key_dict = json.loads(st.secrets["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project="names-project-demo")


@st.cache_data
def load_movies():
    try:
        docs = db.collection('movies').limit(3).stream()
        data = [doc.to_dict() for doc in docs]
        if not data:
            st.warning("La colección 'movies' está vacía o no tienes permisos de lectura.")
        return pd.DataFrame(data)
    except Exception as e:
        import traceback
        st.error(f"Error al leer de Firestore: {e}")
        st.text(traceback.format_exc())
        return pd.DataFrame([])

movies_df = load_movies()

st.sidebar.header("🎬 Dashboard de Filmes")

# Checkbox para mostrar todos los filmes
show_all = st.sidebar.checkbox("Mostrar todos los filmes")
if show_all:
    st.header("Todos los filmes")
    st.dataframe(movies_df)

# Buscar por título (case insensitive, contains)
st.sidebar.subheader("Buscar por título")
search_title = st.sidebar.text_input("Título:")
btn_search = st.sidebar.button("Buscar por título")

if btn_search and search_title:
    # Filtrado insensible a mayúsculas/minúsculas
    mask = movies_df['title'].str.lower().str.contains(search_title.lower(), na=False)
    results = movies_df[mask]
    st.header(f" Resultados de búsqueda para '{search_title}'")
    st.write(f"Total de filmes encontrados: {results.shape[0]}")
    st.dataframe(results)

# Filtrar por director
st.sidebar.subheader("Filtrar por director")
directors = sorted(movies_df['director'].dropna().unique())
selected_director = st.sidebar.selectbox("Selecciona director:", directors)
btn_filter_director = st.sidebar.button("Filtrar por director")

if btn_filter_director and selected_director:
    director_films = movies_df[movies_df['director'] == selected_director]
    st.header(f"Filmes dirigidos por {selected_director}")
    st.write(f"Total de filmes: {director_films.shape[0]}")
    st.dataframe(director_films)


st.sidebar.markdown("---")
st.sidebar.header("Agregar nuevo filme")

with st.sidebar.form("add_movie_form"):
    new_title = st.text_input("Título del filme", key="new_title")
    new_year = st.text_input("Año", key="new_year")
    new_director = st.text_input("Director", key="new_director")
    new_genre = st.text_input("Género", key="new_genre")
    submitted = st.form_submit_button("Agregar filme")

    if submitted:
        if new_title and new_year and new_director and new_genre:
            # Crea el registro como dict
            new_movie = {
                "title": new_title,
                "year": new_year,
                "director": new_director,
                "genre": new_genre
            }
            # Agrega a Firestore
            db.collection('movies').add(new_movie)
            st.success("Filme agregado correctamente.")
        else:
            st.error("¡Por favor, llena todos los campos!")
