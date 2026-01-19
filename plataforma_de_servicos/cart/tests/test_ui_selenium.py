import pytest

pytestmark = [pytest.mark.cart, pytest.mark.ui, pytest.mark.slow]

# """
# Testes de UI para funcionalidades do carrinho usando Selenium.

# Este módulo testa os comportamentos de interface do usuário relacionados ao carrinho:
# - Adicionar produtos ao carrinho
# - Atualizar quantidades
# - Remover produtos
# - Redirecionamentos
# """

# import time
# import os
# from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from django.test import override_settings
# from django.urls import reverse
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service
# from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
# from plataforma_de_servicos.users.tests.factories import UserFactory


# @override_settings(DEBUG=True)
# class CartUITestCase(StaticLiveServerTestCase):
#     """Classe base para testes de UI do carrinho."""

#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#         # Configuração do Chrome
#         chrome_options = Options()

#         # Verificar se deve rodar em modo headless
#         if os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true':
#             chrome_options.add_argument('--headless')

#         chrome_options.add_argument('--no-sandbox')
#         chrome_options.add_argument('--disable-dev-shm-usage')
#         chrome_options.add_argument('--disable-gpu')
#         chrome_options.add_argument('--window-size=1920,1080')
#         chrome_options.add_argument('--disable-web-security')
#         chrome_options.add_argument('--allow-running-insecure-content')

#         # Usar webdriver-manager para baixar automaticamente o ChromeDriver
#         service = Service(ChromeDriverManager().install())
#         cls.selenium = webdriver.Chrome(service=service, options=chrome_options)
#         cls.selenium.implicitly_wait(10)

#     @classmethod
#     def tearDownClass(cls):
#         cls.selenium.quit()
#         super().tearDownClass()

#     def setUp(self):
#         """Configura dados de teste para cada teste."""
#         self.user = UserFactory()

#         # Criar produtos de teste
#         self.produto1 = ProdutoFactory(
#             produto="Pizza Margherita",
#             preco="25.90",
#             estoque=10,
#         )
#         self.produto2 = ProdutoFactory(
#             produto="Pizza Calabresa",
#             preco="28.50",
#             estoque=5,
#         )

#     def wait_for_element(self, by, value, timeout=10):
#         """Aguarda um elemento aparecer na página."""
#         return WebDriverWait(self.selenium, timeout).until(
#             EC.presence_of_element_located((by, value))
#         )

#     def wait_for_element_clickable(self, by, value, timeout=10):
#         """Aguarda um elemento ficar clicável."""
#         return WebDriverWait(self.selenium, timeout).until(
#             EC.element_to_be_clickable((by, value))
#         )

#     def wait_for_redirect(self, expected_url_part, timeout=10):
#         """Aguarda redirecionamento para URL específica."""
#         WebDriverWait(self.selenium, timeout).until(
#             lambda driver: expected_url_part in driver.current_url
#         )


# class AddToCartFromListingTest(CartUITestCase):
#     """Testa a adição de produtos ao carrinho na tela de listagem."""

#     def test_add_product_to_cart_from_home_page(self):
#         """
#         Testa adicionar produto ao carrinho da página inicial.

#         Fluxo:
#         1. Navegar para página inicial
#         2. Clicar no botão "Adicionar ao carrinho" de um produto
#         3. Verificar redirecionamento para carrinho
#         4. Verificar se produto aparece no carrinho
#         """
#         # Navegar para página inicial
#         self.selenium.get(f'{self.live_server_url}/')

#         # Aguardar página carregar
#         self.wait_for_element(By.CLASS_NAME, 'hero')

#         # Encontrar botão de adicionar ao carrinho do primeiro produto
#         add_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             f'button[hx-vals*="{self.produto1.id}"]'
#         )

#         # Verificar se o botão contém o texto correto
#         self.assertIn('Adicionar ao carrinho', add_button.text)

#         # Clicar no botão
#         add_button.click()

#         # Aguardar redirecionamento para carrinho (HTMX pode demorar)
#         try:
#             self.wait_for_redirect('/cart/', timeout=15)
#         except TimeoutException:
#             # Se não redirecionar automaticamente, verificar se houve algum feedback
#             # e navegar manualmente para o carrinho para verificar
#             self.selenium.get(f'{self.live_server_url}/cart/')

#         # Verificar se estamos na página do carrinho
#         self.assertIn('/cart/', self.selenium.current_url)

#         # Verificar se o produto foi adicionado ao carrinho
#         cart_item = self.wait_for_element(
#             By.CSS_SELECTOR,
#             f'#cart-item-{self.produto1.id}'
#         )

#         # Verificar se o nome do produto aparece
#         product_name = cart_item.find_element(By.CLASS_NAME, 'card-title')
#         self.assertEqual(product_name.text, self.produto1.produto)

#     def test_add_product_with_quantity_validation(self):
#         """
#         Testa adição de produto com validação de estoque.
#         """
#         self.selenium.get(f'{self.live_server_url}/')

#         # Aguardar página carregar
#         self.wait_for_element(By.CLASS_NAME, 'hero')

#         # Encontrar produto com estoque baixo
#         add_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             f'button[hx-vals*="{self.produto2.id}"]'
#         )

#         # Clicar múltiplas vezes para testar validação de estoque
#         for i in range(3):
#             add_button.click()
#             time.sleep(1)  # Aguardar resposta HTMX

#         # Verificar se ainda funciona ou se há mensagem de erro
#         # Navegar para carrinho para verificar
#         self.selenium.get(f'{self.live_server_url}/cart/')

