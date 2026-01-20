# #!/usr/bin/env python
# """
# Testes diretos para funcionalidades de modificadores de preço.
# """
# import pytest
# from decimal import Decimal
# from plataforma_de_servicos.produto.models import Produto, Atributo, ValorAtributo, VariacaoProduto
# from plataforma_de_servicos.produto.models.categoria_model import Categoria

# pytestmark = pytest.mark.django_db


# def setup_test_data():
#     """Cria dados básicos para teste"""
#     from django.db import transaction

#     # Limpar dados de teste anteriores usando transação para otimizar memória
#     with transaction.atomic():
#         # Usar bulk_delete para melhor performance e menor uso de memória
#         VariacaoProduto.objects.filter(produto__produto__contains="TestPricing").delete()
#         Produto.objects.filter(produto__contains="TestPricing").delete()
#         ValorAtributo.objects.filter(atributo__nome__contains="TestPricing").delete()
#         Atributo.objects.filter(nome__contains="TestPricing").delete()
#         Categoria.objects.filter(categoria__contains="TestPricing").delete()

#     # Criar categoria
#     categoria = Categoria.objects.create(categoria="TestPricing")

#     # Criar produto base
#     produto = Produto.objects.create(
#         produto="TestPricing Produto",
#         preco=Decimal('100.00'),
#         categoria=categoria,
#         ncm="12345678"
#     )

#     return categoria, produto


# def test_price_modifier_creation():
#     """Testa criação de modificadores de preço"""
#     print("🧪 Test 1: Criação de modificadores de preço")

#     atributo = Atributo.objects.create(nome="TestPricing Cor")

#     # Teste valor padrão
#     valor_padrao = ValorAtributo.objects.create(atributo=atributo, valor="Normal")
#     assert valor_padrao.preco_adicional == Decimal('0')
#     assert valor_padrao.percentual_adicional == Decimal('0')
#     print("✅ Valores padrão corretos")

#     # Teste com modificadores
#     valor_premium = ValorAtributo.objects.create(
#         atributo=atributo,
#         valor="Premium",
#         preco_adicional=Decimal('25.00'),
#         percentual_adicional=Decimal('10.00')
#     )
#     assert valor_premium.preco_adicional == Decimal('25.00')
#     assert valor_premium.percentual_adicional == Decimal('10.00')
#     print("✅ Modificadores criados corretamente")


# def test_price_calculation_basic():
#     """Testa cálculos básicos de preço"""
#     print("\n🧪 Test 2: Cálculos básicos de preço")

#     categoria, produto = setup_test_data()

#     # Atributo sem modificadores
#     cor_attr = Atributo.objects.create(nome="TestPricing CorBasic")
#     cor_normal = ValorAtributo.objects.create(
#         atributo=cor_attr,
#         valor="Azul"
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('100.00'),
#         estoque=10
#     )
#     variacao.valores.add(cor_normal)

#     preco_final = variacao.calcular_preco_final()
#     assert preco_final == Decimal('100.00')
#     print("✅ Cálculo sem modificadores: R$ 100,00")


# def test_price_calculation_fixed_modifier():
#     """Testa modificador fixo"""
#     print("\n🧪 Test 3: Modificador de preço fixo")

#     categoria, produto = setup_test_data()

#     cor_attr = Atributo.objects.create(nome="TestPricing CorFixed")
#     cor_premium = ValorAtributo.objects.create(
#         atributo=cor_attr,
#         valor="Ouro",
#         preco_adicional=Decimal('30.00')
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('100.00'),
#         estoque=10
#     )
#     variacao.valores.add(cor_premium)

#     preco_final = variacao.calcular_preco_final()
#     expected = Decimal('130.00')  # 100 + 30
#     assert preco_final == expected
#     print(f"✅ Cálculo com +R$ 30: R$ {preco_final} (esperado: R$ {expected})")


# def test_price_calculation_percentage_modifier():
#     """Testa modificador percentual"""
#     print("\n🧪 Test 4: Modificador percentual")

#     categoria, produto = setup_test_data()

#     tam_attr = Atributo.objects.create(nome="TestPricing TamPercent")
#     tam_gg = ValorAtributo.objects.create(
#         atributo=tam_attr,
#         valor="GG",
#         percentual_adicional=Decimal('25.00')  # 25%
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('80.00'),
#         estoque=10
#     )
#     variacao.valores.add(tam_gg)

#     preco_final = variacao.calcular_preco_final()
#     expected = Decimal('100.00')  # 80 + (80 * 0.25) = 80 + 20 = 100
#     assert preco_final == expected
#     print(f"✅ Cálculo com +25%: R$ {preco_final} (esperado: R$ {expected})")


# def test_price_calculation_both_modifiers():
#     """Testa ambos modificadores"""
#     print("\n🧪 Test 5: Ambos modificadores")

#     categoria, produto = setup_test_data()

#     mat_attr = Atributo.objects.create(nome="TestPricing Material")
#     mat_premium = ValorAtributo.objects.create(
#         atributo=mat_attr,
#         valor="Couro",
#         preco_adicional=Decimal('15.00'),
#         percentual_adicional=Decimal('20.00')  # 20%
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('50.00'),
#         estoque=10
#     )
#     variacao.valores.add(mat_premium)

#     preco_final = variacao.calcular_preco_final()
#     # 50 + 15 + (50 * 0.20) = 50 + 15 + 10 = 75
#     expected = Decimal('75.00')
#     assert preco_final == expected
#     print(f"✅ Cálculo misto: R$ {preco_final} (esperado: R$ {expected})")


