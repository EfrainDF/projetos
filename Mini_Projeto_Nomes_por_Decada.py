import requests
import streamlit as st
import pandas as pd


def fazer_request(url, parametros=None):
    try:
        resposta = requests.get(url, params=parametros)
        resposta.raise_for_status()
        return resposta.json()
    except requests.HTTPError as erro:
        st.error(f"Erro na requisição: {erro}")
        return None


def obter_dados_por_decadas(nome):
    url = f'https://servicodados.ibge.gov.br/api/v2/censos/nomes/{nome.lower()}'
    dados = fazer_request(url)
    if not dados:
        return []
    return dados[0]['res']


def main():
    st.set_page_config(page_title="Frequência de Nomes por Década", layout="wide")

    st.title("📊 Frequência de Nomes por Década")
    st.markdown(
        "Consulta baseada na [API do IBGE](https://servicodados.ibge.gov.br/api/docs/nomes?versao=2) "
        "com dados estatísticos por década sobre nomes próprios."
    )

    nome = st.text_input("Digite um nome para consultar:", placeholder="Ex: Rafael")

    if nome:
        dados = obter_dados_por_decadas(nome)

        if not dados:
            st.warning("⚠️ Nenhum dado encontrado para o nome informado.")
        else:
            df = pd.DataFrame(dados)
            df.columns = ['Década', 'Frequência']
            df['Frequência'] = df['Frequência'].astype(int)
            df['Frequência'] = df['Frequência'].apply(lambda x: f"{x:,}".replace(",", "."))

            # Layout com colunas ajustadas
            col1, col2 = st.columns([1, 1.3])

            with col1:
                st.subheader("📄 Tabela por Década")
                st.table(df)

            with col2:
                st.subheader("📈 Gráfico de Linha")
                st.line_chart(data=pd.DataFrame(dados).set_index('periodo'), use_container_width=True, height=300)

    else:
        st.info("Digite um nome acima para iniciar a consulta.")


if __name__ == '__main__':
    main()
