import requests
from operator import itemgetter  # alternativa mais legível que lambda para ordenação


def requisitar_dados(url, parametros=None):
    """
    Faz uma requisição HTTP GET para a URL fornecida e retorna o resultado em JSON.
    Em caso de erro, imprime a mensagem e retorna None.
    """
    try:
        resposta = requests.get(url, params=parametros)
        resposta.raise_for_status()  # verifica se houve erro (ex: 404, 500)
        return resposta.json()      # converte a resposta em formato dicionário
    except requests.HTTPError as erro:
        print(f"[ERRO] Não foi possível obter os dados: {erro}")
        return None


def obter_estados_id_nome():
    """
    Retorna um dicionário onde:
    chave = ID do estado (int)
    valor = Nome do estado (str)
    """
    url_estados = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados'
    parametros = {'view': 'nivelado'}
    dados = requisitar_dados(url_estados, parametros)

    if not dados:
        return {}

    estados = {}
    for estado in dados:
        id_estado = int(estado['UF-id'])
        nome_estado = estado['UF-nome']
        estados[id_estado] = nome_estado

    return estados


def obter_dados_nome_por_estado(nome):
    """
    Retorna um dicionário com o ID do estado como chave e um novo dicionário como valor, contendo:
    - 'frequencia': total de pessoas com o nome
    - 'proporcao': número de pessoas por 100 mil habitantes
    """
    url_nome = f'https://servicodados.ibge.gov.br/api/v2/censos/nomes/{nome}'
    parametros = {'groupBy': 'UF'}
    dados = requisitar_dados(url_nome, parametros)

    if not dados:
        return {}

    estatisticas = {}
    for item in dados:
        id_estado = int(item['localidade'])
        valores = item['res'][0]
        estatisticas[id_estado] = {
            'frequencia': valores['frequencia'],
            'proporcao': valores['proporcao']
        }

    return estatisticas


def exibir_resultado(nome):
    """
    Mostra a frequência e proporção do nome informado por estado,
    ordenando da maior para a menor proporção.
    """
    estados = obter_estados_id_nome()
    dados_nome = obter_dados_nome_por_estado(nome)

    if not estados or not dados_nome:
        print("❌ Não foi possível exibir os resultados.")
        return

    print(f"\n🔍 Estatísticas do nome '{nome}' por estado brasileiro (ordem por proporção):\n")

    # Ordena pelo valor da proporção de forma decrescente
    estatisticas_ordenadas = sorted(
        dados_nome.items(),
        key=lambda item: item[1]['proporcao'],
        reverse=True
    )

    for id_estado, dados in estatisticas_ordenadas:
        if id_estado in estados:
            nome_estado = estados[id_estado]
            frequencia = dados['frequencia']
            proporcao = dados['proporcao']
            print(f"📍 {nome_estado}: {frequencia:,} pessoas chamadas '{nome}' "
                  f"(equivalente a {proporcao:.2f} por 100 mil habitantes)")


# Execução principal
if __name__ == '__main__':
    nome_digitado = 'rafael'  # pode ser substituído por input()
    exibir_resultado(nome_digitado)
