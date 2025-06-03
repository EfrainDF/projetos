import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Configuração do navegador (visível para debug)
service = Service()
options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

driver = webdriver.Chrome(service=service, options=options)

# URL com filtros de carros entre 30k e 62k e palavra-chave "impecável"
url = 'https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios/estado-df?ps=30000&pe=62000&q=impecavel&sf=1&f=p&me=160000'
print("🌐 Abrindo página...")
driver.get(url)

# Aguarda o carregamento completo (pode ajustar o tempo conforme sua internet)
time.sleep(15)

# Coleta os anúncios
anuncios = driver.find_elements(By.CLASS_NAME, 'olx-ad-card--horizontal')
print(f"🔎 Anúncios encontrados: {len(anuncios)}")

dados = []

for anuncio in anuncios:
    try:
        conteudo = anuncio.find_element(By.CLASS_NAME, 'olx-ad-card__content--horizontal')

        titulo = conteudo.find_element(By.CLASS_NAME, 'olx-ad-card__title-link')\
                         .find_element(By.TAG_NAME, 'h2').text

        preco = conteudo.find_element(By.CLASS_NAME, 'olx-ad-card__details-price--horizontal')\
                        .find_element(By.CLASS_NAME, 'olx-text--body-large').text

        link = conteudo.find_element(By.CLASS_NAME, 'olx-ad-card__title-link')\
                       .get_attribute('href')

        dados.append({'produto': titulo, 'preco': preco, 'link': link})

    except Exception as e:
        print(f"⚠️ Erro ao processar anúncio: {e}")
        continue

driver.quit()

# Exibe os dados no terminal
if not dados:
    print("⚠️ Nenhum dado coletado.")
else:
    print(f"\n✅ Total de anúncios coletados: {len(dados)}")
    for item in dados:
        print(f"\n🚗 {item['produto']}\n💰 {item['preco']}\n🔗 {item['link']}")
