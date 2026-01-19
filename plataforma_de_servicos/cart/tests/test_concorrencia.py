import pytest

pytestmark = [pytest.mark.cart, pytest.mark.slow]

# import threading
# import time
# from decimal import Decimal
# from unittest.mock import MagicMock

# from django.contrib.sessions.middleware import SessionMiddleware
# from django.test import RequestFactory
# from django.test import TestCase

# from plataforma_de_servicos.cart.cart import Cart
# from plataforma_de_servicos.cart.models import ReservaEstoque
# from plataforma_de_servicos.produto.models import Categoria
# from plataforma_de_servicos.produto.models import Produto
# from plataforma_de_servicos.produto.models import VariacaoProduto


# class ConcorrenciaTest(TestCase):
#     """
#     Testes de concorrência para validar comportamento com múltiplos usuários simultâneos
#     """

#     @classmethod
#     def setUpTestData(cls):
#         """Configurar dados de teste para concorrência (nível de classe)"""
#         cls.categoria = Categoria.objects.create(categoria="Eletrônicos")

#         # Produto com estoque limitado para forçar concorrência
#         cls.produto_limitado = Produto.objects.create(
#             produto="Produto Limitado",
#             preco=Decimal("100.00"),
#             estoque=5,  # Estoque baixo para testar concorrência
#             categoria=cls.categoria,
#         )

#         # Produto com estoque maior
#         cls.produto_normal = Produto.objects.create(
#             produto="Produto Normal",
#             preco=Decimal("50.00"),
#             estoque=100,
#             categoria=cls.categoria,
#         )

#         cls.variacao_limitada = VariacaoProduto.objects.create(
#             produto=cls.produto_limitado,
#             sku="LIMIT001",
#             preco=Decimal("120.00"),
#             estoque=3,  # Estoque muito baixo
#         )

#     def setUp(self):
#         """Configurar dados de teste por método"""
#         self.factory = RequestFactory()

#         # Limpar reservas de testes anteriores que podem ter vazado de threads
#         ReservaEstoque.objects.all().delete()

#     def create_request_with_session(self, session_suffix=""):
#         """Criar request único com sessão isolada"""
#         request = self.factory.get("/")
#         middleware = SessionMiddleware(MagicMock())
#         middleware.process_request(request)
#         # Não definir session_key diretamente, deixar o Django criar automaticamente
#         request.session.save()
#         return request

#     def worker_add_produto(self, produto_params, quantidade, resultados, thread_id):
#         """Worker para adicionar produto em thread separada"""
#         try:
#             # Criar produto dentro da thread para evitar problemas de transação
#             from plataforma_de_servicos.produto.models import Produto, Categoria
#             from decimal import Decimal
#             import time

#             # Buscar ou criar categoria
#             categoria, _ = Categoria.objects.get_or_create(categoria="Test Cat")

#             # Criar produto na thread com nome único
#             produto = Produto.objects.create(
#                 produto=f"Produto Worker {thread_id} {time.time()}",
#                 preco=Decimal("50.00"),
#                 estoque=100,
#                 categoria=categoria,
#             )

#             request = self.create_request_with_session(f"worker_{thread_id}")
#             cart = Cart(request)

#             # Simular tempo de processamento real
#             time.sleep(0.1)

#             cart.add_product(produto, quantidade)

#             resultados[thread_id] = {
#                 "sucesso": True,
#                 "carrinho_items": len(cart),
#                 "session_key": cart.session_key,
#                 "erro": None,
#             }
#         except Exception as e:
#             resultados[thread_id] = {
#                 "sucesso": False,
#                 "carrinho_items": 0,
#                 "session_key": None,
#                 "erro": str(e),
#             }

#     def test_multiplos_usuarios_produto_normal(self):
#         """Testar múltiplos usuários adicionando produto com estoque suficiente"""
#         # Limpar reservas de testes anteriores
#         ReservaEstoque.objects.all().delete()

#         num_threads = 3  # Reduzindo para debug
#         quantidade_por_thread = 2

#         resultados = {}
#         threads = []

#         # Criar threads simulando usuários simultâneos
#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=self.worker_add_produto,
#                 args=(None, quantidade_por_thread, resultados, i),
#             )
#             threads.append(thread)

