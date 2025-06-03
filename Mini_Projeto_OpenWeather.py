import os
import requests
import dotenv
import streamlit as st


def requisitar_dados(url, parametros=None):
    try:
        resposta = requests.get(url, params=parametros)
        resposta.raise_for_status()
        return resposta.json()
    except requests.HTTPError as erro:
        print(f"[ERRO] Não foi possível obter os dados: {erro}")
        return None

def pegar_tempo_para_local(local):
    dotenv.load_dotenv()
    token = os.environ["CHAVE_API_OPENWEATHER"]
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'appid': token,
        'q': local,
        'units': 'metric',
        'lang': 'pt_br'
    }
    return requisitar_dados(url, params)

def main():
    st.title('🌦️ Web App Tempo')
    st.write('Fonte dos dados: [OpenWeather](https://openweathermap.org/current)')

    local = st.text_input('📍 Digite uma cidade:')
    if not local:
        st.stop()

    dados_tempo = pegar_tempo_para_local(local)
    if not dados_tempo:
        st.warning(f'Dados não encontrados para a cidade "{local}".')
        st.stop()

    st.success(f"☁️ Clima atual em **{dados_tempo['name']}**")
    st.write(f"**Temperatura:** {dados_tempo['main']['temp']}°C")
    st.write(f"**Sensação térmica:** {dados_tempo['main']['feels_like']}°C")
    st.write(f"**Descrição:** {dados_tempo['weather'][0]['description'].capitalize()}")
    st.write(f"**Umidade:** {dados_tempo['main']['humidity']}%")
    st.write(f"**Vento:** {dados_tempo['wind']['speed']} m/s")

if __name__ == '__main__':
    main()
