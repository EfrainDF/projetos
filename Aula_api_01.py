import requests
from pprint import pprint

def pegar_ids_estados():
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    params = {
        'view': 'nivelado',
    }
    dados_estados = fazer_request(url, params=params)
    dict_estados = {}
    for dados in dados_estados:
        id_estado = dados['UF-id']
        nome_estado = dados['UF-nome']
        dict_estados[id_estado] = nome_estado
    return dict_estados

def fazer_request(url, params=None):
    resposta = requests.get(url, params=params)
    print(resposta.request.url)
    try:
        resposta.raise_for_status()
    except requests.HTTPError as erro:
        print(f"\nErro no request: {erro}.")
        return None
    else:
        return resposta.json()

def main():
    dict_estados = pegar_ids_estados()
    pprint(dict_estados)

if __name__ == '__main__':
    main()