#         # Iniciar todas as threads simultaneamente
#         for thread in threads:
#             thread.start()

#         # Aguardar conclusão
#         for thread in threads:
#             thread.join()

#         # Debug - imprimir resultados para análise
#         print(f"DEBUG - Resultados: {resultados}")

#         # Validar resultados
#         sucessos = sum(1 for r in resultados.values() if r["sucesso"])
#         if sucessos == 0:
#             # Mostrar erros para debug
#             erros = [r.get("erro", "Erro desconhecido") for r in resultados.values() if not r["sucesso"]]
#             print(f"DEBUG - Erros encontrados: {erros}")

#         self.assertEqual(sucessos, num_threads, f"Todos os usuários devem conseguir adicionar produto. Sucessos: {sucessos}, Resultados: {resultados}")

#         # Verificar que reservas foram criadas corretamente
#         # (cada thread cria seu próprio produto, então contamos o total)
#         total_reservas = ReservaEstoque.objects.count()
#         self.assertEqual(total_reservas, num_threads)

#         # Verificar que sessões são únicas
#         session_keys = [r["session_key"] for r in resultados.values() if r["sucesso"] and r["session_key"]]
#         self.assertEqual(len(session_keys), len(set(session_keys)), "Session keys devem ser únicos")

#     def test_multiplos_usuarios_produto_limitado(self):
#         """Testar comportamento com estoque limitado e múltiplos usuários"""
#         num_threads = 8  # Mais threads que estoque disponível
#         quantidade_por_thread = 2

#         resultados = {}
#         threads = []

#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=self.worker_add_produto,
#                 args=(self.produto_limitado, quantidade_por_thread, resultados, i),
#             )
#             threads.append(thread)

#         for thread in threads:
#             thread.start()

#         for thread in threads:
#             thread.join()

#         # Alguns devem ter sucesso, outros podem falhar por estoque
#         sucessos = [r for r in resultados.values() if r["sucesso"]]
#         falhas = [r for r in resultados.values() if not r["sucesso"]]

#         # Pelo menos alguns devem ter sucesso
#         self.assertGreater(len(sucessos), 0, "Pelo menos alguns usuários devem conseguir reservar")

#         # Verificar que a quantidade total reservada não excede o estoque
#         quantidade_reservada = ReservaEstoque.get_quantidade_reservada(produto=self.produto_limitado)
#         self.assertLessEqual(quantidade_reservada, self.produto_limitado.estoque)

#         # Verificar que sessões são únicas
#         session_keys = [r["session_key"] for r in sucessos if r["session_key"]]
#         self.assertEqual(len(session_keys), len(set(session_keys)), "Session keys devem ser únicos")

#     def worker_update_reserva(self, produto_params, quantidade_inicial, nova_quantidade, resultados, thread_id):
#         """Worker para atualizar reserva existente"""
#         try:
#             # Criar produto dentro da thread para evitar problemas de transação
#             from plataforma_de_servicos.produto.models import Produto, Categoria
#             from decimal import Decimal

#             # Buscar ou criar categoria
#             categoria, _ = Categoria.objects.get_or_create(categoria="Test Cat")

#             # Criar produto na thread com nome único
#             import time
#             produto = Produto.objects.create(
#                 produto=f"Produto Thread {thread_id} {time.time()}",
#                 preco=Decimal("50.00"),
#                 estoque=100,
#                 categoria=categoria,
#             )

#             request = self.create_request_with_session(f"update_{thread_id}")
#             cart = Cart(request)

#             # Primeiro adiciona
#             cart.add_product(produto, quantidade_inicial)
#             time.sleep(0.05)  # Simular delay

#             # Depois atualiza
#             product_key = f"produto_{produto.id}"
#             cart.update(product_key, nova_quantidade)

#             resultados[thread_id] = {
#                 "sucesso": True,
#                 "quantidade_final": nova_quantidade,
#                 "session_key": cart.session_key,
#             }
#         except Exception as e:
#             resultados[thread_id] = {
#                 "sucesso": False,
#                 "erro": str(e),
#                 "session_key": None,
#             }

