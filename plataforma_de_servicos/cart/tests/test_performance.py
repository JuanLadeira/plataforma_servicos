# import statistics
# import time
# from decimal import Decimal
# from unittest.mock import MagicMock

# import pytest
# from django.contrib.sessions.middleware import SessionMiddleware
# from django.db import connection
# from django.test import RequestFactory
# from django.test import TestCase
# from django.test.utils import override_settings

# from plataforma_de_servicos.cart.cart import Cart
# from plataforma_de_servicos.cart.models import ReservaEstoque
# from plataforma_de_servicos.produto.models import Categoria
# from plataforma_de_servicos.produto.models import Produto
# from plataforma_de_servicos.produto.models import VariacaoProduto


# @pytest.mark.performance
# class PerformanceTest(TestCase):
#     """
#     Testes de performance para operações em massa e benchmarks
#     """

#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#         cls.categoria = Categoria.objects.create(categoria="Performance Test")

#         # Criar produtos em massa para teste
#         cls.produtos = []
#         for i in range(50):
#             produto = Produto.objects.create(
#                 produto=f"Produto Performance {i}",
#                 preco=Decimal(f"{10 + i}.99"),
#                 estoque=1000,
#                 categoria=cls.categoria,
#             )
#             cls.produtos.append(produto)

#         # Criar variações em massa
#         cls.variacoes = []
#         for i, produto in enumerate(cls.produtos[:10]):  # Apenas primeiros 10 para variações
#             variacao = VariacaoProduto.objects.create(
#                 produto=produto,
#                 sku=f"PERF{i:03d}",
#                 preco=produto.preco + Decimal("5.00"),
#                 estoque=500,
#             )
#             cls.variacoes.append(variacao)

#     def setUp(self):
#         """Setup para cada teste"""
#         self.factory = RequestFactory()
#         # Reset connection queries counter
#         connection.queries_log.clear()

#     def create_request_with_session(self, session_id="perf_session"):
#         """Criar request com sessão para testes de performance"""
#         request = self.factory.get("/")
#         middleware = SessionMiddleware(MagicMock())
#         middleware.process_request(request)
#         request.session.session_key = f"{session_id}_{time.time()}"
#         request.session.save()
#         return request

#     def measure_time(self, func, *args, **kwargs):
#         """Utilitário para medir tempo de execução"""
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         return result, end_time - start_time

#     def test_adicao_produtos_em_massa_performance(self):
#         """Testar performance de adição de muitos produtos"""
#         request = self.create_request_with_session()
#         cart = Cart(request)

#         num_produtos = 20
#         produtos_teste = self.produtos[:num_produtos]

#         # Benchmark de adição individual
#         tempos_adicao = []
#         queries_iniciais = len(connection.queries)

#         for produto in produtos_teste:
#             _, tempo = self.measure_time(cart.add_product, produto, 1)
#             tempos_adicao.append(tempo)

#         queries_finais = len(connection.queries)
#         total_queries = queries_finais - queries_iniciais

#         # Validações de performance
#         tempo_total = sum(tempos_adicao)
#         tempo_medio = statistics.mean(tempos_adicao)

#         # Assertions de performance
#         self.assertLess(tempo_total, 2.0, f"Adição de {num_produtos} produtos deve levar menos que 2s (levou {tempo_total:.3f}s)")
#         self.assertLess(tempo_medio, 0.1, f"Tempo médio por produto deve ser < 100ms (foi {tempo_medio*1000:.1f}ms)")

#         # Validar eficiência de queries
#         queries_por_produto = total_queries / num_produtos
#         self.assertLess(queries_por_produto, 10, f"Deve usar menos de 10 queries por produto (usado {queries_por_produto:.1f})")

#         # Validar que todos os produtos foram adicionados
#         self.assertEqual(len(cart), num_produtos)

#         print("📊 Performance Adição em Massa:")
#         print(f"   ⏱️  Tempo total: {tempo_total:.3f}s")
#         print(f"   📈 Tempo médio: {tempo_medio*1000:.1f}ms/produto")
#         print(f"   🗃️  Queries: {total_queries} ({queries_por_produto:.1f}/produto)")

#     def test_reservas_em_massa_performance(self):
#         """Testar criação de reservas em massa"""
#         num_sessoes = 30
#         produtos_por_sessao = 5

#         tempos_por_sessao = []
#         queries_iniciais = len(connection.queries)
#         start_total = time.time()

