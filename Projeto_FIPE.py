import os
import requests
import dotenv
import pandas as pd
import streamlit as st
import plotly.express as px

# Carrega a chave da API
dotenv.load_dotenv()
TOKEN = os.getenv("CHAVE_API_FIPE")

HEADERS = {
    "accept": "application/json",
    "X-Subscription-Token": TOKEN
}
URL_BASE = "https://fipe.parallelum.com.br/api/v2"

def requisitar_dados(endpoint, parametros=None):
    try:
        resposta = requests.get(f"{URL_BASE}/{endpoint}", headers=HEADERS, params=parametros)
        resposta.raise_for_status()
        return resposta.json()
    except requests.HTTPError:
        return None

def ordenar_marcas_por_relevancia(marcas):
    prioridades = [
        "VolksWagen", "Fiat", "Chevrolet", "Toyota", "Ford", "Honda",
        "Hyundai", "Renault", "Nissan", "Jeep", "Peugeot", "Citroën", "Mitsubishi"
    ]
    principais = [m for m in marcas if any(p in m['name'] for p in prioridades)]
    demais = [m for m in marcas if m not in principais]
    return principais + sorted(demais, key=lambda x: x['name'])

def consultar_preco_por_referencia(cod_marca, cod_modelo, cod_ano, ref_code):
    url = f"{URL_BASE}/cars/brands/{cod_marca}/models/{cod_modelo}/years/{cod_ano}"
    params = {"reference": ref_code}
    resposta = requests.get(url, headers=HEADERS, params=params)
    if resposta.status_code == 200:
        dados = resposta.json()
        return dados.get("price", None)
    return None

def main():
    st.set_page_config(page_title="FIPE – Histórico de Preço", layout="wide")
    st.title("🚗 Consulta Tabela FIPE – Últimos 6 Meses")

    marcas = requisitar_dados("cars/brands")
    if not marcas:
        st.stop()

    marcas_ordenadas = ordenar_marcas_por_relevancia(marcas)
    nome_para_codigo = {f"{m['name']} (cód: {m['code']})": m['code'] for m in marcas_ordenadas}
    marca_escolhida = st.selectbox("📌 Selecione uma marca:", [""] + list(nome_para_codigo.keys()), index=0)

    if marca_escolhida:
        cod_marca = nome_para_codigo[marca_escolhida]
        modelos = requisitar_dados(f"cars/brands/{cod_marca}/models")
        if not modelos:
            st.warning("⚠️ Nenhum modelo disponível para esta marca.")
            st.stop()

        modelos_ordenados = sorted(modelos, key=lambda x: x['name'])
        nome_para_modelo = {m["name"]: m["code"] for m in modelos_ordenados}
        modelo_selecionado = st.selectbox("📋 Selecione o modelo:", [""] + list(nome_para_modelo.keys()), index=0)

        if modelo_selecionado:
            cod_modelo = nome_para_modelo[modelo_selecionado]
            anos = requisitar_dados(f"cars/brands/{cod_marca}/models/{cod_modelo}/years")
            if not anos:
                st.warning("⚠️ Nenhum ano disponível para este modelo.")
                st.stop()

            nome_para_ano = {a["name"]: a["code"] for a in anos}
            ano_escolhido = st.selectbox("📅 Selecione o ano:", [""] + list(nome_para_ano.keys()), index=0)

            if ano_escolhido:
                cod_ano = nome_para_ano[ano_escolhido]
                referencias = requisitar_dados("references")
                if not referencias or len(referencias) < 7:
                    st.warning("⚠️ Referências insuficientes.")
                    st.stop()

                historico = []
                for ref in referencias[:7]:  # Inclui o 7º mês para cálculo da 1ª variação
                    ref_code = ref["code"]
                    mes_nome = ref["month"]
                    preco_str = consultar_preco_por_referencia(cod_marca, cod_modelo, cod_ano, ref_code)
                    if preco_str:
                        try:
                            preco = float(preco_str.replace("R$", "").replace(".", "").replace(",", "."))
                            historico.append({
                                "Referência": ref_code,
                                "Mês": mes_nome,
                                "Preço (R$)": preco
                            })
                        except:
                            continue

                if len(historico) >= 2:
                    df = pd.DataFrame(historico)
                    df = df.sort_values("Referência").reset_index(drop=True)
                    df["Variação (R$)"] = df["Preço (R$)"].diff()
                    df = df.iloc[1:].reset_index(drop=True)  # Remove o 7º mês

                    preco_atual = df["Preço (R$)"].iloc[-1]
                    preco_anterior = df["Preço (R$)"].iloc[-2] if len(df) > 1 else preco_atual
                    variacao = preco_atual - preco_anterior
                    seta = "⬆️" if variacao > 0 else "⬇️"
                    cor_seta = "green" if variacao > 0 else "red"

                    col1, col2 = st.columns([1.3, 3], gap="large")
                    with col1:
                        st.markdown("### 💰 Preço Atual")
                        st.markdown(f"""
                            <div style="font-size:30px; font-weight:bold">R$ {preco_atual:,.2f}</div>
                            <div style="color:{cor_seta}; font-size:18px;">{seta} {variacao:+,.2f}</div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown("### 📈 Evolução dos Preços")
                        fig = px.line(
                            df,
                            x="Mês",
                            y="Preço (R$)",
                            markers=True,
                            title="Histórico de Preços FIPE"
                        )
                        fig.update_layout(
                            xaxis_title="Mês de Referência",
                            yaxis_title="Preço (R$)",
                            yaxis_range=[
                                df["Preço (R$)"].min() * 0.75,
                                df["Preço (R$)"].max() * 1.25
                            ],
                            hovermode="x unified"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### 📋 Histórico dos Últimos 6 Meses")
                    df_exibir = df.copy()
                    df_exibir["Preço (R$)"] = df_exibir["Preço (R$)"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_exibir["Variação (R$)"] = df_exibir["Variação (R$)"].apply(lambda x: f"{x:+.2f}".replace(".", ","))
                    st.dataframe(df_exibir[["Mês", "Preço (R$)", "Variação (R$)"]],
                                 use_container_width=True, hide_index=True)

                else:
                    st.warning("⚠️ Nenhum histórico de preço disponível para esse veículo.")

if __name__ == "__main__":
    main()
