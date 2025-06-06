import os
import requests
import dotenv
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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
                    "Referência": ref_code,
                    "Mês": ref["month"],
                    "Preço (R$)": preco
                })
            except:
                continue
    if len(historico) < 2:
        return None
    df = pd.DataFrame(historico).sort_values("Referência").reset_index(drop=True)
    df["Variação (R$)"] = df["Preço (R$)"].diff()
    df["Variação (%)"] = (df["Preço (R$)"] / df["Preço (R$)"].shift(1) - 1) * 100
    df = df.iloc[1:].reset_index(drop=True)
    return df


def calcular_variacao_percentual(df):
    if len(df) < 2:
        return None
    preco_inicial = df["Preço (R$)"].iloc[0]
    preco_final = df["Preço (R$)"].iloc[-1]
    return (preco_final - preco_inicial) / preco_inicial * 100


def exibir_historico(df, veiculo_nome=None):
    preco_atual = df["Preço (R$)"].iloc[-1]
    preco_anterior = df["Preço (R$)"].iloc[-2]
    preco_mais_antigo = df["Preço (R$)"].iloc[0]
    variacao_mensal = preco_atual - preco_anterior
    variacao_mensal_perc = (preco_atual / preco_anterior - 1) * 100
    variacao_total = preco_atual - preco_mais_antigo
    variacao_total_perc = (preco_atual / preco_mais_antigo - 1) * 100

    seta = "⬆️" if variacao_mensal > 0 else "⬇️"
    cor_seta = "green" if variacao_mensal > 0 else "red"

    col1, col2 = st.columns([1.3, 3], gap="large")
    with col1:
        st.markdown("### 💰 Preço Atual")
        st.markdown(f"""
            <div style="font-size:30px; font-weight:bold">R$ {preco_atual:,.2f}</div>
            <div style="color:{cor_seta}; font-size:18px;">{seta} {variacao_mensal:+,.2f} ({variacao_mensal_perc:+.2f}%) <span style="color:gray; font-size:14px;">(último mês)</span></div>
            <div style="color:gray; font-size:16px;">📊 Acumulado em {NUM_MESES} meses: R$ {variacao_total:+,.2f} ({variacao_total_perc:+.2f}%)</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 📈 Evolução dos Preços")
        fig = px.line(df, x="Mês", y="Preço (R$)", markers=True,
                      title=f"Histórico de Preços FIPE – Últimos {NUM_MESES} meses" + (
                          f" - {veiculo_nome}" if veiculo_nome else ""))
        fig.update_layout(
            xaxis_title="Mês de Referência",
            yaxis_title="Preço (R$)",
            yaxis_range=[df["Preço (R$)"].min() * 0.75, df["Preço (R$)"].max() * 1.25],
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)


def exibir_comparacao_veiculos(veiculos_comparacao, df_veiculo_buscado, veiculo_buscado_nome):
    if not veiculos_comparacao or df_veiculo_buscado is None:
        return

    # Calcular variação percentual para todos os veículos
    variacoes = []
    for nome, df in veiculos_comparacao:
        variacao = calcular_variacao_percentual(df)
        if variacao is not None:
            variacoes.append((nome, variacao))

    # Adicionar o veículo buscado à comparação (com lupa)
    variacao_buscado = calcular_variacao_percentual(df_veiculo_buscado)
    if variacao_buscado is not None:
        variacoes.append((f"🔍 {veiculo_buscado_nome}", variacao_buscado))  # Alteração aqui

    if not variacoes:
        return

    # Criar DataFrame para o gráfico
    df_comparacao = pd.DataFrame(variacoes, columns=["Veículo", "Variação (%)"])
    df_comparacao = df_comparacao.sort_values("Variação (%)", ascending=False)

    # Criar gráfico de barras
    fig = go.Figure()

    for i, row in df_comparacao.iterrows():
        cor = "green" if row["Variação (%)"] >= 0 else "red"
        fig.add_trace(go.Bar(
            x=[row["Veículo"]],
            y=[row["Variação (%)"]],
            name=row["Veículo"],
            marker_color=cor,
            text=[f"{row['Variação (%)']:.2f}%"],
            textposition='auto'
        ))

    fig.update_layout(
        title=f"Comparação de Valorização/Desvalorização nos Últimos {NUM_MESES} Meses",
        xaxis_title="Veículo",
        yaxis_title="Variação Percentual (%)",
        showlegend=False,
        hovermode="x"
    )

    st.markdown("### 📊 Comparação com Veículos de Referência")
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

    veiculos_fixos = [
        ("Toyota Corolla XEi 2.0 Flex (2012)", "Toyota", "Corolla XEi 2.0 Flex 16V Aut.", 2012),
        ("Nissan Sentra SL 2.0 Flex (2016)", "Nissan", "Sentra SL 2.0/ 2.0 Flex Fuel 16V Aut.", 2016),
        ("Hyundai ix35 GLS 2.0 Flex (2012)", "Hyundai", "ix35 GLS 2.0 16V 2WD Flex Aut.", 2012),
        ("Hyundai Santa Fe 3.3 V6 (2012)", "Hyundai", "Santa Fe/GLS 3.3 V6 4X4 Tiptronic", 2012),
        ("Kia Sportage EX 2.0 Flex (2012)", "Kia Motors", "Sportage EX 2.0 16V/ 2.0 16V Flex Aut.", 2012),
        ("Kia Sorento 3.5 V6 (2012)", "Kia Motors", "Sorento 3.5 V6 24V 4x2 Aut.", 2012),
    ]

    df_veiculo_buscado = None
    veiculo_buscado_nome = None

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
                veiculo_buscado_nome = f"{marca_escolhida.split(' (')[0]} {modelo_selecionado} ({ano_escolhido.split(' ')[0]})"
                df_veiculo_buscado = obter_historico_veiculo(
                    marca_escolhida.split(' (')[0],
                    modelo_selecionado,
                    ano_escolhido.split(' ')[0]
                )

                if df_veiculo_buscado is not None:
                    exibir_historico(df_veiculo_buscado, veiculo_buscado_nome)
                else:
                    st.warning("⚠️ Nenhum histórico de preço disponível para esse veículo.")

    # Obter históricos dos veículos fixos para comparação
    veiculos_comparacao = []
    for nome, marca, modelo, ano in veiculos_fixos:
        df = obter_historico_veiculo(marca, modelo, ano)
        if df is not None:
            veiculos_comparacao.append((nome, df))

    # Exibir comparação mesmo sem veículo buscado
    if veiculos_comparacao:
        if df_veiculo_buscado is not None:
            exibir_comparacao_veiculos(veiculos_comparacao, df_veiculo_buscado, veiculo_buscado_nome)
        else:
            st.markdown("### 📊 Comparação de Veículos de Referência")

            variacoes = []
            for nome, df in veiculos_comparacao:
                variacao = calcular_variacao_percentual(df)
                if variacao is not None:
                    variacoes.append((nome, variacao))

            if variacoes:
                df_comparacao = pd.DataFrame(variacoes, columns=["Veículo", "Variação (%)"])
                df_comparacao = df_comparacao.sort_values("Variação (%)", ascending=False)

                fig = go.Figure()
                for i, row in df_comparacao.iterrows():
                    cor = "green" if row["Variação (%)"] >= 0 else "red"
                    fig.add_trace(go.Bar(
                        x=[row["Veículo"]],
                        y=[row["Variação (%)"]],
                        name=row["Veículo"],
                        marker_color=cor,
                        text=[f"{row['Variação (%)']:.2f}%"],
                        textposition='auto'
                    ))

                fig.update_layout(
                    title=f"Valorização/Desvalorização nos Últimos {NUM_MESES} Meses",
                    xaxis_title="Veículo",
                    yaxis_title="Variação Percentual (%)",
                    showlegend=False,
                    hovermode="x"
                )
                st.plotly_chart(fig, use_container_width=True)

    # Seção dos veículos fixos (que estava faltando)
    st.markdown("---")
    st.markdown("### 🔍 Veículos de Referência (Histórico Completo)")
    for nome, marca, modelo, ano in veiculos_fixos:
        st.markdown(f"#### 🔧 {nome}")
        historico_df = obter_historico_veiculo(marca, modelo, ano)
        if historico_df is not None:
            exibir_historico(historico_df, nome)
        else:
            st.warning("❌ Não foi possível obter o histórico.")


if __name__ == "__main__":
    main()