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
NUM_MESES = 24  # Altere este valor para mudar o número de meses analisados

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

def obter_codigo_por_nome(lista, chave_nome):
    for item in lista:
        if chave_nome.lower() in item['name'].lower():
            return item['code']
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
    for ref in referencias[:NUM_MESES + 1]:  # +1 para calcular a variação inicial
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

    seta = "⬆️" if variacao_mensal > 0 else "⬇️"
    cor_seta = "green" if variacao_mensal > 0 else "red"

    col1, col2 = st.columns([1.3, 3], gap="large")
    with col1:
        st.markdown("### 💰 Preço Atual")
        st.markdown(f"""
            <div style="font-size:30px; font-weight:bold">R$ {preco_atual:,.2f}</div>
            <div style="color:{cor_seta}; font-size:18px;">{seta} {variacao_mensal:+,.2f}</div>
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
                if not referencias or len(referencias) < NUM_MESES + 1:
                    st.warning("⚠️ Referências insuficientes.")
                    st.stop()

                historico = []
                for ref in referencias[:NUM_MESES + 1]:
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
                    df = df.iloc[1:].reset_index(drop=True)

                    exibir_historico(df)

                    df_exibir = df.copy()
                    df_exibir["Preço (R$)"] = df_exibir["Preço (R$)"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_exibir["Variação (R$)"] = df_exibir["Variação (R$)"].apply(lambda x: f"{x:+.2f}".replace(".", ","))
                    st.markdown("### 📋 Histórico Completo")
                    st.dataframe(df_exibir[["Mês", "Preço (R$)", "Variação (R$)"]], use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Nenhum histórico de preço disponível para esse veículo.")

    st.markdown("---")
    st.markdown("### 🔒 Histórico de Preço - Veículos Fixos")
    veiculos_fixos = [
        ("Toyota", "Corolla ALTIS/A.Premiu. 2.0 Flex 16V Aut", 2012),
        ("Nissan", "Sentra SL 2.0/ 2.0 Flex Fuel 16V Aut.", 2016),
        ("Hyundai", "ix35 2.0 16V 170cv 2WD/4WD Aut.", 2012),
        ("Kia Motors", "Sportage EX 2.0 16V/ 2.0 16V Flex Aut.", 2012),
    ]
    for marca, modelo, ano in veiculos_fixos:
        st.markdown(f"#### 🔧 {marca} - {modelo} ({ano})")
        historico_df = obter_historico_veiculo(marca, modelo, ano)
        if historico_df is not None:
            exibir_historico(historico_df)
        else:
            st.warning("❌ Não foi possível obter o histórico.")

if __name__ == "__main__":
    main()