#         for i in range(num_sessoes):
#             request = self.create_request_with_session(f"mass_session_{i}")
#             cart = Cart(request)

#             start_sessao = time.time()

#             # Adicionar múltiplos produtos por sessão
#             for j in range(produtos_por_sessao):
#                 produto_idx = (i * produtos_por_sessao + j) % len(self.produtos)
#                 cart.add_product(self.produtos[produto_idx], 2)

#             end_sessao = time.time()
#             tempos_por_sessao.append(end_sessao - start_sessao)

#         end_total = time.time()
#         queries_finais = len(connection.queries)

#         # Métricas
#         tempo_total = end_total - start_total
#         tempo_medio_sessao = statistics.mean(tempos_por_sessao)
#         total_queries = queries_finais - queries_iniciais
#         total_reservas_criadas = num_sessoes * produtos_por_sessao

#         # Validações
#         self.assertLess(tempo_total, 5.0, f"Criação de {total_reservas_criadas} reservas deve levar < 5s")
#         self.assertLess(tempo_medio_sessao, 0.2, "Sessão média deve levar < 200ms")

#         # Verificar que reservas foram criadas
#         reservas_count = ReservaEstoque.objects.count()
#         self.assertEqual(reservas_count, total_reservas_criadas)

#         # Performance de queries
#         queries_per_reserva = total_queries / total_reservas_criadas
#         self.assertLess(queries_per_reserva, 8, "Máximo 8 queries por reserva")

#         print("📊 Performance Reservas em Massa:")
#         print(f"   🎯 Reservas criadas: {total_reservas_criadas}")
#         print(f"   ⏱️  Tempo total: {tempo_total:.3f}s")
#         print(f"   📈 Throughput: {total_reservas_criadas/tempo_total:.1f} reservas/s")
#         print(f"   🗃️  Queries: {total_queries} ({queries_per_reserva:.1f}/reserva)")

#     def test_limpeza_reservas_expiradas_performance(self):
#         """Testar performance de limpeza de reservas expiradas"""
#         from datetime import timedelta

#         from django.utils import timezone

#         num_reservas_expiradas = 100
#         num_reservas_validas = 50

#         # Criar reservas expiradas em massa
#         reservas_expiradas = []
#         for i in range(num_reservas_expiradas):
#             reserva = ReservaEstoque(
#                 session_key=f"expired_{i}",
#                 produto=self.produtos[i % len(self.produtos)],
#                 quantidade=1,
#                 expires_at=timezone.now() - timedelta(minutes=i+1),
#             )
#             reservas_expiradas.append(reserva)

#         # Bulk create para eficiência
#         ReservaEstoque.objects.bulk_create(reservas_expiradas)

#         # Criar reservas válidas
#         reservas_validas = []
#         for i in range(num_reservas_validas):
#             reserva = ReservaEstoque(
#                 session_key=f"valid_{i}",
#                 produto=self.produtos[i % len(self.produtos)],
#                 quantidade=1,
#             )
#             reservas_validas.append(reserva)

#         ReservaEstoque.objects.bulk_create(reservas_validas)

#         # Validar setup
#         total_antes = ReservaEstoque.objects.count()
#         self.assertEqual(total_antes, num_reservas_expiradas + num_reservas_validas)

#         # Medir performance da limpeza
#         queries_iniciais = len(connection.queries)
#         start_time = time.time()

#         count, _ = ReservaEstoque.limpar_expiradas()

#         end_time = time.time()
#         queries_finais = len(connection.queries)

#         tempo_limpeza = end_time - start_time
#         queries_limpeza = queries_finais - queries_iniciais

#         # Validações
#         self.assertEqual(count, num_reservas_expiradas)
#         self.assertEqual(ReservaEstoque.objects.count(), num_reservas_validas)

#         # Performance
#         self.assertLess(tempo_limpeza, 1.0, f"Limpeza de {num_reservas_expiradas} reservas deve levar < 1s")
#         self.assertLess(queries_limpeza, 5, f"Limpeza deve usar poucas queries (usou {queries_limpeza})")

#         print("📊 Performance Limpeza Reservas:")
#         print(f"   🗑️  Removidas: {count}")
#         print(f"   ⏱️  Tempo: {tempo_limpeza:.3f}s")
#         print(f"   🗃️  Queries: {queries_limpeza}")

#     def test_calculo_quantidade_reservada_performance(self):
#         """Testar performance de cálculo de quantidades reservadas"""
#         produto_teste = self.produtos[0]
#         variacao_teste = self.variacoes[0] if self.variacoes else None