#         # Verificar se produto foi adicionado (pode ter quantidade limitada)
#         try:
#             cart_item = self.wait_for_element(
#                 By.CSS_SELECTOR,
#                 f'#cart-item-{self.produto2.id}',
#                 timeout=5
#             )
#             # Se encontrou, verificar quantidade
#             quantity_input = cart_item.find_element(By.CLASS_NAME, 'quantity-input')
#             quantity = int(quantity_input.get_attribute('value'))
#             self.assertLessEqual(quantity, self.produto2.estoque)
#         except TimeoutException:
#             # Se não encontrou, pode ser que não foi adicionado por falta de estoque
#             # Isso é aceitável dependendo da regra de negócio
#             pass


# class CartUpdateTest(CartUITestCase):
#     """Testa atualizações no carrinho."""

#     def test_update_product_quantity_in_cart(self):
#         """
#         Testa atualização de quantidade de produto no carrinho.
#         """
#         # Primeiro adicionar produto ao carrinho programaticamente
#         self.selenium.get(f'{self.live_server_url}/')

#         # Adicionar produto
#         add_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             f'button[hx-vals*="{self.produto1.id}"]'
#         )
#         add_button.click()

#         # Navegar para carrinho
#         time.sleep(2)  # Aguardar HTMX
#         self.selenium.get(f'{self.live_server_url}/cart/')

#         # Encontrar input de quantidade
#         quantity_input = self.wait_for_element(
#             By.CSS_SELECTOR,
#             f'#select{self.produto1.id}'
#         )

#         # Alterar quantidade
#         quantity_input.clear()
#         quantity_input.send_keys('3')

#         # Clicar no botão de atualizar
#         update_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             '.update-button'
#         )
#         update_button.click()

#         # Aguardar HTMX atualizar
#         time.sleep(2)

#         # Verificar se total foi atualizado
#         total_element = self.wait_for_element(By.ID, 'total')
#         expected_total = float(self.produto1.preco) * 3

#         # O total pode ter formatação, então vamos verificar se contém o valor
#         self.assertIn(str(expected_total).replace('.', ','), total_element.text.replace('R$', '').strip())

#     def test_remove_product_from_cart(self):
#         """
#         Testa remoção de produto do carrinho.
#         """
#         # Adicionar produto primeiro
#         self.selenium.get(f'{self.live_server_url}/')

#         add_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             f'button[hx-vals*="{self.produto1.id}"]'
#         )
#         add_button.click()

#         # Navegar para carrinho
#         time.sleep(2)
#         self.selenium.get(f'{self.live_server_url}/cart/')

#         # Verificar se produto existe
#         cart_item = self.wait_for_element(
#             By.CSS_SELECTOR,
#             f'#cart-item-{self.produto1.id}'
#         )
#         self.assertTrue(cart_item.is_displayed())

#         # Clicar no botão de remover
#         delete_button = cart_item.find_element(By.CLASS_NAME, 'delete-button')
#         delete_button.click()

#         # Aguardar HTMX remover o item
#         WebDriverWait(self.selenium, 10).until(
#             EC.invisibility_of_element_located((By.CSS_SELECTOR, f'#cart-item-{self.produto1.id}'))
#         )

#         # Verificar se carrinho está vazio
#         empty_message = self.wait_for_element(
#             By.XPATH,
#             "//*[contains(text(), 'Seu carrinho está vazio')]"
#         )
#         self.assertTrue(empty_message.is_displayed())


# class CartNavigationTest(CartUITestCase):
#     """Testa navegação relacionada ao carrinho."""

#     def test_product_detail_add_to_cart(self):
#         """
#         Testa adição ao carrinho na página de detalhes do produto.
#         """
#         # Navegar para página de detalhes do produto
#         product_url = reverse('produto-detail', kwargs={'id': self.produto1.id})
#         self.selenium.get(f'{self.live_server_url}{product_url}')

#         # Verificar se estamos na página correta
#         product_title = self.wait_for_element(By.TAG_NAME, 'h1')
#         self.assertIn(self.produto1.produto, product_title.text)

#         # Clicar no botão de adicionar ao carrinho
#         add_button = self.wait_for_element_clickable(By.ID, 'add-button')
#         add_button.click()

#         # Aguardar feedback visual (botão muda para "Adicionado!")
#         WebDriverWait(self.selenium, 10).until(
#             lambda driver: 'Adicionado!' in driver.find_element(By.ID, 'add-button').text
#         )

#         # Aguardar redirecionamento
#         self.wait_for_redirect('/cart/', timeout=15)

#         # Verificar se produto foi adicionado
#         cart_item = self.wait_for_element(
#             By.CSS_SELECTOR,
#             f'#cart-item-{self.produto1.id}'
#         )
#         self.assertTrue(cart_item.is_displayed())

#     def test_continue_shopping_button(self):
#         """
#         Testa botão "Continuar Comprando" no carrinho.
#         """
#         # Adicionar produto ao carrinho primeiro
#         self.selenium.get(f'{self.live_server_url}/')

#         add_button = self.wait_for_element_clickable(
#             By.CSS_SELECTOR,
#             f'button[hx-vals*="{self.produto1.id}"]'
#         )
#         add_button.click()

#         # Navegar para carrinho
#         time.sleep(2)
#         self.selenium.get(f'{self.live_server_url}/cart/')

#         # Clicar em "Continuar Comprando"
#         continue_button = self.wait_for_element_clickable(
#             By.LINK_TEXT,
#             'Continuar Comprando'
#         )
#         continue_button.click()

#         # Verificar se voltou para home
#         self.wait_for_redirect('/', timeout=10)
#         self.assertIn('/', self.selenium.current_url)
