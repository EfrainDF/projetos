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
NUM_MESES = 24

# Lista de veículos fixos
VEICULOS_FIXOS = [
    ("Toyota", "Corolla XEi 2.0 Flex 16V Aut.", 2012),
    ("Nissan", "Sentra SL 2.0/ 2.0 Flex Fuel 16V Aut.", 2016),
    ("Hyundai", "ix35 2.0 16V 170cv 2WD/4WD Aut.", 2012),
    ("Kia Motors", "Sportage EX 2.0 16V/ 2.0 16V Flex Aut.", 2012),
    ("Kia Motors", "Sorento 3.5 V6 24V 4x2 Aut.", 2013),
    ("Hyundai", "Santa Fe GLS 3.5 V6 4x4 Tiptronic", 2013),
]

# Requisição de dados

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
    principais = [m for m in marcas if any(p.lower() in m['name'].lower() for p in prioridades)]
    demais = [m for m in marcas if m not in principais]
    return principais + sorted(demais, key=lambda x: x['name'])

def obter_codigo_por_nome(lista, chave_nome):
    for item in lista:
        if chave_nome.lower() in item['name'].lower():
            return item['code']
    return None

def consultar_preco_por_referencia(cod_marca, cod_modelo, cod_ano, ref_code):
    url = f"{URL_BASE}/cars/brands/{cod_marca}/models/{cod_modelo}/years/{cod_ano}"
    params = {"reference": ref_code}
    resposta = requests.get(url, headers=HEADERS, params=params)
    if resposta.status_code == 200:
        dados = resposta.json()
        return dados.get("price", None)
    return None

def obter_historico_veiculo(marca, modelo_nome, ano_str):
    marcas = requisitar_dados("cars/brands")
    cod_marca = obter_codigo_por_nome(marcas, marca)
    if not cod_marca:
        return None

    modelos = requisitar_dados(f"cars/brands/{cod_marca}/models")
    cod_modelo = obter_codigo_por_nome(modelos, modelo_nome)
    if not cod_modelo:
        return None

    anos = requisitar_dados(f"cars/brands/{cod_marca}/models/{cod_modelo}/years")
    cod_ano = obter_codigo_por_nome(anos, str(ano_str))
    if not cod_ano:
        return None

    referencias = requisitar_dados("references")
    historico = []
    for ref in referencias[:NUM_MESES + 1]:
        ref_code = ref["code"]
        preco_str = consultar_preco_por_referencia(cod_marca, cod_modelo, cod_ano, ref_code)
        if preco_str:
            try:
                preco = float(preco_str.replace("R$", "").replace(".", "").replace(",", "."))
                historico.append({
                    "Mês": ref["month"],
                    "Preço (R$)": preco
                })
            except:
                continue
    if len(historico) < 2:
        return None
    df = pd.DataFrame(historico).sort_index(ascending=False).reset_index(drop=True)
    df["Variação (R$)"] = df["Preço (R$)"].diff()
    df = df.iloc[1:].reset_index(drop=True)
    return df