#         num_reservas = 200

#         # Criar reservas para produto
#         reservas_produto = []
#         for i in range(num_reservas // 2):
#             reserva = ReservaEstoque(
#                 session_key=f"calc_session_p_{i}",
#                 produto=produto_teste,
#                 quantidade=i % 5 + 1,
#             )
#             reservas_produto.append(reserva)

#         # Criar reservas para variação (se disponível)
#         reservas_variacao = []
#         if variacao_teste:
#             for i in range(num_reservas // 2):
#                 reserva = ReservaEstoque(
#                     session_key=f"calc_session_v_{i}",
#                     variacao_produto=variacao_teste,
#                     quantidade=i % 3 + 1,
#                 )
#                 reservas_variacao.append(reserva)

#         # Bulk create
#         ReservaEstoque.objects.bulk_create(reservas_produto + reservas_variacao)

#         # Benchmark cálculo para produto
#         queries_iniciais = len(connection.queries)
#         start_time = time.time()

#         quantidade_produto = ReservaEstoque.get_quantidade_reservada(produto=produto_teste)

#         end_time = time.time()
#         queries_finais = len(connection.queries)

#         tempo_calculo_produto = end_time - start_time
#         queries_produto = queries_finais - queries_iniciais

#         # Benchmark cálculo para variação
#         if variacao_teste:
#             queries_iniciais = len(connection.queries)
#             start_time = time.time()

#             quantidade_variacao = ReservaEstoque.get_quantidade_reservada(variacao_produto=variacao_teste)

#             end_time = time.time()
#             queries_finais = len(connection.queries)

#             tempo_calculo_variacao = end_time - start_time
#             queries_variacao = queries_finais - queries_iniciais

#         # Validações de performance
#         self.assertLess(tempo_calculo_produto, 0.1, "Cálculo para produto deve ser < 100ms")
#         self.assertLess(queries_produto, 5, f"Cálculo produto deve usar poucas queries (usou {queries_produto})")
#         self.assertGreater(quantidade_produto, 0, "Deve encontrar reservas para produto")

#         if variacao_teste:
#             self.assertLess(tempo_calculo_variacao, 0.1, "Cálculo para variação deve ser < 100ms")
#             self.assertLess(queries_variacao, 5, "Cálculo variação deve usar poucas queries")
#             self.assertGreater(quantidade_variacao, 0, "Deve encontrar reservas para variação")

#         print("📊 Performance Cálculo Quantidades:")
#         print(f"   📦 Reservas criadas: {num_reservas}")
#         print(f"   🔢 Quantidade produto: {quantidade_produto} ({tempo_calculo_produto*1000:.1f}ms, {queries_produto} queries)")
#         if variacao_teste:
#             print(f"   🎯 Quantidade variação: {quantidade_variacao} ({tempo_calculo_variacao*1000:.1f}ms, {queries_variacao} queries)")

#     def test_stress_operacoes_carrinho(self):
#         """Teste de stress para operações intensivas do carrinho"""
#         request = self.create_request_with_session()
#         cart = Cart(request)

#         num_operacoes = 100
#         operacoes_realizadas = {
#             "add": 0,
#             "update": 0,
#             "delete": 0,
#         }

#         tempos = {
#             "add": [],
#             "update": [],
#             "delete": [],
#         }

#         queries_iniciais = len(connection.queries)
#         start_total = time.time()

#         # Fase 1: Adicionar produtos
#         for i in range(num_operacoes // 3):
#             produto = self.produtos[i % len(self.produtos)]
#             _, tempo = self.measure_time(cart.add_product, produto, 1)
#             tempos["add"].append(tempo)
#             operacoes_realizadas["add"] += 1

#         # Fase 2: Atualizar quantidades
#         items_carrinho = list(cart.cart.keys())
#         for i in range(min(len(items_carrinho), num_operacoes // 3)):
#             key = items_carrinho[i]
#             nova_quantidade = (i % 5) + 1
#             _, tempo = self.measure_time(cart.update, key, nova_quantidade)
#             tempos["update"].append(tempo)
#             operacoes_realizadas["update"] += 1

#         # Fase 3: Remover alguns itens
#         items_carrinho = list(cart.cart.keys())
#         for i in range(min(len(items_carrinho) // 2, num_operacoes // 3)):
#             key = items_carrinho[i * 2]  # Remove itens alternados
#             _, tempo = self.measure_time(cart.delete, key)
#             tempos["delete"].append(tempo)
#             operacoes_realizadas["delete"] += 1