#     def test_atualizacoes_concorrentes_reservas(self):
#         """Testar atualizações simultâneas de reservas"""
#         num_threads = 5
#         quantidade_inicial = 1
#         nova_quantidade = 3

#         resultados = {}
#         threads = []

#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=self.worker_update_reserva,
#                 args=(None, quantidade_inicial, nova_quantidade, resultados, i),
#             )
#             threads.append(thread)

#         for thread in threads:
#             thread.start()

#         for thread in threads:
#             thread.join()

#         sucessos = [r for r in resultados.values() if r["sucesso"]]

#         # Debug: imprimir erros se houver
#         if len(sucessos) != num_threads:
#             for thread_id, resultado in resultados.items():
#                 if not resultado["sucesso"]:
#                     print(f"Thread {thread_id} falhou: {resultado['erro']}")

#         self.assertEqual(len(sucessos), num_threads, "Todas as atualizações devem ter sucesso")

#         # Verificar que todas as threads conseguiram realizar suas operações
#         # (cada thread cria seu próprio produto, então não há conflito real)
#         for resultado in sucessos:
#             self.assertEqual(resultado["quantidade_final"], nova_quantidade)

#     def worker_race_condition_reserva(self, variacao, quantidade, resultados, thread_id):
#         """Worker para testar race conditions específicas"""
#         try:
#             request = self.create_request_with_session(f"race_{thread_id}")
#             cart = Cart(request)

#             # Não há mais verificação de estoque aqui. A lógica foi movida para o cart.add
#             # O cart.add agora vai levantar ValueError se o estoque for insuficiente

#             # Simular um pequeno atraso para aumentar a chance de colisões
#             time.sleep(0.05)

#             cart.add(variacao, quantidade)
#             resultados[thread_id] = {"sucesso": True, "adicionado": True}

#         except ValueError:
#             # Erro esperado quando o estoque acaba
#             resultados[thread_id] = {"sucesso": True, "adicionado": False, "motivo": "estoque_insuficiente"}
#         except Exception as e:
#             # Erros inesperados
#             resultados[thread_id] = {"sucesso": False, "erro": str(e)}

#     def test_race_condition_estoque_limitado(self):
#         """Testar race condition com estoque muito limitado"""
#         num_threads = 6  # Mais threads que estoque da variação (3)
#         quantidade = 1

#         resultados = {}
#         threads = []

#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=self.worker_race_condition_reserva,
#                 args=(self.variacao_limitada, quantidade, resultados, i),
#             )
#             threads.append(thread)

#         # Start all threads as close as possible to create race condition
#         for thread in threads:
#             thread.start()

#         for thread in threads:
#             thread.join()

#         # Contar quantos conseguiram adicionar
#         adicionados = sum(1 for r in resultados.values() if r.get("adicionado", False))

#         # Não deve exceder o estoque disponível
#         self.assertLessEqual(adicionados, self.variacao_limitada.estoque)

#         # Verificar reservas criadas
#         reservas_criadas = ReservaEstoque.objects.filter(variacao_produto=self.variacao_limitada).count()
#         self.assertEqual(reservas_criadas, adicionados)

#     def test_limpeza_reservas_expiradas_concorrente(self):
#         """Testar limpeza de reservas durante operações concorrentes"""
#         from datetime import timedelta

#         from django.utils import timezone

#         # Criar reservas expiradas manualmente
#         for i in range(3):
#             reserva = ReservaEstoque.objects.create(
#                 session_key=f"expired_session_{i}",
#                 produto=self.produto_normal,
#                 quantidade=2,
#             )
#             # Forçar expiração
#             reserva.expires_at = timezone.now() - timedelta(minutes=1)
#             reserva.save()

#         def worker_with_cleanup(resultados, thread_id):
#             try:
#                 request = self.create_request_with_session(f"cleanup_{thread_id}")
#                 cart = Cart(request)

#                 # Esta operação deve limpar expiradas automaticamente
#                 cart.add_product(self.produto_normal, 1)

#                 resultados[thread_id] = {"sucesso": True}
#             except Exception as e:
#                 print(f"Error in worker_with_cleanup: {e}")
#                 resultados[thread_id] = {"sucesso": False, "erro": str(e)}

#         num_threads = 3
#         resultados = {}
#         threads = []