def exibir_historico(df):
    preco_atual = df["Preço (R$)"].iloc[-1]
    preco_anterior = df["Preço (R$)"].iloc[-2]
    preco_mais_antigo = df["Preço (R$)"].iloc[0]
    variacao_mensal = preco_atual - preco_anterior
    variacao_total = preco_atual - preco_mais_antigo
    variacao_percentual = ((preco_atual - preco_anterior) / preco_anterior) * 100

    seta = "⬆️" if variacao_mensal > 0 else "⬇️"
    cor_seta = "green" if variacao_mensal > 0 else "red"

    col1, col2 = st.columns([1.3, 3], gap="large")
    with col1:
        st.markdown("### 💰 Preço Atual")
        st.markdown(f"""
            <div style="font-size:30px; font-weight:bold">R$ {preco_atual:,.2f}</div>
            <div style="color:{cor_seta}; font-size:18px;">{seta} {variacao_percentual:+.2f}% em 1 mês</div>
            <div style="color:gray; font-size:16px;">📊 Acumulado em {NUM_MESES} meses: R$ {variacao_total:+,.2f}</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 📈 Evolução dos Preços")
        fig = px.line(df, x="Mês", y="Preço (R$)", markers=True, title=f"Histórico de Preços FIPE – Últimos {NUM_MESES} meses")
        fig.update_layout(
            xaxis_title="Mês de Referência",
            yaxis_title="Preço (R$)",
            yaxis_range=[df["Preço (R$)"].min() * 0.75, df["Preço (R$)"].max() * 1.25],
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.set_page_config(page_title="FIPE – Histórico de Preço", layout="wide")
    st.title(f"🚗 Consulta Tabela FIPE – Últimos {NUM_MESES} Meses")

    marcas = requisitar_dados("cars/brands") or []
    marcas = ordenar_marcas_por_relevancia(marcas)

    nome_marca = st.selectbox("Marca", [""] + [m['name'] for m in marcas], index=0)
    veiculos_comparacao = []

    if nome_marca:
        cod_marca = obter_codigo_por_nome(marcas, nome_marca)
        modelos = requisitar_dados(f"cars/brands/{cod_marca}/models") or []
        nome_modelo = st.selectbox("Modelo", [""] + [m['name'] for m in modelos], index=0)

        if nome_modelo:
            cod_modelo = obter_codigo_por_nome(modelos, nome_modelo)
            anos = requisitar_dados(f"cars/brands/{cod_marca}/models/{cod_modelo}/years") or []
            ano_escolhido = st.selectbox("Ano", [""] + [a['name'] for a in anos], index=0)

            if ano_escolhido:
                st.markdown("---")
                df_custom = obter_historico_veiculo(nome_marca, nome_modelo, ano_escolhido)
                if df_custom is not None:
                    veiculos_comparacao.append((f"🔎 {nome_marca} {nome_modelo} ({ano_escolhido})", df_custom))
                    exibir_historico(df_custom)
                else:
                    st.warning("❌ Não foi possível obter o histórico para o veículo selecionado.")

    st.markdown("---")
    st.markdown("### 🔒 Histórico de Preço - Veículos Fixos")

    for marca, modelo, ano in VEICULOS_FIXOS:
        st.markdown(f"#### 🚘 {marca} - {modelo} ({ano})")
        df_hist = obter_historico_veiculo(marca, modelo, ano)
        if df_hist is not None:
            veiculos_comparacao.append((f"{marca} {modelo} ({ano})", df_hist))
            exibir_historico(df_hist)
        else:
            st.warning("❌ Não foi possível obter o histórico.")

    if veiculos_comparacao:
        st.markdown("---")
        st.markdown("### 📊 Comparativo Final – Valorização Acumulada")

        comparativo = []
        for nome, df in veiculos_comparacao:
            preco_inicial = df["Preço (R$)"].iloc[0]
            preco_final = df["Preço (R$)"].iloc[-1]
            variacao = preco_final - preco_inicial
            percentual = (variacao / preco_inicial) * 100
            comparativo.append({
                "Veículo": nome,
                "Variação (R$)": round(variacao, 2),
                "Variação (%)": round(percentual, 2)
            })

        df_comp = pd.DataFrame(comparativo).sort_values("Variação (%)", ascending=False)
        fig_final = px.bar(
            df_comp,
            x="Veículo",
            y="Variação (%)",
            color="Variação (%)",
            color_continuous_scale=["red", "orange", "yellow", "green"],
            title="Comparativo Geral de Valorização – Últimos 24 meses"
        )
        fig_final.update_layout(xaxis_title="", yaxis_title="Variação (%)", height=500)
        st.plotly_chart(fig_final, use_container_width=True)

if __name__ == "__main__":
    main()
