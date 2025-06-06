import os
import requests
import dotenv
import pandas as pd
from tqdm import tqdm

# Carrega a chave da API
dotenv.load_dotenv()
TOKEN = os.getenv("CHAVE_API_FIPE")

HEADERS = {
    "accept": "application/json",
    "X-Subscription-Token": TOKEN
}
URL_BASE = "https://fipe.parallelum.com.br/api/v2"
NUM_MESES = 12

# Marcas a analisar
PRIORITARIAS = ["Nissan"]

# Funções auxiliares
def requisitar_dados(endpoint, parametros=None):
    try:
        resposta = requests.get(f"{URL_BASE}/{endpoint}", headers=HEADERS, params=parametros)
        resposta.raise_for_status()
        return resposta.json()
    except requests.HTTPError:
        return None

def obter_codigo_por_nome(lista, chave_nome):
    if not lista:
        return None
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

def obter_historico(marca, modelo, ano):
    cod_marca = obter_codigo_por_nome(requisitar_dados("cars/brands"), marca)
    if not cod_marca:
        return None

    cod_modelo = obter_codigo_por_nome(requisitar_dados(f"cars/brands/{cod_marca}/models"), modelo)
    if not cod_modelo:
        return None

    anos = requisitar_dados(f"cars/brands/{cod_marca}/models/{cod_modelo}/years")
    if not anos:
        return None

    cod_ano = obter_codigo_por_nome(anos, str(ano))
    if not cod_ano:
        return None

    referencias = requisitar_dados("references")[:NUM_MESES + 1]
    historico = []
    for ref in referencias:
        preco_str = consultar_preco_por_referencia(cod_marca, cod_modelo, cod_ano, ref["code"])
        if preco_str:
            try:
                preco = float(preco_str.replace("R$", "").replace(".", "").replace(",", "."))
                historico.append(preco)
            except:
                continue
    return historico if len(historico) >= 2 else None

# Execução principal
if __name__ == "__main__":
    ano_input = input("Digite o ano do veículo para varredura (ex: 2012): ").strip()
    try:
        ano_filtrado = int(ano_input)
        if not (2006 <= ano_filtrado <= 2016):
            raise ValueError("Ano fora do intervalo permitido.")
    except ValueError:
        print("Ano inválido. Informe um ano entre 2006 e 2016.")
        exit()

    marcas = requisitar_dados("cars/brands")
    marcas = [m for m in marcas if any(p.lower() in m['name'].lower() for p in PRIORITARIAS)]

    resultados = []

    for marca in tqdm(marcas, desc="🔍 Processando marcas"):
        modelos = requisitar_dados(f"cars/brands/{marca['code']}/models")
        if not modelos:
            continue
        for modelo in tqdm(modelos, leave=False, desc=f"Modelos {marca['name']}"):
            historico = obter_historico(marca['name'], modelo['name'], ano_filtrado)
            if historico and len(historico) >= 2:
                preco_inicial = historico[-1]
                preco_final = historico[0]
                variacao = preco_final - preco_inicial
                percentual = (variacao / preco_inicial) * 100

                resultados.append({
                    "Marca": marca['name'],
                    "Modelo": modelo['name'],
                    "Ano": ano_filtrado,
                    "Preço Inicial": round(preco_inicial, 2),
                    "Preço Final": round(preco_final, 2),
                    "Referência Inicial": f"{NUM_MESES} meses atrás",
                    "Referência Final": "Atual",
                    "Variação R$": round(variacao, 2),
                    "Variação %": round(percentual, 2)
                })

    df_resultado = pd.DataFrame(resultados)

    if not df_resultado.empty:
        df_resultado.to_csv("fipe_variacao_completa.csv", sep=";", index=False, encoding="utf-8-sig")
        print("\n✅ Arquivo 'fipe_variacao_completa.csv' salvo com sucesso!")
    else:
        print("\n⚠️ Nenhum veículo com histórico suficiente foi encontrado.")
