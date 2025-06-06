import os
import requests
from requests.auth import HTTPBasicAuth
import dotenv
import streamlit as st

# Carrega variáveis do .env
dotenv.load_dotenv()

# 1️⃣ Autenticação
def autenticar():
    client_id = os.environ["CHAVE_API_SPOTIFY"]
    client_secret = os.environ["CHAVE_CLIENT_SECRET"]
    auth = HTTPBasicAuth(username=client_id, password=client_secret)
    url_token = "https://accounts.spotify.com/api/token"
    body = {"grant_type": "client_credentials"}
    resposta = requests.post(url=url_token, data=body, auth=auth)
    resposta.raise_for_status()
    return resposta.json()["access_token"]

# 2️⃣ Buscar múltiplos artistas parecidos
def buscar_artistas_parecidos(nome_artista, headers):
    url = "https://api.spotify.com/v1/search"
    params = {
        'q': nome_artista,
        "type": "artist",
        "limit": 5
    }
    resposta = requests.get(url, params=params, headers=headers)

    try:
        resposta.raise_for_status()
        return resposta.json()['artists']['items']
    except (requests.HTTPError, KeyError):
        return []

# 3️⃣ Buscar top músicas
def buscar_top_musicas(id_artista, headers, pais="BR"):
    url = f"https://api.spotify.com/v1/artists/{id_artista}/top-tracks"
    params = {"market": pais}
    resposta = requests.get(url, headers=headers, params=params)
    try:
        resposta.raise_for_status()
        return resposta.json()['tracks']
    except requests.HTTPError as erro:
        st.error(f"Erro ao buscar top músicas: {erro}")
        return []

# 4️⃣ Interface principal
def main():
    st.set_page_config(page_title="Spotify Top 10", page_icon="🎧")
    st.title("🎶 Web App - Top 10 Músicas no Spotify")
    st.caption("🔎 Dados via API: https://developer.spotify.com")

    nome_artista_busca = st.text_input("Digite o nome de um artista:")

    if nome_artista_busca:
        token = autenticar()
        HEADERS = {"Authorization": f"Bearer {token}"}

        lista_artistas = buscar_artistas_parecidos(nome_artista_busca, headers=HEADERS)

        if lista_artistas:
            nomes_exibicao = [
                f"{artista['name']} ({artista['followers']['total']} seguidores)"
                for artista in lista_artistas
            ]
            selecao = st.selectbox("Selecione o artista desejado:", nomes_exibicao)
            artista_escolhido = lista_artistas[nomes_exibicao.index(selecao)]

            nome_final = artista_escolhido["name"]
            id_artista = artista_escolhido["id"]
            imagem_artista = artista_escolhido["images"][0]["url"] if artista_escolhido["images"] else None

            st.success(f"🎤 Artista selecionado: {nome_final}")
            if imagem_artista:
                st.image(imagem_artista, width=200)

            top_musicas = buscar_top_musicas(id_artista, headers=HEADERS)

            st.markdown("### 🔥 Top 10 Músicas:")
            for i, musica in enumerate(top_musicas[:10], start=1):
                nome = musica["name"]
                popularidade = musica["popularity"]
                link = musica["external_urls"]["spotify"]
                preview = musica["preview_url"]

                st.markdown(f"**{i}. [{nome}]({link})** — Popularidade: `{popularidade}`")

                # Exibe capa apenas da 1ª música
                if i == 1 and musica["album"]["images"]:
                    capa = musica["album"]["images"][0]["url"]
                    st.image(capa, width=300, caption="🎵 Capa do álbum")

                if preview:
                    st.audio(preview)

                st.markdown("---")
        else:
            st.error("⚠️ Nenhum artista encontrado para a busca.")

if __name__ == "__main__":
    main()