# def test_price_calculation_multiple_attributes():
#     """Testa múltiplos atributos"""
#     print("\n🧪 Test 6: Múltiplos atributos")

#     categoria, produto = setup_test_data()

#     # Cor com preço fixo
#     cor_attr = Atributo.objects.create(nome="TestPricing CorMulti")
#     cor_especial = ValorAtributo.objects.create(
#         atributo=cor_attr,
#         valor="Platina",
#         preco_adicional=Decimal('40.00')
#     )

#     # Tamanho com percentual
#     tam_attr = Atributo.objects.create(nome="TestPricing TamMulti")
#     tam_xl = ValorAtributo.objects.create(
#         atributo=tam_attr,
#         valor="XL",
#         percentual_adicional=Decimal('30.00')  # 30%
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('100.00'),
#         estoque=10
#     )
#     variacao.valores.add(cor_especial, tam_xl)

#     preco_final = variacao.calcular_preco_final()
#     # 100 + 40 + (100 * 0.30) = 100 + 40 + 30 = 170
#     expected = Decimal('170.00')
#     assert preco_final == expected
#     print(f"✅ Cálculo múltiplos atributos: R$ {preco_final} (esperado: R$ {expected})")


# def test_price_formatting():
#     """Testa formatação de preços"""
#     print("\n🧪 Test 7: Formatação de preços")

#     categoria, produto = setup_test_data()

#     cor_attr = Atributo.objects.create(nome="TestPricing CorFormat")
#     cor_value = ValorAtributo.objects.create(
#         atributo=cor_attr,
#         valor="Test",
#         preco_adicional=Decimal('234.56')
#     )

#     variacao = VariacaoProduto.objects.create(
#         produto=produto,
#         preco=Decimal('1000.00'),
#         estoque=10
#     )
#     variacao.valores.add(cor_value)

#     # Teste método get_preco_display
#     preco_display = variacao.get_preco_display()
#     expected_display = "R$ 1.234,56"
#     assert preco_display == expected_display
#     print(f"✅ Formatação correta: {preco_display}")


# def test_edge_cases():
#     """Testa casos extremos"""
#     print("\n🧪 Test 8: Casos extremos")

#     categoria, produto = setup_test_data()

#     # Teste sem preço definido
#     produto_sem_preco = Produto.objects.create(
#         produto="TestPricing SemPreco",
#         preco=None,
#         categoria=categoria,
#         ncm="87654321"
#     )

#     cor_attr = Atributo.objects.create(nome="TestPricing CorEdge")
#     cor_value = ValorAtributo.objects.create(
#         atributo=cor_attr,
#         valor="Qualquer",
#         preco_adicional=Decimal('10.00')
#     )

#     variacao_sem_preco = VariacaoProduto.objects.create(
#         produto=produto_sem_preco,
#         preco=Decimal('0.00'),  # Também usar 0 aqui
#         estoque=10
#     )
#     variacao_sem_preco.valores.add(cor_value)

#     preco_final = variacao_sem_preco.calcular_preco_final()
#     # Como produto.preco=None e variacao.preco=0, preco_base=0, então if not preco_base retorna 0
#     expected_sem_preco = Decimal('0.00')
#     assert preco_final == expected_sem_preco
#     print(f"✅ Com produto sem preço: R$ {preco_final} (esperado: R$ {expected_sem_preco})")

#     # Teste fallback para preço do produto (usando preco=0 já que o campo não permite NULL)
#     # O método calcular_preco_final trata preco=0 como fallback para o produto
#     variacao_fallback = VariacaoProduto.objects.create(
#         produto=produto,  # Este tem preço R$ 100,00
#         preco=Decimal('0.00'),  # Preco zerado para simular fallback
#         estoque=10
#     )
#     variacao_fallback.valores.add(cor_value)

#     preco_fallback = variacao_fallback.calcular_preco_final()
#     expected_fallback = Decimal('110.00')  # 100 + 10
#     assert preco_fallback == expected_fallback
#     print(f"✅ Fallback para produto: R$ {preco_fallback} (esperado: R$ {expected_fallback})")


# def run_all_tests():
#     """Executa todos os testes"""
#     from django.db import transaction
#     import gc

#     print("🚀 Iniciando testes de modificadores de preço...")
#     print("=" * 60)

#     try:
#         # Executar testes em transação para controle de memória
#         with transaction.atomic():
#             test_price_modifier_creation()
#             gc.collect()  # Força limpeza de memória

#             test_price_calculation_basic()
#             gc.collect()

#             test_price_calculation_fixed_modifier()
#             gc.collect()

#             test_price_calculation_percentage_modifier()
#             gc.collect()

#             test_price_calculation_both_modifiers()
#             gc.collect()

#             test_price_calculation_multiple_attributes()
#             gc.collect()

#             test_price_formatting()
#             gc.collect()

#             test_edge_cases()
#             gc.collect()

#         print("\n" + "=" * 60)
#         print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
#         print("✅ Sistema de modificadores de preço está funcionando corretamente")

#     except AssertionError as e:
#         print(f"\n❌ TESTE FALHOU: {e}")
#         return False
#     except Exception as e:
#         print(f"\n💥 ERRO INESPERADO: {e}")
#         return False
#     finally:
#         # Limpeza final de memória
#         gc.collect()

#     return True


# if __name__ == "__main__":
#     import sys
#     success = run_all_tests()
#     sys.exit(0 if success else 1)