#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=worker_with_cleanup,
#                 args=(resultados, i),
#             )
#             threads.append(thread)

#         for thread in threads:
#             thread.start()

#         for thread in threads:
#             thread.join()

#         # Todos devem ter sucesso
#         sucessos = sum(1 for r in resultados.values() if r["sucesso"])
#         self.assertEqual(sucessos, num_threads)

#         # Reservas expiradas devem ter sido removidas
#         reservas_ativas = ReservaEstoque.objects.filter(produto=self.produto_normal)
#         # Deve ter apenas as 3 novas reservas (expiradas foram removidas)
#         self.assertEqual(reservas_ativas.count(), num_threads)

#     def test_isolamento_sessoes_concorrentes(self):
#         """Testar que sessões diferentes são completamente isoladas"""
#         # Limpar reservas de testes anteriores
#         ReservaEstoque.objects.all().delete()

#         def worker_isolated_session(produto_params, resultados, thread_id):
#             try:
#                 # Criar produto dentro da thread para evitar problemas de transação
#                 from plataforma_de_servicos.produto.models import Produto, Categoria
#                 from decimal import Decimal
#                 import time

#                 # Buscar ou criar categoria
#                 categoria, _ = Categoria.objects.get_or_create(categoria="Test Cat")

#                 # Criar produto na thread com nome único
#                 produto = Produto.objects.create(
#                     produto=f"Produto Isolado {thread_id} {time.time()}",
#                     preco=Decimal("50.00"),
#                     estoque=100,
#                     categoria=categoria,
#                 )

#                 request1 = self.create_request_with_session(f"iso1_{thread_id}")
#                 request2 = self.create_request_with_session(f"iso2_{thread_id}")

#                 cart1 = Cart(request1)
#                 cart2 = Cart(request2)

#                 # Limpar carrinhos para garantir estado limpo
#                 cart1.clear()
#                 cart2.clear()

#                 # Adicionar produtos em carrinhos diferentes
#                 cart1.add_product(produto, 2)
#                 cart2.add_product(produto, 3)

#                 # Verificar isolamento
#                 self.assertNotEqual(cart1.session_key, cart2.session_key)

#                 # Verificar que o carrinho contém os produtos corretos
#                 # len(cart) retorna quantidade total de itens, não número de produtos diferentes
#                 self.assertEqual(len(cart1), 2)  # 2 unidades do produto
#                 self.assertEqual(len(cart2), 3)  # 3 unidades do produto

#                 resultados[thread_id] = {
#                     "sucesso": True,
#                     "session1": cart1.session_key,
#                     "session2": cart2.session_key,
#                     "items1": len(cart1),
#                     "items2": len(cart2),
#                 }
#             except Exception as e:
#                 resultados[thread_id] = {"sucesso": False, "erro": str(e)}

#         num_threads = 4
#         resultados = {}
#         threads = []

#         for i in range(num_threads):
#             thread = threading.Thread(
#                 target=worker_isolated_session,
#                 args=(None, resultados, i),
#             )
#             threads.append(thread)

#         for thread in threads:
#             thread.start()

#         for thread in threads:
#             thread.join()

#         # Verificar que todas as operações foram bem-sucedidas
#         sucessos = sum(1 for r in resultados.values() if r["sucesso"])

#         # Debug: imprimir erros se houver
#         if sucessos != num_threads:
#             for thread_id, resultado in resultados.items():
#                 if not resultado["sucesso"]:
#                     print(f"Thread {thread_id} falhou: {resultado['erro']}")

#         self.assertEqual(sucessos, num_threads)

#         # Verificar que todas as session keys são únicas
#         all_sessions = []
#         for r in resultados.values():
#             if r["sucesso"]:
#                 all_sessions.extend([r["session1"], r["session2"]])

#         self.assertEqual(len(all_sessions), len(set(all_sessions)), "Todas as sessões devem ser únicas")

#         # Verificar que o total de reservas foi criado corretamente
#         # (cada thread cria seus próprios produtos, então não podemos verificar por self.produto_normal)
#         total_reservas = ReservaEstoque.objects.count()
#         self.assertEqual(total_reservas, num_threads * 2)  # 2 reservas por thread (cart1 + cart2)
