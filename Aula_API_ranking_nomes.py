import requests
from pprint import pprint

decada = '2010'

url = "https://servicodados.ibge.gov.br/api/v2/censos/nomes/ranking"
params = {
    'decada': decada,
    'localidade': 53,
    'sexo': 'm'
}

resposta = requests.get(url, params=params)

print(resposta.request.url)

try:
    resposta.raise_for_status()
except requests.HTTPError as erro:
    print(f"\nImpossível fazer o request! Erro: {erro}.")
    resultado = None
else:
    resultado = resposta.json()

if resultado:
    pprint(resultado[0]['res'])  # Exibe a lista de nomes mais frequentes