#         end_total = time.time()
#         queries_finais = len(connection.queries)

#         # Métricas finais
#         tempo_total = end_total - start_total
#         total_operacoes = sum(operacoes_realizadas.values())
#         total_queries = queries_finais - queries_iniciais

#         # Cálculos de performance
#         throughput = total_operacoes / tempo_total
#         tempo_medio_add = statistics.mean(tempos["add"]) if tempos["add"] else 0
#         tempo_medio_update = statistics.mean(tempos["update"]) if tempos["update"] else 0
#         tempo_medio_delete = statistics.mean(tempos["delete"]) if tempos["delete"] else 0

#         # Validações
#         self.assertLess(tempo_total, 10.0, f"Stress test deve completar em < 10s (levou {tempo_total:.3f}s)")
#         self.assertGreater(throughput, 10, f"Throughput deve ser > 10 ops/s (foi {throughput:.1f})")
#         self.assertLess(tempo_medio_add, 0.1, "Add médio deve ser < 100ms")
#         self.assertLess(tempo_medio_update, 0.1, "Update médio deve ser < 100ms")
#         self.assertLess(tempo_medio_delete, 0.1, "Delete médio deve ser < 100ms")

#         # Verificar estado final do carrinho
#         self.assertGreater(len(cart), 0, "Carrinho deve ter itens após stress test")

#         print("📊 Stress Test Carrinho:")
#         print(f"   🔄 Total operações: {total_operacoes}")
#         print(f"   ⚡ Throughput: {throughput:.1f} ops/s")
#         print(f"   ➕ Add: {operacoes_realizadas['add']} ({tempo_medio_add*1000:.1f}ms médio)")
#         print(f"   ✏️  Update: {operacoes_realizadas['update']} ({tempo_medio_update*1000:.1f}ms médio)")
#         print(f"   🗑️  Delete: {operacoes_realizadas['delete']} ({tempo_medio_delete*1000:.1f}ms médio)")
#         print(f"   🗃️  Total queries: {total_queries}")
#         print(f"   🛒 Itens finais: {len(cart)}")

#     @override_settings(DEBUG=True)  # Para capturar queries
#     def test_memory_usage_carrinho_grande(self):
#         """Testar uso de memória com carrinho muito grande"""
#         import os

#         import psutil

#         process = psutil.Process(os.getpid())
#         memoria_inicial = process.memory_info().rss / 1024 / 1024  # MB

#         request = self.create_request_with_session()
#         cart = Cart(request)

#         # Adicionar muitos produtos únicos
#         num_produtos_grande = 500
#         for i in range(min(num_produtos_grande, len(self.produtos))):
#             produto = self.produtos[i]
#             cart.add_product(produto, i % 10 + 1)

#         memoria_final = process.memory_info().rss / 1024 / 1024  # MB
#         memoria_usada = memoria_final - memoria_inicial

#         # Validações
#         self.assertEqual(len(cart), min(num_produtos_grande, len(self.produtos)))
#         self.assertLess(memoria_usada, 100, f"Uso de memória deve ser < 100MB (usou {memoria_usada:.1f}MB)")

#         # Testar serialização para sessão
#         start_time = time.time()
#         cart._save_to_session()
#         tempo_serializacao = time.time() - start_time

#         self.assertLess(tempo_serializacao, 1.0, f"Serialização deve ser < 1s (foi {tempo_serializacao:.3f}s)")

#         print("📊 Teste Memória Carrinho Grande:")
#         print(f"   📦 Produtos no carrinho: {len(cart)}")
#         print(f"   💾 Memória usada: {memoria_usada:.1f}MB")
#         print(f"   ⏱️  Serialização: {tempo_serializacao:.3f}s")

#     def tearDown(self):
#         """Cleanup após cada teste"""
#         # Limpar reservas criadas durante os testes
#         ReservaEstoque.objects.all().delete()

#     @classmethod
#     def tearDownClass(cls):
#         """Cleanup final"""
#         # Remover dados de teste
#         ReservaEstoque.objects.all().delete()
#         VariacaoProduto.objects.filter(produto__categoria=cls.categoria).delete()
#         Produto.objects.filter(categoria=cls.categoria).delete()
#         cls.categoria.delete()
#         super().tearDownClass()
