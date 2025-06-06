import requests
import streamlit as st
import pandas as pd
import difflib
import plotly.express as px
import time
time.sleep(1)  # espera 1 segundo entre chamadas


# --- CONFIG
URL_BASE = "http://veiculos.fipe.org.br/api/veiculos"
HEADERS = {
    "Host": "veiculos.fipe.org.br",
    "Referer": "http://veiculos.fipe.org.br",
    "Content-Type": "application/json"
}
NUM_MESES = 12

# --- Funções auxiliares
def requisita(endpoint, body):
    try:
        time.sleep(1)  # evitar excesso de chamadas
        resposta = requests.post(f"{URL_BASE}/{endpoint}", headers=HEADERS, json=body)
        resposta.raise_for_status()
        return resposta.json()
    except Exception as e:
        st.error(f"Erro na requisição: {e}")
        return None

def obter_tabela_referencia():
    return requisita("ConsultarTabelaDeReferencia", {})

def obter_marcas(cod_ref):
    return requisita("ConsultarMarcas", {"codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1})

def obter_modelos(cod_ref, cod_marca):
    return requisita("ConsultarModelos", {"codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1, "codigoMarca": cod_marca})

def obter_anos(cod_ref, cod_marca, cod_modelo):
    return requisita("ConsultarAnoModelo", {
        "codigoTabelaReferencia": cod_ref,
        "codigoTipoVeiculo": 1,
        "codigoMarca": cod_marca,
        "codigoModelo": cod_modelo
    })

def obter_valor(cod_ref, cod_marca, cod_modelo, ano):
    ano_modelo, tipo_comb = ano.split("-")
    return requisita("ConsultarValorComTodosParametros", {
        "codigoTabelaReferencia": cod_ref,
        "codigoTipoVeiculo": 1,
        "codigoMarca": cod_marca,
        "ano": ano,
        "codigoTipoCombustivel": int(tipo_comb),
        "anoModelo": int(ano_modelo),
        "codigoModelo": cod_modelo,
        "tipoConsulta": "tradicional"
    })

def encontrar_modelo_aproximado(nome_desejado, lista_modelos):
    nomes_api = [m["Label"] for m in lista_modelos]
    correspondencias = difflib.get_close_matches(nome_desejado, nomes_api, n=1, cutoff=0.6)
    if correspondencias:
        for modelo in lista_modelos:
            if modelo["Label"] == correspondencias[0]:
                return modelo["Value"], modelo["Label"]
    return None, None

def coletar_historico(cod_marca, cod_modelo, ano, refs):
    historico = []
    for ref in refs[:NUM_MESES]:
        ano_modelo, tipo_comb = ano.split("-")
        valor = obter_valor(ref["Codigo"], cod_marca, cod_modelo, ano)
        if valor:
            try:
                preco = float(valor['Valor'].replace("R$", "").replace(".", "").replace(",", "."))
                historico.append({"Mês": ref["Mes"], "Preço (R$)": preco})
            except:
                continue
    return pd.DataFrame(historico[::-1])

# --- Veículos fixos
VEICULOS_FIXOS = [
    ("Toyota", "Corolla XEi 2.0 Flex 16V Aut.", 2012),
    ("Honda", "Civic Sed. LXL/ LXL SE 1.8 Flex 16V Aut.", 2013),
    ("Nissan", "Sentra SL 2.0/ 2.0 Flex Fuel 16V Aut.", 2016),
    ("Hyundai", "ix35 GLS 2.0 16V 2WD Flex Aut.", 2012),
    ("Kia Motors", "Sportage EX 2.0 16V/ 2.0 16V Flex Aut.", 2012),
    ("Kia Motors", "Sorento 3.5 V6 24V 4x2 Aut.", 2013),
    ("Hyundai", "Santa Fe GLS 3.5 V6 4x4 Tiptronic", 2013),
]

# --- Streamlit App
st.set_page_config("FIPE – Projeto Paralelo", layout="wide")
st.title("🔎 FIPE – Projeto Paralelo com API Alternativa")

refs = obter_tabela_referencia()
if not refs:
    st.stop()
cod_ref = refs[0]["Codigo"]
st.success(f"🔢 Tabela de Referência: {refs[0]['Mes'].strip()} (código {cod_ref})")

marcas = obter_marcas(cod_ref)
if not marcas:
    st.stop()

veiculos_graficos = []
for marca_nome, modelo_nome, ano in VEICULOS_FIXOS:
    marca = next((m for m in marcas if m["Label"].lower() == marca_nome.lower()), None)
    if not marca:
        continue
    modelos_data = obter_modelos(cod_ref, marca["Value"])
    if not modelos_data:
        continue
    cod_modelo, modelo_api = encontrar_modelo_aproximado(modelo_nome, modelos_data["Modelos"])
    if not cod_modelo:
        continue
    anos = obter_anos(cod_ref, marca["Value"], cod_modelo)
    if not anos:
        continue
    ano_cod = next((a["Value"] for a in anos if str(ano) in a["Label"]), None)
    if not ano_cod:
        continue
    df = coletar_historico(marca["Value"], cod_modelo, ano_cod, refs)
    if not df.empty:
        veiculos_graficos.append((f"{marca_nome} - {modelo_api} ({ano})", df))

st.markdown("---")
st.subheader("🔍 Pesquisar veículo personalizado")
marca_input = st.selectbox("Marca", [m["Label"] for m in marcas])
marca_selecionada = next((m for m in marcas if m["Label"] == marca_input), None)

if marca_selecionada:
    modelos_data = obter_modelos(cod_ref, marca_selecionada["Value"])
    modelos_opcoes = [m["Label"] for m in modelos_data["Modelos"]]
    modelo_input = st.selectbox("Modelo", modelos_opcoes)
    modelo_cod = next((m["Value"] for m in modelos_data["Modelos"] if m["Label"] == modelo_input), None)

    anos = obter_anos(cod_ref, marca_selecionada["Value"], modelo_cod)
    ano_opcoes = [a["Label"] for a in anos]
    ano_input = st.selectbox("Ano", ano_opcoes)
    ano_cod = next((a["Value"] for a in anos if a["Label"] == ano_input), None)

    if st.button("Consultar Histórico"):
        df_personalizado = coletar_historico(marca_selecionada["Value"], modelo_cod, ano_cod, refs)
        if not df_personalizado.empty:
            veiculos_graficos.append((f"🔎 {marca_input} - {modelo_input} ({ano_input})", df_personalizado))

if veiculos_graficos:
    st.markdown("---")
    st.subheader("📊 Gráfico Comparativo – Últimos 24 meses")
    fig = px.line()
    for nome, df in veiculos_graficos:
        fig.add_scatter(x=df["Mês"], y=df["Preço (R$)"], mode="lines+markers", name=nome)
    fig.update_layout(xaxis_title="Mês", yaxis_title="Preço (R$)", height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Variação do último mês e acumulada")
    comparativo = []
    for nome, df in veiculos_graficos:
        if len(df) >= 2:
            variacao_mensal = df["Preço (R$)"].iloc[-1] - df["Preço (R$)"].iloc[-2]
            variacao_total = df["Preço (R$)"].iloc[-1] - df["Preço (R$)"].iloc[0]
            comparativo.append({"Veículo": nome, "Último Mês (R$)": variacao_mensal, "24 Meses (R$)": variacao_total})
    st.dataframe(pd.DataFrame(comparativo))
